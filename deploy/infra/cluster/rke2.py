import shlex
from dataclasses import dataclass
from typing import List, Sequence

import pulumi
from pulumi import Config, ResourceOptions
from pulumi_command import local, remote


config = Config()


@dataclass
class Rke2Automation:
    control_ready: remote.Command
    worker_joins: List[remote.Command]
    cluster_ready: remote.Command
    kubeconfig: local.Command
    kubeconfig_path: str
    kubeconfig_server: pulumi.Input[str]


def _q(value: str) -> str:
    return shlex.quote(value)


def _bastion_connection(bastion_instance):
    return remote.ConnectionArgs(
        host=bastion_instance.bastion_floating_ip_association.floating_ip,
        user=config.require("sshUser"),
        private_key=bastion_instance.private_key.private_key_pem,
    )


def _build_control_ready_command(control_ip: str, kubeconfig_server: str) -> str:
    ssh_user = config.require("sshUser")
    return f"""bash <<'SCRIPT'
set -euo pipefail

SSH_USER={_q(ssh_user)}
CONTROL_IP={_q(control_ip)}
KUBECONFIG_SERVER={_q(kubeconfig_server)}
SSH_KEY="/home/${{SSH_USER}}/.ssh/key.pem"
SSH_OPTS="-i ${{SSH_KEY}} -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/home/${{SSH_USER}}/.ssh/known_hosts -o ConnectTimeout=10"

wait_for_bastion_key() {{
  for i in $(seq 1 60); do
    [ -s "${{SSH_KEY}}" ] && return 0
    echo "Waiting for bastion SSH key..."
    sleep 5
  done
  echo "Timed out waiting for ${{SSH_KEY}}" >&2
  return 1
}}

ssh_control() {{
  ssh ${{SSH_OPTS}} "${{SSH_USER}}@${{CONTROL_IP}}" "$@"
}}

wait_for_control_ssh() {{
  for i in $(seq 1 90); do
    if ssh_control "true" >/dev/null 2>&1; then
      return 0
    fi
    echo "Waiting for control node SSH..."
    sleep 10
  done
  echo "Timed out waiting for control node SSH at ${{CONTROL_IP}}" >&2
  return 1
}}

wait_for_rke2_server() {{
  for i in $(seq 1 120); do
    if ssh_control "sudo test -s /var/lib/rancher/rke2/server/node-token && sudo test -s /etc/rancher/rke2/rke2.yaml && sudo systemctl is-active --quiet rke2-server.service"; then
      return 0
    fi
    echo "Waiting for RKE2 server token, kubeconfig and service..."
    sleep 10
  done
  echo "Timed out waiting for RKE2 server readiness" >&2
  ssh_control "sudo journalctl -u rke2-server.service --no-pager -n 120" || true
  return 1
}}

wait_for_bastion_key
wait_for_control_ssh
wait_for_rke2_server

ssh_control "sudo cat /etc/rancher/rke2/rke2.yaml" \
  | sed -E "s#server: https://[^[:space:]]+:6443#server: ${{KUBECONFIG_SERVER}}#" \
  > "/home/${{SSH_USER}}/kubeconfig.yaml"
chmod 600 "/home/${{SSH_USER}}/kubeconfig.yaml"
SCRIPT
"""


