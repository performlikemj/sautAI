#!/bin/bash

# Example script to create Azure Container App for sautAI Frontend
# Copy this to container-app-create.sh and update with your actual values
set -e

# Configuration - update these values based on your existing setup
RESOURCE_GROUP="sautAI"
CONTAINER_APP_ENV="sautai-env-westus2"  # Change to "sautai-env" if you prefer East US
ACR_NAME="sautairegistry"
APP_NAME="sautai-frontend"
IMAGE_NAME="sautai-frontend:latest"

# Environment variables (set these before running the script)
# You should have these in your environment or Azure Key Vault
# export DJANGO_URL=https://sautai-django-westus2.redcliff-686826f3.westus2.azurecontainerapps.io
# export OPENAI_KEY=your-openai-api-key

echo "Deploying sautAI Frontend to Azure Container Apps..."

# Validate required environment variables
if [ -z "$DJANGO_URL" ]; then
    echo "Error: DJANGO_URL environment variable is not set"
    echo "Set it with: export DJANGO_URL=https://your-backend-url.azurecontainerapps.io"
    exit 1
fi

if [ -z "$OPENAI_KEY" ]; then
    echo "Error: OPENAI_KEY environment variable is not set"
    echo "Set it with: export OPENAI_KEY=your-openai-api-key"
    exit 1
fi

# Check if the container app already exists
if az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP >/dev/null 2>&1; then
    echo "Container app $APP_NAME already exists. Updating..."
    
    # Update existing container app
    az containerapp update \
        --name $APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --image $ACR_NAME.azurecr.io/$IMAGE_NAME \
        --set-env-vars \
            DJANGO_URL="$DJANGO_URL" \
            OPENAI_KEY="$OPENAI_KEY" \
            STREAMLIT_SERVER_PORT=8501 \
            STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
            STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
            STREAMLIT_SERVER_HEADLESS=true
else
    echo "Creating new container app $APP_NAME..."
    
    # Create new container app
    az containerapp create \
        --name $APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --environment $CONTAINER_APP_ENV \
        --image $ACR_NAME.azurecr.io/$IMAGE_NAME \
        --target-port 8501 \
        --ingress external \
        --query properties.configuration.ingress.fqdn \
        --env-vars \
            DJANGO_URL="$DJANGO_URL" \
            OPENAI_KEY="$OPENAI_KEY" \
            STREAMLIT_SERVER_PORT=8501 \
            STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
            STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
            STREAMLIT_SERVER_HEADLESS=true \
        --cpu 0.5 \
        --memory 1Gi \
        --min-replicas 1 \
        --max-replicas 3
fi

# Get the FQDN
FQDN=$(az containerapp show \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query properties.configuration.ingress.fqdn \
    --output tsv)

echo ""
echo "✅ Deployment completed successfully!"
echo "🌐 Your sautAI Frontend is available at: https://$FQDN"
echo ""
echo "Next steps:"
echo "1. Update your DNS/domain configuration to point to this URL"
echo "2. Configure SSL certificates if using a custom domain"
echo "3. Set up monitoring and logging"
echo "4. Configure auto-scaling rules if needed" 