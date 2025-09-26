from fastapi import FastAPI
from models import ChatRequest, ChatResponse
from db import fetch_products, init_db
from contextlib import asynccontextmanager
from bot import ConversationalRAGBot

app = FastAPI()
bot = ConversationalRAGBot()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("Starting up...")
    await init_db()
    print("Database initialized.")
    
    yield  # <-- App runs while inside this context
    
    # Shutdown logic
    print("Shutting down...")

app = FastAPI(lifespan=lifespan)

@app.post("/chat")
async def chat(request: ChatRequest):
    # # Fetch products from DB
    # rows = fetch_products()

    # Get AI response
    answer = await bot.generate_response(
        user_id=request.user_id,
        user_query=request.user_query,
    )
    return {"response": answer}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)