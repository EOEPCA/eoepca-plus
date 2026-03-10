# Connect Workers to Cluster

With RKE2 there is a manual step to connect the workers to the cluster.

Once the `pulumi up` has completed, SSH into the control node with:

```bash
ssh -i rke2-generated_key.pem eouser@<YOUR BASTION IP>
ssh -i ~/.ssh/key.pem eouser@<YOUR CONTROL NODE IP>`
```

Retrieve the `node token`

```bash
sudo cat /var/lib/rancher/rke2/server/node-token
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

This will then connect the worker to the cluster and you should see it in the output of `kubectl get nodes` on the control node.