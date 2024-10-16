import pulumi
import pulumi_kubernetes as k8s

from infra.bastion import bastion
from infra.cluster import rke_cluster
from infra.instance import instance
from infra.keys import keys
from infra.load_balancer import load_balancer
from infra.network import network
from infra.nfs import nfs
from k8s.argocd import argocd
from k8s.certs import cert_manager
from k8s.ingress_nginx import ingress_nginx
from k8s.nfs import nfs_provisioner, nfs_pvc

config = pulumi.Config()


def main():
    # Generate Key Pair
    key_pair = keys.deploy()

    # Deploy Network
    network_instance, subnet_instance = network.deploy()

    # Deploy Load Balancer
    (
        api_pool,
        http_pool,
        https_pool,
        load_balancer_floating_ip,
        apisix_pool,
        apisix_floating_ip,
        apisix_lb,
        apisix_https_pool,
    ) = load_balancer.deploy(subnet_instance)

    pulumi.export("apisix_floating_ip", apisix_floating_ip.address)

    # Deploy Bastion
    bastion_instance = bastion.Bastion(network_instance, key_pair)

    # Deploy NFS
    nfs_instance = nfs.deploy(network_instance)

    # Deploy Control Node Instance
    control_node = instance.deploy(
        "control-node", config.require("controlPlaneNodeFlavour"), network_instance
    )

    # Deploy Worker Nodes Instances
    worker_nodes = []
    for i in range(config.require_int("workerNodeCount")):
        node = instance.deploy(
            f"worker-node-{i}", config.require("workerNodeFlavour"), network_instance
        )
        load_balancer.add_member(
            f"worker-node-{i}",
            node,
            http_pool,
            https_pool,
            apisix_pool,
            apisix_https_pool,
            subnet_instance,
        )
        worker_nodes.append(node)

    # Deploy RKE Cluster
    nodes = {
        "control_node": control_node,
        "worker_nodes": worker_nodes,
    }
    cluster, kubeconfig = rke_cluster.deploy(
        nodes, bastion_instance, subnet_instance, api_pool, load_balancer_floating_ip
    )

    # Connect kubeconfig to the RKE cluster
    k8s_provider = k8s.Provider(
        "k8s-provider",
        kubeconfig=kubeconfig,
        opts=pulumi.ResourceOptions(
            depends_on=[cluster], ignore_changes=["kubeconfig", "deleteUnreachable"]
        ),
        enable_server_side_apply=True,
    )

    # Deploy Ingress Nginx
    ingress_chart = ingress_nginx.deploy(k8s_provider)

    # Deploy Cert Manager
    cluster_issuer = cert_manager.deploy(k8s_provider)

    # Add NFS Provisioner to the RKE cluster
    nfs_provisioner.deploy(k8s_provider, nfs_instance)
    nfs_pvc.deploy(k8s_provider)

    # Deploy ArgoCD onto the RKE cluster
    argocd_chart = argocd.deploy(
        k8s_provider,
        ingress_chart,
    )


if __name__ == "__main__":
    main()
