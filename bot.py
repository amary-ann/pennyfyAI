from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import JsonOutputParser
from models import Session
from functionality import (
    search_documents_find_product,
    search_documents_compare_price,
    search_documents_recommendations,
    search_documents_shopping_list,
    search_documents_qa,
)


from config import endpoint, deployment, subscription_key

llm = AzureChatOpenAI(
    openai_api_version="2024-12-01-preview",  
    azure_deployment=deployment,              
    azure_endpoint=endpoint,                  
    api_key=subscription_key,
)

def get_user_request(session: Session, request_type_prompt):
    convo_string, _, user_query = get_chat_history(session)
    request_type= PromptTemplate.from_template(request_type_prompt)
    request_chain = request_type | llm

    response = request_chain.invoke({"chat_history" : convo_string })

    return response

# Initialize model client
def get_chat_history(session):
    convo_string = ""
    messages = []
    user_query = ""
    for message in session.chats:
        if message.is_user:
            convo_string += f"Customer: {message.message}\n"
            messages.append(HumanMessage(content=message.message))
            
            # Set user_query to the last message from the user
            user_query = message.message
        else:
            convo_string += f"PennyfyAI: {message.message}\n"
            messages.append(AIMessage(content=message.message))
    
    return convo_string, messages, user_query

def get_default_response(session, general_prompt):
    """Handle the default response unrelated to transaction requests."""
    convo_string, _, user_query = get_chat_history(session)
    general_prompt = ChatPromptTemplate.from_template(general_prompt)

    general_chain = general_prompt | llm | JsonOutputParser()

    response = general_chain.invoke({
        'chat_history': convo_string
        })
    return response

async def process_find_product(session, prompt, top_k: int = 10):

    convo_string, _, user_query = get_chat_history(session)

    llm = AzureChatOpenAI(
    openai_api_version="2024-12-01-preview",  
    azure_deployment=deployment,              
    azure_endpoint=endpoint,                  
    api_key=subscription_key,
)
    
    docs = await search_documents_find_product(user_query, limit=top_k)
    context = "\n".join([f"- {d['text']} | {d['metadata']}" for d in docs])

    find_prod_prompt = ChatPromptTemplate.from_template(
        prompt
    )
    
    find_prod_chain = find_prod_prompt | llm |JsonOutputParser()

    response = find_prod_chain.invoke({
        "product_info": context,
        "chat_history": convo_string,
    })

    return response

async def process_shopping_list(session, prompt):
    """
    Handles the end-to-end flow for creating a shopping list request.
    """
    convo_string, _, user_query = get_chat_history(session)

    llm = AzureChatOpenAI(
    openai_api_version="2024-12-01-preview",  
    azure_deployment=deployment,              
    azure_endpoint=endpoint,                  
    api_key=subscription_key,
)
    # 1️⃣ Retrieve items + prices from DB
    results = await search_documents_shopping_list(user_query, llm)

    # 2️⃣ Generate a clean response with LLM (optional step for tone)
    if not results["shopping_list"]:
        return results # No items found
    
    context = "\n".join(
        [f"- {r['product_name']} (${r['price']}) from {r['store']}" for r in results["shopping_list"]]
    )

    shopping_list_prompt = ChatPromptTemplate.from_template(
        prompt
    )

    shopping_list_chain = shopping_list_prompt | llm |JsonOutputParser()

    response = shopping_list_chain.invoke({
        "shopping_list_info": context,
        "chat_history": convo_string,
    })

    return response

async def process_compare_price(session,prompt, top_k: int = 20):

    convo_string, _, user_query = get_chat_history(session)

    llm = AzureChatOpenAI(
    openai_api_version="2024-12-01-preview",  
    azure_deployment=deployment,              
    azure_endpoint=endpoint,                  
    api_key=subscription_key,
)
    
    docs = await search_documents_compare_price(user_query,llm)

    print("docs type:", docs)
    print("🧠 Compare price retrieved data:", docs)
    
    # --- 2️⃣ If retrieval failed ---
    if not docs["comparisons"]:
        return {"error": "No comparable products found."}
    
    # --- 3️⃣ Build a readable context for the LLM ---
    comparison_lines = []
    for comparison in docs["comparisons"]:
        product = comparison["product"]
        comparison_lines.append(f"\n### {product.title()}:\n")
        for r in comparison["results"]:
            store = r.get("store", "Unknown")
            name = r.get("product_name", "N/A")
            price = r.get("price", "N/A")
            comparison_lines.append(f"- {store}: {name} — ${price}")

    comparison_context = "\n".join(comparison_lines)
    print("🧠 Comparison context for LLM:", comparison_context)

    comparison_prompt = ChatPromptTemplate.from_template(
        prompt
    )
    comparison_chain = comparison_prompt| llm |JsonOutputParser()

    response = comparison_chain.invoke({
        "comparison_context": comparison_context,
        "chat_history": convo_string,
    })

    return response


async def process_recommendation(session: str,prompt, top_k: int = 15):
    convo_string, _, user_query = get_chat_history(session)
    
    llm = AzureChatOpenAI(
    openai_api_version="2024-12-01-preview",  
    azure_deployment=deployment,              
    azure_endpoint=endpoint,                  
    api_key=subscription_key,
)
    docs = await search_documents_recommendations(user_query,limit=top_k)
    context = "\n".join([f"- {d['text']} | {d['metadata']}" for d in docs])

    prod_rec_prompt = ChatPromptTemplate.from_template(
        prompt
    )

    prod_rec_chain = prod_rec_prompt | llm |JsonOutputParser()

    response = prod_rec_chain.invoke({
        "recommendation_context": context,
        "chat_history": convo_string,
    })

    return response

async def process_qa(session, prompt, top_k: int = 10):
    convo_string, _, user_query = get_chat_history(session)

    llm = AzureChatOpenAI(
    openai_api_version="2024-12-01-preview",  
    azure_deployment=deployment,              
    azure_endpoint=endpoint,                  
    api_key=subscription_key,
)
    
    docs = await search_documents_qa(user_query, limit=top_k)
    context = "\n".join([f"- {d['text']} | {d['metadata']}" for d in docs])

    qa_prompt = ChatPromptTemplate.from_template(
        prompt
    )

    qa_chain = qa_prompt | llm |JsonOutputParser()

    response = qa_chain.invoke({
        "qa_context": context,
        "chat_history": convo_string,
    })

    return response
