import pulumi

from bastion import bastion
from cluster import rke2_cluster
from instance import instance
from keys import keys
from network import network
from nfs import nfs

config = pulumi.Config()


def main():
    # Generate Key Pair
    key_pair = keys.deploy()

    # Deploy Network
    network_instance, subnet_instance = network.deploy()

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
        worker_nodes.append(node)

    # Deploy RKE Cluster
    nodes = {
        "control_node": control_node,
        "worker_nodes": worker_nodes,
    }
    rke2_cluster.deploy(
        nodes, bastion_instance, subnet_instance
    )


if __name__ == "__main__":
    main()
