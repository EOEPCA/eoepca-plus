import pulumi
from pulumi import Config, ResourceOptions
from pulumi_command import remote
from pulumi_openstack import compute, networking

from infra.keys.keys import private_key
from infra.network import security_group

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
            depends_on=[network_instance], ignore_changes=["security_groups"]
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


def attach_floating_ip(instance, pool_name="external"):
    floating_ip = networking.FloatingIp(f"{instance._name}-floating-ip", pool=pool_name)
    floating_ip_assoc = pulumi.Output.all(instance.id, floating_ip.address).apply(
        lambda args: compute.FloatingIpAssociate(
            f"{instance._name}-fip-assoc",
            floating_ip=args[1],
            instance_id=args[0],
            opts=ResourceOptions(depends_on=[instance, floating_ip]),
        )
    )

    return floating_ip, floating_ip_assoc


def deploy(instance_name, flavour, network_instance):
    # Security Groups
    security_groups = get_node_security_groups(instance_name)

    # Create instance
    test_instance = create_instance(
        instance_name=instance_name,
        key_pair_name=config.require("keyPairName"),
        flavor=flavour,
        image=config.require("nodeImage"),
        security_groups=security_groups,
        networks=[{"uuid": network_instance.id}],
        network_instance=network_instance,
        user_data=get_docker_user_data_script(),
    )

    pulumi.export(f"{instance_name}_access_ip", test_instance.access_ip_v4)

    return test_instance


# TODO: There are unresolved issues regarding the security group setup
#       For now allowing all traffic to and from the instance is acceptable as the nodes are not exposed to the internet
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
