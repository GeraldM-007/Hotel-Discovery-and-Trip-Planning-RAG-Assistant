from pathlib import Path
from datetime import date
from bs4 import BeautifulSoup
import hashlib
import json
import re

BASE_DIR = Path(__file__).resolve().parents[3]
RAW_KWS_HTML_DIR = BASE_DIR / "TravelAfricaRAGProject" / "Data" / "kws_raw"
KWS_JSON_DIR = BASE_DIR / "TravelAfricaRAGProject" / "Data" / "kws_processed" / "json"

# create a deterministic file ID from the filename using sha256
def create_document_id(filename: str):
    return hashlib.sha256(filename.encode()).hexdigest()[:16]


# Cleanup text taken from HTML: non-breaking spaces, line breaks, double spaces and the stray spaces
# that appear when get_text(" ") joins bold/inline tags 
def clean_text(text: str):
    text = text.replace("\xa0", " ").replace("​", "")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;:!?%)])", r"\1", text)
    text = re.sub(r"\(\s+", "(", text)
    return text


# Only keep links that look like real web addresses. KWS has some broken ones, e.g. "http://Sentrim Hotel"
def clean_url(href: str):
    href = (href or "").strip()

    if re.match(r"^https?://[^\s/]+\.[^\s/]+\S*$", href):
        # KWS booking links carry a fixed stay date (?start=2026-02-18&end=...) that would be out of date
        if "reservations.kws.go.ke" in href:
            href = href.split("?")[0]

        return href

    return None


# Remove parts of the page that do not contain park information
def clean_content(content):
    for tag in content.find_all(["script", "style", "noscript", "svg", "iframe", "nav", "footer", "button"]):
        tag.decompose()

    # star rating anfeedback widgets
    for element in content.find_all(class_=re.compile(r"rmp-")):
        element.decompose()

    return content


# A paragraph that is nothing but bold text is a label for what follows it
# e.g. <p><b>Public campsite</b></p> followed by a list of campsites
def is_label(paragraph):
    bold_text = "".join(b.get_text() for b in paragraph.find_all(["b", "strong"]))

    return bool(bold_text.strip()) and clean_text(bold_text) == clean_text(paragraph.get_text(" ", strip=True))


# Accommodation is split into groups by a bold label. Work out what kind of place each group is.
# Labels without a keyword (e.g. "Tsavo East N. Park Southern") belong to the type before them.
def accommodation_type(label: str):
    text = label.lower()

    if "mbugani" in text:
        return "kws_guesthouse"      # KWS run guest houses and cottages

    if "public" in text:
        return "public_campsite"

    if "special" in text:
        return "special_campsite"

    if "private" in text:
        return "private_lodge"       # hotels and lodges owned by private companies

    return None


# Page level information
def extract_metadata(soup):
    title = soup.title.get_text(strip=True) if soup.title else None

    # canonical tag contains the preferred URL of the page
    canonical_tag = soup.find("link", attrs={"rel": "canonical"})
    source_url = (canonical_tag.get("href") if canonical_tag else None)

    description_tag = soup.find("meta", attrs={"name": "description"})
    description = description_tag.get("content") if description_tag else None

    # park name is the only h1 on the page
    h1 = soup.find("h1")
    park_name = clean_text(h1.get_text(" ", strip=True)) if h1 else None

    if not park_name and title:
        park_name = title.split("–")[0].strip()

    # the body has a class like "postid-4895": KWS's own ID for the page
    post_id = None

    if soup.body:
        for css_class in soup.body.get("class", []):
            match = re.fullmatch(r"postid-(\d+)", css_class)

            if match:
                post_id = int(match.group(1))

    return title, source_url, description, park_name, post_id


# "About Park" paragraphs
def extract_about(main):
    heading = next(
        (h for h in main.find_all(["h2", "h3", "h4"]) if h.get_text(strip=True).lower().startswith("about")),
        None,
    )

    if not heading:
        return []

    elements = []

    # paragraphs after the heading, until the "Important Information" heading starts the tabs
    for element in heading.find_all_next(["p", "h5"]):
        if element.name == "h5" or element.find_parent(class_="fusion-tabs"):
            break

        text = clean_text(element.get_text(" ", strip=True))

        if text:
            elements.append({"tag": "p", "text": text, "section": "About"})

    return elements


# Tabs: Attractions, Accommodation, Park History, How to get there, Visitor Tips, Safety Guidelines, Park Contacts
def extract_tabs(main):
    tabs = main.select_one("div.fusion-tabs")

    if not tabs:
        return []

    elements = []

    for index, pane in enumerate(tabs.select("div.tab-pane"), start=1):
        # each pane is preceded by a small heading holding the tab's name
        nav = pane.find_previous_sibling(class_="fusion-mobile-tab-nav")
        section = clean_text(nav.get_text(" ", strip=True)) if nav else f"Tab {index}"

        # current sub-heading inside the tab, e.g. "Public campsite" or "Privately owned Hotels/Lodges in the Park"
        group = None
        current_type = None

        for element in pane.find_all(["p", "li"]):
            # a list item that contains another list is only a wrapper
            if element.name == "li" and element.find("li"):
                continue

            # a paragraph inside a list item is already part of that item
            if element.name == "p" and element.find_parent("li"):
                continue

            text = clean_text(element.get_text(" ", strip=True))

            if not text:
                continue

            if element.name == "p" and is_label(element):
                # a long bold sentence is the tab's introduction, not a label
                if len(text) > 80:
                    continue

                group = text.rstrip(":;,. ").strip()
                current_type = accommodation_type(group) or current_type
                continue

            if section.lower() == "accommodation":
                text = text.rstrip(",;. ")   # example "Kenmare," -> "Kenmare"

            item = {"tag": element.name, "text": text, "section": section}

            if group:
                item["group"] = group

            if section.lower() == "accommodation" and current_type:
                item["accommodation_type"] = current_type

            # lodges and camps often link to their own website
            link = element.find("a", href=True)

            if link and clean_url(link["href"]):
                item["url"] = clean_url(link["href"])

            elements.append(item)

    return elements


