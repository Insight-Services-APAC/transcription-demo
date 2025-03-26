# Deploying Transcription Demo on Azure Container Apps

This guide walks through deploying the transcription demo application to Azure Container Apps, primarily using the Azure Portal for configuration.

## Prerequisites

- Azure account with subscription access
- Docker installed locally (for container image building)
- Azure CLI installed (for some commands)
- The transcription demo code repository
- Git (for cloning the repository)

## Step 1: Prepare Your Application for Containerization

### Create a Dockerfile

Create a `Dockerfile` in your project root directory:

```Dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads instance

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production

# Expose port for the application
EXPOSE 8080

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "app:app"]
```

### Create a Celery Worker Dockerfile

Create a separate Dockerfile for the Celery worker, named `Dockerfile.worker`:

```Dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads instance

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production

# Command to run Celery worker
CMD ["celery", "-A", "celery_worker.celery", "worker", "--loglevel=info"]
```

### Container Registry Setup

1. In the Azure Portal, search for "Container registries" and click "Create"
2. Fill in the following details:
   - Registry name: `transcriptiondemoacr` (or your preferred name)
   - Resource group: Create new or select existing
   - Location: Choose a location near you
   - SKU: Standard
3. Click "Review + create" and then "Create"

### Build and Push Docker Images

After your registry is created, build and push your Docker images:

```bash
# Login to Azure
az login

# Login to your container registry
az acr login --name transcriptiondemoacr

# Build and tag your images
docker build -t transcriptiondemoacr.azurecr.io/transcription-app:latest .
docker build -t transcriptiondemoacr.azurecr.io/transcription-worker:latest -f Dockerfile.worker .

# Push images to ACR
docker push transcriptiondemoacr.azurecr.io/transcription-app:latest
docker push transcriptiondemoacr.azurecr.io/transcription-worker:latest
```

## Step 2: Set Up Azure Resources

### Create a Resource Group (if not already created)

1. In the Azure Portal, search for "Resource groups" and click "Create"
2. Provide a name (e.g., `transcription-demo-rg`) and select a region
3. Click "Review + create" and then "Create"

### Create Azure Storage Account

1. In the Azure Portal, search for "Storage accounts" and click "Create"
2. Fill in the following details:
   - Subscription: Select your subscription
   - Resource group: Select the resource group you created
   - Storage account name: `transcriptiondemostore` (or your preferred name)
   - Region: Choose the same region as your resource group
   - Performance: Standard
   - Redundancy: Locally-redundant storage (LRS)
3. Click "Review + create" and then "Create"
4. After creation, navigate to your storage account:
   - Under "Data storage", click "Containers"
   - Click "+ Container" to create a new container named `transcriptions`
   - Set the public access level to "Private"
5. Get your connection string:
   - In your storage account, go to "Access keys"
   - Copy the connection string for use in the next steps

### Create Azure Database for PostgreSQL

1. In the Azure Portal, search for "Azure Database for PostgreSQL" and click "Create"
2. Select "Flexible server" for better performance/cost ratio
3. Fill in the following details:
   - Subscription: Select your subscription
   - Resource group: Select your resource group
   - Server name: `transcription-demo-db` (or your preferred name)
   - Region: Choose the same region as your resource group
   - PostgreSQL version: 13
   - Authentication: Password
   - Admin username: Create a username
   - Password: Create a strong password (save this!)
4. Click "Review + create" and then "Create"
5. After creation:
   - Go to your PostgreSQL server
   - Under "Settings", click "Networking"
   - Set "Allow public access from any Azure service" to "Yes"
   - Add your local IP address for development access
   - Click "Save"
6. Create a database:
   - Under your PostgreSQL server, go to "Databases"
   - Click "+ Add" to create a new database named `transcriptiondb`

### Create Azure Speech Services

1. In the Azure Portal, search for "Speech services" and click "Create"
2. Fill in the following details:
   - Subscription: Select your subscription
   - Resource group: Select your resource group
   - Region: Choose a region where Speech services are available
   - Name: `transcription-demo-speech`
   - Pricing tier: Standard S0
3. Click "Review + create" and then "Create"
4. After creation, go to your Speech service resource:
   - Under "Resource Management", click "Keys and Endpoint"
   - Copy Key 1 and the Region for use in the next steps

### Create Azure Cache for Redis

1. In the Azure Portal, search for "Azure Cache for Redis" and click "Create"
2. Fill in the following details:
   - Subscription: Select your subscription
   - Resource group: Select your resource group
   - DNS name: `transcription-demo-redis` (or your preferred name)
   - Location: Choose the same region as your resource group
   - Pricing tier: Basic C0 (for dev/test) or Standard C1 (for production)
3. Click "Review + create" and then "Create"
4. After creation, go to your Redis resource:
   - Under "Settings", click "Access keys"
   - Copy the Primary connection string for use in the next steps

## Step 3: Deploy the Application to Azure Container Apps

### Create Container Apps Environment

1. In the Azure Portal, search for "Container Apps" and click "Create"
2. Fill in the following details:
   - Subscription: Select your subscription
   - Resource group: Select your resource group
   - Container app name: `transcription-demo-app`
   - Region: Choose the same region as your resource group
   - Container Apps Environment: Create new
     - Name: `transcription-demo-env`
     - Zone redundancy: Disabled (for cost savings)
