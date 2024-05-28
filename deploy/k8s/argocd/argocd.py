import pulumi
from pulumi_kubernetes.core.v1 import Namespace
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts
from pulumi_kubernetes.yaml import ConfigFile

config = pulumi.Config()


def deploy(k8s_provider, cluster_issuer, ingress_chart, sealed_secrets_crd):
    # Create Argo CD namespace
    argocd_namespace = Namespace(
        "argocd",
        metadata={"name": "argocd"},
        opts=pulumi.ResourceOptions(
            provider=k8s_provider,
            depends_on=[k8s_provider],
        ),
    )

    argo_domain_name = f"argocd.{config.require('domainName')}"

    # Deploy Argo CD using Helm Chart
    argo_chart = Chart(
        "argocd",
        ChartOpts(
            chart="argo-cd",
            version=config.require("argoCDVersion"),
            fetch_opts=FetchOpts(repo="https://argoproj.github.io/argo-helm"),
            namespace=argocd_namespace.metadata["name"],
            values={
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
        opts=pulumi.ResourceOptions(
            provider=k8s_provider, depends_on=[argocd_namespace, ingress_chart]
        ),
    )

    # Install CRDs for Argo CD
    argocd_crd = ConfigFile(
        "argocd-crd",
        file="https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/crds/application-crd.yaml",
        opts=pulumi.ResourceOptions(
            provider=k8s_provider, depends_on=[argocd_namespace]
        ),
    )

    # Set up ArgoCD Application and Project
    project = ConfigFile(
        "project",
        file="k8s/argocd/project.yaml",
        opts=pulumi.ResourceOptions(
            provider=k8s_provider, depends_on=[argo_chart, argocd_crd]
        ),
    )

    application = ConfigFile(
        "application",
        file="k8s/argocd/application.yaml",
        opts=pulumi.ResourceOptions(
            provider=k8s_provider, depends_on=[argo_chart, project, argocd_crd]
        ),
    )

    return argo_chart
