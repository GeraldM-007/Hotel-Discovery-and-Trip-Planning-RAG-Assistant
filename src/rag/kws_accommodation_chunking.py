"""
Two kinds of chunks:
  1. one chunk per home - name, park, amenities, resident and non-resident price per night
  2. one chunk per park - every home in the park with its prices
"""

from collections import Counter, defaultdict
from pathlib import Path
import json
from app.config import BASE_DIR
from src.rag.chunking import chunk_text, save_chunks

ACCOMMODATION_JSON_PATH = BASE_DIR / "Data" / "kws_accommodation" / "kws_accommodation.json"
ACCOMMODATION_CHUNKS_PATH = BASE_DIR / "Data" / "processed" / "chunks" / "kws_accommodation_chunks.jsonl"

CHUNK_SIZE = 300
OVERLAP = 50

# Chunk ids start with this so they can never collide with the park chunks or Magical Kenya chunks.
ID_PREFIX = "kws_homes"

PRICE_NOTE = (
    "Prices are per night as listed on the KWS reservations site. The listing does not say how many "
    "people a home sleeps or whether the price is per house or per person. Park entry fees are charged "
    "separately."
)

#convert amount listed from eg. amount: 10000.0 -> KES 10,000
def money(price):
    if not price:
        return "not listed"
    return f"{price['currency']} {price['amount']:,.0f}"

#Extract park name
def park_name(home):
    park_name = (home.get("park") or "Unknown park").replace(" And ", " and ")
    return park_name

#Extract amenities
def amenity_text(home):
    items = home.get("amenities") or []
    return ", ".join(items) if items else "none listed"


def base_chunk(chunk_id, destination, section, doc_type, text, source_url, last_verified, **extra):
    chunk = {
        "chunk_id": chunk_id,
        "document_id": chunk_id.rsplit("_", 1)[0],
        "destination": destination,
        "section": section,
        "source_url": source_url,
        "title": f"{destination} - {section}",
        "source_name": "KWS",
        "doc_type": doc_type,
        "last_verified": last_verified,
        "text": text,
        "word_count": len(text.split()),
    }
    chunk.update(extra)
    return chunk

#converts the park name into a slug name
def slug(text):
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")


#read the json file with the scrapped json data from the websites
def load_homes(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    homes = data["homes"]
    return homes


#Create a chunk for each existing home/accommodation 
def create_home_chunks(homes):
    chunks = []
    for home in homes:
        park = park_name(home)
        text = (
            f"{park} - KWS accommodation: {home['name']}"
            f"Park: {park}"
            f"Resident price: {money(home.get('resident_price'))} per night"
            f"Non-resident price: {money(home.get('non_resident_price'))} per night"
            f"Amenities: {amenity_text(home)}."
            f"{PRICE_NOTE}"
        )
        chunks.append(
            base_chunk(
                f"{ID_PREFIX}_{home['document_id']}_000",
                park,
                f"Accommodation and prices - {home['name']}",
                "park_accommodation_pricing",
                text,
                home["source_url"],
                home["last_verified"],
                home_name=home["name"],
                resident_price_kes=home["resident_price"]["amount"] if home.get("resident_price") else None,
                non_resident_price_kes=home["non_resident_price"]["amount"] if home.get("non_resident_price") else None,
            )
        )
    return chunks

#create a chunk for all homes/accommodations in a park
def create_park_chunks(homes):
    by_park = defaultdict(list)
    for home in homes:
        by_park[park_name(home)].append(home)

    chunks = []
    for park, items in sorted(by_park.items()):
        items = sorted(items, key=lambda h: h["non_resident_price"]["amount"] if h.get("non_resident_price") else 0)
        lines = [
            f"- {h['name']}: resident {money(h.get('resident_price'))}, "
            f"non-resident {money(h.get('non_resident_price'))} per night"
            for h in items
        ]
        text = (
            f"{park} - KWS accommodation prices"
            f"{park} has {len(items)} KWS home{'s' if len(items) != 1 else ''} you can book "
            f"(cottages, houses or bandas)."
            + "".join(lines)
            + f"{PRICE_NOTE}"
        )
        pieces = chunk_text(text, CHUNK_SIZE, OVERLAP) if len(text.split()) > CHUNK_SIZE else [text]
        for n, piece in enumerate(pieces):
            if n:  # keep continuation pieces findable on their own
                piece = f"{park} - KWS accommodation prices (continued){piece}"
            chunks.append(
                base_chunk(
                    f"{ID_PREFIX}_{slug(park)}_{n:03d}", park, "Accommodation prices (all homes in this park)", "park_accommodation_summary", piece, "https://reservations.kws.go.ke/mbugani-homes",
                    max(h["last_verified"] for h in items), home_count=len(items),
                )
            )
    return chunks


def check_accommodation_chunks(chunks, homes):
    problems = []
    
    #check for duplicate chunk ids
    ids = [c["chunk_id"] for c in chunks]
    if len(ids) != len(set(ids)):
        problems.append("duplicate chunk ids")

    #verify that chunks were created for all homes
    home_chunks = [c for c in chunks if c["doc_type"] == "park_accommodation_pricing"]
    if len(home_chunks) != len(homes):
        problems.append("a home has no chunk")
    
    #verify if chunk contains prices for the homes
    for home in homes:
        text = next((c["text"] for c in home_chunks if c["source_url"] == home["source_url"]), "")
        for key in ("resident_price", "non_resident_price"):
            if home.get(key) and money(home[key]) not in text:
                problems.append(f"{home['name']}: {key} missing from its chunk")
    
    #check for chunks with chunksize greater than the required size(chunksize + overlap)
    for c in chunks:
        if c["word_count"] > CHUNK_SIZE + OVERLAP:
            problems.append(f"{c['chunk_id']}: {c['word_count']} words")
    
    return problems

'''
def main():
    
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


if __name__ == "__main__":
    main()

'''