import pulumi
from pulumi import Config
import pulumi_kubernetes as k8s
from argocd import argocd
from certs import cert_manager
from ingress_nginx import ingress_nginx
from nfs import nfs_provisioner, nfs_pvc

config = Config()


def main():
    # Deploy Ingress Nginx
    # ingress_chart = ingress_nginx.deploy()

    # Deploy Cert Manager
    # cert_manager.deploy()

    # Add NFS Provisioner to the RKE cluster
    # nfs_provisioner.deploy()
    # nfs_pvc.deploy()

    # Deploy ArgoCD onto the RKE cluster
    argocd.deploy(
        # ingress_chart,
    )


if __name__ == "__main__":
    main()
