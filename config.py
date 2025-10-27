import os
from dotenv import load_dotenv

load_dotenv()
# openai_api_key = os.getenv("OPENAI_API_KEY", "your-openai-key")  # replace with your key
subscription_key = os.getenv("AZURE_OPENAI_API_KEY", "your-azure-key") # replace with your key
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://your-resource-name.openai.azure.com/") # replace with your endpoint
deployment = os.getenv("DEPLOYMENT_NAME", "deployment-name") # replace with your deployment name
embed_deployment = os.getenv("EMBED_DEPLOYMENT")

DB_CONFIG = {
    "host": os.getenv("PG_HOST"),
    "user": os.getenv("PG_USER"),
    "password": os.getenv("PG_PWD"),
    "database": os.getenv("PG_DB"),
    "port": os.getenv("PORT"),
}
