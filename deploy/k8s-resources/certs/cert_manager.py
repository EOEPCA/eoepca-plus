import pulumi
from pulumi import Config
from pulumi_kubernetes.apiextensions.CustomResource import CustomResource
from pulumi_kubernetes.core.v1 import Namespace
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts

config = Config()


def deploy():
    namespace_name = "cert-manager"
    ns = Namespace(
        "cert-manager-ns",
        metadata={"name": namespace_name},
    )

    cert_manager = Chart(
        "cert-manager",
        ChartOpts(
            chart="cert-manager",
            version=config.require("certManagerVersion"),
            fetch_opts=FetchOpts(repo="https://charts.jetstack.io"),
            namespace=namespace_name,
            values={
                "installCRDs": True,
            },
        ),
        opts=pulumi.ResourceOptions(depends_on=[ns]),
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
        opts=pulumi.ResourceOptions(
            depends_on=[cert_manager],
            custom_timeouts=pulumi.CustomTimeouts(create="5m"),
        ),
    )

    return cert_manager