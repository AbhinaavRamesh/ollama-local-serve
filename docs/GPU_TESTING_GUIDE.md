# GPU Testing & Verification Guide

This guide provides step-by-step instructions for testing and verifying the Kubernetes deployment, GPU monitoring, and new dashboard features on a system with an NVIDIA GPU.

## Prerequisites

### Hardware Requirements
- NVIDIA GPU (single GPU deployment)
- Minimum 8GB VRAM recommended
- NVIDIA Driver 525+ installed

### Software Requirements
- Docker with NVIDIA Container Toolkit
- Kubernetes cluster (minikube, k3s, or cloud provider)
- NVIDIA Device Plugin for Kubernetes
- kubectl configured
- Helm 3.x (for K8s deployment)

## Quick Verification Commands

Run these commands to verify your GPU setup before deployment:

```bash
# 1. Verify NVIDIA driver and GPU detection
nvidia-smi

# 2. Verify Docker GPU access
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi

# 3. Verify Kubernetes GPU plugin (if using K8s)
kubectl get nodes -o jsonpath='{.items[*].status.allocatable.nvidia\.com/gpu}'
```

---

## Part 1: Docker Compose Deployment (Recommended for Testing)

### Step 1: Clone and Setup

```bash
cd ollama-local-serve

# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

### Step 2: Enable GPU in docker-compose.yml

Uncomment the GPU section in `docker-compose.yml`:

```yaml
ollama:
  image: ollama/ollama:latest
  # ... other config ...
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1  # Single GPU
            capabilities: [gpu]
```

### Step 3: Start the Stack

```bash
# Start all services
docker compose up -d

# Check logs
docker compose logs -f ollama-monitor

# Verify health
curl http://localhost:8000/api/health
```

### Step 4: Verify GPU Metrics

```bash
# Check GPU metrics endpoint
curl http://localhost:8000/api/gpu | python3 -m json.tool

# Expected output:
# {
#   "available": true,
#   "gpu_count": 1,
#   "gpus": [{
#     "name": "NVIDIA GeForce RTX ...",
#     "utilization_gpu_percent": 5,
#     "memory_used_mb": 1024,
#     ...
#   }]
# }
```

### Step 5: Verify Prometheus Metrics

```bash
# Check Prometheus metrics endpoint
curl http://localhost:8000/api/metrics

# Should include GPU metrics:
# ollama_gpu_available 1
# ollama_gpu_count 1
# ollama_gpu_memory_used_bytes{gpu="0",...} 1073741824
# ollama_gpu_utilization_percent{gpu="0",...} 5
```

---

## Part 2: Dashboard Verification

### Step 1: Access Dashboard

Open your browser to: `http://localhost:3000`

### Step 2: Verify New Dashboard Panels

#### System Overview Panel
Check for the following metrics:
- [ ] **GPU Util**: Shows percentage (should be 0-100%)
- [ ] **VRAM Used**: Shows GB used (e.g., "8.4 GB")
- [ ] **Queue Depth**: Shows pending requests count
- [ ] **Active Models**: Lists recently used models
- [ ] VRAM utilization progress bar

#### Performance Metrics Panel
Verify:
- [ ] **Tokens/Second by Model**: Bar chart with per-model throughput
- [ ] **Latency Percentiles**: P50, P95, P99 with color coding
  - Green: < 500ms
  - Amber: 500-2000ms
  - Red: > 2000ms
- [ ] Total requests, tokens, and error rate

#### Infrastructure Health Panel
Verify:
- [ ] **Overall Status**: Banner showing healthy/degraded/unhealthy
- [ ] **Service Status**: Ollama and Database status indicators
- [ ] **GPU Temp**: Temperature in Celsius with warnings
- [ ] **VRAM**: Current usage with percentage
- [ ] **Queue**: Pending requests
- [ ] **Errors (24h)**: Error count and rate

### Step 3: Generate Test Load

