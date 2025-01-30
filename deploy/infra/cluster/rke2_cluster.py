import pulumi
from pulumi import Config
from pulumi_rancher2 import Provider, Cluster, ClusterRkeConfigArgs, ClusterRkeConfigNodeArgs
from keys.keys import private_key

config = Config()

rancher_api_url = config.require("rancherApiUrl")
rancher_token = config.require_secret("rancherToken")

rancher_provider = Provider("rancher2", api_url=rancher_api_url, token_key=rancher_token)

def deploy(nodes, bastion_instance, subnet_instance):
    node_config = []
    for node in nodes["worker_nodes"]:
        node_config.append(
            ClusterRkeConfigNodeArgs(
                address=node.access_ip_v4,
                internal_address=node.access_ip_v4,
                user=config.require("sshUser"),
                roles=["worker"],
                ssh_key=private_key.private_key_pem,
            )
        )
    
    node_config.append(
        ClusterRkeConfigNodeArgs(
            address=nodes["control_node"].access_ip_v4,
            internal_address=nodes["control_node"].access_ip_v4,
            user=config.require("sshUser"),
            roles=["etcd", "controlplane"],
            ssh_key=private_key.private_key_pem,
        )
    )

    rke_cluster = Cluster(
        "my-rke2-cluster",
        name="my-rke2-cluster",
        rke_config=ClusterRkeConfigArgs(
            kubernetes_version=config.require("kubernetesVersion"),
            nodes=node_config
        ),
        opts=pulumi.ResourceOptions(
            provider=rancher_provider,
            depends_on=[bastion_instance.bastion_instance, subnet_instance],
        ),
    )

    # Corrected line: Use `kube_config` instead of `kube_config_yaml`
    pulumi.export("kubeconfig", rke_cluster.kube_config)

    modified_kubeconfig = pulumi.Output.all(
        rke_cluster.kube_config,
        bastion_instance.bastion_floating_ip_association.floating_ip,
        nodes["control_node"].access_ip_v4,
    ).apply(
        lambda args: args[0].replace(f"{args[2]}", f"{args[1]}")
    )

    modified_kubeconfig.apply(lambda v: open("kubeconfig.yaml", "w").write(v))
    return rke_cluster, modified_kubeconfig
