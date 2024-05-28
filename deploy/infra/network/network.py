import pulumi
from pulumi import Config
from pulumi_openstack import networking

config = Config()


def deploy():
    network_name = config.require("networkName")
    subnet_name = config.require("subnetName")
    router_name = config.require("routerName")
    cidr = config.require("networkCIDR")
    external_network_id = config.get("externalNetworkID")

    # Create a network
    network = networking.Network(network_name, name=network_name)

    # Create a subnet within the specified network
    subnet = networking.Subnet(
        subnet_name,
        network_id=network.id,
        cidr=cidr,
        ip_version=4,
        opts=pulumi.ResourceOptions(depends_on=[network]),
    )

    # Create a router with an external gateway
    router = networking.Router(
        router_name,
        name=router_name,
        external_network_id=external_network_id,
        opts=pulumi.ResourceOptions(depends_on=[subnet]),
    )

    # Attach the subnet to the router
    router_interface = networking.RouterInterface(
        f"{router._name}-interface",
        router_id=router.id,
        subnet_id=subnet.id,
        opts=pulumi.ResourceOptions(depends_on=[router]),
    )

    # Output network ID
    pulumi.export("network_id", network.id)

    return network, subnet
