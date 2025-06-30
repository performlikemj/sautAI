#!/bin/bash

# Script to create Azure Container App for sautAI Frontend using Key Vault
set -e

# Configuration - based on your existing setup
RESOURCE_GROUP="sautAI"
CONTAINER_APP_ENV="sautai-env-westus2"  # Change to "sautai-env" if you prefer East US
ACR_NAME="sautairegistry"
APP_NAME="sautai-frontend"
IMAGE_NAME="sautai-frontend:latest"
KEY_VAULT_NAME="sautai-keyvault"
MANAGED_IDENTITY="django-keyvault-identity"

echo "Deploying sautAI Frontend to Azure Container Apps..."
echo "Using secrets from Key Vault: $KEY_VAULT_NAME"
echo "Using managed identity: $MANAGED_IDENTITY"

# Check if the container app already exists
if az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP >/dev/null 2>&1; then
    echo "Container app $APP_NAME already exists. Updating..."
    
    # Update existing container app
    az containerapp update \
        --name $APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --image $ACR_NAME.azurecr.io/$IMAGE_NAME
else
    echo "Creating new container app $APP_NAME..."
    
    # Create new container app with Key Vault integration
    az containerapp create \
        --name $APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --environment $CONTAINER_APP_ENV \
        --image $ACR_NAME.azurecr.io/$IMAGE_NAME \
        --target-port 8501 \
        --ingress external \
        --user-assigned /subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.ManagedIdentity/userAssignedIdentities/$MANAGED_IDENTITY \
        --secrets \
            django-url=keyvaultref:https://$KEY_VAULT_NAME.vault.azure.net/secrets/django-url,identityref:/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.ManagedIdentity/userAssignedIdentities/$MANAGED_IDENTITY \
            openai-api-key=keyvaultref:https://$KEY_VAULT_NAME.vault.azure.net/secrets/openai-api-key,identityref:/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.ManagedIdentity/userAssignedIdentities/$MANAGED_IDENTITY \
        --env-vars \
            DJANGO_URL=secretref:django-url \
            OPENAI_KEY=secretref:openai-api-key \
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
echo "🔐 Security: Using Key Vault secrets:"
echo "  - DJANGO_URL from sautai-keyvault/django-url"
echo "  - OPENAI_KEY from sautai-keyvault/openai-api-key"
echo ""
echo "Next steps:"
echo "1. Update your DNS/domain configuration to point to this URL"
echo "2. Configure SSL certificates if using a custom domain"
echo "3. Set up monitoring and logging"
echo "4. Configure auto-scaling rules if needed" 