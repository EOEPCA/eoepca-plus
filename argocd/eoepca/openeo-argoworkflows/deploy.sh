#!/bin/bash

# OpenEO ArgoWorkflows Deployment Script
# This script deploys the OpenEO ArgoWorkflows application using ArgoCD

set -e

echo "🚀 Deploying OpenEO ArgoWorkflows via ArgoCD..."

# Check if ArgoCD is available
if ! kubectl get ns argocd >/dev/null 2>&1; then
    echo "❌ ArgoCD namespace not found. Please install ArgoCD first."
    echo "   kubectl create namespace argocd"
    echo "   kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml"
    exit 1
fi

# Apply the ArgoCD Application
echo "📦 Applying ArgoCD Application..."
kubectl apply -f app-openeo-argoworkflows.yaml

echo "✅ OpenEO ArgoWorkflows application submitted to ArgoCD"
echo ""
echo "📊 Monitor deployment with:"
echo "   argocd app get openeo-argoworkflows"
echo "   argocd app sync openeo-argoworkflows"
echo ""
echo "🔍 Check status with:"
echo "   kubectl get pods -n openeo"
echo ""
echo "🌐 Access API (after deployment) with:"
echo "   kubectl port-forward -n openeo svc/openeo-openeo-argo 8080:8000"
echo "   curl http://localhost:8080/openeo/1.1.0/"