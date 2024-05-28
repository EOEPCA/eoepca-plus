import pulumi
from pulumi import Config
from pulumi_kubernetes.apps.v1 import Deployment
from pulumi_kubernetes.core.v1 import Namespace
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts

config = pulumi.Config()


def deploy(k8s_provider):
    # Deploy CoreDNS using Helm Chart
    coredns_chart = Chart(
        "coredns",
        ChartOpts(
            chart="coredns",
            version="1.16.1",
            fetch_opts=FetchOpts(repo="https://coredns.github.io/helm"),
            namespace="kube-system",
            values={
                "replicas": 2,
                "service": {"type": "ClusterIP", "clusterIP": "10.43.0.10"},
                "autopath": {"enabled": True},
                "prometheus": {"enabled": True, "service": {"port": 9153}},
            },
        ),
        opts=pulumi.ResourceOptions(provider=k8s_provider),
    )

    return coredns_chart