def _build_join_worker_command(control_ip: str, worker_ip: str) -> str:
    ssh_user = config.require("sshUser")
    server_url = f"https://{control_ip}:9345"

    return f"""bash <<'SCRIPT'
set -euo pipefail

SSH_USER={_q(ssh_user)}
CONTROL_IP={_q(control_ip)}
WORKER_IP={_q(worker_ip)}
SERVER_URL={_q(server_url)}
SSH_KEY="/home/${{SSH_USER}}/.ssh/key.pem"
SSH_OPTS="-i ${{SSH_KEY}} -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/home/${{SSH_USER}}/.ssh/known_hosts -o ConnectTimeout=10"

ssh_control() {{
  ssh ${{SSH_OPTS}} "${{SSH_USER}}@${{CONTROL_IP}}" "$@"
}}

ssh_worker() {{
  ssh ${{SSH_OPTS}} "${{SSH_USER}}@${{WORKER_IP}}" "$@"
}}

wait_for_worker_ssh() {{
  for i in $(seq 1 90); do
    if ssh_worker "true" >/dev/null 2>&1; then
      return 0
    fi
    echo "Waiting for worker node SSH at ${{WORKER_IP}}..."
    sleep 10
  done
  echo "Timed out waiting for worker node SSH at ${{WORKER_IP}}" >&2
  return 1
}}

wait_for_token() {{
  for i in $(seq 1 120); do
    if ssh_control "sudo test -s /var/lib/rancher/rke2/server/node-token"; then
      return 0
    fi
    echo "Waiting for RKE2 node token..."
    sleep 10
  done
  echo "Timed out waiting for RKE2 node token" >&2
  return 1
}}

wait_for_token
TOKEN="$(ssh_control "sudo cat /var/lib/rancher/rke2/server/node-token")"
wait_for_worker_ssh
ssh_worker "sudo cloud-init status --wait"
ssh_worker "sudo mkdir -p /etc/rancher/rke2"

{{
  printf 'server: %s\\n' "${{SERVER_URL}}"
  printf 'token: %s\\n' "${{TOKEN}}"
  cat <<'CONFIG'
kubelet-arg:
  - max-pods=500
  - container-log-max-size=50Mi
  - container-log-max-files=3
CONFIG
}} | ssh_worker "sudo tee /etc/rancher/rke2/config.yaml >/dev/null"

ssh_worker "sudo bash -s" <<'WORKER_SCRIPT'
set -euo pipefail

if [ ! -x /usr/local/bin/rke2 ]; then
  curl -sfL https://get.rke2.io | INSTALL_RKE2_TYPE="agent" sh -
fi

systemctl enable rke2-agent.service
systemctl restart rke2-agent.service

for i in $(seq 1 90); do
  if systemctl is-active --quiet rke2-agent.service; then
    exit 0
  fi
  echo "Waiting for rke2-agent.service..."
  sleep 10
done

echo "Timed out waiting for rke2-agent.service" >&2
journalctl -u rke2-agent.service --no-pager -n 120 || true
exit 1
WORKER_SCRIPT
SCRIPT
"""


def _build_cluster_ready_command(control_ip: str, expected_nodes: int) -> str:
    ssh_user = config.require("sshUser")
    return f"""bash <<'SCRIPT'
set -euo pipefail

SSH_USER={_q(ssh_user)}
CONTROL_IP={_q(control_ip)}
EXPECTED_NODES={expected_nodes}
SSH_KEY="/home/${{SSH_USER}}/.ssh/key.pem"
SSH_OPTS="-i ${{SSH_KEY}} -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/home/${{SSH_USER}}/.ssh/known_hosts -o ConnectTimeout=10"

ssh_control() {{
  ssh ${{SSH_OPTS}} "${{SSH_USER}}@${{CONTROL_IP}}" "$@"
}}

for i in $(seq 1 120); do
  ready_count="$(
    ssh_control "sudo /var/lib/rancher/rke2/bin/kubectl --kubeconfig /etc/rancher/rke2/rke2.yaml get nodes --no-headers" \
      | awk '$2 ~ /Ready/ {{ count++ }} END {{ print count + 0 }}'
  )"

  if [ "${{ready_count}}" -ge "${{EXPECTED_NODES}}" ]; then
    ssh_control "sudo /var/lib/rancher/rke2/bin/kubectl --kubeconfig /etc/rancher/rke2/rke2.yaml get nodes -o wide"
    exit 0
  fi

  echo "Waiting for ${{EXPECTED_NODES}} Kubernetes nodes to become Ready; currently ${{ready_count}}."
  sleep 15
done

echo "Timed out waiting for Kubernetes nodes to become Ready" >&2
ssh_control "sudo /var/lib/rancher/rke2/bin/kubectl --kubeconfig /etc/rancher/rke2/rke2.yaml get nodes -o wide" || true
exit 1
SCRIPT
"""


