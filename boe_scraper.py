import requests
import json
import datetime
import unicodedata

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

def get_items_from_boe_json(data):
    """
    Recursively extract all 'item' objects from the BOE JSON.
    The BOE API returns single elements as objects and multiple elements as arrays.
    """
    items = []
    if isinstance(data, dict):
        for key, value in data.items():
            if key == 'item':
                if isinstance(value, list):
                    items.extend(value)
                else:
                    items.append(value)
            else:
                items.extend(get_items_from_boe_json(value))
    elif isinstance(data, list):
        for item in data:
            items.extend(get_items_from_boe_json(item))
    return items

def search_boe_for_resolutions():
    """
    Fetches the BOE for the current day and searches for specific resolutions.
    Returns a list of matching dictionaries with details.
    """
    # Current date in YYYYMMDD format
    today_str = datetime.datetime.now().strftime('%Y%m%d')
    url = f"https://www.boe.es/datosabiertos/api/boe/sumario/{today_str}"
    
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 404:
            # No BOE today (e.g. Sunday or holiday, or not published yet)
            return []
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching BOE: {e}")
        return []
        
    try:
        data = response.json()
    except json.JSONDecodeError:
        print("Error decoding BOE JSON")
        return []

    # Extract all items from the summary
    items = get_items_from_boe_json(data.get('data', {}).get('sumario', {}))
    
    matching_resolutions = []
    
    for item in items:
        if not isinstance(item, dict):
            continue
            
        title = item.get('titulo', '')
        if not title:
            continue
            
        title_normalized = remove_accents(title.lower())
        
        # We are looking for "Ayuntamiento de Sant Fruitós de Bages" and "convocatoria para proveer"
        if "sant fruitos de bages" in title_normalized and "convocatoria para proveer" in title_normalized:
            identificador = item.get('identificador', '')
            url_html = item.get('url_html', '')
            
            if url_html and not url_html.startswith('http'):
                url_html = 'https://www.boe.es' + url_html
            
            # The readable URL usually is txt.php instead of xml.php if it's available
            # But url_html usually points to the readable HTML version
            if url_html == '' and identificador:
                url_html = f"https://www.boe.es/diario_boe/txt.php?id={identificador}"
                
            matching_resolutions.append({
                'id': identificador,
                'title': title,
                'url': url_html
            })
            
    return matching_resolutions

if __name__ == "__main__":
    # Test script locally
    res = search_boe_for_resolutions()
    print("Found resolutions:", res)
