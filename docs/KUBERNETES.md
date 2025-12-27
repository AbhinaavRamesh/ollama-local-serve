# Kubernetes Deployment

Deploy to Kubernetes for production-ready scalability and local network access.

## Prerequisites

- Kubernetes cluster (Docker Desktop, minikube, or cloud)
- Helm 3.x installed
- kubectl configured

## Quick Start with Helm

```bash
# Clone the repository
git clone https://github.com/AbhinaavRamesh/ollama-local-serve.git
cd ollama-local-serve

# Build Docker images locally
docker build -t ollama-monitor:latest -f Dockerfile .
docker build -t ollama-frontend:latest -f frontend/Dockerfile frontend/

# Create namespace
kubectl create namespace ollama

# Deploy simple databases (for local dev)
kubectl apply -f k8s/local-databases.yaml

# Deploy with Helm (local development values)
cd k8s
helm install ollama-serve . -n ollama -f values-local.yaml \
  --set 'ollama.resources.limits.nvidia\.com/gpu=null'
```

## Access Services

| Service | URL | Description |
|---------|-----|-------------|
| Frontend Dashboard | http://localhost:30080 | Monitoring UI |
| API Server | http://localhost:30800 | FastAPI REST API |
| Prometheus Metrics | http://localhost:30800/api/metrics | Prometheus format |

For network access, replace `localhost` with your machine's IP address.

## Useful Commands

```bash
# Check deployment status
kubectl get pods -n ollama

# View logs
kubectl logs -f deployment/ollama-serve-ollama-local-serve-api -n ollama

# Upgrade deployment
helm upgrade ollama-serve . -n ollama -f values-local.yaml

# Uninstall
helm uninstall ollama-serve -n ollama
kubectl delete namespace ollama
```

## Pulling Models

After deployment, pull models into the Ollama pod:

```bash
# Pull a model (e.g., llama3.2)
kubectl exec -it deployment/ollama-serve-ollama-local-serve-ollama -n ollama -- ollama pull llama3.2

# List available models
kubectl exec -it deployment/ollama-serve-ollama-local-serve-ollama -n ollama -- ollama list
```

Models are persisted in a PersistentVolumeClaim and survive pod restarts.

## GPU Support (NVIDIA)

For GPU-enabled nodes, remove the GPU null override:

```bash
helm install ollama-serve . -n ollama -f values.yaml  # Uses default GPU config
```

### GPU Setup Checklist

```bash
# 1. Install NVIDIA Device Plugin
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml

# 2. Verify GPU availability
kubectl get nodes -o json | jq '.items[].status.allocatable | select(."nvidia.com/gpu")'

# 3. Deploy Ollama with GPU
helm install ollama-serve . -n ollama -f values.yaml \
  --set ollama.resources.limits."nvidia\.com/gpu"=1

# 4. Verify GPU in pod
kubectl exec -it deployment/ollama-serve-ollama-local-serve-ollama -n ollama -- nvidia-smi
```

## Ingress Configuration

To expose services externally with ingress:

### Example 1: Nginx Ingress

```bash
# Install Nginx Ingress Controller (if not present)
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install nginx-ingress ingress-nginx/ingress-nginx

# Deploy with ingress enabled
helm install ollama-serve . -n ollama -f values.yaml \
  --set ingress.enabled=true \
  --set ingress.className=nginx \
  --set ingress.hosts[0].host=ollama.example.com \
  --set ingress.hosts[0].paths[0].path=/
```

Update `/etc/hosts` or DNS:
```
192.168.1.100 ollama.example.com
```

Access services:
- Dashboard: http://ollama.example.com
- API: http://ollama.example.com/api/

### Example 2: Configure Ingress in values.yaml

Edit `k8s/values-local.yaml`:
```yaml
ingress:
  enabled: true
  className: nginx
  hosts:
    - host: ollama.local
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: ollama-tls
      hosts:
        - ollama.local
```

### Example 3: Access via LoadBalancer

For cloud providers (AWS, GCP, Azure):

```bash
helm install ollama-serve . -n ollama -f values.yaml \
  --set frontend.service.type=LoadBalancer \
  --set api.service.type=LoadBalancer

# Get external IPs
kubectl get svc -n ollama

# Access via external IP
curl http://<EXTERNAL-IP>:8000/api/health
```

## Advanced Configuration

### Scaling Ollama Replicas

For horizontal scaling (distribute inference load):

```bash
helm upgrade ollama-serve . -n ollama -f values.yaml \
  --set ollama.replicaCount=3
```

### Resource Requests and Limits

