import os
from dotenv import load_dotenv

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY", "your-openai-key")  # replace with your key
subscription_key = os.getenv("AZURE_OPENAI_API_KEY", "your-azure-key") # replace with your key
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://your-resource-name.openai.azure.com/") # replace with your endpoint
deployment = os.getenv("DEPLOYMENT_NAME", "deployment-name") # replace with your deployment name
embed_deployment = os.getenv("EMBED_DEPLOYMENT")

DB_CONFIG = {
    "host": "pennyfy-staging.cpuqassmwrgm.us-east-1.rds.amazonaws.com",
    "user": "pennyfy",
    "password": "Freda29%",
    "database": "pennyfy",
    "port": 5432,
}