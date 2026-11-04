#Splitting the scrapped data from raw html files into text chunks using both semantic and word based chunking
from pathlib import Path
from collections import Counter #counts how frequent items appear
import json
import math #calculates thresholds using ceil()
import re #cleans text using regular expresions

BASE_DIR = Path(__file__).resolve().parents[3]
KWS_JSON_DIR = BASE_DIR / "TravelAfricaRAGProject" / "Data" / "kws_processed" / "json"
KWS_CHUNKS_PATH = BASE_DIR / "TravelAfricaRAGProject" / "Data" / "processed" / "chunks" / "kws_chunks.jsonl"

# A rule/contact line that appears on this many park pages is general information, not park information.
# It is stored once under "All KWS parks" instead of once per park
COMMON_MIN_PARKS = 3 #shared information must appear in atleast 3 parks
COMMON_MIN_SHARE = 0.6 #shared information must appear in atleast 60% of the documents
COMMON_SECTIONS = {"Safety Guidelines", "Park Contacts"} #what is considered for the common sections

COMMON_DESTINATION = "All KWS parks"
COMMON_SOURCE_URL = "https://kws.go.ke/parks/"

# Semantic chunking: the page's tabs are grouped by topic, so a chunk is about one thing and is not a 10 word fragment.
# Each group becomes one chunk (or several overlapping word chunks if it is long).
# doc_type lets us filter the search later (e.g. only fee chunks).
#defines which page tabs should be combined into topic-based chunks
SECTION_GROUPS = [
    ("Overview", "park_guide", ["About", "Attractions"]),
    ("Park History", "park_guide", ["Park History"]),
    ("Getting there and visitor information", "park_guide", ["How to get there", "Visitor Tips", "Park Contacts"]),
    ("Park-specific safety guidelines", "park_rules", ["Safety Guidelines"]),
]

#Sections whose content should be combined as lists
LIST_TABS = {"Attractions", "Visitor Tips"}

#Defines labels added when multiple tabs are combined
PART_PREFIX = {
    "About": "",
    "Attractions": "Attractions: ",
    "Park History": "",
    "How to get there": "How to get there: ",
    "Visitor Tips": "Visitor tips: ",
    "Park Contacts": "Park contacts: ",
    "Safety Guidelines": "",
}

# The park pages show the rates but do not say what they are charged for.
FEE_UNIT_NOTE = "The KWS park page does not say whether these rates are per day or per entry."

#Normalized visitor category tables
CATEGORY_NAMES = {
    "East African Citizen": "East African citizens",
    "Kenya Resident": "Kenyan residents",
    "Non-Resident": "Non-residents",
    "African Citizen": "African citizens (outside East Africa)",
}

# Words in a group's label that already say what kind of place it is (so the kind is not repeated)
ACCOMMODATION_KINDS = {
    "kws_guesthouse": ("KWS guest house or cottage", ("mbugani",)),
    "public_campsite": ("public campsite", ("public",)),
    "special_campsite": ("special campsite", ("special",)),
    "private_lodge": ("privately owned hotel or lodge", ("private",)),
}

# Split text into overlapping word-based chunks
def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50):

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if not 0 <= overlap < chunk_size:
        raise ValueError("overlap must be between 0 and chunk_size")

    words = text.split() #divides text into words using whitespace
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

# Write all chunks as JSONL
def save_chunks(chunks, output_path: Path):

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk, ensure_ascii=False) + "\n")

# Reading the scraped documents
def load_kws_documents(json_dir: Path):
    documents = []

    for file_path in sorted(json_dir.glob("*.json")):
        with file_path.open("r", encoding="utf-8") as file:
            document = json.load(file)
            documents.append(document)

    return documents


# create a normalized version of a text line so the script can identify repeated information
def item_key(text: str):
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


