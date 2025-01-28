import pulumi

from bastion import bastion
from cluster import rke_cluster
from instance import instance
from keys import keys
from load_balancer import load_balancer
from network import network
from nfs import nfs

config = pulumi.Config()


def main():
    # Generate Key Pair
    key_pair = keys.deploy()

    # Deploy Network
    network_instance, subnet_instance = network.deploy()

    # # Deploy Load Balancer
    # (
    #     api_pool,
    #     http_pool,
    #     https_pool,
    #     load_balancer_floating_ip,
    #     apisix_pool,
    #     apisix_floating_ip,
    #     apisix_lb,
    #     apisix_https_pool,
    # ) = load_balancer.deploy(subnet_instance)

    # pulumi.export("apisix_floating_ip", apisix_floating_ip.address)

    # Deploy Bastion
    bastion_instance = bastion.Bastion(network_instance, key_pair)

    # Deploy NFS
    nfs.deploy(network_instance)

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
        # load_balancer.add_member(
        #     f"worker-node-{i}",
        #     node,
        #     http_pool,
        #     https_pool,
        #     apisix_pool,
        #     apisix_https_pool,
        #     subnet_instance,
        # )
        worker_nodes.append(node)

    # Deploy RKE Cluster
    nodes = {
        "control_node": control_node,
        "worker_nodes": worker_nodes,
    }
    rke_cluster.deploy(
        nodes, bastion_instance, subnet_instance #, api_pool, load_balancer_floating_ip
    )


if __name__ == "__main__":
    main()
