# Podcast Generator - Kubernetes Deployment Guide

This guide explains how to deploy the Podcast Generator application on a Kubernetes cluster using Digital Ocean.

## Prerequisites

- [Digital Ocean](https://www.digitalocean.com/) account with API access
- [doctl](https://docs.digitalocean.com/reference/doctl/how-to/install/) command-line tool
- [kubectl](https://kubernetes.io/docs/tasks/tools/) command-line tool
- [Docker](https://docs.docker.com/get-docker/) installed locally (for building images)
- A domain name with access to DNS settings

## Environment Setup

1. Create a `.env` file in the root of the project with the following variables:

```
REPLICATE_API_TOKEN=your_replicate_token
REPLICATE_OWNER=your-replicate-username
REPLICATE_LORA_TRAINER_MODEL=model_id
DJANGO_SECRET_KEY=your_secret_key
DJANGO_SETTINGS_MODULE=config.settings
DJANGO_DEBUG=False
DOMAIN=example.com
K8S_DOMAIN=k8s.example.com
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_db_password
DO_API_TOKEN=your_do_api_token
DO_SPACES_BUCKET=your_spaces_bucket
DO_SPACES_KEY=your_spaces_key
DO_SPACES_SECRET=your_spaces_secret
```

## Kubernetes Cluster Setup

### 1. Create a Kubernetes cluster on Digital Ocean

```bash
doctl kubernetes cluster create podcast-generator-cluster \
  --region nyc3 \
  --node-pool "name=podcast-generator-worker-pool;size=s-2vcpu-4gb;count=3;tag=podcast-generator" \
  --version latest
```

### 2. Configure kubectl to use your cluster

```bash
doctl kubernetes cluster kubeconfig save podcast-generator-cluster
kubectl get nodes # Verify connection
```

### 3. Building and Pushing the Docker Image

You can either:

A) Use the deployment script which builds and pushes the image:
```bash
./deployment/k8s-deploy.sh
```

B) Build and push manually:
```bash
# Log in to DO Container Registry
doctl registry login --expiry-seconds 3600

# Build and tag the image
docker build -t registry.digitalocean.com/podcast-generator-registry/podcast-generator:latest .

# Push the image
docker push registry.digitalocean.com/podcast-generator-registry/podcast-generator:latest
```

## Deployment

### Option 1: Using the Deployment Script (Recommended)

```bash
./deployment/k8s-deploy.sh
```

This script:
- Creates the Kubernetes namespace
- Configures secrets and config maps
- Sets up persistent volume claims
- Deploys all components (Redis, web, Celery, Nginx)
- Configures the ingress with SSL
- Checks deployment status

### Option 2: Manual Deployment

1. Create the namespace:
```bash
kubectl create namespace podcast-generator
```

2. Apply the Kubernetes configuration files:
```bash
kubectl apply -f k8s/01-namespace.yaml
kubectl apply -f k8s/02-configmap.yaml
kubectl apply -f k8s/03-persistent-volumes.yaml
kubectl apply -f k8s/04-secrets.yaml
kubectl apply -f k8s/05-redis.yaml
kubectl apply -f k8s/06-web-deployment.yaml
kubectl apply -f k8s/07-celery-deployment.yaml
kubectl apply -f k8s/08-celery-beat-deployment.yaml
kubectl apply -f k8s/09-nginx-config.yaml
kubectl apply -f k8s/10-services.yaml
kubectl apply -f k8s/11-cert-issuer.yaml
kubectl apply -f k8s/12-ingress.yaml
kubectl apply -f k8s/13-hpa.yaml
```

## Critical Notes and Troubleshooting

### 1. Persistent Volume Claims
- Digital Ocean Block Storage only supports **ReadWriteOnce** access mode
- Make sure to set the access mode to ReadWriteOnce in your PVC configurations

### 2. DNS Configuration
- Point your domain (e.g., `k8s.example.com`) to the Load Balancer IP:
```bash
LB_IP=$(kubectl get service nginx -n podcast-generator -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "Configure DNS for k8s.example.com to point to $LB_IP"
```

### 3. Common Issues

#### PVC Not Binding
```bash
kubectl get pvc -n podcast-generator # Check status
kubectl describe pvc media-pvc -n podcast-generator # Get details on errors
```

#### Pods Not Starting
```bash
kubectl get pods -n podcast-generator # Check pod status
kubectl describe pod <pod-name> -n podcast-generator # Get details on errors
kubectl logs <pod-name> -n podcast-generator # Check container logs
```

#### SSL Certificate Issues
```bash
kubectl get certificates -n podcast-generator
kubectl describe certificate app-tls -n podcast-generator
kubectl get certificaterequests -n podcast-generator
```

#### Resource Issues
Check if your nodes have sufficient resources:
```bash
kubectl describe nodes
```

Consider updating resource requests/limits in your deployment YAML files if your cluster has limited resources.

## Monitoring and Management

### Check Deployment Status
```bash
kubectl get all -n podcast-generator
```

### View Application Logs
```bash
kubectl logs -f deployment/web -n podcast-generator
kubectl logs -f deployment/celery -n podcast-generator
```

### Access a Shell in Web Pod
```bash
kubectl exec -it deployment/web -n podcast-generator -- bash
```

### Port Forward for Local Testing
```bash
kubectl port-forward service/web -n podcast-generator 8000:8000
```

## GitHub Actions Integration

To enable CI/CD with GitHub Actions:

1. Add the following secrets to your GitHub repository:
   - `DO_API_TOKEN`
   - `REPLICATE_API_TOKEN`
   - `REPLICATE_OWNER`
   - `REPLICATE_LORA_TRAINER_MODEL`
   - `DJANGO_SECRET_KEY`
   - `DOMAIN` (your main domain)
   - `K8S_DOMAIN` (your Kubernetes-specific subdomain)
   - `POSTGRES_DB`
   - `POSTGRES_USER`
   - `POSTGRES_PASSWORD`
   - `DO_SPACES_BUCKET`
   - `DO_SPACES_KEY`
   - `DO_SPACES_SECRET`

2. The GitHub workflow file at `.github/workflows/deploy.yml` will automatically:
   - Build and push the Docker image
   - Deploy to your Kubernetes cluster
   - Update DNS records (if requested)
   - Run database migrations (if requested)

3. You can trigger a deployment manually from the GitHub Actions tab, or it will deploy automatically on pushes to the main branch.

## Updating the Application

To update the application:

1. Make your code changes
2. Push to the main branch (or manually trigger GitHub Actions)
3. The CI/CD pipeline will handle the deployment

Alternatively, you can update locally:
```bash
./deployment/k8s-deploy.sh
```

# Migrations

```bash
kubectl exec -it deployment/web -n podcast-generator -- python manage.py makemigrations
kubectl exec -it deployment/web -n podcast-generator -- python manage.py migrate
```
