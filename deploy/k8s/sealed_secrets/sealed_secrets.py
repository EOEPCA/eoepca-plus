import pulumi
from pulumi_kubernetes.core.v1 import Namespace, Secret
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts
from pulumi_kubernetes.yaml import ConfigFile


def deploy(k8s_provider):
    # Create Sealed Secrets namespace if it doesn't already exist
    sealed_secrets_namespace = Namespace(
        "sealed-secrets",
        metadata={"name": "sealed-secrets"},
        opts=pulumi.ResourceOptions(provider=k8s_provider),
    )

    # Install Sealed Secrets CRD
    sealed_secrets_crd = ConfigFile(
        "sealed-secrets-crd",
        file="https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.18.0/controller.yaml",
        opts=pulumi.ResourceOptions(
            provider=k8s_provider, depends_on=[sealed_secrets_namespace]
        ),
    )

    return sealed_secrets_crd
