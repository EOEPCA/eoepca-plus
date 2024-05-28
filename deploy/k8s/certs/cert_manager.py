import pulumi
from pulumi import Config
from pulumi_kubernetes.apiextensions.CustomResource import CustomResource
from pulumi_kubernetes.core.v1 import Namespace
from pulumi_kubernetes_cert_manager import CertManager, ReleaseArgs

config = Config()


# Function to deploy cert-manager and configure a ClusterIssuer
def deploy(k8s_provider):
    namespace_name = "cert-manager-ns"
    ns = Namespace(
        "cert-manager-ns",
        metadata={"name": namespace_name},
        opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[k8s_provider]),
    )

    cert_manager = CertManager(
        "cert-manager",
        install_crds=True,
        helm_options=ReleaseArgs(
            namespace=namespace_name,
            values={"meta": {"helm.sh/release-namespace": namespace_name}},
        ),
        opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[ns]),
    )

    issuer = CustomResource(
        "letsencrypt-prod",
        api_version="cert-manager.io/v1",
        kind="ClusterIssuer",
        metadata={
            "name": "letsencrypt-prod",
        },
        spec={
            "acme": {
                "server": "https://acme-v02.api.letsencrypt.org/directory",
                "email": config.require("maintainerEmail"),
                "privateKeySecretRef": {"name": "letsencrypt-prod"},
                "solvers": [{"http01": {"ingress": {"class": "nginx"}}}],
            }
        },
        opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[cert_manager]),
    )

    return issuer
