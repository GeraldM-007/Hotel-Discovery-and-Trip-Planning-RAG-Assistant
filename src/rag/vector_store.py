#Turning chunks into vectors and storing them in vector database (chromaDB)
import json
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer #loads the embedding model and generates vectors
from typing import Any
from app.config import BASE_DIR

CHUNKS_PATH = BASE_DIR/ "Data" / "processed" / "chunks" / "magical_kenya_chunks.jsonl"
VECTOR_DB_DIR = BASE_DIR / "Data" / "vector-store"

COLLECTION_NAME = "travel_africa_kenya_destinations"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

#read the chunks in the .jsonl file create a list of validated chunks. VectorDB should not received malformed records.
def load_chunks(chunks_path: Path = CHUNKS_PATH):
    #check if chunk file exists and raise error if it doesn't
    if not chunks_path.is_file():
        raise FileNotFoundError(f"Chunk file not found: {chunks_path}")
    
    #create a list of validated chunks.
    chunks = []
    
    with chunks_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start = 1):
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at line {line_number}") from exc            
            chunks.append(chunk)
            
    return chunks

#Build an embedding fuction. It turns words into vectors
def create_embeddings(texts:list[str], model: SentenceTransformer):
    if not texts:
        return[]
    
    #pass the text chunks through the embedding model, 32 words at a time and 
    vectors = model.encode(texts, batch_size = 32, normalize_embeddings=True, show_progress_bar=False)
    #The model returns an array like numerical structure and we convert it into a python list using .tolist() which can be passed to chromaDB
    return vectors.tolist() 

#Creating a persistent collection(table in chromaDB)
def create_collection(db_dir: Path = VECTOR_DB_DIR, collection_name: str = COLLECTION_NAME):
    db_dir.mkdir(parents=True, exist_ok=True)
    
    #create a persistent DB so that vectors can be available even after the ChromaDB stops running
    client = chromadb.PersistentClient(path=str(db_dir))
    collection = client.get_or_create_collection(name= collection_name, metadata={"hnsw:space": "cosine"})
    
    return collection

#create metadata for the chunks
def chunk_metadata(chunk: dict[str, Any]): #the keys are strings, but values can be anything
    metadata = {}
    
    for key, value in chunk.items():
        #exclude text and chunk because they do not make the metadata, they are content
        if key in {"text", "chunk_id", "word_count"} or value is None:
            continue
        #create metadata from the other present values
        if isinstance(value, (str, int, float, bool)):
            metadata[key] = value
        
    return metadata

#Embedd and insert chunks into the vectorDB in batches
def store_vectors(chunks: list[dict[str, Any]], collection, model: SentenceTransformer, batch_size: int = 64):
        
    if batch_size <= 0:
        raise ValueError("Bath size cannot be a negative value")
    
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        texts = [chunk["text"] for chunk in batch]
        collection.upsert(
            ids =[chunk["chunk_id"] for chunk in batch],
            documents = texts,
            embeddings = create_embeddings(texts, model),
            metadatas = [chunk_metadata(chunk) for chunk in batch]
        )
    return len(chunks)

#Telling vectorDB how to search the stored vectors
def search_vectors(query: str, collection, model: SentenceTransformer, n_results: int =5):
    
    #check if the collection contains records
    count = collection.count()
    if count == 0:
        return []
    
    #convert the user's query into a vector
    query_embedding = create_embeddings([query], model)[0]
    
    #Apply the vector similarity search (usually cosine similarity)
    search_results = collection.query(
        query_embeddings = [query_embedding], #the query in vector form
        n_results = min(n_results, count), #never ask for more results than exist in the collection
        include = ["documents", "metadatas", "distances"] #tells the database what to return
    )
    
    return[
        {
            "chunk_id": chunk_id,
            "text": text,
            "metadata": metadata,
            "distance": distance,
        }
        #formatt the output using zip() to combine corresponding values from the list into individual records
        for chunk_id, text, metadata, distance in zip(
            search_results["ids"][0],
            search_results["documents"][0],
            search_results["metadatas"][0],
            search_results["distances"][0]
        )
    ]
