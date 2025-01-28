import pulumi
from pulumi import ResourceOptions
from pulumi_openstack import blockstorage, compute

from instance.instance import create_instance, get_node_security_groups

config = pulumi.Config()


# Function to attach volume to NFS server
def attach_volume(instance, size_gb):
    nfs_volume = blockstorage.Volume(
        "nfs_volume",
        size=size_gb,
        volume_type="ceph",
        description="NFS Volume",
        opts=ResourceOptions(ignore_changes=["volume_type"]),
    )

    volume_attachment = compute.VolumeAttach(
        "nfs_volume_attachment",
        instance_id=instance.id,
        volume_id=nfs_volume.id,
        device="/dev/sdb",
        opts=ResourceOptions(depends_on=[instance], ignore_changes=["device"]),
    )
    return nfs_volume, volume_attachment


# Alternate function to return user_data script for NFS server
def get_user_data_script():
    # Open the nfs-setup and read the content
    with open("nfs/nfs-setup.sh", "r") as file:
        user_data = file.read()
    return user_data


# Deployment function for NFS infrastructure
def deploy(network_instance):

    # Deploy NFS Server using the shared function
    nfs_server = create_instance(
        "nfs-server",
        "eoepca-dev-keypair",
        config.require("nfsFlavour"),
        #config.require("nodeImage"),
        [{"uuid": network_instance.id}],
        get_node_security_groups("nfs-server"),
        network_instance,
        user_data=get_user_data_script(),
    )

    # Attach NFS Volume
    nfs_volume, volume_attachment = attach_volume(
        nfs_server, config.require_int("nfsVolumeSize")
    )

    return nfs_server
