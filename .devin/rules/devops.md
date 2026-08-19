---
trigger: always_on
---

# 🚀 Devin DevOps Best Practices

Comprehensive guidelines for containerization, orchestration, infrastructure as code, and deployment automation.

---

## 🐳 Docker Best Practices

### Image Optimization

**Reduce Image Size:**
- Use **multi-stage builds** to separate build dependencies from runtime
- Start with minimal base images: `alpine`, `distroless`, or `scratch` when possible
- Combine `RUN` commands to reduce layers: `RUN apt-get update && apt-get install -y pkg && rm -rf /var/lib/apt/lists/*`
- Clean up package manager caches in the same layer they're created
- Use `.dockerignore` aggressively to exclude unnecessary files

**Critical .dockerignore Rules:**
```
# Development files
.git/
.gitignore
.env*
*.md
docs/

# Datasets and large files (CRITICAL - often forgotten)
datasets/
data/
*.csv
*.json
*.parquet
*.arrow
*.h5
*.hdf5
literature/
research/
*.pdf

# Build artifacts
target/
build/
dist/
node_modules/
__pycache__/
*.pyc
.pytest_cache/

# IDE and OS
.vscode/
.idea/
.DS_Store
*.swp
```

**Layer Caching Strategy:**
- Order instructions from least to most frequently changed
- Copy dependency files first (package.json, requirements.txt, go.mod)
- Install dependencies before copying source code
- Use `COPY --from=builder` to copy only artifacts from build stage

**Security:**
- Never include secrets in images - use environment variables or secrets management
- Scan images with `docker scan` or `trivy` before deployment
- Run containers as non-root user: `USER nonroot`
- Use specific image tags, never `:latest` in production
- Keep base images updated for security patches

**Example Multi-Stage Build:**
```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

# Production stage
FROM node:20-alpine
RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001
WORKDIR /app
COPY --from=builder --chown=nodejs:nodejs /app/dist ./dist
COPY --from=builder --chown=nodejs:nodejs /app/node_modules ./node_modules
USER nodejs
EXPOSE 3000
CMD ["node", "dist/index.js"]
```

---

## 🎯 Docker Compose Best Practices

**Resource Management:**
```yaml
services:
  api:
    image: myapp:latest
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

**Best Practices:**
- Use `depends_on` with health checks, not just service names
- Define explicit networks instead of default bridge
- Use named volumes for persistence
- Set `restart` policies appropriately
- Always include health checks for critical services
- Use environment variable files (.env) instead of hardcoded values
- Version your compose files: `version: '3.8'`

---

## ☸️ Kubernetes Best Practices

### Resource Management

**Always Define Resource Requests and Limits:**
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

**Why:**
- Requests ensure pod scheduling on appropriate nodes
- Limits prevent resource hogging and cascading failures
- Enables horizontal pod autoscaling (HPA)

**Resource Sizing Guidelines:**
- Start conservative, measure, adjust
- Set limits 1.5-2x higher than requests
- Memory limits should account for spikes (JVM heap, Python GC)
- CPU throttling is acceptable, OOM kills are not

### Pod Design

**One Concern Per Container:**
- Main application in primary container
- Sidecar containers for auxiliary tasks (logging, proxy, metrics)
- Init containers for setup tasks
- Avoid running multiple processes in one container

**Health Checks:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 2
```

**Liveness vs Readiness:**
- Liveness: Is the container alive? (restart if fails)
- Readiness: Is the container ready to serve traffic? (remove from service if fails)
- Startup: For slow-starting containers (prevents premature kills)

### Deployment Strategies

**Rolling Updates:**
```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
```

**Blue-Green or Canary:**
- Use service mesh (Istio, Linkerd) or ingress controller (Nginx, Traefik)
- Gradually shift traffic to new version
- Monitor error rates and rollback if needed

**Pod Disruption Budgets:**
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: api
```

### Security

**RBAC:**
- Principle of least privilege
- Use service accounts for pods
- Never use cluster-admin unless absolutely necessary
- Audit RBAC regularly

**Network Policies:**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-network-policy
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
```

**Secrets Management:**
- Use external secrets operator (AWS Secrets Manager, Vault, Google Secret Manager)
- Never commit secrets to Git
- Rotate secrets regularly
- Use sealed-secrets or SOPS for GitOps

---

## 🏗️ Infrastructure as Code (Terraform)

### Project Structure

```
terraform/
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   ├── staging/
│   └── prod/
├── modules/
│   ├── vpc/
│   ├── eks/
│   └── rds/
├── global/
│   └── s3-backend/
└── README.md
```

### Best Practices

**State Management:**
- Always use remote backend (S3 + DynamoDB, Terraform Cloud, GCS)
- Enable state locking to prevent concurrent modifications
- Encrypt state files (contains sensitive data)
- Use separate state files per environment
- Never commit state files to Git

**Module Design:**
- Keep modules focused and reusable
- Use semantic versioning for modules
- Document inputs, outputs, and examples
- Validate inputs with validation blocks
- Use `terraform-docs` to auto-generate documentation

