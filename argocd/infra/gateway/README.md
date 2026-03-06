
# Gateway - Traffic Routing - `develop` cluster

The motivation for this `Gateway` is to address the needs for multiple points of TLS termination:
* APISIX ingress controller, including IAM policy enforcement
* Workspace vClusters exposing Kubernetes API access with dedicated TLS certificates

The platform exposes a single public entrypoint - which must route the traffic to these internal endpoints. **Significantly, the traffic must be routed with SSL passthrough such that APISIX and the Workspace vClusters can perform their own SSL termination.**

The outcome of this approach, from the point if the building-blocks, is largely transparent:
* BBs create `Ingress` and `ApisixRoute` resources as per existing approach - to be satisfied by APISIX
* To expose Workspace vCluster Kubernetes API - the Workspace BB can use `TLSRoute` resources instead of the current `Ingress` resources used - which are directly routed (SSL passthrough) from the gateway to the vCluster endpoint - see [TLS Passthrough](#tls-passthrough) below

## Plumbing

Single public facing IP address `64.225.140.153`.

```
Internet
 -> Load-balancer - 64.225.140.153 (Cloudferro)
     -> Envoy Gateway - `NodePort 31080/31443`
         -> APISIX (default route) - `*.rke2.deploybox.co.uk` - full TLS passthrough
         -> Nginx (specific route) - `*.ngx.rke2.deploybox.co.uk` - full TLS passthrough
```

> NOTE that the second public IP address is no longer required - since the `Gateway` allows to better handle combined traffic destined for APISIX and nginx, without the need to split the traffic with dedicated IPs.

## DNS records

```
*.rke2.deploybox.co.uk.  300  IN  CNAME  rke2.deploybox.co.uk.
rke2.deploybox.co.uk.    197  IN  A      64.225.140.153
```

## TLS Passthrough

The `Gateway` allows to configure [full TLS passthrough](parts/gateway-eoepca-public.yaml), for both [APISIX](parts/route-apisix.yaml) and [nginx](parts/route-nginx.yaml)...

```yaml
  listeners:
    - name: http
      protocol: HTTP
      port: 80
      allowedRoutes:
        namespaces:
          from: All
    - name: https
      protocol: TLS
      port: 443
      tls:
        mode: Passthrough
      allowedRoutes:
        namespaces:
          from: All
```

> NOTE that `ingress-nginx` is only retained in support of the Workspace vCluster (Kubernetes API).<br>
> These can be be migrated from `Ingress` to `TLSRoute` - at which which point `ingress-nginx` and `*.ngx.` can be deprecated.

For example, the Workspace vCluster `Ingress` for user `eoepcauser` can be migrated to...

```yaml
apiVersion: gateway.networking.k8s.io/v1alpha2
kind: TLSRoute
metadata:
  name: vcluster
  namespace: ws-eoepcauser
spec:
  parentRefs:
    - name: eoepca-public
      namespace: gateway
  hostnames:
    - ws-eoepcauser.rke2.deploybox.co.uk
  rules:
    - backendRefs:
        - name: vcluster-ws-eoepcauser
          port: 443
```

> NOTE the `.ngx` is dropped - which may require update of the associated kubeconfig/certs.
