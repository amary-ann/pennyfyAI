import asyncpg
from typing import List, Optional
from vector_store import VectorStore  # Handles embedding generation
from prompts import EXTRACT_SHOPPING_ITEMS_PROMPT, EXTRACT_STORE_NAMES_PROMPT
import json
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import AzureChatOpenAI

from config import endpoint, deployment, subscription_key


pool: asyncpg.Pool | None = None

def normalize_text(text: str) -> str:
    """Convert text to uppercase and remove all spaces."""
    if not text:
        return ""
    return text.replace(" ", "").upper()

# ------------------------------
# ✅ DB CONNECTION INITIALIZER
# ------------------------------
async def init_db(config):
    """Initialize asyncpg connection pool."""
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(
            user=config["user"],
            password=config["password"],
            database=config["database"],
            host=config["host"],
            port=config["port"],
            min_size=2,
            max_size=20,
        )


# ------------------------------
# ✅ GENERIC SEARCH UTILITY
# ------------------------------
async def _query_documents(q_emb, limit: int = 10, filters: Optional[dict] = None):

    global pool
    if pool is None:
        raise RuntimeError("Database connection pool not initialized. Call init_db(config) first.")
    
    if isinstance(q_emb, list):
        q_emb = "[" + ",".join(str(x) for x in q_emb) + "]"  # ✅ Convert list to vector string

    where_clauses = ["embedding IS NOT NULL"]
    params = [q_emb]
    idx = 2



    # Dynamic filters (optional)
    if filters:
        for key, value in filters.items():
            where_clauses.append(f"{key} = ${idx}")
            params.append(value)
            idx += 1

    where_sql = f"WHERE {' AND '.join(where_clauses)}"

    sql = f"""
        SELECT 
            id,
            text,
            metadata,
            product_id,
            store_id,
            store_name,
            location,
            price,
            category,
            1 - (embedding <#> $1) AS similarity
        FROM documents
        {where_sql}
        ORDER BY embedding <#> $1
        LIMIT {limit};
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)

    return [dict(row) for row in rows]


# ------------------------------
# 🧩 FIND PRODUCT
# ------------------------------
async def search_documents_find_product(query_text: str, limit: int = 10, filters: Optional[dict] = None):
    vs = VectorStore()
    q_emb = vs.embed_text(query_text)
    rows = await _query_documents(q_emb, limit, filters)
    return [
        {
            "id": r["id"],
            "text": f"{r['text']}",
            "metadata": {
                "price": r["price"],
                "store": r["store_name"],
                "category": r["category"],
                "similarity": r["similarity"],
            },
        }
        for r in rows
    ]


# ------------------------------
# ⚖️ COMPARE PRICE
# ------------------------------
async def search_documents_compare_price(query_text: str,llm_client, limit: int = 5):
    """
    Compare the price of a product mentioned in the query across the stores named in the same query.
    Example:
      "Compare iPhone 15 from Pennyfy Mobile and TechMart"
    """
    
    vs = VectorStore()
    q_emb = vs.embed_text(query_text)

    # --- 1️⃣ Extract potential store names from query ---
    extract_store = ChatPromptTemplate.from_template(
        EXTRACT_STORE_NAMES_PROMPT
        )
    extract_chain = extract_store | llm_client |JsonOutputParser()

    response = extract_chain.invoke({
        "user_request": query_text,
    })

    print("🧠 Extracted entities:", response)

    products = response["product_names"]
    stores = response["store_names"]

    print(f"Products to compare: {products}")

    if not products:
        return {"error": "No products found in query."}
    
    stores = [normalize_text(s) for s in stores if s]

    results = []

     # --- 2️⃣ Batch embed all products ---
    print(f"Embedding {len(products)} products...")
    embeddings = vs.embeddings.embed_documents(products)
    print("✅ Embeddings generated")

    # --- 2️⃣ Search for each store (if specified) ---
    async with pool.acquire() as conn:
        # --- 3️⃣ For each product, compare across stores ---
        for product, emb in zip(products, embeddings):
            emb_vector = "[" + ",".join(str(x) for x in emb) + "]"
            product_comparisons = []
            for store in stores or [None]:
                where_clauses = ["embedding IS NOT NULL"]
                params = [emb_vector]
                idx = 2

                if store:
                    where_clauses.append(
                        f"LOWER(REPLACE(store_name, ' ', '')) = LOWER(REPLACE(${idx}, ' ', ''))"
                    )
                    params.append(store)
                    idx += 1

                where_sql = f"WHERE {' AND '.join(where_clauses)}"

                sql = f"""
                    SELECT
                        text,
                        store_name,
                        price,
                        category,
                        1 - (embedding <#> $1) AS similarity
                    FROM documents
                    {where_sql}
                    ORDER BY embedding <#> $1
                    LIMIT {limit};
                """

                rows = await conn.fetch(sql, *params)
                print(f"🔍 {len(rows)} matches for '{product}' in {store or 'all stores'}")

                if not rows:
                    product_comparisons.append({
                        "store": store or "N/A",
                        "product_name": None,
                        "price": None,
                        "similarity": 0.0,
                        "found": False
                    })
                    continue

                best = max(rows, key=lambda r: r["similarity"] or 0.0)
                product_comparisons.append({
                    "store": best["store_name"],
                    "product_name": best["text"],
                    "price": float(best["price"]) if best["price"] else None,
                    "similarity": float(best["similarity"]),
                    "found": True
                })

            results.append({
                "product": product,
                "results": product_comparisons
            })

    return {
        "comparisons": results
    }


# ------------------------------
# 🛍️ PRODUCT RECOMMENDATIONS
# ------------------------------
async def search_documents_recommendations(query_text: str, limit: int = 10):
    vs = VectorStore()
    q_emb = vs.embed_text(query_text)
    rows = await _query_documents(q_emb, limit)
    return [
        {
            "id": r["id"],
            "text": f"{r['text']}",
            "metadata": {
                "store": r["store_name"],
                "price": r["price"],
                "category": r["category"],
                "similarity": r["similarity"],
            },
        }
        for r in rows
    ]

# ------------------------------
# 🧾 SHOPPING LIST
# ------------------------------
async def search_documents_shopping_list(query_text: str, llm_client, limit: int = 5):
    """
    Given a user request like "Make a shopping list for baking a cake",
    extract items (via LLM) and find matching products across stores.
    """
    vs = VectorStore()

    # --- 1️⃣ Extract relevant items using the LLM ---
    extract_item = ChatPromptTemplate.from_template(
        EXTRACT_SHOPPING_ITEMS_PROMPT
        )
    extract_chain = extract_item | llm_client |JsonOutputParser()

    response = extract_chain.invoke({
        "user_request": query_text,
    })

    print("Extracted shopping list response:", response)

    # Assume extraction returns JSON like {"task": "baking a cake", "items": ["flour", "sugar", "eggs", "butter"]}
    try:
        items = response["items"]
        task = response["task"]
    except Exception:
        items, task = [], ""

    if not items:
        return {"shopping_list": [], "total_price": 0.0, "task": task, "response_message": response['response_message']}
    
      # --- Step 2️⃣: Batch embed all items ---
    print(f"Embedding {len(items)} items in batch...")
    embeddings = vs.embeddings.embed_documents(items)
    print("✅ Embeddings generated successfully")

    # 3️⃣ Prepare search patterns
    search_patterns = [f"%{item.lower()}%" for item in items]

    shopping_list = []
    total_price = 0.0

    async with pool.acquire() as conn:
        # 4️⃣ Single query for all items (with optional store filter)
        store = normalize_text(response.get("store")) if response.get("store") else None
        if store:
            rows = await conn.fetch(
         """
                SELECT text, store_name, price, category
                FROM documents
                WHERE LOWER(text) ILIKE ANY($1::text[])
                  AND LOWER(REPLACE(store_name, ' ', '')) = LOWER(REPLACE($2, ' ', ''))
                ORDER BY price ASC
                """,
                search_patterns, store
            )
        else:
            rows = await conn.fetch(
                """
                SELECT text, store_name, price, category
                FROM documents
                WHERE LOWER(text) ILIKE ANY($1::text[])
                ORDER BY price ASC
                """,
                search_patterns
            )

        # 5️⃣ Map rows to items
        for item, emb in zip(items, embeddings):
            # Filter rows that match this item
            matches = [r for r in rows if item.lower() in r["text"].lower()]
            
            if not matches:
                # Fallback embedding similarity
                emb_vector = "[" + ",".join(str(x) for x in emb) + "]"
                matches = await conn.fetch(
                    """
                    SELECT text, store_name, price, category,
                           1 - (embedding <#> $1) AS similarity
                    FROM documents
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <#> $1
                    LIMIT $2
                    """,
                    emb_vector, limit
                )

            if matches:
                best = matches[0]
                product = {
                    "item": item,
                    "product_name": best["text"],
                    "store": best["store_name"],
                    "price": float(best["price"]) if best["price"] else 0.0,
                    "category": best["category"],
                }
                total_price += product["price"]
                shopping_list.append(product)

    return {
        "task": task,
        "shopping_list": shopping_list,
        "total_price": round(total_price, 2),
        "response_message": ""
    }


# ------------------------------
# 💬 QA REQUESTS
# ------------------------------
async def search_documents_qa(query_text: str, limit: int = 5):
    """
    Handles informational questions like:
    - "Which stores are in Lagos?"
    - "What are the top stores selling shoes?"
    """
    vs = VectorStore()
    q_emb = vs.embed_text(query_text)
    if isinstance(q_emb, list):
                    q_emb = "[" + ",".join(str(x) for x in q_emb) + "]"

    # Optional heuristic filter for location queries
    filters = None
    if "lagos" in query_text.lower():
        filters = {"location": "Lagos"}

    rows = await _query_documents(q_emb, limit, filters)
    return [
        {
            "text": f"{r['store_name']} in {r['location']} sells {r['category']} products.",
            "metadata": {
                "store": r["store_name"],
                "location": r["location"],
                "category": r["category"],
            },
        }
        for r in rows
    ]
