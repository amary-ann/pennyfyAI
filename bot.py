from langchain_openai import AzureChatOpenAI
from langchain.schema import HumanMessage
from config import endpoint, deployment, subscription_key
from vector_store import VectorStore
from db import fetch_conversation_history, fetch_products, fetch_stores
from utils import extract_price_range, extract_store_names


class ConversationalRAGBot:
    def __init__(self):
        self.vector_store = VectorStore()
        self.client = AzureChatOpenAI(
            openai_api_version="2024-12-01-preview",  # match your Azure API version
            azure_deployment=deployment,              # the deployment name of your GPT model in Azure
            azure_endpoint=endpoint,                  # your Azure endpoint from the portal
            api_key=subscription_key,                 # your Azure API key
        )

    async def generate_response(self, user_id, user_query):
        # save_message(user_id, "User", user_query)

        # Get available stores
        available_stores = await fetch_stores()

        # Extract filters
        min_price, max_price = extract_price_range(user_query)
        store_names = extract_store_names(user_query, available_stores)

        # Fetch only relevant rows
        rows = await fetch_products(
            min_price=min_price,
            max_price=max_price,
            store_names=store_names,
            limit=None
        )
        # Vector similarity
        retrieved_items = self.vector_store.query(user_query, rows, k=5)

        retrieved_text = "\n".join(
            [f"{pname} from {store_name} under {category} at ${price}" for _, pname, price, category, store_name in retrieved_items]
        )

        # Fetch conversation history
        # history = await fetch_conversation_history(user_id)
        # history_text = "\n".join(history)
        history_text = ""

        prompt = f"""
You are a helpful shopping assistant.

CONTEXT:
{retrieved_text or "No relevant products found."}

CONVERSATION HISTORY:
{history_text}

USER QUERY:
{user_query}

INSTRUCTIONS:
- Only use the retrieved context to answer the user's query.
- Keep it conversational, friendly, and concise.
- If no relevant info, politely say you don’t have enough information.

ANSWER:
"""
        response = self.client.invoke([HumanMessage(content=prompt)])
        answer = response.content

        # Save assistant response
        # save_message(user_id, "Assistant", answer)

        return answer