# Join items into one readable passage.
#Joins multiple scrapped elements while preserving the difference between lists of names and ordinary text
def join_items(items, as_list=None):
    #removes empty items and trims sorounding white space
    items = [item.strip() for item in items if item.strip()]

    if not items:
        return ""

    if as_list is None:
        #a sentence is made of text that ends with a punctuation
        sentences = sum(1 for item in items if item.endswith((".", "!", "?")))
        #if the length of items is fewer than half the items in a sentence, then it this becomes a list
        as_list = sentences < len(items) / 2

    #If as_list=False(it is a sentence). Join sentences with spaces and add full stop if item does not end with punctuation
    #If as_list=True, remove trailing full stops, commas and semicolons from individual items then join the sentences with semi colons
    if not as_list:
        items = [item.rstrip(",; ") for item in items]
        return " ".join(item if item.endswith((".", "!", "?", ":")) else item + "." for item in items)

    text = ""

    for index, item in enumerate(items):
        item = item.rstrip(".;,")
        text = item if index == 0 else text + (" " if text.endswith(":") else "; ") + item

    return text


#Define a format for all currencies (adds a comma seperator and formats to 2 decimal places)
def format_money(currency: str, amount):
    if isinstance(amount, float):
        return f"{currency} {amount:,.2f}"

    return f"{currency} {amount:,}"


# Make sure a passage ends with a full stop
def end_sentence(text: str):
    text = text.rstrip(",; ")
    return text if text.endswith((".", "!", "?")) else text + "."


# Identify introductory texts that do not provide useful information on their own
def is_lead_in(text: str):
    words = text.rstrip().split()

    return len(words) <= 5 and (text.rstrip().endswith(":") or words[-1].lower().strip(".,;:") in ("are", "include", "following"))


# General information shared by (almost) every park
# Find the lines that appear on enough park pages to count as general information
def find_common_keys(documents):
    #handle an empty document list
    if not documents:
        return {}

    #eg needed = max(3,[0.6 x 10]) = 6 meaning that a line must appear on atleast six park pages to qualify as common information
    needed = max(COMMON_MIN_PARKS, math.ceil(COMMON_MIN_SHARE * len(documents)))
    counts = Counter()

    #count normalized lines
    for document in documents:
        # using a set ensures that a line repeated multiple times in one park page counts only once for that document
        keys = {(e["section"], item_key(e["text"])) for e in document["elements"] if e["section"] in COMMON_SECTIONS}
        keys |= {("categories", item_key(c["category"] + " " + c["definition"])) for c in document.get("visitor_categories", [])}
        counts.update(keys)

    #Only keys appearing in enough documents are retained. Returns a set of tuples identifying common lines
    return {key for key, count in counts.items() if count >= needed}


# Building the text of each chunk
#Package a text chunk and it's metadata into a consistent dictionary
def make_chunk(document, document_id, destination, section, doc_type, text, chunk_number):
    chunk = {
        "chunk_id": f"{document_id}_{chunk_number:03d}",
        "document_id": document_id,
        "destination": destination,
        "section": section,
        "source_url": document["source_url"],
        "title": document["title"],
        "source_name": "KWS",
        "doc_type": doc_type,
        "last_verified": document["last_verified"],
        "park_slug": document["park_slug"],
        "text": text,
        "word_count": len(text.split()),
    }
    chunk.update()

    return chunk


# Semantic + word based chunking of one section.
# The section is already one topic (semantic split). If it is longer than CHUNK_SIZE words it is cut into
# overlapping word chunks, and every piece repeats the destination/section lines so it can be found on its own.
def split_section(document, document_id, destination, section, doc_type, text, start_number, chunk_size:int=300, overlap:int=50):
    #add context into each chunk to improve semantic retrieval
    context = f"Destination: {destination}\nSection: {section}\n\n"

    #split the text using word based chunking
    pieces = chunk_text(context + text, chunk_size, overlap)

    chunks = []

    for index, piece in enumerate(pieces):
        # If the passage is small the result will contain one piece. Longer passages will contain multiple overlapping pieces
        full_text = piece if index == 0 else " ".join(context.split()) + " " + piece
        chunks.append(make_chunk(document, document_id, destination, section, doc_type, full_text, start_number + index))

    return chunks


