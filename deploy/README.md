# sautAI Frontend Deployment Guide

This directory contains deployment configurations and scripts for containerizing and deploying the sautAI Streamlit frontend to Azure Container Apps.

## Prerequisites

1. **Azure CLI** installed and logged in
2. **Docker** installed for building images
3. **Azure Container Registry** (ACR) set up
4. **Azure Container Apps Environment** created
5. **Existing sautAI backend services** running in Container Apps

## Quick Start

### 1. Build and Push Container Image

```bash
# Update the configuration in scripts/build-and-push.sh
# Set your ACR name, resource group, etc.
./scripts/build-and-push.sh
```

### 2. Deploy to Azure Container Apps

**Option A: Using Azure Key Vault (Recommended - More Secure)**
```bash
# No environment variables needed - all secrets come from sautai-keyvault
./deploy/container-app-create-keyvault.sh
```

**Option B: Using Environment Variables**
```bash
# Set environment variables
export DJANGO_URL="https://your-backend-container-app.azurecontainerapps.io"
export OPENAI_KEY="your-openai-api-key"

# Run deployment script
./deploy/container-app-create.sh
```

## Configuration

### Environment Variables Required

#### Key Vault Secrets (Recommended)
The deployment uses existing secrets from `sautai-keyvault`:

| Secret Name | Description | Container Env Var |
|-------------|-------------|-------------------|
| `django-url` | Backend API URL | `DJANGO_URL` |
| `openai-api-key` | OpenAI API Key | `OPENAI_KEY` |

#### Manual Environment Variables (Alternative)
If not using Key Vault:

| Variable | Description | Example |
|----------|-------------|---------|
| `DJANGO_URL` | Backend API URL | `https://sautai-django-westus2.redcliff-686826f3.westus2.azurecontainerapps.io` |
| `OPENAI_KEY` | OpenAI API Key | `sk-...` |

#### Auto-configured Variables
| Variable | Description | Value |
|----------|-------------|-------|
| `STREAMLIT_SERVER_PORT` | Port | `8501` |
| `STREAMLIT_SERVER_ADDRESS` | Address | `0.0.0.0` |

### Resource Configuration

- **CPU**: 0.5 cores (can be adjusted)
- **Memory**: 1 GiB (can be adjusted)
- **Replicas**: 1-3 (auto-scaling enabled)
- **Port**: 8501 (Streamlit default)

## Integration with Existing Services

This frontend is designed to work with your existing sautAI backend services. Ensure:

1. **Backend API** is accessible at the `DJANGO_URL`
2. **CORS settings** in Django allow requests from the frontend domain
3. **Authentication tokens** are properly configured
4. **Network connectivity** between containers (should work automatically in Container Apps)

## Security Considerations

1. **Environment Variables**: Store sensitive values in Azure Key Vault or Container Apps secrets
2. **HTTPS**: Enable HTTPS for production deployments
3. **CORS**: Configure backend CORS settings appropriately
4. **API Keys**: Rotate OpenAI API keys regularly

## Monitoring and Logging

### Health Checks
The container includes built-in health checks at `/_stcore/health`

### Logs
View application logs:
```bash
az containerapp logs show --name sautai-frontend --resource-group $RESOURCE_GROUP
```

### Metrics
Monitor in Azure Portal:
- Request count and latency
- CPU and memory usage
- Replica scaling events

## Development Workflow

### Local Development
```bash
# Run with docker-compose for local testing
docker-compose up

# Or run Streamlit directly
streamlit run sautai.py
```

### CI/CD Integration
Update `azure-pipelines.yml` to include:
1. Build Docker image
2. Push to ACR
3. Deploy to Container Apps

## Troubleshooting

### Common Issues

1. **Container not starting**: Check logs for Python/dependency errors
2. **502 Bad Gateway**: Verify port 8501 is exposed and health check passes
3. **API connection errors**: Verify `DJANGO_URL` and network connectivity
4. **Image pull errors**: Ensure ACR authentication is configured

### Debug Commands
```bash
# Check container app status
az containerapp show --name sautai-frontend --resource-group $RESOURCE_GROUP

# View logs
az containerapp logs show --name sautai-frontend --resource-group $RESOURCE_GROUP --follow

# Test health endpoint
curl https://your-app-url.azurecontainerapps.io/_stcore/health
```

## Cost Optimization

1. **Scale to Zero**: Configure minimum replicas to 0 during off-hours
2. **Resource Limits**: Adjust CPU/memory based on actual usage
3. **Reserved Capacity**: Use Azure Reserved Instances for predictable workloads

## Updating the Application

```bash
# Build new image with version tag
./scripts/build-and-push.sh v1.2.0

# Update container app
az containerapp update \
  --name sautai-frontend \
  --resource-group $RESOURCE_GROUP \
  --image your-acr.azurecr.io/sautai-frontend:v1.2.0
``` 