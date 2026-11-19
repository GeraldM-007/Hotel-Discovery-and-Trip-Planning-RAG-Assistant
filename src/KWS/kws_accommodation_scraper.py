"""
Scrape the KWS Mbugani Homes listing pages (reservations.kws.go.ke/mbugani-homes).

For every home we keep: name, detail URL, park, amenities, resident and
non-resident price per night (KES). Reviews and star ratings are NOT scraped.

"""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from bs4 import BeautifulSoup, Comment
from app.config import BASE_DIR


KWS_ACCOMMODATION_PROCESSED_DIR = BASE_DIR / "Data" / "kws_accommodation"

PRICE_RE = re.compile(r"(KSh|KES|USD|\$)\s*([\d,]+(?:\.\d+)?)", re.I)
TOTAL_RE = re.compile(r"of\s+(\d+)\s+Homes", re.I)
FOUND_RE = re.compile(r"(\d+)\s+homes?\s+found", re.I)

#remove white spaces before and after words
def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()

#remove the query string from the URL and URL fragments
def clean_url(url):
    return (url or "").split("?")[0].split("#")[0]

#standardise park names into lower case. 'MT.  ELGON NATIONAL PARK' -> 'Mt. Elgon National Park'
def title_case_park(text):
    text = clean_text(text).title()
    return re.sub(r"\bMt\b\.?", "Mt.", text)

#Extract numerical price and currency from a text string
#standardize the prices format. KSh10,000 /night' -> (10000.0, 'KES')
def parse_price(text):
    #PRICE.RE regular expression identifies the numerical price figure in the text
    match = PRICE_RE.search(clean_text(text))
    if not match:
        return None, None
    
    #Extract the currency. group(1) retrieves the first captured group, the currency symbol
    symbol = match.group(1).upper()
    
    #standardize the currency into standard currency codes
    currency = "KES" if symbol in ("KSH", "KES") else "USD"
    
    #extract the amount from the numerical portion as float
    amount =  float(match.group(2).replace(",", ""))
    
    return amount, currency

#Extract resident and non-resident accommodation prices
#pair each 'Resident/Non Resident" label with the value after it
def extract_prices(card):
    prices = {}
    
    #find the price container in the raw html document
    box = card.select_one("div.g-price")
    if not box:
        return prices
    
    #find comments inside the price container and remove them all
    for comment in box.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()

    label = None
    
    #find labels and prices
    for node in box.select("div.prefix, div.price"):
        
        #identify the price category (resident/non resident)
        if "prefix" in node.get("class", []):
            label = clean_text(node.get_text(" ")).lower()
        
        elif label:
            #when a price element is encountered, extract the amount and currency
            amount, currency = parse_price(node.get_text(" "))
            
            #searches for an element containing the price unit
            unit = node.select_one("span.unit")
            
            if amount is not None:
                #determine whether the price is resdient on non-resident
                key = "non_resident" if label.startswith("non") else "resident"
                
                #store the price in a structured dictionary
                prices[key] = {
                    "amount": amount,
                    "currency": currency,
                    "unit": clean_text(unit.get_text()).lstrip("/") if unit else "night",
                }
            
            #reset the label to prevent the next price element from using the previous label
            label = None
            
    return prices

#Extract all the required information about one accommodation from its HTML card
def extract_home(card):
    link = card.select_one("div.item-title a")
    if not link:
        return None
    
    #Extract and clean the accommodation name
    name = clean_text(link.get_text())
    
    #Extract the url (href attribute) and clean it
    url = clean_url(link.get("href"))
    
    #get the accommodation location. Should be a park name
    location = card.select_one("div.location")

    #Extract amenities
    amenities = [
        clean_text(a.get_text())
        for a in card.select("div.g-attributes span.item")
        if "attr-title" not in a.get("class", []) and clean_text(a.get_text())
    ]
    
    #calls the function to extract prices
    prices = extract_prices(card)
    
    #return all the relevant accommodation information
    return {
        "name": name,
        "url": url,
        "park": title_case_park(location.get_text()) if location else None,
        "amenities": amenities,
        "resident_price": prices.get("resident"),
        "non_resident_price": prices.get("non_resident"),
    }

#Reads one saved HTML file and extracts all accommodation cards on that page
def parse_listing(file_path):
    
    #convert the HTML file into a navigatable html tree
    soup = BeautifulSoup(Path(file_path).read_text(encoding="utf-8", errors="ignore"), "lxml")
    
    #create a list of valid accommodation dictionaries
    homes = [h for h in (extract_home(c) for c in soup.select("div.item-loop-list")) if h]

    return {"source_file": Path(file_path).name, "homes": homes}

#generate a unique hash for each accommodation based in its URL. 16 characters long
def home_id(url):
    return hashlib.sha256(url.encode()).hexdigest()[:16]

#validate extracted accommodation data, identify missing info or incomplete scrapping
def check_homes(homes):
    problems = []
    
    #checks if any information is missing, the accommodation is flagged
    for h in homes:
        if not h["park"]:
            problems.append(f"{h['name']}: no park")
        if not h["resident_price"] or not h["non_resident_price"]:
            problems.append(f"{h['name']}: missing price")
        if not h["amenities"]:
            problems.append(f"{h['name']}: no amenities")
    return problems

'''
def main():
    
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


if __name__ == "__main__":
    main()

'''