```bash
helm install ollama-serve . -n ollama -f values.yaml \
  --set ollama.resources.requests.memory="4Gi" \
  --set ollama.resources.requests.cpu="2" \
  --set ollama.resources.limits.memory="8Gi" \
  --set ollama.resources.limits.cpu="4"
```

### Persistent Storage Configuration

```bash
# Use custom storage class
helm install ollama-serve . -n ollama -f values.yaml \
  --set ollama.persistence.storageClass=fast-ssd \
  --set ollama.persistence.size=50Gi
```

### Environment Variables

```bash
helm install ollama-serve . -n ollama -f values.yaml \
  --set env.OLLAMA_MODEL=mistral \
  --set env.OLLAMA_TIMEOUT=120 \
  --set env.EXPORTER_TYPE=clickhouse
```

## Monitoring and Logging

### View Pod Logs

```bash
# API server logs
kubectl logs -f deployment/ollama-serve-ollama-local-serve-api -n ollama

# Ollama logs
kubectl logs -f deployment/ollama-serve-ollama-local-serve-ollama -n ollama

# Frontend logs
kubectl logs -f deployment/ollama-serve-ollama-local-serve-frontend -n ollama

# All pods in namespace
kubectl logs -f -n ollama --all-containers=true --max-log-requests=10
```

### Port Forwarding

```bash
# Access API locally
kubectl port-forward svc/ollama-serve-ollama-local-serve-api 8000:8000 -n ollama

# Access Dashboard locally
kubectl port-forward svc/ollama-serve-ollama-local-serve-frontend 3000:3000 -n ollama

# Access both in parallel
kubectl port-forward svc/ollama-serve-ollama-local-serve-api 8000:8000 -n ollama &
kubectl port-forward svc/ollama-serve-ollama-local-serve-frontend 3000:3000 -n ollama &
```

### Check Pod Status

```bash
# Detailed pod info
kubectl describe pod <pod-name> -n ollama

# Resource usage
kubectl top pods -n ollama

# Events for troubleshooting
kubectl get events -n ollama --sort-by='.lastTimestamp'
```

## Troubleshooting Kubernetes Deployments

### Pod Stuck in Pending

```bash
# Check what's wrong
kubectl describe pod <pod-name> -n ollama

# Common issues:
# 1. Insufficient resources
kubectl top nodes

# 2. Image pull issues
kubectl logs <pod-name> -n ollama

# 3. Volume binding issues
kubectl get pvc -n ollama
```

### Readiness/Liveness Probe Failures

```bash
# Check probe configuration
kubectl get deployment -n ollama -o yaml | grep -A 20 "livenessProbe"

# Test probe manually
kubectl exec -it <pod-name> -n ollama -- curl localhost:8000/readyz

# View probe events
kubectl describe pod <pod-name> -n ollama | grep -A 5 "Liveness"
```

### Database Connection Errors

```bash
# Check if database pods are running
kubectl get pods -n ollama | grep postgres
kubectl get pods -n ollama | grep clickhouse

# Test database connectivity from API pod
kubectl exec -it <api-pod-name> -n ollama -- \
  curl http://postgres:5432

# Check database logs
kubectl logs -f deployment/postgres -n ollama
```

### Helm Deployment Issues

```bash
# Validate Helm chart
helm lint k8s/

# Dry run to see what will be deployed
helm install ollama-serve k8s --dry-run --debug -n ollama -f k8s/values-local.yaml

# Rollback failed deployment
helm rollback ollama-serve -n ollama

# Check Helm release status
helm status ollama-serve -n ollama

# View Helm values
helm get values ollama-serve -n ollama
```

### Network/Connectivity Issues

```bash
# Test DNS resolution
kubectl run -it --rm debug --image=alpine --restart=Never -- \
  nslookup ollama-serve-ollama-local-serve-api.ollama.svc.cluster.local

# Test service connectivity
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl http://ollama-serve-ollama-local-serve-api:8000/api/health

# Check network policies
kubectl get networkpolicies -n ollama

# Check service endpoints
kubectl get endpoints -n ollama
```

### GPU Not Available in Pod

```bash
# Check NVIDIA device plugin
kubectl get pods -n kube-system | grep nvidia

# Check node GPU allocation
kubectl get nodes -o json | jq '.items[].status.allocatable | select(."nvidia.com/gpu")'

# Check pod GPU requests
kubectl get pod <pod-name> -n ollama -o yaml | grep -A 5 "nvidia.com/gpu"

# Verify GPU in pod
kubectl exec -it <ollama-pod-name> -n ollama -- nvidia-smi
```

## Cleanup

```bash
# Remove Ollama deployment
helm uninstall ollama-serve -n ollama

# Delete namespace (removes all resources)
kubectl delete namespace ollama

# Remove NVIDIA device plugin (if you installed it)
kubectl delete -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml
```