```bash
# Generate test requests to populate metrics
for i in {1..10}; do
  curl -s -X POST http://localhost:8000/api/chat \
    -H "Content-Type: application/json" \
    -d '{"model": "qwen2.5:0.5b", "prompt": "Say hello"}' &
done
wait

# Wait a few seconds, then refresh dashboard
```

### Step 4: Verify Live Updates

1. Keep dashboard open
2. Send more requests in terminal
3. Verify metrics update in real-time (auto-refresh every 5 seconds)

---

## Part 3: Kubernetes Deployment Verification

### Step 1: Install NVIDIA Device Plugin

```bash
# For GPU support in Kubernetes
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml

# Verify GPU is allocatable
kubectl get nodes -o json | jq '.items[].status.allocatable | select(."nvidia.com/gpu")'
```

### Step 2: Deploy Helm Chart

```bash
cd k8s

# Update dependencies
helm dependency update

# Install chart
helm install ollama-serve . \
  --namespace ollama \
  --create-namespace \
  --set ollama.gpu.enabled=true \
  --set ollama.resources.limits."nvidia\.com/gpu"=1

# Check deployment status
kubectl -n ollama get pods -w
```

### Step 3: Verify Kubernetes Probes

```bash
# Check liveness probe
kubectl -n ollama exec -it deployment/ollama-serve-api -- curl localhost:8000/healthz

# Check readiness probe
kubectl -n ollama exec -it deployment/ollama-serve-api -- curl localhost:8000/readyz

# Expected output for readiness:
# {"ready": true, "checks": {"database": true, "ollama": true}, "message": "All checks passed"}
```

### Step 4: Verify ServiceMonitor (if Prometheus Operator installed)

```bash
# Check ServiceMonitor
kubectl -n ollama get servicemonitor

# Verify Prometheus is scraping
kubectl -n monitoring port-forward svc/prometheus-operated 9090:9090 &
# Then visit http://localhost:9090/targets
```

### Step 5: Access via Ingress

```bash
# If ingress is enabled
kubectl -n ollama get ingress

# Add to /etc/hosts (replace IP with your ingress controller IP)
echo "192.168.1.100 ollama.local" | sudo tee -a /etc/hosts

# Access dashboard
open http://ollama.local
```

---

## Part 4: API Endpoint Verification Checklist

### Core Endpoints

| Endpoint | Method | Expected Response | Test Command |
|----------|--------|-------------------|--------------|
| `/api/health` | GET | Health status | `curl localhost:8000/api/health` |
| `/api/gpu` | GET | GPU metrics | `curl localhost:8000/api/gpu` |
| `/api/metrics` | GET | Prometheus format | `curl localhost:8000/api/metrics` |
| `/api/stats/enhanced` | GET | Enhanced stats with percentiles | `curl localhost:8000/api/stats/enhanced` |
| `/api/infrastructure` | GET | Infrastructure health | `curl localhost:8000/api/infrastructure` |
| `/healthz` | GET | Liveness probe | `curl localhost:8000/healthz` |
| `/readyz` | GET | Readiness probe | `curl localhost:8000/readyz` |

### Full Test Script

```bash
#!/bin/bash
# Full API verification script

BASE_URL="${1:-http://localhost:8000}"

echo "Testing endpoints on $BASE_URL"
echo "================================"

# Health check
echo -e "\n1. Health Check:"
curl -s "$BASE_URL/api/health" | python3 -m json.tool

# GPU metrics
echo -e "\n2. GPU Metrics:"
curl -s "$BASE_URL/api/gpu" | python3 -m json.tool

# Enhanced stats
echo -e "\n3. Enhanced Stats:"
curl -s "$BASE_URL/api/stats/enhanced" | python3 -m json.tool

# Infrastructure health
echo -e "\n4. Infrastructure Health:"
curl -s "$BASE_URL/api/infrastructure" | python3 -m json.tool

# Kubernetes probes
echo -e "\n5. Liveness Probe:"
curl -s "$BASE_URL/healthz" | python3 -m json.tool

echo -e "\n6. Readiness Probe:"
curl -s "$BASE_URL/readyz" | python3 -m json.tool

# Prometheus metrics
echo -e "\n7. Prometheus Metrics (first 20 lines):"
curl -s "$BASE_URL/api/metrics" | head -20

echo -e "\n================================"
echo "Verification complete!"
```

