import pulumi
from pulumi import Config, ResourceOptions
from pulumi_command import remote

from infra.instance import instance
from infra.keys.keys import private_key
from infra.network import security_group

config = Config()


def deploy(network_instance, key_pair):
    # Setup Security Group for Bastion
    bastion_sg_rules = [
        {
            "direction": "ingress",
            "protocol": "tcp",
            "port_range_min": 22,
            "port_range_max": 22,
            "remote_ip_prefix": "0.0.0.0/0",  # TODO: Change this to a more secure IP range,
        }
    ]
    bastion_security_group = security_group.deploy(
        "bastion-sg",
        "Security group for the bastion instance",
        bastion_sg_rules,
    )

    # Private key pem
    private_key_pem = private_key.private_key_pem

    # Create Bastion Instance
    bastion_instance = instance.create_instance(
        "bastion",
        key_pair.name,
        config.require("bastionFlavour"),
        config.require("nodeImage"),
        [{"uuid": network_instance.id}],
        [bastion_security_group.id],
        network_instance,
        # allow ssh tunnel
        user_data="""#!/bin/bash
        echo "GatewayPorts yes" >> /etc/ssh/sshd_config
        echo "AllowTcpForwarding yes" >> /etc/ssh/sshd_config
        echo "PermitTunnel yes" >> /etc/ssh/sshd_config
        systemctl restart sshd
        """,
    )

    # Attach External IP to Bastion
    bastion_floating_ip, bastion_floating_ip_association = instance.attach_floating_ip(
        bastion_instance
    )
    pulumi.export("bastion_ip", bastion_floating_ip_association.floating_ip)

    return bastion_instance, bastion_floating_ip_association


class Bastion:
    def __init__(self, network_instance, key_pair):
        self.network_instance = network_instance
        self.key_pair = key_pair
        self.private_key = private_key
        self.bastion_instance, self.bastion_floating_ip_association = (
            self.deploy_bastion()
        )

    def deploy_bastion(self):
        return deploy(self.network_instance, self.key_pair)

    def run_command(self, name, command, ip_to_run_on):
        return remote.Command(
            name,
            connection=remote.ConnectionArgs(
                host=self.bastion_floating_ip_association.floating_ip,
                user=config.require("sshUser"),
                private_key=self.private_key.private_key_pem,
            ),
            create=command,
            opts=ResourceOptions(depends_on=[self.bastion_instance]),
        )
