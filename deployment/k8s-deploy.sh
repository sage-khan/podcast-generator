#!/bin/bash
set -e

echo "==================================================================="
echo "Podcast Generator Kubernetes Deployment"
echo "==================================================================="

# Define variables
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
K8S_DIR="$PROJECT_ROOT/k8s"
ENV_FILE="$PROJECT_ROOT/.env"
KUBECONFIG_PATH="${KUBECONFIG:-$HOME/.kube/config}"

# Initialize status flags
ALL_CHECKS_PASSED=true
REGISTRY_LOGIN_SUCCESS=false

# Make script executable
chmod +x "$0"

# Source environment variables
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment variables from $ENV_FILE..."
    set -a
    source "$ENV_FILE"
    set +a
else
    echo "Error: Environment file not found at $ENV_FILE"
    exit 1
fi

# Set default values if not defined in .env
K8S_NAMESPACE="${K8S_NAMESPACE:-podcast-generator}"
K8S_DOCKER_IMAGE="${K8S_REGISTRY}/${K8S_REGISTRY_NAME}/${K8S_IMAGE_NAME}:latest"

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed. Please install it first."
    exit 1
fi

# Check if kubeconfig is accessible
if [ ! -f "$KUBECONFIG_PATH" ]; then
    echo "Error: kubeconfig file not found at $KUBECONFIG_PATH"
    echo "Please ensure you have configured your kubeconfig file correctly."
    exit 1
fi

# Check DO CLI access with token
echo "Checking Digital Ocean access..."
if [ -z "$DO_API_TOKEN" ]; then
    echo "Error: Digital Ocean API token not found in environment variables."
    ALL_CHECKS_PASSED=false
else
    echo "Digital Ocean API token found. "
fi

# Set up DO CLI if available
if command -v doctl &> /dev/null; then
    echo "Authenticating with Digital Ocean..."
    doctl auth init -t "$DO_API_TOKEN"
    
    # Get Kubernetes cluster configuration
    echo "Getting Kubernetes cluster configuration..."
    # List available clusters
    echo "Available Kubernetes clusters:"
    doctl kubernetes cluster list
    
    # Get the first cluster ID (or you can filter for a specific cluster name)
    CLUSTER_ID=$(doctl kubernetes cluster list --format ID --no-header | head -n 1)
    
    if [ -z "$CLUSTER_ID" ]; then
        echo "ERROR: No Kubernetes clusters found in Digital Ocean account"
        ALL_CHECKS_PASSED=false
    else
        echo "Using Kubernetes cluster ID: $CLUSTER_ID"
        doctl kubernetes cluster kubeconfig save $CLUSTER_ID
    fi
    
    # Login to container registry
    echo "Logging into Digital Ocean container registry..."
    doctl registry login
    if [ $? -eq 0 ]; then
        echo "Successfully logged into Digital Ocean container registry. "
        REGISTRY_LOGIN_SUCCESS=true
    else
        echo "Warning: Failed to login to Digital Ocean container registry."
        echo "Will attempt direct Docker login as fallback."
    fi
else
    echo "Warning: Digital Ocean CLI (doctl) not found."
    echo "Will attempt direct Docker login to registry."
fi

# Fallback Docker registry login if doctl failed or is not available
if [ "$REGISTRY_LOGIN_SUCCESS" = false ]; then
    echo "Logging into Docker registry using direct authentication..."
    echo "$DO_API_TOKEN" | docker login ${K8S_REGISTRY} -u "$DO_API_TOKEN" --password-stdin
    if [ $? -eq 0 ]; then
        echo "Successfully logged into Docker registry. "
        REGISTRY_LOGIN_SUCCESS=true
    else
        echo "Error: Failed to login to Docker registry."
        ALL_CHECKS_PASSED=false
    fi
fi

# Final checks before proceeding
if [ "$ALL_CHECKS_PASSED" = false ]; then
    echo "Error: Some prerequisite checks failed. Please fix the issues above before continuing."
    exit 1
fi

# Check if we should skip image build (useful for quick redeployments)
if [ "$1" = "--skip-build" ]; then
    echo "Skipping Docker image build as requested..."
    SKIP_BUILD=true
