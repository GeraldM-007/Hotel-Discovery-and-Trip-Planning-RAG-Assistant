import os
from contextlib import asynccontextmanager
from pathlib import Path
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request  
from fastapi.middleware.cors import CORSMiddleware 
from openai import OpenAI
from pydantic import BaseModel, Field #defines and validates request and response data
from sentence_transformers import SentenceTransformer 
from fastapi.staticfiles import StaticFiles
from src.rag.rag import answer_question, NVIDIA_BASE_URL
from src.rag.vector_store import create_collection
from app.config import BASE_DIR

VECTOR_DB_DIR = BASE_DIR / "Data" / "vector-store"
FRONTEND_DIR = BASE_DIR / "frontend"

COLLECTION_NAME = "travel_africa_kenya_destinations"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

#lifespan function provides initialization when app starts and provides place for cleanup after shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv(BASE_DIR / ".env") 
    #valiate that the api key exists
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise RuntimeError("NVIDIA_API_KEY not found!")
    
    #app.state lets different endpoints access a shared application resources without loading the model for every request
    #load the embedding model into memory and store into FastAPI application state
    app.state.embedding_model = SentenceTransformer(EMBEDDING_MODEL) 
    
    #open collection containing embeddings
    app.state.collection = create_collection(VECTOR_DB_DIR, COLLECTION_NAME)
    
    #verify if the collection contains data. If not raise error
    if app.state.collection.count() == 0:
        raise RuntimeError(f"Vector store at {VECTOR_DB_DIR} is empty.")
    
    #initialize the groq client
    app.state.nvidia_client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)
    
    yield 


#lifespan = lifespan tells FastAPI to run the lifespan function when the app starts
app = FastAPI(title="Travel Africa RAG API", lifespan=lifespan)

#allow cross origin resource sharing as browsers enforce restrictions on requests from one origin to another
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8080"],
    allow_credentials= True,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

#defines the json data accepted by /api/ask endpoint
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    n_results: int = 5

#Defines the structure of each source returned with the answer
class Source(BaseModel):
    reference: str
    destination: str | None = None
    section: str | None = None
    source_url: str | None = None
    distance: float | None = None

#Defines the structure of a successful response
class AskResponse(BaseModel):
    answer: str 
    sources: list[Source] 

#define what is returned when the endpoint / is accessed
@app.get("/api/health")
def api_health():
    return {"status": "healthy"}


@app.post("/api/ask", response_model=AskResponse)
def ask(body: AskRequest, request: Request):
    #remove white spaces from the beginning and end of the question
    question = body.question.strip()
    
    #reject an empty question by throwing an error
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    
    #call the function answer_question in rag.py
    try:
        return answer_question(
            question=question,
            collection=request.app.state.collection,
            embedding_model=request.app.state.embedding_model,
            nvidia_client=request.app.state.nvidia_client,
            n_results=body.n_results,
        )
    except ValueError as exc:  # raised by answer_question for bad input
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=502, detail="The assistant couldn't answer right now. Please try again.")


# Serve the UI last so it doesn't shadow /api/*
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run("server:app", reload = True, host= "127.0.0.1", port=8080)