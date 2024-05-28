# EOEPCA+ Deployment

**Still in development.**

This repository contains the Pulumi infrastructure code for setting up the EOEPCA+ platform on OpenStack.

## Prerequisites

Before you begin, make sure you have the following installed:
- [Python 3.x](https://www.python.org/downloads/)
- [Pulumi](https://www.pulumi.com/docs/get-started/install/)
- [OpenStack CLI](https://docs.openstack.org/python-openstackclient/latest/)

## Installation

1. **Clone the Repository**:
```
git clone https://github.com/EOEPCA/eoepca-pulumi-prototype
cd eoepca-pulumi-prototype
```

2. **Install Dependencies**:
```
pip install -r requirements.txt
```

3. **Setup Pulumi Locally**:
```
pulumi login --local
```

4. **Configure OpenStack Provider**:
Either set the necessary openstack environment variables, or run your openstack rc file:
```
source eoepca-openrc-2f.sh
```

5. **Create a new stack**:
```
pulumi stack init dev
```

6. **Deploy the stack**:
```
pulumi up
```

Review the plan and confirm the deployment by selecting `yes`.

## Project Structure

- `infra/`: Contains all infrastructure components like bastion, cluster, instances, etc.
- `k8s/`: Kubernetes resources including applications like ArgoCD, Cert Manager, and Ingress NGINX.
- `__main__.py`: The main entry point for Pulumi that orchestrates the deployment process.
- `Pulumi.yaml`: Contains the project's configuration details for Pulumi.

## License

This project is licensed under the terms of the Apache 2.0 license.

## Contributors

Feel free to contribute to this project by submitting issues and pull requests.
