import pulumi
from pulumi import Config
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts

config = pulumi.Config()


def deploy(k8s_provider, nfs_instance):
    NFS_IP = nfs_instance.access_ip_v4

    # Deploy the NFS provisioner from its Helm chart
    nfs_provisioner_chart = Chart(
        "nfs-provisioner",
        ChartOpts(
            chart="nfs-subdir-external-provisioner",
            version=config.require("nfsProvisionerVersion"),
            fetch_opts=FetchOpts(
                repo="https://kubernetes-sigs.github.io/nfs-subdir-external-provisioner/"
            ),
            values={
                "provisionerName": "nfs-storage",
                "storageClass": {
                    "name": "managed-nfs-storage",
                    "create": True,
                    "defaultClass": False,
                    "reclaimPolicy": "Delete",
                    "allowVolumeExpansion": True,
                },
                "nfs": {"server": NFS_IP, "path": "/data/dynamic"},
            },
        ),
        opts=pulumi.ResourceOptions(provider=k8s_provider),
    )

    # Deploy the NFS provisioner from its Helm chart
    nfs_provisioner_chart_retain = Chart(
        "nfs-provisioner-retain",
        ChartOpts(
            chart="nfs-subdir-external-provisioner",
            version=config.require("nfsProvisionerVersion"),
            fetch_opts=FetchOpts(
                repo="https://kubernetes-sigs.github.io/nfs-subdir-external-provisioner/"
            ),
            values={
                "provisionerName": "nfs-storage-retain",
                "storageClass": {
                    "name": "managed-nfs-storage-retain",
                    "create": True,
                    "defaultClass": False,
                    "reclaimPolicy": "Retain",
                    "allowVolumeExpansion": True,
                },
                "nfs": {"server": NFS_IP, "path": "/data/dynamic"},
            },
        ),
        opts=pulumi.ResourceOptions(provider=k8s_provider),
    )

    return nfs_provisioner_chart, nfs_provisioner_chart_retain