**Resource Naming:**
```hcl
resource "aws_instance" "web" {
  # Use consistent naming convention
  tags = {
    Name        = "${var.environment}-${var.project}-web"
    Environment = var.environment
    Project     = var.project
    ManagedBy   = "terraform"
  }
}
```

**Variables and Outputs:**
```hcl
variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
  
  validation {
    condition     = can(regex("^t3\\.", var.instance_type))
    error_message = "Only t3 instance types allowed in this environment."
  }
}

output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.web.id
}

output "db_password" {
  description = "Database password"
  value       = aws_db_instance.main.password
  sensitive   = true  # Never log sensitive outputs
}
```

**Cost Optimization:**
- Use `terraform plan` to preview costs before apply
- Tag all resources for cost allocation
- Use spot instances where appropriate
- Set up budget alerts
- Clean up unused resources regularly
- Use resource lifecycle policies

**Security:**
- Use terraform.tfvars for non-sensitive defaults
- Store secrets in parameter stores/secret managers
- Enable encryption at rest and in transit
- Use private subnets for databases
- Implement least privilege IAM policies
- Enable CloudTrail/audit logs

---

## 🔄 CI/CD Best Practices

### Pipeline Design

**Stages:**
1. **Lint & Format** - Fail fast on style issues
2. **Unit Tests** - Test individual components
3. **Integration Tests** - Test component interactions
4. **Security Scans** - SAST, dependency scanning, container scanning
5. **Build** - Create artifacts (Docker images, binaries)
6. **Deploy to Staging** - Automated deployment to staging
7. **E2E Tests** - Full system tests in staging
8. **Deploy to Production** - Manual approval or automated with safeguards

**Deployment Safeguards:**
- Require manual approval for production deployments
- Implement deployment windows (avoid Friday deployments)
- Use feature flags for gradual rollouts
- Monitor key metrics post-deployment
- Automate rollback on critical metric degradation

### GitHub Actions / GitLab CI Best Practices

**Reusable Workflows:**
```yaml
name: Reusable Docker Build

on:
  workflow_call:
    inputs:
      image_name:
        required: true
        type: string

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: ${{ inputs.image_name }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

**Secrets Management:**
- Use GitHub Secrets / GitLab CI Variables
- Rotate secrets regularly
- Use environment-specific secrets
- Never echo secrets in logs

**Optimization:**
- Use caching for dependencies (npm cache, pip cache, docker layer cache)
- Run jobs in parallel when possible
- Use matrix builds for multiple versions/platforms
- Set appropriate timeouts to prevent hanging jobs

---

## 📊 Monitoring & Observability

### The Three Pillars

**1. Metrics (Prometheus/Grafana)**
- Track RED metrics: Rate, Errors, Duration
- Monitor resource usage: CPU, memory, disk, network
- Set up alerts for SLO violations
- Use histograms for latency, not averages

**2. Logs (ELK/Loki)**
- Use structured logging (JSON)
- Include correlation IDs for request tracing
- Set appropriate log levels (INFO for production)
- Implement log rotation and retention policies
- Index logs for fast searching

**3. Traces (Jaeger/Tempo)**
- Instrument critical paths
- Use distributed tracing for microservices
- Track database and external API calls
- Set sampling rates appropriately

### Alerting Best Practices

**Alert on Symptoms, Not Causes:**
- ✅ "API latency > 500ms for 5 minutes"
- ❌ "High CPU usage"

**Alert Fatigue Prevention:**
- Set appropriate thresholds (based on SLO)
- Use alert aggregation and deduplication
- Implement on-call rotation
- Include runbook links in alerts
- Review and adjust alerts regularly

---

## 🔐 Security Best Practices

### Secrets Management

**Never:**
- Commit secrets to Git (even in private repos)
- Hardcode secrets in code or configs
- Share secrets via Slack/email/unsecured channels
- Store secrets in container images

**Always:**
- Use secrets managers (AWS Secrets Manager, Vault, Azure Key Vault)
- Rotate secrets regularly (90 days maximum)
- Use different secrets per environment
- Implement least privilege access
- Audit secret access logs

### Container Security

**Scanning:**
- Scan images for vulnerabilities before deployment
- Use Trivy, Clair, or cloud-native scanners
- Fail builds on critical/high vulnerabilities
- Keep base images updated

**Runtime Security:**
- Run containers as non-root
- Use read-only file systems where possible
- Drop unnecessary capabilities
- Use AppArmor/SELinux profiles
- Implement pod security policies/standards

---

## 💰 Cost Optimization

### Resource Right-Sizing

**Continuous Optimization:**
- Monitor actual resource usage vs allocated
- Use vertical pod autoscaler (VPA) for recommendations
- Implement cluster autoscaler for dynamic node scaling
- Use spot/preemptible instances for non-critical workloads

**Storage Optimization:**
- Implement lifecycle policies for object storage
- Use appropriate storage classes (SSD vs HDD)
- Clean up unused volumes and snapshots
- Compress logs before archiving

### Cloud Cost Management

**Tagging Strategy:**
- Tag all resources with: Environment, Project, Owner, CostCenter
- Use tag-based billing reports
- Set up budget alerts
- Review costs weekly

**Savings:**
- Use reserved instances for predictable workloads
- Leverage savings plans
- Use spot instances for batch jobs
- Shutdown dev/test environments outside business hours
- Use auto-scaling to match demand

---

## 🧪 Testing in DevOps

### Test Pyramid

**Unit Tests (70%):**
- Fast, isolated, deterministic
- Run on every commit
- High code coverage (>80%)

**Integration Tests (20%):**
- Test component interactions
- Use test doubles/mocks for external dependencies
- Run in CI pipeline

**E2E Tests (10%):**
- Test full user flows
- Run in staging environment
- Keep minimal due to maintenance cost

### Testing Best Practices

**Containerized Tests:**
- Use docker-compose for local integration testing
- Use testcontainers for spinning up dependencies
- Ensure tests clean up resources

**Performance Testing:**
- Load test before production deployment
- Use k6, Gatling, or JMeter
- Test at expected peak load + 20%
- Monitor resource usage during tests

---

## 📝 Documentation Requirements

**Infrastructure Documentation:**
- Architecture diagrams (use draw.io, Mermaid, PlantUML)
- Runbooks for common operations
- Disaster recovery procedures
- Scaling guidelines
- Cost optimization opportunities

**Keep Updated:**
- Document all manual steps
- Update after each major change
- Include examples and screenshots
- Version documentation with code

---

## 🚨 Incident Response

### On-Call Best Practices

**Preparation:**
- Maintain runbooks for common issues
- Have rollback procedures ready
- Know escalation paths
- Test disaster recovery procedures

**During Incident:**
- Communicate status regularly
- Focus on mitigation first, root cause later
- Document actions taken
- Involve specialists early if needed

**Post-Incident:**
- Conduct blameless postmortems
- Document lessons learned
- Create tickets for preventive measures
- Share learnings with team

---

## 🔄 GitOps Best Practices

**Principles:**
- Git is the single source of truth
- Declarative desired state
- Automated reconciliation
- Immutable infrastructure

**Tools:**
- ArgoCD or Flux for Kubernetes deployments
- Use separate repos for application code and manifests
- Implement branch protection rules
- Use pull requests for changes
- Automate manifest generation (Kustomize, Helm)

**Directory Structure:**
```
gitops-repo/
├── apps/
│   ├── frontend/
│   ├── backend/
│   └── database/
├── infrastructure/
│   ├── ingress/
│   ├── monitoring/
│   └── logging/
└── environments/
    ├── dev/
    ├── staging/
    └── prod/
