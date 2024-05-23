# Zoo-DRU `Application`

Zoo-DRU is deployed as an ArgoCD `Application` using the `zoo-project-dru` helm chart from the [ZOO-Project helm chart repository](https://zoo-project.github.io/charts/).

Of particular interest is the approach to the specification of the helm values - which are provided through multiple dedicated values files.

The values files are referenced using the approach described in the ArgoCD documentation section ['Helm value files from external Git repository'](https://argo-cd.readthedocs.io/en/stable/user-guide/multiple_sources/#helm-value-files-from-external-git-repository)...

* The git repo is defined as a `source` for the values...
  ```
  - repoURL: https://github.com/EOEPCA/eoepca-plus
    targetRevision: deploy-rconway
    ref: values
  ```
* The values files are then referenced from this source...
  ```
  valueFiles:
    - $values/argocd/eoepca/zoo-dru/values-zoo.yaml
    - $values/argocd/eoepca/zoo-dru/values-stageout.yaml
  ```
