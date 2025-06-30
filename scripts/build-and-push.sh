#!/bin/bash

# Build and push script for sautAI Frontend to Azure Container Registry
set -e

# Configuration - update these values
ACR_NAME="sautairegistry"
IMAGE_NAME="sautai-frontend"
TAG="${1:-latest}"
RESOURCE_GROUP="sautAI"

echo "Building and pushing sautAI Frontend to Azure Container Registry..."

# Login to Azure (if not already logged in)
echo "Logging into Azure..."
az login --identity 2>/dev/null || az login

# Login to ACR
echo "Logging into Azure Container Registry..."
az acr login --name $ACR_NAME

# Build the Docker image
echo "Building Docker image..."
docker build -t $ACR_NAME.azurecr.io/$IMAGE_NAME:$TAG .

# Push the image to ACR
echo "Pushing image to ACR..."
docker push $ACR_NAME.azurecr.io/$IMAGE_NAME:$TAG

# Also tag and push as latest if not already latest
if [ "$TAG" != "latest" ]; then
    docker tag $ACR_NAME.azurecr.io/$IMAGE_NAME:$TAG $ACR_NAME.azurecr.io/$IMAGE_NAME:latest
    docker push $ACR_NAME.azurecr.io/$IMAGE_NAME:latest
fi

echo "Successfully built and pushed $ACR_NAME.azurecr.io/$IMAGE_NAME:$TAG"
echo ""
echo "To deploy to Azure Container Apps, run:"
echo "az containerapp update --name sautai-frontend --resource-group $RESOURCE_GROUP --image $ACR_NAME.azurecr.io/$IMAGE_NAME:$TAG" 