```

---

## ✅ Pre-Deployment Checklist

**Before Every Deployment:**
- [ ] All tests passing in CI
- [ ] Security scans completed with no critical issues
- [ ] Resource limits defined
- [ ] Health checks configured
- [ ] Monitoring and alerts set up
- [ ] Rollback plan documented
- [ ] Secrets rotated if needed
- [ ] Documentation updated
- [ ] Stakeholders notified
- [ ] Deployment window approved

---

## 🎯 DevOps Metrics to Track

**DORA Metrics:**
- Deployment Frequency
- Lead Time for Changes
- Change Failure Rate
- Time to Restore Service

**Infrastructure Metrics:**
- Cluster/Node utilization
- Pod restart rate
- Image pull time
- Build duration
- Deployment success rate

**Cost Metrics:**
- Cost per service/environment
- Waste (unused resources)
- Reserved vs on-demand usage
- Trend over time

---

## 🚫 Anti-Patterns to Avoid

**Docker:**
- ❌ Using `:latest` tag in production
- ❌ Running multiple services in one container
- ❌ Storing data in containers
- ❌ Building images without `.dockerignore`
- ❌ Including datasets/large files in images

**Kubernetes:**
- ❌ No resource limits defined
- ❌ Running as root
- ❌ Storing secrets as plain ConfigMaps
- ❌ No health checks
- ❌ Deploying to default namespace

**Terraform:**
- ❌ Committing state files
- ❌ No remote backend
- ❌ Hardcoded values instead of variables
- ❌ No modules for repeated patterns
- ❌ Applying without `terraform plan`

**CI/CD:**
- ❌ Deploying directly from local machine
- ❌ No testing before deployment
- ❌ Manual secret management
- ❌ No rollback plan
- ❌ Deploying on Fridays without on-call

---

## 🎓 Continuous Learning

**Stay Updated:**
- Follow CNCF projects and updates
- Read post-mortems from major incidents
- Participate in DevOps communities
- Experiment with new tools in dev environments
- Share knowledge through documentation and demos

**Recommended Resources:**
- CNCF Landscape: https://landscape.cncf.io/
- SRE Books (Google)
- Kubernetes docs: https://kubernetes.io/docs/
- Terraform docs: https://www.terraform.io/docs/
- DevOps Roadmap: https://roadmap.sh/devops

---

**Remember: DevOps is culture first, tools second. Automate everything, monitor proactively, and always have a rollback plan.**