else
    SKIP_BUILD=false
fi

# Build and push Docker image if not skipped
if [ "$SKIP_BUILD" = false ]; then
    echo "Building and pushing Docker image to Digital Ocean registry..."
    docker build -t ${K8S_DOCKER_IMAGE} "$PROJECT_ROOT"
    if [ $? -ne 0 ]; then
        echo "Error: Docker build failed. Please check your Dockerfile and try again."
        exit 1
    fi

    echo "Pushing Docker image to registry..."
    docker push ${K8S_DOCKER_IMAGE}
    if [ $? -ne 0 ]; then
        echo "Error: Failed to push Docker image to registry."
        echo "Please ensure you are logged into the Docker registry."
        exit 1
    fi
else
    echo "Using existing Docker image: ${K8S_DOCKER_IMAGE}"
fi

# Deploy Kubernetes resources in the correct order
echo "Deploying Kubernetes resources..."

# Create namespace
echo "1. Creating namespace..."
kubectl apply -f "$K8S_DIR/00-namespace.yaml"

# Create ConfigMap and Secrets
echo "2. Creating ConfigMap and Secrets..."
kubectl apply -f "$K8S_DIR/01-secrets.yaml" -f "$K8S_DIR/02-configmap.yaml"

# Create Persistent Volume Claims
echo "3. Creating Persistent Volume Claims..."
kubectl apply -f "$K8S_DIR/03-persistent-volumes.yaml" -f "$K8S_DIR/05-redis-pvc.yaml"

# Wait for PVCs to be bound
echo "Waiting for PVCs to be bound..."
kubectl wait --for=condition=bound pvc/media-pvc -n ${K8S_NAMESPACE} --timeout=60s || true
kubectl wait --for=condition=bound pvc/redis-pvc -n ${K8S_NAMESPACE} --timeout=60s || true
echo "Note: PVCs may take time to bind fully. Continuing deployment..."

# Check if managed PostgreSQL is available
echo "Checking managed PostgreSQL availability..."
PGHOST=$(kubectl get configmap app-config -n ${K8S_NAMESPACE} -o jsonpath='{.data.PGHOST}' 2>/dev/null)
PGPORT=$(kubectl get configmap app-config -n ${K8S_NAMESPACE} -o jsonpath='{.data.PGPORT}' 2>/dev/null)
PGUSER=$(kubectl get secret app-secrets -n ${K8S_NAMESPACE} -o jsonpath='{.data.POSTGRES_USER}' | base64 --decode 2>/dev/null)
PGPASSWORD=$(kubectl get secret app-secrets -n ${K8S_NAMESPACE} -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 --decode 2>/dev/null)

# Try to connect to the managed PostgreSQL
if [ -n "$PGHOST" ] && [ -n "$PGPORT" ] && [ -n "$PGUSER" ] && [ -n "$PGPASSWORD" ]; then
  echo "Attempting to connect to managed PostgreSQL at $PGHOST:$PGPORT..."
  # Use a temporary pod to test the connection
    # Modified code
    if kubectl run pg-test --rm -it --restart=Never -n ${K8S_NAMESPACE} --image=postgres:13 \
    --env="PGPASSWORD=$PGPASSWORD" \
    --env="PGSSLMODE=verify-ca" \
    --env="PGSSLROOTCERT=/ca/ca.crt" \
    --overrides='{
        "spec": {
        "containers": [
            {
            "name": "pg-test",
            "image": "postgres:13",
            "env": [
                {"name": "PGPASSWORD", "value": "'$PGPASSWORD'"}
            ],
            "volumeMounts": [
                {"name": "ca-cert", "mountPath": "/ca"}
            ],
            "command": ["psql", "-h", "'$PGHOST'", "-p", "'$PGPORT'", "-U", "'$PGUSER'", "-c", "SELECT 1"]
            }
        ],
        "volumes": [
            {"name": "ca-cert", "secret": {"secretName": "postgres-ca"}}
        ]
        }
    }' -- /bin/bash >/dev/null 2>&1; then
    echo "Successfully connected to managed PostgreSQL. Skipping local PostgreSQL deployment."
    USING_MANAGED_DB=true
  else
    echo "Failed to connect to managed PostgreSQL. Falling back to local PostgreSQL deployment."
    USING_MANAGED_DB=false
  fi
