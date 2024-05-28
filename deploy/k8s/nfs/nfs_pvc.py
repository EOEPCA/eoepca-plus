import pulumi
import pulumi_kubernetes as k8s


def deploy(k8s_provider):
    # Create a PVC
    nfs_pvc = k8s.core.v1.PersistentVolumeClaim(
        "nfs-pvc",
        metadata={
            "name": "test-pvc",
            "labels": {"k8s-app": "data-access", "name": "data-access"},
        },
        spec={
            "storageClassName": "managed-nfs-storage",
            "accessModes": ["ReadWriteMany"],
            "resources": {"requests": {"storage": "5Gi"}},
        },
        opts=pulumi.ResourceOptions(provider=k8s_provider),
    )

    # Create a PVC for retain
    nfs_pvc = k8s.core.v1.PersistentVolumeClaim(
        "nfs-pvc-retain",
        metadata={
            "name": "test-pvc-retain",
            "labels": {"k8s-app": "data-access", "name": "data-access"},
        },
        spec={
            "storageClassName": "managed-nfs-storage-retain",
            "accessModes": ["ReadWriteMany"],
            "resources": {"requests": {"storage": "5Gi"}},
        },
        opts=pulumi.ResourceOptions(provider=k8s_provider),
    )

    return nfs_pvc
