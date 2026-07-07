import pulumi
from pulumi_openstack import loadbalancer

from bastion import bastion
from cluster import rke2
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
    network_instance, subnet_instance, router_interface = network.deploy()

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
    ) = load_balancer.deploy(subnet_instance, router_interface)

    pulumi.export("apisix_floating_ip", apisix_floating_ip.address)

    # Deploy Bastion
    bastion_instance = bastion.Bastion(network_instance, key_pair, router_interface)

    # Deploy NFS
    nfs_server = nfs.deploy(network_instance)
    pulumi.export("nfs_server_ip", nfs_server.access_ip_v4)

    # Deploy Control Nodes (configurable count)
    control_node_count = config.get_int("controlPlaneNodeCount") or 1
    control_nodes = []
    for i in range(control_node_count):
        node = instance.deploy(
            f"rke2-control-node-{i}",
            config.require("controlPlaneNodeFlavour"),
            network_instance,
            role="server",
            load_balancer_ip=load_balancer_floating_ip.address,
        )
        # Add to API pool
        loadbalancer.Member(
            f"rke2-control-node-{i}-api",
            pool_id=api_pool.id,
            address=node.access_ip_v4,
            protocol_port=6443,
            subnet_id=subnet_instance.id,
        )
        control_nodes.append(node)

    # Deploy Worker Nodes
    worker_nodes = []
    for i in range(config.require_int("workerNodeCount")):
        node = instance.deploy(
            f"rke2-worker-node-{i}",
            config.require("workerNodeFlavour"),
            network_instance
        )
        load_balancer.add_member(
            f"rke2-worker-node-{i}",
            node,
            http_pool,
            https_pool,
            apisix_pool,
            apisix_https_pool,
            subnet_instance,
        )
        worker_nodes.append(node)

    kubeconfig_server = config.get("kubeconfigServer")
    if not kubeconfig_server:
        kubeconfig_server = load_balancer_floating_ip.address.apply(
            lambda ip: f"https://{ip}:6443"
        )

    rke2_automation = rke2.configure(
        bastion_instance,
        control_nodes,
        worker_nodes,
        kubeconfig_server,
    )

    # Export for Ansible
    pulumi.export("control_node_ips", [n.access_ip_v4 for n in control_nodes])
    pulumi.export("worker_node_ips", [n.access_ip_v4 for n in worker_nodes])
    pulumi.export("bastion_ip", bastion_instance.bastion_floating_ip_association.floating_ip)
    pulumi.export("load_balancer_ip", load_balancer_floating_ip.address)
    pulumi.export("kubeconfig_server", rke2_automation.kubeconfig_server)
    pulumi.export("kubeconfig_path", rke2_automation.kubeconfig_path)

    # Export SSH commands
    pulumi.export("ssh_bastion", bastion_instance.bastion_floating_ip_association.floating_ip.apply(
        lambda ip: f"ssh -i rke2-generated_key.pem eouser@{ip}"
    ))
    pulumi.export("ssh_control_node", pulumi.Output.all(
        bastion_instance.bastion_floating_ip_association.floating_ip,
        control_nodes[0].access_ip_v4
    ).apply(
        lambda args: f"ssh -i rke2-generated_key.pem eouser@{args[0]} then ssh -i ~/.ssh/key.pem eouser@{args[1]}"
    ))
    pulumi.export("ssh_worker_node", pulumi.Output.all(
        bastion_instance.bastion_floating_ip_association.floating_ip,
        worker_nodes[0].access_ip_v4
    ).apply(
        lambda args: f"ssh -i rke2-generated_key.pem eouser@{args[0]} then ssh -i ~/.ssh/key.pem eouser@{args[1]}"
    ))


if __name__ == "__main__":
    main()
