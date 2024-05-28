import pulumi_tls as tls
from pulumi import Config
from pulumi_openstack import compute

config = Config()

# Generate an SSH key pair for the instance
private_key = tls.PrivateKey("node-key", algorithm="RSA")
private_key_path = "generated_key.pem"
private_key.private_key_pem.apply(
    lambda pem: open(private_key_path, "wb").write(pem.encode())
)


def deploy():
    # Create key pair
    key_pair = compute.Keypair(
        "ssh-key-pair",
        name=config.require("keyPairName"),
        public_key=private_key.public_key_openssh,
    )

    return key_pair
