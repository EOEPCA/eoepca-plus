# Point your domain DNS to the load balancer IP address

From the Pulumi output you should see the ArgoCD and Rancher on a floating IP and then 

`*.rke2` and `rke2.<YOUR DOMAIN>` which are the wildcard and root domain for your cluster. You will need to point these to the floating IP address listed at `apisix_floating_ip` in the Pulumi output.

# Connect Workers to Cluster

> You will not be able to access the Rancher dashboard until you have at least one worker node connected to the cluster.

Worker connection is automated by the Pulumi stack in `infra/`.

Run the infrastructure deployment as normal:

```bash
cd infra
pulumi up
```

Pulumi now waits for the control node to expose its RKE2 node token and kubeconfig, uses the bastion to join each worker node as an RKE2 agent, waits for all Kubernetes nodes to become `Ready`, and writes an updated kubeconfig locally.

The local kubeconfig path is exported as `kubeconfig_path` and defaults to:

```bash
kubeconfig.yaml
```

You can use it with:

```bash
export KUBECONFIG="$(pulumi stack output kubeconfig_path)"
kubectl get nodes
```

The kubeconfig API endpoint defaults to the Kubernetes load balancer floating IP, and can be overridden with:

```bash
pulumi config set kubeconfigServer https://<HOSTNAME-OR-IP>:6443
```

If you need a different output path:

```bash
pulumi config set kubeconfigPath kubeconfig.yaml
```

The RKE2 node token is read directly on the bastion during the Pulumi run and is not exported.

Now proceed to `k8s-resources` directory one level above and run the `scripts/bootstrap-argocd.sh` script to deploy ArgoCD to the cluster.
