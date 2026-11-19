import requests
import time
from app.config import BASE_DIR, HEADERS

RAW_ACCOMMODATION_HTML_DIR = BASE_DIR / "Data" / "kws_accommodation_raw"
LISTING_URL = "https://reservations.kws.go.ke/mbugani-homes"
PAGES = 4
 
def download_pages():
    
    #make dir if does not exist
    RAW_ACCOMMODATION_HTML_DIR.mkdir(parents=True, exist_ok=True)
    
    #scrape all 4 available pages
    for page in range(1, PAGES + 1):
        #loop through the pages using the base URL and the page number 
        url = f"{LISTING_URL}?page={page}"
        
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        response.raise_for_status()
        
        (RAW_ACCOMMODATION_HTML_DIR / f"mbugani_homes_page_{page}.html").write_text(response.text, encoding="utf-8")
        
        print(f"Downloaded {url}")
        
        #pauses for one second before scrapping the next page. Be polite to the server
        time.sleep(1)
 
def main():
    download_pages()
    
if __name__ == "__main__":
    main()