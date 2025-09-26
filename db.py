# import mysql.connector
# from config import DB_CONFIG

# def get_connection():
#     return mysql.connector.connect(**DB_CONFIG)

# def fetch_stores():
#     conn = get_connection()
#     cursor = conn.cursor()
#     cursor.execute("SELECT name FROM store")
#     rows = cursor.fetchall()
#     cursor.close()
#     conn.close()
#     return [r[0] for r in rows]  # flatten list

# def fetch_products(min_price=None, max_price=None, store_names=None, limit=100):
#     conn = get_connection()
#     cursor = conn.cursor()

#     query = """
#     SELECT p.id, p.name, p.pennyfyprice, p.category, s.name AS store_name
#     FROM product p
#     JOIN store s ON p.storeid = s.id
#     WHERE 1=1
#     """
#     params = []

#     if min_price is not None:
#         query += " AND p.pennyfyprice >= %s"
#         params.append(min_price)

#     if max_price is not None:
#         query += " AND p.pennyfyprice <= %s"
#         params.append(max_price)

#     if store_names:
#         query += " AND s.name IN (%s)" % ",".join(["%s"] * len(store_names))
#         params.extend(store_names)

#     query += " LIMIT %s"
#     params.append(limit)

#     cursor.execute(query, params)
#     rows = cursor.fetchall()
#     cursor.close()
#     conn.close()
#     return rows


# # --- Conversation storage ---

# def save_message(user_id: str, role: str, message: str):
#     conn = get_connection()
#     cursor = conn.cursor()
#     query = """
#     INSERT INTO conversations (userid, role, message)
#     VALUES (%s, %s, %s)
#     """
#     cursor.execute(query, (user_id, role, message))
#     conn.commit()
#     cursor.close()
#     conn.close()

# def fetch_conversation_history(user_id: str, limit: int = 10):
#     conn = get_connection()
#     cursor = conn.cursor()
#     query = """
#     SELECT role, message
#     FROM conversations
#     WHERE userid = %s
#     ORDER BY created_at DESC
#     LIMIT %s
#     """
#     cursor.execute(query, (user_id, limit))
#     rows = cursor.fetchall()
#     cursor.close()
#     conn.close()
#     # Return newest-last for prompt context
#     return [f"{role}: {msg}" for role, msg in reversed(rows)]


import asyncpg
from config import DB_CONFIG

pool: asyncpg.Pool = None

async def init_db():
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"],
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            min_size=1,
            max_size=5,  # adjust based on load
        )

# ---- QUERIES ----

async def fetch_products(min_price=None, max_price=None, store_names=None,limit=None, offset=0):
    async with pool.acquire() as conn:
        query = """
        SELECT p.id, p.name, p."pennyfyPrice", p.category, s.name AS store_name
        FROM "Product" p
        JOIN "Store" s ON p."storeId" = s.id
        WHERE 1=1
        """
        params = []

        if min_price is not None:
            query += ' AND p."pennyfyPrice" >= $%d' % (len(params) + 1)
            params.append(min_price)

        if max_price is not None:
            query += ' AND p."pennyfyPrice" <= $%d' % (len(params) + 1)
            params.append(max_price)

        if store_names:
            placeholders = ",".join([f"${i}" for i in range(len(params) + 1, len(params) + 1 + len(store_names))])
            query += f" AND s.name IN ({placeholders})"
            params.extend(store_names)

        if limit is not None:
            query += f" LIMIT ${len(params) + 1}"
            params.append(limit)

        query += f" ORDER BY p.id ASC LIMIT ${len(params)+1} OFFSET ${len(params)+2}"
        params.extend([limit, offset])

        rows = await conn.fetch(query, *params)
        return [tuple(row.values()) for row in rows]


async def save_message(user_id: str, role: str, message: str):
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO conversations (userid, role, message)
            VALUES ($1, $2, $3)
            """,
            user_id, role, message
        )


async def fetch_conversation_history(user_id: str, limit: int = 10):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT role, message
            FROM conversations
            WHERE userid = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            user_id, limit
        )
        return [f"{r['role']}: {r['message']}" for r in reversed(rows)]


async def fetch_stores():
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT name FROM "Store"')
        return [r["name"] for r in rows]
