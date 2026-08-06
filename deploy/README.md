
# EOEPCA+ Deployment

This repository contains the Pulumi infrastructure code for setting up the EOEPCA+ platform on OpenStack (primarily for development and testing).

## Prerequisites

Make sure you have the following installed:

- [Python 3.x](https://www.python.org/downloads/)
- [Pulumi](https://www.pulumi.com/docs/get-started/install/)
- [OpenStack CLI](https://docs.openstack.org/python-openstackclient/latest/)

## Installation

1. **Clone the Repository**
    
    ```bash
    git clone https://github.com/EOEPCA/eoepca-plus
    cd deploy
    ```
    
2. **Install Dependencies**
    
    ```bash
    cd infra/
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
    
3. **Set Up Pulumi Locally**
    
    ```bash
    pulumi login --local
    ```
    
4. **Configure OpenStack Provider**  
    Either source your OpenStack RC file or export the required environment variables. See Openstack documentation for openrc file generation, you should be able to download this file through the CloudFerro portal.
    
    ```bash
    source eoepca-openrc-2f.sh
    ```
    
5. **Create a New Pulumi Stack**
    
    ```bash
    pulumi stack init dev
    ```
    
6. **Configure Stack Variables**
    
    - Copy `Pulumi.example.yaml` to `Pulumi.dev.yaml` (or edit the example file directly) and update all the required values to match your environment. Key settings in `Pulumi.dev.yaml` (for the `infra` stack) include:
        - `domainName`: The domain name for your platform (e.g. `eoepca.org`).
        - `cloudflareDnsApiToken`: The Cloudflare DNS API token used by cert-manager during ArgoCD bootstrap.
        - `loadBalancerFloatingIPID`: An existing Floating IP ID for your load balancer. We chose to configure this outside of Pulumi, otherwise the Floating IP would be changed every time the stack is updated.
        - `externalNetworkID`: Your external (public) network ID in OpenStack. Configure this in the dashboard.

    - If you also plan to deploy resources in **`k8s-resources`**, you'll need to edit (or create) `Pulumi.dev.yaml` within that directory as well to set values such as:
        - `nfsServerIP`: The IP address of the NFS server created by `infra`.
        - `SSOClientID`, `SSOClientSecret`, `SSOOrg` and `SSOTeam`: GitHub OAuth client credentials for ArgoCD SSO. [See this guide for SSO Setup instructions](https://argo-cd.readthedocs.io/en/stable/operator-manual/user-management/#1-register-the-application-in-the-identity-provider).

7. **Deploy the Stack**
    
    ```bash
    pulumi up
    ```

    After the stack is deployed, Pulumi exports `bootstrap_argocd_command`, which includes the domain, NFS server IP, and Cloudflare token:

    ```bash
    pulumi stack output bootstrap_argocd_command
    ```
    
8. **(Optional) Deploy Kubernetes Resources**  
    If you also want to deploy the Kubernetes resources found under `k8s-resources/`, repeat similar steps in that directory (create a new stack, configure, and run `pulumi up`).
    

## Project Structure

- `infra/`: Contains the core infrastructure components such as Bastion, Network, Load Balancer, and Nodes.
- `k8s-resources/`: Contains Kubernetes resources (e.g., ArgoCD, Cert Manager, Ingress NGINX).

## License

This project is licensed under the Apache 2.0 license.

## Contributors

Feel free to contribute by submitting issues and pull requests.
