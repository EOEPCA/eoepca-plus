import os
import pulumi_tls as tls
from pulumi import Config
from pulumi_openstack import compute

config = Config()

# Generate an SSH key pair for the instance
private_key = tls.PrivateKey("rke2-node-key", algorithm="RSA")
private_key_path = "rke2-generated_key.pem"


def write_key(pem):
    if os.path.exists(private_key_path):
        os.chmod(private_key_path, 0o600)
    with open(private_key_path, "wb") as f:
        f.write(pem.encode())
    os.chmod(private_key_path, 0o400)


private_key.private_key_pem.apply(write_key)


def deploy():
    key_pair = compute.Keypair(
        "rke2-ssh-key-pair",
        name="rke2-eoepca-keypair",
        public_key=private_key.public_key_openssh,
    )

    return key_pair