# Build one entry fee passage per park
# Converts structured fee data into readable results containing all available visitor categories and their prices
def build_fee_text(document):
    rates = document.get("rates", [])

    if not rates:
        return None

    # keep the order of the page: category = {age group: price}
    by_category = {}

    for rate in rates:
        name = CATEGORY_NAMES.get(rate["category"], rate["category"] or rate["label"])
        by_category.setdefault(name, {})[rate["age_group"] or "entry"] = format_money(rate["currency"], rate["amount"])

    sentences = []

    #convert each category into a sentence
    for name, prices in by_category.items():
        parts = []

        if "Adult" in prices:
            parts.append(f"{prices['Adult']} for adults")

        if "Child" in prices:
            parts.append(f"{prices['Child']} for children")

        if "entry" in prices:
            parts.append(f"{prices['entry']}")

        sentences.append(f"{name} pay " + " and ".join(parts) + ".")

    text = (
        f"Park entry fees at {document['park_name']} (Kenya Wildlife Service rates shown on the KWS park page, "
        f"checked {document['last_verified']}). "
        + " ".join(sentences)
        + f" {FEE_UNIT_NOTE}"
    )
    
    #If an online payment URL for park fees exists
    if document.get("payment_url"):
        
        #The URL is appended to the text passage
        text += f" Park entry can be paid online at {document['payment_url']}."

    return text


# Convert scrapped accommodation listings into useful text passages while retaining accommodation type metadata
def build_accommodation_texts(document, park, chunk_size:int=300):
    groups = {}
    
    #only elements in accommodation section are considered
    for element in document["elements"]:
        if element["section"] != "Accommodation":
            continue
        
        #Each element is grouped by it's display group and accommodation type, keeping related listings together
        key = (element.get("group") or "Accommodation", element.get("accommodation_type"))
        groups.setdefault(key, []).append(element)

    passages = []

    for (group, accommodation_type), elements in groups.items():
        names = []
        
        #If an accommodation listing has a URL in it, it is included in the passage
        for element in elements:
            names.append(f"{element['text']} (website: {element['url']})" if element.get("url") else element["text"])

        # say what kind of place it is, unless the group's name already does
        kind, label_words = ACCOMMODATION_KINDS.get(accommodation_type, (None, ())) #obtains a descriptive label from ACCOMMODATION_KINDS
        kind_text = f" [{kind}]" if kind and not any(word in group.lower() for word in label_words) else ""
        
        #construct a passage for each group
        passages.append((f"{group}{kind_text}: " + "; ".join(names) + ".", accommodation_type))

    if not passages:
        return []
    
    #create an introduction for the passage
    intro = f"Accommodation in and around {park}. "
    whole = intro + " ".join(text for text, _ in passages)
    
    #If the created passage is less than the chunk_size a list containing a tuple with full test and a comma-separated list of accommodation types
    if len(whole.split()) <= chunk_size:
        types = sorted({t for _, t in passages if t})
        return [(whole, ",".join(types))]

    return [(intro + text, accommodation_type or "") for text, accommodation_type in passages]


# One park document -> chunks
#Build all the park specific chunks from one scrapped document 
def create_park_chunks(document, common_keys):
    document_id = document["document_id"]
    destination = document["park_name"]

    chunks = []

    def add(section, doc_type, text):
        chunks.extend(split_section(document, document_id, destination, section, doc_type, text, len(chunks) + 1))

    # the page's elements grouped by tab, in page order
    sections = {}

    for element in document["elements"]:
        sections.setdefault(element["section"], []).append(element)

    # Retrieve elements in a tab, exclude lines already identified as common information, remove introductory fragments,
    # format the content as list or passage then join the remaining text
    def tab_text(name):
        items = [
            e["text"] for e in sections.get(name, [])
            if (name, item_key(e["text"])) not in common_keys and not is_lead_in(e["text"])
        ]
        as_list = name in LIST_TABS or all(e["tag"] == "li" for e in sections.get(name, []))
        return join_items(items, as_list) if items else ""

    used = set()
    
    #Build a semantic topic groups
    #For each group, collect non-empty tab content, add appropriate prefixes and join the passages into one
    for group_name, doc_type, tabs in SECTION_GROUPS:
        parts = []

        for tab in tabs:
            used.add(tab)
            text = tab_text(tab)

            if text:
                parts.append(PART_PREFIX.get(tab, f"{tab}: ") + end_sentence(text))

        if parts:
            add(group_name, doc_type, " ".join(parts))

    # any tab KWS adds in future that is not in SECTION_GROUPS still gets indexed (handle new unexpected tabs)
    for tab in sections:
        if tab not in used and tab != "Accommodation" and tab_text(tab):
            add(tab, "park_guide", f"{tab}: {tab_text(tab)}")

    for text, types in build_accommodation_texts(document, destination):
        extra = {"accommodation_types": types} if types else {}
        add("Accommodation", "park_accommodation", text)

    #add the fee chunk
    fee_text = build_fee_text(document)

    if fee_text:
        add("Park entry fees", "park_fee", fee_text)

    return chunks


