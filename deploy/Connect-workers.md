# Point your domain DNS to the load balancer IP address

From the Pulumi output you should see the ArgoCD and Rancher on a floating IP and then 

`*.rke2` and `rke2.<YOUR DOMAIN>` which are the wildcard and root domain for your cluster. You will need to point these to the floating IP address listed at `apisix_floating_ip` in the Pulumi output.

# Connect Workers to Cluster

> You will not be able to access the Rancher dashboard until you have at least one worker node connected to the cluster.

With RKE2 there is a manual step to connect the workers to the cluster.

Once the `pulumi up` has completed, SSH into the control node with:

```bash
ssh -i rke2-generated_key.pem eouser@<YOUR BASTION IP>
ssh -i ~/.ssh/key.pem eouser@<YOUR CONTROL NODE IP>`
```

Retrieve the `node token` from the control node.

```bash
sudo cat /var/lib/rancher/rke2/server/node-token
```

__Optional__ Retrieve the `kubeconfig` file to use with `kubectl` on your local machine.

```bash
sudo cat /etc/rancher/rke2/rke2.yaml
```

Exit the control node and SSH into your worker node:

```bash
ssh -i ~/.ssh/key.pem eouser@<YOUR WORKER NODE IP>
```

Then modify and run the following:
```bash
curl -sfL https://get.rke2.io | INSTALL_RKE2_TYPE="agent" sudo sh -
sudo mkdir -p /etc/rancher/rke2
sudo tee /etc/rancher/rke2/config.yaml <<EOF
server: https://<CONTROL NODE IP>:9345
token: <THE NODE TOKEN YOU RETRIEVED EARLIER>
EOF

sudo systemctl enable rke2-agent.service
sudo systemctl start rke2-agent.service
```

This will then connect the worker to the cluster and you should see it in the output of `kubectl get nodes`.

Now proceed to `k8s-resources` directory one level above and run the `scripts/bootstrap-argocd.sh` script to deploy ArgoCD to the cluster.