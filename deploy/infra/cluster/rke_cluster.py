import pulumi
from pulumi import Config, ResourceOptions
from pulumi_openstack import loadbalancer
from pulumi_rke import (Cluster, ClusterAuthenticationArgs,
                        ClusterBastionHostArgs, ClusterDnsArgs,
                        ClusterIngressArgs, ClusterNodeArgs)

from infra.keys.keys import private_key

config = Config()


def deploy(nodes, bastion_instance, subnet_instance, pool, load_balancer_floating_ip):
    # Node setup
    node_config = []
    for node in nodes["worker_nodes"]:
        node_config.append(
            ClusterNodeArgs(
                address=node.access_ip_v4,
                internal_address=node.access_ip_v4,
                user=config.require("sshUser"),
                roles=["worker"],
                ssh_key=private_key.private_key_pem,
            )
        )
    node_config.append(
        ClusterNodeArgs(
            address=nodes["control_node"].access_ip_v4,
            internal_address=nodes["control_node"].access_ip_v4,
            user=config.require("sshUser"),
            roles=["controlplane", "etcd"],
            ssh_key=private_key.private_key_pem,
        )
    )

    # Cluster setup
    rke_cluster = Cluster(
        "my-rke-cluster",
        nodes=node_config,
        kubernetes_version=config.require("kubernetesVersion"),
        enable_cri_dockerd=True,
        addon_job_timeout=60,
        bastion_host=ClusterBastionHostArgs(
            address=bastion_instance.bastion_floating_ip_association.floating_ip,
            user=config.require("sshUser"),
            ssh_key=private_key.private_key_pem,
        ),
        authentication=ClusterAuthenticationArgs(
            strategy="x509",
            sans=[
                bastion_instance.bastion_floating_ip_association.floating_ip,
                load_balancer_floating_ip.address,
            ],
        ),
        ingress=ClusterIngressArgs(
            provider="none",
        ),
        opts=pulumi.ResourceOptions(
            depends_on=[
                bastion_instance.bastion_instance,
                subnet_instance,
                pool,
                load_balancer_floating_ip,
            ],
            ignore_changes=["ingress"],
        ),
    )

    # Kubeconfig setup
    pulumi.export("kubeconfig", rke_cluster.kube_config_yaml)
    modified_kubeconfig = pulumi.Output.all(
        rke_cluster.kube_config_yaml,
        load_balancer_floating_ip.address,
        nodes["control_node"].access_ip_v4,
    ).apply(
        lambda args: args[0].replace(
            f"{args[2]}",
            f"{args[1]}",
        )
    )
    modified_kubeconfig.apply(lambda v: open("kubeconfig.yaml", "w").write(v))

    # Create a member for the pool
    member = loadbalancer.Member(
        "k8s-member",
        pool_id=pool.id,
        address=nodes["control_node"].access_ip_v4,
        protocol_port=6443,
        subnet_id=subnet_instance.id,
        opts=pulumi.ResourceOptions(depends_on=[rke_cluster, pool]),
    )

    return rke_cluster, modified_kubeconfig