# Create chunks for shared KWS information(such as safety guidelines)
def create_common_chunks(documents, common_keys):
    if not common_keys:
        return []

    # a stand-in "document" so make_chunk function can fill in the usual fields
    common_document = {
        "source_url": COMMON_SOURCE_URL,
        "title": "Kenya Wildlife Service parks: information that applies to all parks",
        "last_verified": max(d["last_verified"] for d in documents),
        "park_slug": "all-parks",
    }
    document_id = "kws_common"

    chunks = []
    number = 1

    # one section at a time, in the order the lines first appear
    for section_name, label, doc_type, intro in (
        ("Safety Guidelines", "Park rules and safety (all parks)", "park_rules", "Rules that apply in all Kenya Wildlife Service parks: "),
        ("Park Contacts", "Contacts (all parks)", "park_contacts", "Kenya Wildlife Service contacts that apply to all parks: "),
    ):
        items = []
        seen = set()

        for document in documents:
            for element in document["elements"]:
                key = (section_name, item_key(element["text"]))

                if element["section"] == section_name and key in common_keys and key not in seen:
                    seen.add(key)
                    items.append(element["text"])

        if items:
            text = intro + join_items(items, as_list=False)
            new_chunks = split_section(common_document, document_id, COMMON_DESTINATION, label, doc_type, text, number)
            chunks.extend(new_chunks)
            number += len(new_chunks)

    # create vistor categories. Who counts as an East African citizen, Kenya resident, etc.
    definitions = []
    seen = set()

    for document in documents:
        for category in document.get("visitor_categories", []):
            key = ("categories", item_key(category["category"] + " " + category["definition"]))

            if key in common_keys and key not in seen:
                seen.add(key)
                definitions.append(f"{category['category']}: {category['definition'].rstrip('.')}.")

    if definitions:
        text = "Visitor categories used for KWS park entry fees (as defined by KWS): " + " ".join(definitions)
        chunks.extend(split_section(common_document, document_id, COMMON_DESTINATION, "Visitor categories for park fees", "park_fee", text, number))

    return chunks

#Serve as the main orchestration function for chunk creation (co-ordinate the entire chunk-building process)
def create_kws_chunks(documents):
    #identify information shared across enough park documents
    common_keys = find_common_keys(documents)

    all_chunks = []
    
    #create park specific chunks
    for document in documents:
        all_chunks.extend(create_park_chunks(document, common_keys))
    
    #create shared chunks for shared information among all park documents
    all_chunks.extend(create_common_chunks(documents, common_keys))

    return all_chunks, common_keys



# Run consistency checks after chunk generation
def check_chunks(chunks, documents, chunk_size:int=300, overlap:int=50):
    problems = []
    
    #check for duplicate ids
    ids = [chunk["chunk_id"] for chunk in chunks]

    if len(ids) != len(set(ids)):
        problems.append("duplicate chunk_ids")

    for document in documents:
        
        mine = [c for c in chunks if c["document_id"] == document["document_id"]]
        
        #check missing fee chunks. Checks whether atleast one chunk type per park fee exists
        if not any(c["doc_type"] == "park_fee" for c in mine):
            problems.append(f"{document['park_name']}: no fee chunk")
        
        #check for overview chunks per park 
        if not any(c["section"] == "Overview" for c in mine):
            problems.append(f"{document['park_name']}: no overview chunk")
            
    #check for chunks that exceed the configured size by more than 25 words
    for chunk in chunks:
        if chunk["word_count"] > chunk_size + 25:
            problems.append(f"{chunk['chunk_id']}: {chunk['word_count']} words")

    return problems


def main():

    documents = load_kws_documents(KWS_JSON_DIR)

    if not documents:
        print(f"No KWS documents found in {KWS_JSON_DIR}")
        print("Run scrapper.py first.")
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


if __name__ == "__main__":
    main()