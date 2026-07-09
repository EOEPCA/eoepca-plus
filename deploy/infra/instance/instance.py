import pulumi
from pulumi import Config, ResourceOptions
from pulumi_command import remote
from pulumi_openstack import compute, networking

from network import security_group

config = Config()


def create_instance(
    instance_name,
    key_pair_name,
    flavor,
    image,
    networks,
    security_groups,
    network_instance,
    user_data=None,
):
    return compute.Instance(
        instance_name,
        flavor_name=flavor,
        image_name=image,
        key_pair=key_pair_name,
        security_groups=security_groups,
        networks=networks,
        user_data=user_data,
        opts=ResourceOptions(
            depends_on=[network_instance],
            ignore_changes=["security_groups", "imageName"],
        ),
    )


def run_command_on_instance(instance, private_key_pem, name, command, opts=None):
    return remote.Command(
        name,
        connection=remote.ConnectionArgs(
            host=instance.access_ip_v4,
            user=config.require("sshUser"),
            private_key=private_key_pem,
        ),
        create=command,
        opts=opts or ResourceOptions(depends_on=[instance]),
    )


def get_docker_user_data_script():
    install_docker_script = f"""#!/bin/bash
        echo "Waiting a bit longer before attempting to install Docker"
        curl https://releases.rancher.com/install-docker/24.0.sh | sh
        sudo usermod -a -G docker {config.require("sshUser")}
        echo "Wait 5 seconds again"
        sleep 5
    """

    return install_docker_script


def get_rke2_user_data_script():
    return """#!/bin/bash
set -euo pipefail
exec > /var/log/rke2-setup.log 2>&1

# Wait for DNS to actually work
until getent hosts nova.clouds.archive.ubuntu.com >/dev/null 2>&1; do
    echo "Waiting for DNS..."
    sleep 5
done

# Wait for apt lock
while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do
    echo "Waiting for apt lock..."
    sleep 5
done

swapoff -a
sed -i '/ swap / s/^/#/' /etc/fstab

cat <<EOF | tee /etc/modules-load.d/rke2.conf
overlay
br_netfilter
EOF
modprobe overlay
modprobe br_netfilter

cat <<EOF | tee /etc/sysctl.d/99-kubernetes-cri.conf
net.bridge.bridge-nf-call-iptables  = 1
net.ipv4.ip_forward                 = 1
net.bridge.bridge-nf-call-ip6tables = 1
EOF
sysctl --system

# Retry iptables install until it succeeds
for i in $(seq 1 10); do
    apt-get update && apt-get install -y iptables && break
    echo "apt attempt $i failed, sleeping 15s"
    sleep 15
done

# Fail loudly if still not installed
command -v iptables >/dev/null || { echo "FATAL: iptables install failed after retries"; exit 1; }

mkdir -p /etc/rancher/rke2
cat <<EOF > /etc/rancher/rke2/config.yaml
kubelet-arg:
  - max-pods=500
  - container-log-max-size=50Mi
  - container-log-max-files=3
EOF
"""