else
  echo "Managed PostgreSQL configuration not found. Using local PostgreSQL deployment."
  USING_MANAGED_DB=false
fi

# Deploy local PostgreSQL if managed is not available
if [ "$USING_MANAGED_DB" = "false" ]; then
  echo "3a. Creating PostgreSQL PVC..."
  kubectl apply -f "$K8S_DIR/03-postgres-pvc.yaml"
  
  echo "3b. Deploying local PostgreSQL..."
  kubectl apply -f "$K8S_DIR/04-postgres-deployment.yaml"
  
  echo "Waiting for PostgreSQL to be ready..."
  kubectl wait --for=condition=available deployment/postgres -n ${K8S_NAMESPACE} --timeout=120s || true
  echo "Note: PostgreSQL may take time to become available. Continuing deployment..."
  
  # Update the service to point to the local PostgreSQL
  echo "Updating configuration to use local PostgreSQL..."
  kubectl patch configmap app-config -n ${K8S_NAMESPACE} --type=merge -p '{"data":{"DB_HOST":"postgres", "DB_PORT":"5432"}}'
fi

# Deploy Redis
echo "4. Deploying Redis..."
kubectl apply -f "$K8S_DIR/05-redis-deployment.yaml"
echo "Waiting for Redis to be ready..."
kubectl wait --for=condition=available deployment/redis -n ${K8S_NAMESPACE} --timeout=120s || true
echo "Note: Redis may take time to become available. Continuing deployment..."

# Deploy Web and Celery
echo "5. Deploying Web and Celery services..."
kubectl apply -f "$K8S_DIR/06-web-deployment.yaml" -f "$K8S_DIR/07-celery-deployment.yaml" -f "$K8S_DIR/08-celery-beat-deployment.yaml"

# Deploy Nginx and Services
echo "6. Deploying Nginx and Services..."
kubectl apply -f "$K8S_DIR/09-nginx-config.yaml" -f "$K8S_DIR/10-nginx-deployment.yaml" -f "$K8S_DIR/11-services.yaml"

# Configure Ingress and Cert Issuer
echo "7. Configuring Ingress and Certificate Issuer..."

# Create bootstrap SSL certificate if it doesn't exist
if ! kubectl get secret app-tls -n ${K8S_NAMESPACE} &>/dev/null; then
  echo "Creating bootstrap SSL certificate for initial deployment..."
  
  # Create temporary directory for certificate files
  TMP_CERT_DIR=$(mktemp -d)
  
  # Generate self-signed certificate
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ${TMP_CERT_DIR}/tls.key -out ${TMP_CERT_DIR}/tls.crt \
    -subj "/CN=${K8S_DOMAIN}" -addext "subjectAltName=DNS:${K8S_DOMAIN}"
  
  # Create Kubernetes secret with the certificate
  kubectl create secret tls app-tls -n ${K8S_NAMESPACE} \
    --key=${TMP_CERT_DIR}/tls.key --cert=${TMP_CERT_DIR}/tls.crt
  
  # Clean up temporary files
  rm -rf ${TMP_CERT_DIR}
  
  echo "Bootstrap SSL certificate created successfully."
fi

kubectl apply -f "$K8S_DIR/12-ingress.yaml" -f "$K8S_DIR/13-cert-issuer.yaml"

# Create Horizontal Pod Autoscalers if they exist
if [ -f "$K8S_DIR/14-web-hpa.yaml" ] && [ -f "$K8S_DIR/15-celery-hpa.yaml" ]; then
    echo "8. Creating Horizontal Pod Autoscalers..."
    kubectl apply -f "$K8S_DIR/14-web-hpa.yaml" -f "$K8S_DIR/15-celery-hpa.yaml"
fi

echo "==================================================================="
echo "Waiting for deployments to start... (This may take a few minutes)"
echo "==================================================================="