def _build_fetch_kubeconfig_command(bastion_ip: str, kubeconfig_path: str) -> str:
    ssh_user = config.require("sshUser")
    return f"""set -euo pipefail

SSH_USER={_q(ssh_user)}
BASTION_IP={_q(bastion_ip)}
KUBECONFIG_PATH={_q(kubeconfig_path)}
SSH_KEY="rke2-generated_key.pem"
SSH_OPTS="-i ${{SSH_KEY}} -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=.pulumi-known-hosts -o ConnectTimeout=10"

for i in $(seq 1 60); do
  if ssh ${{SSH_OPTS}} "${{SSH_USER}}@${{BASTION_IP}}" "test -s /home/${{SSH_USER}}/kubeconfig.yaml"; then
    break
  fi
  if [ "$i" -eq 60 ]; then
    echo "Timed out waiting for kubeconfig on bastion" >&2
    exit 1
  fi
  echo "Waiting for kubeconfig on bastion..."
  sleep 5
done

tmp="$(mktemp "${{KUBECONFIG_PATH}}.XXXXXX")"
scp ${{SSH_OPTS}} "${{SSH_USER}}@${{BASTION_IP}}:/home/${{SSH_USER}}/kubeconfig.yaml" "${{tmp}}"
chmod 600 "${{tmp}}"
mv "${{tmp}}" "${{KUBECONFIG_PATH}}"
"""


def configure(
    bastion_instance,
    control_nodes: Sequence,
    worker_nodes: Sequence,
    kubeconfig_server: pulumi.Input[str],
) -> Rke2Automation:
    if not control_nodes:
        raise ValueError("At least one control node is required for RKE2 automation")

    kubeconfig_path = config.get("kubeconfigPath") or "kubeconfig.yaml"
    control_node = control_nodes[0]

    control_ready = remote.Command(
        "rke2-control-ready",
        connection=_bastion_connection(bastion_instance),
        create=pulumi.Output.all(control_node.access_ip_v4, kubeconfig_server).apply(
            lambda args: _build_control_ready_command(args[0], args[1])
        ),
        update=pulumi.Output.all(control_node.access_ip_v4, kubeconfig_server).apply(
            lambda args: _build_control_ready_command(args[0], args[1])
        ),
        triggers=[control_node.access_ip_v4, kubeconfig_server],
        opts=ResourceOptions(
            depends_on=[
                bastion_instance.bastion_instance,
                bastion_instance.bastion_floating_ip_association,
                control_node,
            ]
        ),
    )

    worker_joins = []
    for index, worker_node in enumerate(worker_nodes):
        join_command = pulumi.Output.all(
            control_node.access_ip_v4, worker_node.access_ip_v4
        ).apply(lambda args: _build_join_worker_command(args[0], args[1]))

        worker_joins.append(
            remote.Command(
                f"rke2-worker-{index}-join",
                connection=_bastion_connection(bastion_instance),
                create=join_command,
                update=join_command,
                triggers=[control_node.access_ip_v4, worker_node.access_ip_v4],
                opts=ResourceOptions(depends_on=[control_ready, worker_node]),
            )
        )

    cluster_ready = remote.Command(
        "rke2-cluster-ready",
        connection=_bastion_connection(bastion_instance),
        create=control_node.access_ip_v4.apply(
            lambda ip: _build_cluster_ready_command(
                ip, 1 + len(worker_nodes)
            )
        ),
        update=control_node.access_ip_v4.apply(
            lambda ip: _build_cluster_ready_command(
                ip, 1 + len(worker_nodes)
            )
        ),
        triggers=[control_node.access_ip_v4, len(control_nodes), len(worker_nodes)],
        opts=ResourceOptions(depends_on=[control_ready, *worker_joins]),
    )

    kubeconfig = local.Command(
        "rke2-fetch-kubeconfig",
        create=bastion_instance.bastion_floating_ip_association.floating_ip.apply(
            lambda ip: _build_fetch_kubeconfig_command(ip, kubeconfig_path)
        ),
        update=bastion_instance.bastion_floating_ip_association.floating_ip.apply(
            lambda ip: _build_fetch_kubeconfig_command(ip, kubeconfig_path)
        ),
        triggers=[
            bastion_instance.bastion_floating_ip_association.floating_ip,
            kubeconfig_server,
            kubeconfig_path,
        ],
        dir=".",
        interpreter=["/bin/bash", "-c"],
        opts=ResourceOptions(depends_on=[cluster_ready]),
    )

    return Rke2Automation(
        control_ready=control_ready,
        worker_joins=worker_joins,
        cluster_ready=cluster_ready,
        kubeconfig=kubeconfig,
        kubeconfig_path=kubeconfig_path,
        kubeconfig_server=kubeconfig_server,
    )
