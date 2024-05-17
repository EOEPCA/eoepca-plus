# EOEPCA ArgoCD App-of-apps

## Login

Login to argocd...

```
argocd login argocd.guide.svc.rconway.uk
```

Supply credentials of an admin user...

```
  Username: admin
  Password: <admin-password>
```

## Project

Create `eoepca` argocd project...

```
argocd proj create eoepca -f https://raw.githubusercontent.com/rconway/argo-deploy/develop/argocd/project.yaml
```

## App-of-apps

Create app-of-apps...

```
argocd app create eoepca \
  --project eoepca \
  --dest-namespace argocd \
  --dest-server https://kubernetes.default.svc \
  --repo https://github.com/rconway/argo-deploy \
  --path argocd \
  --revision develop \
  --sync-policy automated \
  --auto-prune \
  --self-heal
```
