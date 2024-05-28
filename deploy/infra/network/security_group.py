import pulumi
from pulumi_openstack import networking


def deploy(name, description, rules):
    # Create the security group
    sec_group = networking.SecGroup(
        name,
        name=name,
        description=description,
    )

    # Iterate over the rules and add them to the security group
    for rule in rules:
        first_four_numbers = ".".join(rule["remote_ip_prefix"].split(".")[0:4])
        networking.SecGroupRule(
            f"{name}-{first_four_numbers}-{rule['direction']}-{rule['protocol']}-{rule['port_range_min']}-{rule['port_range_max']}",
            security_group_id=sec_group.id,
            direction=rule["direction"],
            protocol=rule["protocol"],
            port_range_min=rule["port_range_min"],
            port_range_max=rule["port_range_max"],
            remote_ip_prefix=rule["remote_ip_prefix"],
            ethertype="IPv4",
        )

    return sec_group
