from pathlib import Path
import json
from src.MagicalKenya.Parser import parse_html
from src.rag.chunking import load_documents, create_document_chunks, save_chunks
from src.rag.vector_store import load_chunks, SentenceTransformer, create_collection, store_vectors
import os
from dotenv import load_dotenv
from groq import Groq
from app.config import BASE_DIR
from src.MagicalKenya.Parser import RAW_DIR, PARSED_DIR
from src.rag.chunking import JSON_DIR, OUTPUT_PATH
from src.rag.vector_store import CHUNKS_PATH, VECTOR_DB_DIR, COLLECTION_NAME, EMBEDDING_MODEL
from src.rag.rag import answer_question

def main():
    
    #(MAGICAL KENYA) Scraping/Parsing downloaded html files into json
    for file_path in RAW_DIR.glob("*.html"):
        
        print(f"Parsing: {file_path}")
        
        document = parse_html(file_path)
        
        output_file = (PARSED_DIR / f"{file_path.stem}.json")
        
        with output_file.open("w", encoding = "utf-8") as f:
            json.dump(document, f, ensure_ascii = False, indent = 2)
            
        print(f"Saved: {output_file}")  
        
    #(MAGICAL KENYA) Chunking parsed json files into word and semantic based chunking
    documents = load_documents(JSON_DIR)
    
    all_chunks = []
    
    for document in documents:
        chunks = create_document_chunks(document, chunk_size=300, overlap=50)
        
        all_chunks.extend(chunks)
    
    save_chunks(all_chunks, OUTPUT_PATH)
    
    print(f"Documents processed: {len(documents)}")
    print(f"Chunks created: {len(all_chunks)}")
    print(f"saved to: {OUTPUT_PATH}")
    
    
    #(KWS) Scraping/parsing downloaded .html kws files into json
    
    
    #(KWS) Chunking parsed json files into word and semantic based chunking
    
    
    #STORING CREATED CHUNKS INTO A VECTORDB AND DEFINING HOW TO SEARCH THE DATABASE
    chunks = load_chunks(CHUNKS_PATH)
    if not chunks:
        print(f"No chunks found in {CHUNKS_PATH}: Nothing to store")
        return
    
    model = SentenceTransformer(EMBEDDING_MODEL)
    collection = create_collection(VECTOR_DB_DIR, COLLECTION_NAME)
    count = store_vectors(chunks, collection, model)
    
    print(f"chunks processed: {count}")
    print(f"Vectors in collection: {collection.count()}")
    print(f"ChromaDB location {VECTOR_DB_DIR}")
    
    # QUERYING THE VECTORDB AND PASSING THE OUTPUT TO AN LLM VIA PROMPT

    # Load environment variables
    load_dotenv(BASE_DIR / ".env")

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError("GROQ_API_KEY not found")

    # Load the embedding model
    embedding_model = SentenceTransformer(EMBEDDING_MODEL)

    # Connect to the existing ChromaDB collection
    collection = create_collection(VECTOR_DB_DIR, COLLECTION_NAME)
    
    #if the collection is empty and there is nothing to retrieve, the program stops
    if collection.count() == 0:
        print("Vector database is empty!!")
        return

    # Initialize Groq client
    groq_client = Groq(api_key=api_key)

    print("TravelAfrica RAG Assistant")
    print("Type 'exit' to quit.")

    while True:

        question = input("\nQuestion: ").strip()

        if question.lower() in {"exit", "quit"}:
            break

        if not question:
            continue

        result = answer_question(question=question, collection=collection, embedding_model=embedding_model, groq_client=groq_client, n_results=5)

        print("\nAnswer:")
        print(result["answer"])

        print("\nSources:")

        for source in result["sources"]:
            print(
                f"{source['reference']} "
                f"{source['destination']} - "
                f"{source['section']}"
            )
            print(f"URL: {source['source_url']}")

    
if __name__ == "__main__":
    main()