3. Click "Next: App settings"
4. Under "App settings":
   - Select "Use quickstart image": No
   - Image source: Azure Container Registry
   - Registry: Select your ACR
   - Image: `transcription-app`
   - Image tag: `latest`
   - CPU and Memory: 1.0 CPU cores, 2.0 Gi memory
   - Scale: Min: 1, Max: 3
   - Ingress: Enabled
   - Ingress type: External
   - Target port: 8080
5. Click "Next: Environment variables"
6. Add the following environment variables:
   ```
   SECRET_KEY                        your-secure-secret-key
   DATABASE_URL                      postgresql://username:password@transcription-demo-db.postgres.database.azure.com/transcriptiondb
   AZURE_STORAGE_CONNECTION_STRING   your-azure-storage-connection-string
   AZURE_STORAGE_CONTAINER           transcriptions
   AZURE_SPEECH_KEY                  your-azure-speech-key
   AZURE_SPEECH_REGION               your-azure-speech-region
   CELERY_BROKER_URL                 redis://default:password@transcription-demo-redis.redis.cache.windows.net:6380/0?ssl=True
   CELERY_RESULT_BACKEND             redis://default:password@transcription-demo-redis.redis.cache.windows.net:6380/0?ssl=True
   PYANNOTE_AUTH_TOKEN               your-huggingface-access-token
   ```
7. Click "Review + create" and then "Create"

### Deploy Celery Worker Container App

1. In the Azure Portal, search for "Container Apps" and click "Create"
2. Fill in the following details:
   - Subscription: Select your subscription
   - Resource group: Select your resource group
   - Container app name: `transcription-demo-worker`
   - Region: Choose the same region as your resource group
   - Container Apps Environment: Use existing
     - Select the environment you created earlier
3. Click "Next: App settings"
4. Under "App settings":
   - Select "Use quickstart image": No
   - Image source: Azure Container Registry
   - Registry: Select your ACR
   - Image: `transcription-worker`
   - Image tag: `latest`
   - CPU and Memory: 1.0 CPU cores, 2.0 Gi memory
   - Scale: Min: 1, Max: 2
   - Ingress: Disabled
5. Click "Next: Environment variables"
6. Add the same environment variables as you did for the main app
7. Click "Review + create" and then "Create"

## Step 4: Configure Azure Storage CORS Settings

To allow your application to access Azure Storage from the browser:

1. Go to your Azure Storage account
2. Under "Settings", click "Resource sharing (CORS)"
3. Add a new CORS rule:
   - Allowed origins: Enter your Container App URL (e.g., `https://transcription-demo-app.azurecontainerapps.io`)
   - Allowed methods: SELECT, GET
   - Allowed headers: *
   - Exposed headers: *
   - Max age: 200
4. Click "Save"

## Step 5: Access Your Application

Once deployment is complete:

1. Go to your Container Apps service for `transcription-demo-app`
2. Under "Overview", find the "Application Url" 
3. Click the URL to access your application

## Troubleshooting and Monitoring

### View Container App Logs

1. Go to your Container App service
2. Under "Monitoring", click "Log stream" to see real-time logs
3. For more detailed logs, click "Logs" to use Azure Log Analytics

### Check Container Health

1. Go to your Container App service
2. Under "Application", click "Containers" to see container status
3. Under "Application", click "Revisions" to see deployment history

### Monitor Redis Cache

1. Go to your Redis Cache service
2. Under "Monitoring", view the metrics for cache hits, memory usage, etc.

### Database Monitoring

1. Go to your PostgreSQL server
2. Under "Monitoring", view the metrics for connections, storage, etc.

## Performance Tuning and Scaling

### Scale Your Container Apps

1. Go to your Container App service
2. Under "Application", click "Scale and replicas"
3. Adjust the minimum and maximum replica count based on your needs

### Scale Your Database

1. Go to your PostgreSQL server
2. Under "Settings", click "Compute + storage"
3. Adjust the compute tier and storage based on your needs

### Optimize Redis Cache

1. Go to your Redis Cache service
2. Under "Settings", click "Scale"
3. Consider upgrading to a higher tier if needed

## Security Considerations

1. **Access Management**:
   - Use Azure Active Directory to manage access to your resources
   - Apply the principle of least privilege for service identities

2. **Network Security**:
   - Consider using VNet integration for Container Apps
   - Use Private Endpoints for Azure services where possible

3. **Secrets Management**:
   - Consider using Azure Key Vault for storing secrets
   - Rotate access keys and passwords regularly

4. **Monitoring and Alerts**:
   - Set up alerts for abnormal activity
   - Regularly review security recommendations in Azure Security Center

## Cost Optimization

1. **Resource Sizing**:
   - Adjust the compute resources based on actual usage
   - Consider using reserved instances for predictable workloads

2. **Auto-scaling**:
   - Configure auto-scaling rules to scale down during periods of low activity

3. **Storage Optimization**:
   - Implement lifecycle management for blob storage
   - Monitor database storage and clean up unused data

## Backup and Disaster Recovery

1. **Database Backups**:
   - Configure automated backups for your PostgreSQL database
   - Test restoration procedures regularly

2. **Application State**:
   - Ensure all application state is stored in persistent storage
   - Document the steps to recreate the environment if needed

3. **Regional Redundancy**:
   - For production workloads, consider deploying to multiple regions
   - Set up traffic manager for failover