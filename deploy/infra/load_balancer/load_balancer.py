import pulumi
from pulumi import Config
from pulumi_openstack import loadbalancer, networking

config = Config()


def deploy(subnet_id):
    # Create the load balancer
    lb_floating_ip_id = config.require("loadBalancerFloatingIPID")
    floating_ip = networking.FloatingIp.get("k8s-floating-ip", id=lb_floating_ip_id)

    lb = loadbalancer.LoadBalancer(
        "k8s-lb",
        name="k8s-lb",
        vip_subnet_id=subnet_id,
    )

    # Attach the floating IP to the load balancer
    lb_floating_ip = networking.FloatingIpAssociate(
        "lb-floating-ip",
        floating_ip=floating_ip.address,
        port_id=lb.vip_port_id,
        opts=pulumi.ResourceOptions(depends_on=[lb]),
    )

    # Listener for the Kubernetes API server
    api_listener = loadbalancer.Listener(
        "k8s-listener",
        loadbalancer_id=lb.id,
        protocol="TCP",
        protocol_port=6443,  # Kubernetes API server port
        opts=pulumi.ResourceOptions(depends_on=[lb]),
    )

    # Listener for HTTP
    http_listener = loadbalancer.Listener(
        "http-listener",
        loadbalancer_id=lb.id,
        protocol="HTTP",
        protocol_port=80,
        opts=pulumi.ResourceOptions(depends_on=[lb]),
    )

    # Listener for HTTPS
    https_listener = loadbalancer.Listener(
        "https-listener",
        loadbalancer_id=lb.id,
        protocol="HTTPS",
        protocol_port=443,
        opts=pulumi.ResourceOptions(depends_on=[lb]),
    )

    # Pool for the API listener
    api_pool = loadbalancer.Pool(
        "k8s-pool",
        listener_id=api_listener.id,
        protocol="TCP",
        lb_method=config.get("lbMethod") or "ROUND_ROBIN",
        opts=pulumi.ResourceOptions(depends_on=[api_listener]),
    )

    # Pool for HTTP
    http_pool = loadbalancer.Pool(
        "http-pool",
        listener_id=http_listener.id,
        protocol="HTTP",
        lb_method=config.get("lbMethod") or "ROUND_ROBIN",
        opts=pulumi.ResourceOptions(depends_on=[http_listener]),
    )

    # Pool for HTTPS
    https_pool = loadbalancer.Pool(
        "https-pool",
        listener_id=https_listener.id,
        protocol="HTTPS",
        lb_method=config.get("lbMethod") or "ROUND_ROBIN",
        opts=pulumi.ResourceOptions(depends_on=[https_listener]),
    )

    return (
        api_pool,
        http_pool,
        https_pool,
        floating_ip,
    )


def add_member(name, node, http_pool, https_pool, subnet_instance):

    http_member = loadbalancer.Member(
        f"{name}-ingress-nginx-http",
        address=node.access_ip_v4,
        protocol_port=31080,
        pool_id=http_pool.id,
        subnet_id=subnet_instance.id,
        opts=pulumi.ResourceOptions(depends_on=[http_pool]),
    )

    https_member = loadbalancer.Member(
        f"{name}-ingress-nginx-https",
        address=node.access_ip_v4,
        protocol_port=31443,
        pool_id=https_pool.id,
        subnet_id=subnet_instance.id,
        opts=pulumi.ResourceOptions(depends_on=[https_pool]),
    )
