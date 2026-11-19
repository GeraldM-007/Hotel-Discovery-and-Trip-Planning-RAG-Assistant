from pathlib import Path
import json
from src.MagicalKenya.Parser import parse_html
from src.rag.chunking import load_documents, create_document_chunks, save_chunks
from src.rag.vector_store import load_chunks, SentenceTransformer, create_collection, store_vectors
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from openai import OpenAI
from collections import Counter, defaultdict
from app.config import BASE_DIR
from src.MagicalKenya.Parser import RAW_DIR, PARSED_DIR
from src.rag.chunking import JSON_DIR, OUTPUT_PATH
from src.rag.vector_store import CHUNKS_PATH, VECTOR_DB_DIR, COLLECTION_NAME, EMBEDDING_MODEL
from src.KWS.kws_parser import RAW_KWS_HTML_DIR, KWS_JSON_DIR, check_document, kws_parse_html
from src.rag.kws_chunking import KWS_CHUNKS_PATH, load_kws_documents, create_kws_chunks, save_chunks, check_chunks, COMMON_DESTINATION
from src.rag.rag import answer_question, NVIDIA_BASE_URL
from src.KWS.kws_accommodations_download import RAW_ACCOMMODATION_HTML_DIR
from app.config import KWS_ACCOMMODATIONS_LISTING_URL
from src.KWS.kws_accommodation_scraper import KWS_ACCOMMODATION_PROCESSED_DIR, parse_listing, home_id, check_homes
from src.rag.kws_accommodation_chunking import ACCOMMODATION_JSON_PATH, ACCOMMODATION_CHUNKS_PATH, load_homes, create_home_chunks, create_park_chunks, check_accommodation_chunks

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
    
    #(KWS_DESTINATIONS) Scraping/parsing downloaded .html kws files into json
    
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


    #(KWS_DESTINATIONS) Chunking parsed json files into word and semantic based chunking
    
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
            
    #(KWS_ACCOMMODATIONS) Scrapping/Parsing downloaded kws_accommodation sites from kws.go.ke/mbugani-homes
        
    kws_accommodation_files = sorted(RAW_ACCOMMODATION_HTML_DIR.glob("*.html")) + list(RAW_ACCOMMODATION_HTML_DIR.glob("*.htm"))
    
    if not kws_accommodation_files:
        print(f"No saved pages in {RAW_ACCOMMODATION_HTML_DIR}")
    
    #create dir if does not exist
    KWS_ACCOMMODATION_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    all_homes = {}
    
    for file in kws_accommodation_files:
        page = parse_listing(file)
        
        #retrieve the last modified timestamp of each dowmloaded file and used as last verified date
        mtime = datetime.fromtimestamp(file.stat().st_mtime, tz=timezone.utc).date().isoformat()
        
        for home in page["homes"]:
            home.update(
                {
                    "document_id": home_id(home["url"]),
                    "source_name": "KWS",
                    "doc_type": "park_accommodation_pricing",
                    "source_url": home["url"],
                    "listing_url": KWS_ACCOMMODATIONS_LISTING_URL,
                    "last_verified": mtime,
                }
            )
            all_homes.setdefault(home["url"], home)  # de-duplicate across pages
        print(f"{file.name}: {len(page['homes'])} homes")
    
    #convert the dictionary into a list
    homes = list(all_homes.values())
    
    result = {"source_name": "KWS", "listing_url": KWS_ACCOMMODATIONS_LISTING_URL, "homes": homes}
    
    output_file =  (KWS_ACCOMMODATION_PROCESSED_DIR / "kws_accommodation.json")
    
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nHomes saved: {len(homes)}")
    problems = check_homes(homes)
    if problems:
        print("CHECK:")
        for p in problems:
            print(" -", p)
            
    #(KWS_ACCOMMODATIONS) Chunking scrapped kws_accommodations .json file
    
    if not ACCOMMODATION_JSON_PATH.is_file():
        print(f"Not found: {ACCOMMODATION_JSON_PATH}")
        return

    homes = load_homes(ACCOMMODATION_JSON_PATH)
    chunks = create_home_chunks(homes) + create_park_chunks(homes)
    save_chunks(chunks, ACCOMMODATION_CHUNKS_PATH)

    print(f"Homes processed: {len(homes)}")
    print(f"Chunks created: {len(chunks)}")
    print(f"Saved to: {ACCOMMODATION_CHUNKS_PATH}")
    
    for doc_type, count in sorted(Counter(c["doc_type"] for c in chunks).items()):
        print(f"  {doc_type}: {count}")
    
    words = [c["word_count"] for c in chunks]
    print(f"Words per chunk: min {min(words)}, max {max(words)}, average {sum(words) // len(words)}")

    problems = check_accommodation_chunks(chunks, homes)
    if problems:
        print("CHECK:")
        for p in problems:
            print(" -", p)
    else:
        print("All checks passed.")


    
    #STORING CREATED CHUNKS (from Magical kenya,  KWS Destinations and KWS Acccommodations) INTO A VECTORDB AND DEFINING HOW TO SEARCH THE DATABASE
    '''
    chunks = load_chunks(CHUNKS_PATH)
    if not chunks:
        print(f"No chunks found in {CHUNKS_PATH}: Nothing to store")
        return
    '''
    #add the Magical Kenya chunks
    chunks = load_chunks(CHUNKS_PATH) if CHUNKS_PATH.is_file() else []
    
    if KWS_CHUNKS_PATH.is_file():
        chunks += load_chunks(KWS_CHUNKS_PATH)
    
    #add the KWS Accommodations chunks
    if ACCOMMODATION_CHUNKS_PATH.is_file():
        chunks += load_chunks(ACCOMMODATION_CHUNKS_PATH)
        
    if not chunks:
        print(f"No chunks found in {CHUNKS_PATH} or {KWS_CHUNKS_PATH} or {ACCOMMODATION_CHUNKS_PATH}: Nothing to store")
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

        result = answer_question(question=question, collection=collection, embedding_model=embedding_model, nvidia_client=nvidia_client, n_results=8)

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