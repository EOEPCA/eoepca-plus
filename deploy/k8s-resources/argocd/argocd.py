import pulumi
from pulumi import ResourceOptions
from pulumi_kubernetes.core.v1 import Namespace
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts
from pulumi_kubernetes.yaml import ConfigFile

config = pulumi.Config()


def deploy(ingress_chart):
    argocd_namespace = Namespace(
        "argocd",
        metadata={"name": "argocd"},
    )

    argo_domain_name = f"argocd.{config.require('domainName')}"

    # Deploy ArgoCD - the Helm chart installs its own CRDs
    argo_chart = Chart(
        "argocd",
        ChartOpts(
            chart="argo-cd",
            version=config.require("argoCDVersion"),
            fetch_opts=FetchOpts(repo="https://argoproj.github.io/argo-helm"),
            namespace=argocd_namespace.metadata["name"],
            values={
                "crds": {
                    "install": True,
                    "keep": True,
                },
                "server": {
                    "service": {"type": "ClusterIP"},
                    "extraArgs": ["--insecure"],
                    "ingress": {
                        "enabled": True,
                        "hostname": argo_domain_name,
                        "annotations": {
                            "kubernetes.io/ingress.class": "nginx",
                            "nginx.ingress.kubernetes.io/ssl-passthrough": "false",
                            "nginx.ingress.kubernetes.io/force-ssl-redirect": "false",
                            "cert-manager.io/cluster-issuer": "letsencrypt-prod",
                        },
                        "hosts": [argo_domain_name],
                        "tls": [
                            {
                                "hosts": [argo_domain_name],
                                "secretName": "argocd-server-tls",
                            }
                        ],
                    },
                },
                "applicationSet": {
                    "enabled": True,
                },
                "dex": {
                    "enabled": True,
                },
                "configs": {
                    "cm": {
                        "url": f"https://{argo_domain_name}",
                        "dex.config": f"""
                            connectors:
                            - type: github
                                id: github
                                name: GitHub
                                config:
                                    clientID: {config.require("SSOClientID")}
                                    clientSecret: {config.require("SSOClientSecret")}
                                    orgs:
                                    - name: {config.require("SSOOrg")}
                                    teams:
                                    - name: {config.require("SSOTeam")}
                            """,
                    },
                    "rbac": {
                        "policy.default": config.require("RBACPolicyDefault"),
                    },
                },
            },
        ),
        opts=ResourceOptions(
            depends_on=[argocd_namespace, ingress_chart],
            custom_timeouts=pulumi.CustomTimeouts(create="10m"),
        ),
    )

    # Wait for the Helm chart (and its CRDs) before creating Application/Project
    project = ConfigFile(
        "project",
        file="argocd/project.yaml",
        opts=ResourceOptions(
            depends_on=[argo_chart],
            custom_timeouts=pulumi.CustomTimeouts(create="5m"),
        ),
    )

    application = ConfigFile(
        "application",
        file="argocd/application.yaml",
        opts=ResourceOptions(
            depends_on=[argo_chart, project],
            custom_timeouts=pulumi.CustomTimeouts(create="5m"),
        ),
    )

    return argo_chart