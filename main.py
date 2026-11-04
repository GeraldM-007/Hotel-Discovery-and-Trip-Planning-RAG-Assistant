from pathlib import Path
import json
from src.MagicalKenya.Parser import parse_html
from src.rag.chunking import load_documents, create_document_chunks, save_chunks
from src.rag.vector_store import load_chunks, SentenceTransformer, create_collection, store_vectors
import os
from dotenv import load_dotenv
from openai import OpenAI
from app.config import BASE_DIR
from src.MagicalKenya.Parser import RAW_DIR, PARSED_DIR
from src.rag.chunking import JSON_DIR, OUTPUT_PATH
from src.rag.vector_store import CHUNKS_PATH, VECTOR_DB_DIR, COLLECTION_NAME, EMBEDDING_MODEL
from src.KWS.kws_parser import RAW_KWS_HTML_DIR, KWS_JSON_DIR, check_document, kws_parse_html
from src.rag.kws_chunking import KWS_CHUNKS_PATH, load_kws_documents, create_kws_chunks, save_chunks, check_chunks, COMMON_DESTINATION
from src.rag.rag import answer_question, NVIDIA_BASE_URL


def main():
    
    #(MAGICAL KENYA) Scraping/Parsing downloaded html files into json
    for file_path in RAW_DIR.glob("*.html"):
        
        print(f"Parsing: {file_path}")
        
        mg_document = parse_html(file_path)
        
        output_file = (PARSED_DIR / f"{file_path.stem}.json")
        
        with output_file.open("w", encoding = "utf-8") as f:
            json.dump(mg_document, f, ensure_ascii = False, indent = 2)
            
        print(f"Saved: {output_file}")  
        
    #(MAGICAL KENYA) Chunking parsed json files into word and semantic based chunking
    mg_documents = load_documents(JSON_DIR)
    
    all_chunks = []
    
    for mg_document in mg_documents:
        chunks = create_document_chunks(mg_document, chunk_size=300, overlap=50)
        
        all_chunks.extend(chunks)
    
    save_chunks(all_chunks, OUTPUT_PATH)
    
    print(f"Documents processed: {len(mg_documents)}")
    print(f"Chunks created: {len(all_chunks)}")
    print(f"saved to: {OUTPUT_PATH}")
    
    #(KWS) Scraping/parsing downloaded .html kws files into json
    
    html_files = sorted(RAW_KWS_HTML_DIR.glob("*.html"))

    if not html_files:
        print(f"No .html files found in {RAW_KWS_HTML_DIR}")
        return
    
    #create processed dir if does not exist
    KWS_JSON_DIR.mkdir(parents=True, exist_ok=True)

    pages_with_problems = []

    for file_path in html_files:
        print(f"Scraping: {file_path}")

        try:
            document = kws_parse_html(file_path)
        except Exception as error:
            print(f"  FAILED: {error}")
            pages_with_problems.append((file_path.name, [f"failed: {error}"]))
            continue

        output_file = KWS_JSON_DIR / f"{file_path.stem}.json"

        with output_file.open("w", encoding="utf-8") as f:
            json.dump(document, f, ensure_ascii=False, indent=2)

        print(f"Saved: {output_file}")
        print(f"  {document['park_name']}: {len(document['elements'])} elements, {len(document['rates'])} rates")

        problems = check_document(document)

        if problems:
            print(f"  CHECK: {'; '.join(problems)}")
            pages_with_problems.append((file_path.name, problems))

    print(f"\nPages scraped: {len(html_files)}")
    print(f"Pages to check: {len(pages_with_problems)}")

    for name, problems in pages_with_problems:
        print(f"  {name}: {'; '.join(problems)}")


    #(KWS) Chunking parsed json files into word and semantic based chunking
    
    documents = load_kws_documents(KWS_JSON_DIR)

    if not documents:
        print(f"No KWS documents found in {KWS_JSON_DIR}")
        return

    chunks, common_keys = create_kws_chunks(documents)

    save_chunks(chunks, KWS_CHUNKS_PATH)

    print(f"Documents processed: {len(documents)}")
    print(f"Lines moved to '{COMMON_DESTINATION}': {len(common_keys)}")
    print(f"Chunks created: {len(chunks)}")
    print(f"Saved to: {KWS_CHUNKS_PATH}")

    problems = check_chunks(chunks, documents)

    if problems:
        print("\nCHECK:")
        for problem in problems:
            print(f"  {problem}")


    
    #STORING CREATED CHUNKS (from both magical kenya and KWS json files) INTO A VECTORDB AND DEFINING HOW TO SEARCH THE DATABASE
    '''
    chunks = load_chunks(CHUNKS_PATH)
    if not chunks:
        print(f"No chunks found in {CHUNKS_PATH}: Nothing to store")
        return
    '''
    chunks = load_chunks(CHUNKS_PATH) if CHUNKS_PATH.is_file() else []
    
    if KWS_CHUNKS_PATH.is_file():
        chunks += load_chunks(KWS_CHUNKS_PATH)
        
    if not chunks:
        print(f"No chunks found in {CHUNKS_PATH} or {KWS_CHUNKS_PATH}: Nothing to store")
        return


    # add the Kenya Wildlife Service park chunks 
    if KWS_CHUNKS_PATH.is_file():
        chunks += load_chunks(KWS_CHUNKS_PATH)
    
    model = SentenceTransformer(EMBEDDING_MODEL)
    collection = create_collection(VECTOR_DB_DIR, COLLECTION_NAME)
    count = store_vectors(chunks, collection, model)
    
    print(f"chunks processed: {count}")
    print(f"Vectors in collection: {collection.count()}")
    print(f"ChromaDB location {VECTOR_DB_DIR}")
    
    # QUERYING THE VECTORDB AND PASSING THE OUTPUT TO AN LLM VIA PROMPT

    # Load environment variables
    load_dotenv(BASE_DIR / ".env")

    api_key = os.getenv("NVIDIA_API_KEY")

    if not api_key:
        raise ValueError("NVIDIA_API_KEY not found")

    # Load the embedding model
    embedding_model = SentenceTransformer(EMBEDDING_MODEL)

    # Connect to the existing ChromaDB collection
    collection = create_collection(VECTOR_DB_DIR, COLLECTION_NAME)
    
    #if the collection is empty and there is nothing to retrieve, the program stops
    if collection.count() == 0:
        print("Vector database is empty!!")
        return

    # Initialize Groq client
    nvidia_client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)

    print("TravelAfrica RAG Assistant")
    print("Type 'exit' to quit.")

    while True:

        question = input("\nQuestion: ").strip()

        if question.lower() in {"exit", "quit"}:
            break

        if not question:
            continue

        result = answer_question(question=question, collection=collection, embedding_model=embedding_model, nvidia_client=nvidia_client, n_results=5)

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