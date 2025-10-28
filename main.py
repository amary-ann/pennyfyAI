import os
import logging
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException,Depends, Security,Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
from datetime import datetime, timezone
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY
from beanie import init_beanie
from models import Session, Message,Request
from prompts import (
    GENERAL_BOT_PROMPT,
    REQUEST_DETECTOR_PROMPT,
    FIND_PRODUCT_SYSTEM_PROMPT,
    CREATE_SHOPPING_LIST_SYSTEM_PROMPT,
    COMPARE_PRICE_SYSTEM_PROMPT,
    PRODUCT_RECOMMENDATION_SYSTEM_PROMPT,
    QA_CONVERSATION_SYSTEM_PROMPT,
)
from bot import (
    get_user_request,
    get_default_response, 
    process_qa,
    process_find_product,
    process_compare_price, 
    process_shopping_list, 
    process_recommendation
)

from config import DB_CONFIG


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("execution before startup")
    collection_name =  os.getenv("MONGO_DB_COLLECTION")
    mongo_string = os.getenv("MONGO_CONNECTION_STRING")
    client = AsyncIOMotorClient(mongo_string)

    await init_beanie(
        database=client[collection_name],
        document_models=[Session]
    )
     # --- Initialize Postgres (asyncpg pool) ---
    from functionality import init_db

    await init_db(DB_CONFIG)
    print("✅ Postgres connection pool initialized")

    yield print("Execute before closed")

    
app = FastAPI(lifespan=lifespan)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/message")
async def send_message(request: Request):
    current_time = datetime.now(timezone.utc).replace(tzinfo=timezone.utc).time()

    session = await Session.find_one({"user_id": request.user_id})
    message = Message(message = request.message, is_user = True)
    
    if session:
        session.chats.append(message)
        await session.save()
        logging.info("User message saved to session")

    else:
        session = Session(user_id=request.user_id)
        session.chats = [message]
        await session.insert()
        logging.info("New session created and user message saved.")

    request_type = get_user_request(session, REQUEST_DETECTOR_PROMPT)
    print(request_type.content)

    if(request_type.content == "default"):
        res = get_default_response(session, GENERAL_BOT_PROMPT)
        result = res['response_message']
        print("Default", result)
    
    elif(request_type.content == "qa_conversation"):
        res  = await process_qa(session, QA_CONVERSATION_SYSTEM_PROMPT)
        result = res['response_message']
        print("QA response", result)

    elif(request_type.content == "find_product"):
        res  = await process_find_product(session, FIND_PRODUCT_SYSTEM_PROMPT)
        result = res['response_message']
        print("Response :", result)

    elif(request_type.content == "compare_price"):
        res  = await process_compare_price(session, COMPARE_PRICE_SYSTEM_PROMPT)
        result = res['response_message']
        print("Response :", result)

    elif(request_type.content == "product_recommendation"):
        res  = await process_recommendation(session, PRODUCT_RECOMMENDATION_SYSTEM_PROMPT)
        result = res['response_message']
        print("Response :", result)

    elif(request_type.content == "create_shopping_list"):
        res  =  await process_shopping_list(session, CREATE_SHOPPING_LIST_SYSTEM_PROMPT)
        result = res['response_message']
        print("Response :", result)

    print("Response after transfer:", result)
        
    if result:
        message = Message(message=result, is_user=False)
        session.chats.append(message)
        await session.save()
        logging.info("Bot response saved to session.")
        return {'response' : result}

    else: 
        return {'response' : "Error getting a response!!!" }
    