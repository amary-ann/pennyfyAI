import faiss
import numpy as np
from openai import AzureOpenAI
from config import openai_api_key, endpoint, subscription_key

class VectorStore:
    def __init__(self, embedding_model="text-embedding-3-large"):
        self.embedding_model = embedding_model
        self.client = AzureOpenAI(
            api_version="2024-12-01-preview",
            azure_endpoint=endpoint,
            api_key=subscription_key,
        )
        # Cache to avoid recomputing embeddings
        self.embedding_cache = {}

    def embed_text(self, text: str):
        """Get embedding for a single text, with caching."""
        if text in self.embedding_cache:
            return self.embedding_cache[text]

        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        vector = np.array(response.data[0].embedding, dtype=np.float32)
        self.embedding_cache[text] = vector
        return vector

    def query(self, query_text, rows, k=5):
        """
        Given pre-filtered rows from DB, do semantic search.
        """
        if not rows:
            return []

        embeddings = []
        for pid, pname, price, category, store_name in rows:
            text = f"Product: {pname}, Price: ${price}, Category:{category}, Store: {store_name}"
            emb = self.embed_text(text)
            embeddings.append(emb)

        embeddings = np.vstack(embeddings)
        dim = embeddings.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(embeddings)

        query_emb = self.embed_text(query_text).reshape(1, -1)
        distances, indices = index.search(query_emb, min(k, len(rows)))

        return [rows[i] for i in indices[0]]


