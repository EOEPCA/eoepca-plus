import pulumi
from pulumi import Config
from pulumi_openstack import loadbalancer, networking

config = Config()

def deploy(subnet_id):
    lb_floating_ip_id = config.require("loadBalancerFloatingIPID")
    floating_ip = networking.FloatingIp.get("k8s-floating-ip", id=lb_floating_ip_id)

    lb = loadbalancer.LoadBalancer(
        "k8s-lb",
        name="k8s-lb",
        vip_subnet_id=subnet_id,
    )

    # Attach the primary floating IP to the load balancer
    lb_floating_ip = networking.FloatingIpAssociate(
        "lb-floating-ip",
        floating_ip=floating_ip.address,
        port_id=lb.vip_port_id,
        opts=pulumi.ResourceOptions(depends_on=[lb]),
    )

    # Existing Listeners and Pools
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


    # Create a Second Load Balancer for APISIX
    apisix_lb = loadbalancer.LoadBalancer(
        "apisix-lb",
        name="apisix-lb",
        vip_subnet_id=subnet_id,
        opts=pulumi.ResourceOptions(depends_on=[lb]),
    )

    # Allocate a Floating IP for APISIX Load Balancer
    apisix_floating_ip = networking.FloatingIp(
        "apisix-floating-ip",
        pool=config.require("floatingIpPool"),
        opts=pulumi.ResourceOptions(depends_on=[apisix_lb]),
    )

    # Associate the Floating IP with APISIX Load Balancer's VIP Port
    apisix_floating_ip_association = networking.FloatingIpAssociate(
        "apisix-floating-ip-association",
        floating_ip=apisix_floating_ip.address,
        port_id=apisix_lb.vip_port_id,
        opts=pulumi.ResourceOptions(depends_on=[apisix_floating_ip]),
    )

    # Create Listeners and Pools for APISIX
    apisix_listener = loadbalancer.Listener(
        "apisix-listener",
        loadbalancer_id=apisix_lb.id,
        protocol="TCP",
        protocol_port=80,
        opts=pulumi.ResourceOptions(depends_on=[apisix_lb]),
    )

    apisix_pool = loadbalancer.Pool(
        "apisix-pool",
        listener_id=apisix_listener.id,
        protocol="TCP",
        lb_method=config.get("lbMethod") or "ROUND_ROBIN",
        opts=pulumi.ResourceOptions(depends_on=[apisix_listener]),
    )

    apisix_https_listener = loadbalancer.Listener(
        "apisix-https-listener",
        loadbalancer_id=apisix_lb.id,
        protocol="TCP",
        protocol_port=443,
        opts=pulumi.ResourceOptions(depends_on=[apisix_lb]),
    )

    apisix_https_pool = loadbalancer.Pool(
        "apisix-https-pool",
        listener_id=apisix_https_listener.id,
        protocol="TCP",
        lb_method=config.get("lbMethod") or "ROUND_ROBIN",
        opts=pulumi.ResourceOptions(depends_on=[apisix_https_listener]),
    )

    return (
        api_pool,
        http_pool,
        https_pool,
        floating_ip,
        apisix_pool,
        apisix_floating_ip,
        apisix_lb,
        apisix_https_pool,
    )

def add_member(name, node, http_pool, https_pool, apisix_pool, apisix_https_pool, subnet_instance):
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

    # Add Members to APISIX Pool
    apisix_member = loadbalancer.Member(
        f"{name}-apisix",
        address=node.access_ip_v4,
        protocol_port=32080,
        pool_id=apisix_pool.id,
        subnet_id=subnet_instance.id,
        opts=pulumi.ResourceOptions(depends_on=[apisix_pool]),
    )

    apisix_member_https = loadbalancer.Member(
        f"{name}-apisix-https",
        address=node.access_ip_v4,
        protocol_port=32443,
        pool_id=apisix_https_pool.id,
        subnet_id=subnet_instance.id,
        opts=pulumi.ResourceOptions(depends_on=[apisix_https_pool]),
    )
