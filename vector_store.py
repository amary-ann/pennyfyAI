from langchain_openai import AzureOpenAIEmbeddings
from config import embed_deployment, subscription_key, embed_endpoint

class VectorStore:
    def __init__(self):
        self.embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=embed_endpoint,
            azure_deployment=embed_deployment,
            api_key=subscription_key,
            api_version="2024-06-01"
        )

    def embed_text(self, text: str):
        return self.embeddings.embed_query(text)