def get_rke2_server_user_data_script(domain_name, lb_ip, email):
    return f"""#!/bin/bash
set -euo pipefail
exec > /var/log/rke2-setup.log 2>&1

# Disable swap
swapoff -a
sed -i '/ swap / s/^/#/' /etc/fstab

# Kernel modules
cat <<EOF | tee /etc/modules-load.d/rke2.conf
overlay
br_netfilter
EOF
modprobe overlay
modprobe br_netfilter

cat <<EOF | tee /etc/sysctl.d/99-kubernetes-cri.conf
net.bridge.bridge-nf-call-iptables  = 1
net.ipv4.ip_forward                 = 1
net.bridge.bridge-nf-call-ip6tables = 1
EOF
sysctl --system

# Install iptables (needed by CNI portmap plugin)
apt-get update
apt-get install -y iptables

# Install RKE2
curl -sfL https://get.rke2.io | sh -
systemctl enable rke2-server.service

# Configure RKE2
mkdir -p /etc/rancher/rke2
cat <<EOF > /etc/rancher/rke2/config.yaml
tls-san:
  - {lb_ip}
  - {domain_name}
  - rancher.{domain_name}
node-taint:
  - "CriticalAddonsOnly=true:NoExecute"
kubelet-arg:
  - max-pods=500
  - container-log-max-size=50Mi
  - container-log-max-files=3
EOF

systemctl start rke2-server.service

# Wait for kubeconfig
while [ ! -f /etc/rancher/rke2/rke2.yaml ]; do
    sleep 5
done

export KUBECONFIG=/etc/rancher/rke2/rke2.yaml
export PATH=$PATH:/var/lib/rancher/rke2/bin

# Wait for node ready
until kubectl get nodes | grep -q ' Ready'; do
    sleep 10
done

# Install Helm
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

helm repo add rancher-stable https://releases.rancher.com/server-charts/stable
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Install cert-manager (idempotent, retried: helm can transiently fail
# right after the apiserver comes up)
kubectl create namespace cert-manager --dry-run=client -o yaml | kubectl apply -f -
cert_manager_ok=false
for i in $(seq 1 5); do
    if helm upgrade --install cert-manager jetstack/cert-manager \
        --namespace cert-manager \
        --version v1.16.3 \
        --set crds.enabled=true \
        --wait --timeout 5m; then
        cert_manager_ok=true
        break
    fi
    echo "cert-manager install attempt $i failed, retrying in 15s"
    sleep 15
done
if [ "$cert_manager_ok" != "true" ]; then
    echo "FATAL: cert-manager install failed after retries"
    kubectl get pods -n cert-manager || true
    exit 1
fi

# Wait for ingress-nginx to be ready (bounded, was previously an infinite loop
# that could hang the whole script and block cattle-system from ever being created)
echo "Waiting for ingress-nginx admission webhook..."
ingress_ready=false
for i in $(seq 1 60); do
    ip="$(kubectl get endpoints -n kube-system rke2-ingress-nginx-controller-admission -o jsonpath='{{.subsets[0].addresses[0].ip}}' 2>/dev/null || true)"
    if [ -n "$ip" ]; then
        ingress_ready=true
        break
    fi
    echo "Still waiting for ingress-nginx... ($i/60)"
    sleep 10
done
if [ "$ingress_ready" != "true" ]; then
    echo "FATAL: ingress-nginx admission webhook not ready after 10m"
    kubectl get pods -n kube-system -l app.kubernetes.io/name=rke2-ingress-nginx || true
    exit 1
fi
echo "Ingress-nginx is ready"
sleep 15

# Install Rancher (idempotent, retried)
kubectl create namespace cattle-system --dry-run=client -o yaml | kubectl apply -f -
rancher_ok=false
for i in $(seq 1 3); do
    if helm upgrade --install rancher rancher-stable/rancher \
        --namespace cattle-system \
        --set hostname=rancher.{domain_name} \
        --set letsEncrypt.email={email} \
        --set letsEncrypt.ingress.class=nginx \
        --set ingress.tls.source=letsEncrypt \
        --set replicas=1 \
        --wait --timeout 10m; then
        rancher_ok=true
        break
    fi
    echo "Rancher install attempt $i failed, retrying in 30s"
    sleep 30
done
if [ "$rancher_ok" != "true" ]; then
    echo "FATAL: Rancher install failed after retries"
    kubectl get pods -n cattle-system || true
    exit 1
fi

# Verify the bootstrap secret actually exists before relying on it below
secret_ok=false
for i in $(seq 1 30); do
    if kubectl get secret --namespace cattle-system bootstrap-secret >/dev/null 2>&1; then
        secret_ok=true
        break
    fi
    echo "Waiting for Rancher bootstrap-secret... ($i/30)"
    sleep 10
done
if [ "$secret_ok" != "true" ]; then
    echo "FATAL: cattle-system/bootstrap-secret not found after Rancher install"
    exit 1
fi

# Save bootstrap password
kubectl get secret --namespace cattle-system bootstrap-secret \
    -o go-template='{{{{.data.bootstrapPassword|base64decode}}}}' \
    > /home/eouser/rancher-bootstrap-password.txt
chown eouser:eouser /home/eouser/rancher-bootstrap-password.txt
"""

def attach_floating_ip(instance, pool_name="external", extra_deps=None):
    floating_ip = networking.FloatingIp(f"{instance._name}-floating-ip", pool=pool_name)

    deps = [instance, floating_ip]
    if extra_deps:
        deps.extend(extra_deps)

    floating_ip_assoc = compute.FloatingIpAssociate(
        f"{instance._name}-fip-assoc",
        floating_ip=floating_ip.address,
        instance_id=instance.id,
        opts=ResourceOptions(depends_on=deps),
    )

    return floating_ip, floating_ip_assoc


def deploy(instance_name, flavour, network_instance, role="worker", load_balancer_ip=None):
    security_groups = get_node_security_groups(instance_name)

    if role == "server":
        lb_ip = load_balancer_ip or config.require("loadBalancerIP")
        user_data = pulumi.Output.all(lb_ip).apply(
            lambda args: get_rke2_server_user_data_script(
                config.require("domainName"),
                args[0],
                config.require("maintainerEmail"),
            )
        )
    else:
        user_data = get_rke2_user_data_script()

    test_instance = create_instance(
        instance_name=instance_name,
        key_pair_name="rke2-eoepca-keypair",
        flavor=flavour,
        image=config.require("nodeImage"),
        security_groups=security_groups,
        networks=[{"uuid": network_instance.id}],
        network_instance=network_instance,
        user_data=user_data,
    )

    pulumi.export(f"{instance_name}_access_ip", test_instance.access_ip_v4)
    return test_instance


def get_node_security_groups(instance_name):
    sg_rules = [
        {
            "direction": "ingress",
            "protocol": "tcp",
            "port_range_min": 0,
            "port_range_max": 0,
            "remote_ip_prefix": "0.0.0.0/0",
        },
        {
            "direction": "egress",
            "protocol": "tcp",
            "port_range_min": 0,
            "port_range_max": 0,
            "remote_ip_prefix": "0.0.0.0/0",
        },
        {
            "direction": "ingress",
            "protocol": "udp",
            "port_range_min": 0,
            "port_range_max": 0,
            "remote_ip_prefix": "0.0.0.0/0",
        },
        {
            "direction": "egress",
            "protocol": "udp",
            "port_range_min": 0,
            "port_range_max": 0,
            "remote_ip_prefix": "0.0.0.0/0",
        },
    ]

    sg = security_group.deploy(
        f"{instance_name}-sg",
        f"Security group for the {instance_name} instance",
        sg_rules,
    )

    return [sg.id]
