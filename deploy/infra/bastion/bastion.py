import pulumi
from pulumi import Config, ResourceOptions
from pulumi_command import remote

from instance import instance
from keys.keys import private_key
from network import security_group

config = Config()


def deploy(network_instance, key_pair, router_interface):
    bastion_sg_rules = [
        {
            "direction": "ingress",
            "protocol": "tcp",
            "port_range_min": 22,
            "port_range_max": 22,
            "remote_ip_prefix": "0.0.0.0/0",
        }
    ]
    bastion_security_group = security_group.deploy(
        "rke2-bastion-sg",
        "Security group for the rke2 bastion instance",
        bastion_sg_rules,
    )

    private_key_pem = private_key.private_key_pem

    # User data script that configures SSH and writes the private key
    user_data = private_key_pem.apply(
        lambda pem: f"""#!/bin/bash
echo "GatewayPorts yes" >> /etc/ssh/sshd_config
echo "AllowTcpForwarding yes" >> /etc/ssh/sshd_config
echo "PermitTunnel yes" >> /etc/ssh/sshd_config
systemctl restart sshd

# Write private key for SSH to internal nodes
cat <<'KEYEOF' > /home/eouser/.ssh/key.pem
{pem}
KEYEOF
chmod 400 /home/eouser/.ssh/key.pem
chown eouser:eouser /home/eouser/.ssh/key.pem
"""
    )

    bastion_instance = instance.create_instance(
        "rke2-bastion",
        key_pair.name,
        config.require("bastionFlavour"),
        config.require("nodeImage"),
        [{"uuid": network_instance.id}],
        [bastion_security_group.id],
        network_instance,
        user_data=user_data,
    )

    bastion_floating_ip, bastion_floating_ip_association = instance.attach_floating_ip(
        bastion_instance, extra_deps=[router_interface]
    )
    pulumi.export("bastion_ip", bastion_floating_ip_association.floating_ip)

    return bastion_instance, bastion_floating_ip_association


class Bastion:
    def __init__(self, network_instance, key_pair, router_interface):
        self.network_instance = network_instance
        self.key_pair = key_pair
        self.router_interface = router_interface
        self.private_key = private_key
        self.bastion_instance, self.bastion_floating_ip_association = (
            self.deploy_bastion()
        )

    def deploy_bastion(self):
        return deploy(self.network_instance, self.key_pair, self.router_interface)

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