# Rates (entry fees)
# "East Africa Citizen Adult KES. 1,000" -> label, currency, amount
RATE_PATTERN = re.compile(
    r"^(?P<label>.+?)\s+(?P<currency>KES|KSHS?|USD|US\$|\$)\.?\s*(?P<amount>\d[\d,]*(?:\.\d+)?)$",
    re.IGNORECASE,
)


# Turn the visitor group in the label into one consistent name
def normalise_category(label: str):
    text = label.lower()

    if "east africa" in text:
        return "East African Citizen"

    if re.search(r"\bnon[\s-]*resident", text):
        return "Non-Resident"

    if "kenya" in text and "resident" in text:
        return "Kenya Resident"

    if "africa" in text:
        return "African Citizen"

    return None


def parse_rate(text: str):
    match = RATE_PATTERN.match(text)

    if not match:
        return None

    label = match.group("label")
    currency = match.group("currency").upper()
    currency = "KES" if currency.startswith("KSH") else "USD" if currency in ("US$", "$") else currency

    amount = float(match.group("amount").replace(",", ""))
    amount = int(amount) if amount.is_integer() else amount

    age_match = re.search(r"\b(adult|child)\b", label, re.IGNORECASE)

    return {
        "category": normalise_category(label),
        "age_group": age_match.group(1).capitalize() if age_match else None,
        "currency": currency,
        "amount": amount,
        "label": label,
    }


def extract_rates(main):
    heading = next(
        (h for h in main.find_all("h5") if h.get_text(strip=True).lower().endswith("rates")),
        None,
    )

    if not heading:
        return [], []

    column = heading.find_parent(class_=re.compile(r"fusion-layout-column"))

    if not column:
        return [], []

    rates = []
    categories = []

    # the rates sit in the columns that follow the heading, until the next heading (the gallery)
    for block in column.find_next_siblings():
        if block.find("h5"):
            break

        # the explanation of who counts as East African citizen, resident, etc.
        legend_items = block.select("ol li")

        if legend_items:
            for item in legend_items:
                text = clean_text(item.get_text(" ", strip=True))
                name, _, definition = text.partition(":")
                categories.append({"category": name.strip(), "definition": definition.strip()})
            continue

        rate = parse_rate(clean_text(block.get_text(" ", strip=True)))

        if rate:
            rates.append(rate)

    return rates, categories


# KWS online payment page for this park
def extract_payment_url(main):
    for link in main.find_all("a", href=True):
        if "pay for" in link.get_text(" ", strip=True).lower():
            return clean_url(link["href"])

    return None


# Create a .json file for each raw html file
def kws_parse_html(file_path: Path):
    html = file_path.read_text(encoding="utf-8", errors="ignore")

    soup = BeautifulSoup(html, "lxml")

    title, source_url, description, park_name, post_id = extract_metadata(soup)

    # the park content is inside <main>. The menu, footer and "Explore other Parks" are not
    main = soup.find("main") or soup.body or soup

    main = clean_content(main)

    elements = extract_about(main) + extract_tabs(main)

    rates, visitor_categories = extract_rates(main)

    payment_url = extract_payment_url(main)

    # fall back to the first About paragraph when the page has no meta description
    if not description and elements:
        description = elements[0]["text"]

    # date the page was downloaded
    last_verified = date.fromtimestamp(file_path.stat().st_mtime).isoformat()

    # The final .json document contents
    document = {
        "document_id": create_document_id(file_path.name),
        "source_file": file_path.name,
        "source_name": "KWS",
        "doc_type": "park_guide",
        "source_url": source_url,
        "title": title,
        "description": description,
        "content_type": "html",
        "park_name": park_name,
        "park_slug": file_path.stem,
        "kws_post_id": post_id,
        "last_verified": last_verified,
        "payment_url": payment_url,
        "visitor_categories": visitor_categories,
        "rates": rates,
        "elements": elements,
    }

    return document


# Things that look wrong on a page
def check_document(document):
    problems = []

    if not document["park_name"]:
        problems.append("no park name")

    if not document["source_url"]:
        problems.append("no source URL")

    sections = {element["section"] for element in document["elements"]}

    for expected in ("About", "Attractions", "Accommodation", "How to get there"):
        if expected not in sections:
            problems.append(f"no '{expected}' section")

    if len(document["rates"]) != 8:
        problems.append(f"{len(document['rates'])} rates found (expected 8)")

    return problems