Save as `test_endpoints.sh` and run:
```bash
chmod +x test_endpoints.sh
./test_endpoints.sh http://localhost:8000
```

---

## Part 5: Troubleshooting

### GPU Not Detected

```bash
# Check nvidia-smi accessibility
nvidia-smi

# If not available, check driver
lsmod | grep nvidia

# For Docker, ensure nvidia-container-toolkit
dpkg -l | grep nvidia-container-toolkit
```

### GPU Metrics Showing "N/A"

1. Ensure nvidia-smi is in PATH inside the container
2. Check container has GPU access:
   ```bash
   docker exec ollama-monitor nvidia-smi
   ```
3. Verify GPU resources in docker-compose or K8s manifest

### Prometheus Scraping Issues

```bash
# Verify metrics endpoint is accessible
curl -v http://localhost:8000/api/metrics

# Check format is valid Prometheus format
curl http://localhost:8000/api/metrics | promtool check metrics
```

### Queue Depth Always 0

Queue depth tracks in-flight requests. Send concurrent requests to see non-zero values:
```bash
# Parallel requests
for i in {1..20}; do
  curl -s -X POST http://localhost:8000/api/chat \
    -H "Content-Type: application/json" \
    -d '{"model": "qwen2.5:0.5b", "prompt": "Tell me a long story"}' &
done
```

---

## Part 6: Performance Benchmarking

### Basic Load Test

```bash
# Install hey (HTTP load generator)
go install github.com/rakyll/hey@latest

# Simple load test
hey -n 100 -c 10 -m POST \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen2.5:0.5b", "prompt": "Hello"}' \
  http://localhost:8000/api/chat
```

### Monitor During Load

In separate terminals:
```bash
# Terminal 1: Watch GPU utilization
watch -n 1 nvidia-smi

# Terminal 2: Watch metrics
watch -n 1 'curl -s http://localhost:8000/api/stats/enhanced | python3 -m json.tool'

# Terminal 3: Watch queue depth
watch -n 0.5 'curl -s http://localhost:8000/api/stats/enhanced | jq .queue_depth'
```

---

## Verification Checklist Summary

### Docker Compose Deployment
- [ ] GPU detected by docker (`docker run --gpus all nvidia/cuda:12.0-base nvidia-smi`)
- [ ] Ollama service running with GPU
- [ ] API returning GPU metrics
- [ ] Prometheus metrics endpoint working
- [ ] Dashboard showing GPU metrics

### Kubernetes Deployment
- [ ] NVIDIA Device Plugin installed
- [ ] GPU allocatable on nodes
- [ ] Ollama pod scheduled with GPU
- [ ] Liveness probe passing
- [ ] Readiness probe passing
- [ ] ServiceMonitor created (if Prometheus Operator)
- [ ] Ingress routing correctly

### Dashboard Features
- [ ] System Overview panel showing GPU metrics
- [ ] Performance Metrics panel with tokens/sec chart
- [ ] Latency percentiles (P50/P95/P99)
- [ ] Infrastructure Health panel
- [ ] Live refresh working
- [ ] Error states handled gracefully

---

## Next Steps

1. **Production Deployment**: Review `k8s/values.yaml` for production settings
2. **Alerting**: Configure Prometheus AlertManager rules
3. **Grafana**: Import dashboard JSON for advanced visualization
4. **Scaling**: Adjust HPA settings based on load testing results

For issues or questions, open an issue at: https://github.com/AbhinaavRamesh/ollama-local-serve/issues
