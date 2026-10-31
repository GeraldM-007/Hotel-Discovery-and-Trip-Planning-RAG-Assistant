import json
import re
from pathlib import Path
from app.config import BASE_DIR

JSON_DIR = BASE_DIR / "Data" / "processed" / "json"
OUTPUT_PATH = BASE_DIR / "Data" / "processed" / "chunks" / "magical_kenya_chunks.jsonl"


# Read all parsed JSON documents
def load_documents(json_dir: Path):
    documents = []

    for file_path in sorted(json_dir.glob("*.json")):
        with file_path.open("r", encoding="utf-8") as file:
            document = json.load(file)

        documents.append(document)

    return documents


# Split text into overlapping word-based chunks
def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50):

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if not 0 <= overlap < chunk_size:
        raise ValueError("overlap must be between 0 and chunk_size")

    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))

        chunk = " ".join(words[start:end])

        if chunk:
            chunks.append(chunk)

        if end == len(words):
            break

        start += chunk_size - overlap

    return chunks


# Identify the beginning of a trip planner
def is_trip_planner(text: str):
    return "trip planner" in text.lower()


# Identify itinerary days
def is_itinerary_day(text: str):
    return bool(re.match(r"^day\s+\d+\b", text, re.IGNORECASE))


# Identify activity categories
# Extend this list as new categories are encountered.
ACTIVITY_CATEGORIES = {
    "nature & wildlife",
    "adventure",
    "culture & heritage",
    "food & drink",
    "arts & culture",
    "wellness",
    "sports",
    "family",
    "beaches",
    "history",
}


# Headings without associated destination content
IGNORED_HEADINGS = {
    "weather today",
    "places to stay",
    "things to do",
}


def create_semantic_chunks(document):
    elements = document.get("elements", [])

    destination = next(
        (
            element["text"]
            for element in elements
            if element.get("tag") == "h1"
        ),
        document.get("title", "Unknown destination").split(" - ")[0]
    )

    sections = []

    current_section = "Overview"
    current_text = []

    in_trip_planner = False

    def save_section():
        if current_text:
            sections.append({
                "section": current_section,
                "text": "\n".join(current_text)
            })

    for element in elements:
        tag = element.get("tag", "")
        text = element.get("text", "").strip()

        if not text:
            continue

        if tag == "h1":
            continue

        normalized = text.lower()

        if normalized in IGNORED_HEADINGS:
            continue

        # Trip planner begins
        if is_trip_planner(text):
            save_section()

            current_section = "Trip Planner"
            current_text = [text]
            in_trip_planner = True
            continue

        # Preserve itinerary days together
        if in_trip_planner:
            current_text.append(text)
            continue

        # Skip section labels without independent content
        if normalized.startswith("top things to do in"):
            save_section()

            current_section = "Activities"
            current_text = []
            continue

        # New activity category
        if tag.startswith("h") and normalized in ACTIVITY_CATEGORIES:
            save_section()

            current_section = text
            current_text = []
            continue

        # Activity heading or paragraph
        current_text.append(text)

    save_section()

    return destination, sections


# Apply word-based chunking to semantic sections
def create_document_chunks(document, chunk_size=300, overlap=50):

    destination, sections = create_semantic_chunks(document)

    chunks = []
    chunk_number = 1

    for section in sections:
        section_name = section["section"]

        # Add context to improve embedding retrieval
        text = (
            f"Destination: {destination}\n"
            f"Section: {section_name}\n\n"
            f"{section['text']}"
        )

        text_chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

        for chunk in text_chunks:
            chunks.append({
                "chunk_id": f"{document['document_id']}_{chunk_number:03d}",
                "document_id": document["document_id"],
                "destination": destination,
                "section": section_name,
                "source_url": document.get("source_url"),
                "title": document.get("title"),
                "text": chunk,
                "word_count": len(chunk.split())
            })

            chunk_number += 1

    return chunks


# Save all chunks as JSONL
def save_chunks(chunks, output_path: Path):

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk, ensure_ascii=False) + "\n")
