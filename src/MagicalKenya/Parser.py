from pathlib import Path
from bs4 import BeautifulSoup
import json
import hashlib
from app.config import BASE_DIR

#Directories used in parsing
RAW_DIR = BASE_DIR / "Data" / "raw"
PARSED_DIR = BASE_DIR / "Data" /"processed" / "json"
#make dir if not exist
BASE_DIR.mkdir(parents = True, exist_ok = True)
RAW_DIR.mkdir(parents = True, exist_ok = True)
PARSED_DIR.mkdir(parents = True, exist_ok = True)


#create a deterministic file ID from the filename using sha256 algorithm
def create_document_id(filename: str):
    #turn filename into bytes, calculate hash and convert into hexadecimal string
    return hashlib.sha256(filename.encode()).hexdigest()[:16]

#Read downloaded HTML files
def parse_html(file_path: Path):
    #load the entire file into a python string, decoding in utf-8 while ignoring invalid utf-8 characters
    html = file_path.read_text(encoding = "utf-8", errors = "ignore")
    
    #Beautifulsoup turns the raw html string into a navigatable html tree
    #lxml is the html parser in use
    soup = BeautifulSoup(html, "lxml")
        
    #Extract metadata from the read text
    title = None #safe default incase html doesn't contain a title
    
    if soup.title:
        title = soup.title.get_text(strip = True)
        
        #find a meta element whose 'name' attribute equals to'description'
        description_tag = soup.find("meta", attrs = {"name": "description"})
        
        #Extract the description content
        description = (description_tag.get("content") if description_tag else None)
        
        #canonical tag contains the prefered/original URL of the webpage
        #Find the link element with canonical naming
        canonical_tag = soup.find("link", attrs = {"rel": "canonical"})
        
        #Extract the url
        source_url = (canonical_tag.get("href") if canonical_tag else None)
        
    #Extract content from article/main or the body its self
    content = ( soup.find('div', attrs={"data-elementor-type": "wp-post"}) or soup.find("article") or soup.find("main") or soup.body or soup)
    
    content = clean_content(content)

    #Extract useful elements
    elements = []
    
    for element in content.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        # Extract text from the current HTML element.
        # " " puts spaces between nested elements.
        text = element.get_text(" ", strip=True)
        
        # Ignore empty elements
        if not text:
            continue
        
        widget = element.find_parent(attrs={"data-widget_type": True})
        
        widget_type = (widget.get("data-widget_type") if widget else None)
        
        elements.append({"tag": element.name, "text": text, "widget_type": widget_type})
        

    #The final document
    document = {
        "document_id": create_document_id(file_path.name),
        "source_file": file_path.name,
        "source_url": source_url,
        "title": title,
        "description": description,
        "content_type": "html",
        "elements": elements
    }
    
    return document

    
def clean_content(content):
    #Remove unwanted content
    for tag in content.find_all(["script", "style", "noscript", "svg", "iframe", "nav", "footer"]):
        tag.decompose()   #decompose completely removes a HTML element and its contents from BeautifulSoup tree
    
    for loop_item in content.find_all(attrs={"data-elementor-type": "loop-item"}):
        loop_item.decompose()
    
    for element in content.find_all(attrs={"data-widget_type": "icon-box.default"}):
        element.decompose()
        
    return content
    
