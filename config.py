import os
from dotenv import load_dotenv

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY", "your-openai-key")  # replace with your key
subscription_key = os.getenv("AZURE_OPENAI_API_KEY", "your-azure-key") # replace with your key
endpoint = os.getenv("ENDPOINT_URL", "https://your-resource-name.openai.azure.com/") # replace with your endpoint
deployment = os.getenv("DEPLOYMENT_NAME", "gpt-4.1")


# DB_CONFIG = {
#         "user": os.getenv("MYSQL_USER"),
#         "password": os.getenv("MYSQL_PASSWORD"),
#         "host": os.getenv("MYSQL_HOST"),
#         "database": os.getenv("MYSQL_DB"),
#         "port": int(os.getenv("MYSQL_PORT", 3306)),
#     }

DB_CONFIG = {
    "host": "pennyfy-staging.cpuqassmwrgm.us-east-1.rds.amazonaws.com",
    "user": "pennyfy",
    "password": "Freda29%",
    "database": "pennyfy",
    "port": 5432,
}