# Wait for deployments to start (not necessarily be ready)
sleep 30

echo "Checking deployment status..."
kubectl get pods -n ${K8S_NAMESPACE}

# Wait for web deployment to be ready with a longer timeout
echo "Waiting for web deployment to become available..."
kubectl wait --for=condition=available deployment/${K8S_DEPLOYMENT_NAME} -n ${K8S_NAMESPACE} --timeout=300s || true
echo "Note: Web deployment may still be initializing if the above wait failed."

echo "==================================================================="
echo "Deployment completed!"
echo "==================================================================="

# Get the LoadBalancer IP
echo "Getting LoadBalancer IP..."
LOADBALANCER_IP=$(kubectl get service nginx -n ${K8S_NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)

if [ -n "$LOADBALANCER_IP" ]; then
    echo "Your application is accessible at: http://$LOADBALANCER_IP"
    echo "For HTTPS access, configure your domain ($K8S_DOMAIN) to point to this IP."
    
    # Check for existing DNS record
    if command -v dig &> /dev/null && [ -n "$K8S_DOMAIN" ]; then
        echo "Checking DNS record for $K8S_DOMAIN..."
        DNS_IP=$(dig +short $K8S_DOMAIN)
        if [ -n "$DNS_IP" ]; then
            if [ "$DNS_IP" = "$LOADBALANCER_IP" ]; then
                echo ""
                echo "DNS record for $K8S_DOMAIN correctly points to $LOADBALANCER_IP"
            else
                echo ""
                echo "DNS record for $K8S_DOMAIN points to $DNS_IP, but should point to $LOADBALANCER_IP"
            fi
        else
            echo ""
            echo "No DNS record found for $K8S_DOMAIN. Please create an A record pointing to $LOADBALANCER_IP"
        fi
    fi
else
    echo "LoadBalancer IP not yet available. This is normal and may take a few minutes."
    echo "Check status with: kubectl get service nginx -n ${K8S_NAMESPACE}"
fi

# Testing webhook connectivity
if [ -n "$LOADBALANCER_IP" ] && [ -n "$K8S_DOMAIN" ]; then
    echo ""
    echo "Testing webhook connectivity (important for Replicate API callbacks)..."
    WEBHOOK_URL="${K8S_WEBHOOK_BASE_URL}/api/webhooks/test"
    if command -v curl &> /dev/null; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$WEBHOOK_URL" || echo "Failed")
        if [ "$HTTP_CODE" = "404" ]; then
            echo "Webhook endpoint accessible (404 is expected for test endpoint)"
        elif [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
            echo "Webhook endpoint accessible (status code: $HTTP_CODE)"
        else
            echo "Webhook test failed with status code: $HTTP_CODE"
            echo "   Replicate API may not be able to send callbacks. Check your SSL configuration."
        fi
    else
        echo "Curl not found. Cannot test webhook connectivity."
    fi
fi

echo ""
echo "Monitoring and Debugging Commands:"
echo "==================================="
echo "• View all resources:      kubectl get all -n ${K8S_NAMESPACE}"
echo "• Check pod logs:          kubectl logs -f deployment/${K8S_DEPLOYMENT_NAME} -n ${K8S_NAMESPACE}"
echo "• Check Celery logs:       kubectl logs -f deployment/celery -n ${K8S_NAMESPACE}"
echo "• Check Redis logs:        kubectl logs -f deployment/redis -n ${K8S_NAMESPACE}"
echo "• Access shell in web pod: kubectl exec -it deployment/${K8S_DEPLOYMENT_NAME} -n ${K8S_NAMESPACE} -- bash"
echo "• Port forward to web:     kubectl port-forward service/web -n ${K8S_NAMESPACE} 8000:8000"
echo "• Check SSL certificates:  kubectl get certificates -n ${K8S_NAMESPACE}"
echo "• Check Nginx ingress:     kubectl describe ingress -n ${K8S_NAMESPACE}"
echo ""
echo "Remember: The first deployment may take 5-10 minutes to fully initialize."
echo "To rebuild and redeploy:   run this script again."