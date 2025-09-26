import asyncio
import asyncpg
from openai import AzureOpenAI
import numpy as np
from config import DB_CONFIG, endpoint, subscription_key

client = AzureOpenAI(
    api_version="2024-12-01-preview",
    azure_endpoint=endpoint,
    api_key=subscription_key,
)

async def backfill_embeddings():
    conn = await asyncpg.connect(**DB_CONFIG)

    rows = await conn.fetch('SELECT id, name, "pennyfyPrice", category FROM "Product" WHERE embedding IS NULL')
    for r in rows:
        text = f"Product: {r['name']}, Price: ${r['pennyfyPrice']}, Category: {r['category']}"
        response = client.embeddings.create(
            model="text-embedding-3-large",
            input=text,
        )
        emb = response.data[0].embedding
        vector_str = "[" + ",".join(f"{x:.6f}" for x in emb) + "]"

        await conn.execute(
            'UPDATE "Product" SET embedding = $1::vector WHERE id = $2',
            vector_str,
            r["id"],
        )

    await conn.close()

asyncio.run(backfill_embeddings())
