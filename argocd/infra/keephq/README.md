Make sure to create the `keep-auth-secrets` Secret:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: keep-auth-secrets
  namespace: infra
type: Opaque
stringData:
  KEEP_JWT_SECRET: "your-generated-jwt-secret"
  KEEP_DEFAULT_PASSWORD: "your-admin-password"
```

Furthermore, Alertmanager needs a valid API Key from KeepHQ to push the alerts to it:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: keep-api-key
  namespace: "your-namespacce"
type: Opaque
stringData:
  username: api_key
  password: api_key

```
