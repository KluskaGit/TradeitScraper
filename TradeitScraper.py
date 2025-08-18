import requests
import time
import random
import os
from dotenv import load_dotenv

class TradeitScraper:
    def __init__(self, skin_min_price, skin_max_price, stickers_to_lookup):
        self.start = 0
        self.limit = 120
        self.skin_min_price = skin_min_price
        self.skin_max_price = skin_max_price
        self.stickers_to_lookup = stickers_to_lookup
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://google.com/',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Upgrade-Insecure-Requests': '1'
        }
    
    
    def get_item_details(self, item):

        # Extracting item details
        id = item.get('id', 'Unknown')
        name = item.get('name', 'Unknown')
        price = item.get('price', 0)
        store_price = item.get('storePrice', 0)
        group_id = item.get('groupId', -1)
        stickers = item.get('stickers', [])

        if self.lookup_for_stickers(stickers, self.stickers_to_lookup):
            msg = f'<b>Name:</b> {name},\n<b>Price:</b> {price/100}$, <b>Store Price:</b> {store_price/100}$\n<b>Stickers:</b>'


            # Extracting sticker details
            for sticker in stickers:

                sticker_name = sticker.get('name', 'Unknown')
                #sticker_link = sticker.get('link', 'No link')
                sticker_price = sticker.get('price', 0)
                msg+=(f'\n      {sticker_name}, <b>Price:</b> {sticker_price/100}$')

            image_path = self.get_image(id)
            self.send_img_with_caption(image_path, msg)


    def lookup_for_stickers(self, stickers, stickers_names):
        """
        This function checks if any of the stickers in the provided list match the names in stickers_names.
        If a match is found, it returns True; otherwise, it returns False.
        """
        
        for sticker_name in stickers_names:
            for sticker in stickers:
                if sticker_name.lower() in sticker.get('name', 'Unknown').lower():
                    return True
        return False
    

    
    def send_img_with_caption(self, img_path, message):
        load_dotenv()
        token = os.getenv('TOKEN')
        chat_id = os.getenv('CHAT_ID')
        url = f'https://api.telegram.org/bot{token}/sendPhoto'
        payload = {
            'chat_id': chat_id,
            'photo': img_path, 
            'caption': message, 
            'parse_mode': 'HTML'}
        requests.post(url, data=payload, headers=self.headers)

    def get_image(self, item_id):
        url = f'https://tradeit.gg/api/v2/inventory/csgo-full-img?assetId={item_id}'
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            image_data = response.json().get('data', {})
            
            if image_data:
                image_path = image_data.get('front', 'No image found')
                return image_path
            else:
                print(f"No image data found for item ID {item_id}")
                return None
        else:
            print(f"Failed to retrieve image for item ID {item_id}: code {response.status_code}: {response.text}")
            return None

    

    def scrape(self):

        while True:
            url = f'https://tradeit.gg/api/v2/inventory/data?gameId=730&offset={self.start}&limit={self.limit}&sortType=Price+-+high&searchValue=&minPrice={self.skin_min_price}&maxPrice={self.skin_max_price}&minFloat=0&maxFloat=1&sticker=true&showTradeLock=true&onlyTradeLock=true&colors=&showUserListing=true&stickerName=&tradeLockDays[]=7&tradeLockDays[]=8&context=trade&fresh=true&isForStore=0'
            
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                    
                site_data = response.json()
                grouped_items = site_data.get('items', [])

                if grouped_items:
                    group_ids = (str(item_data.get('groupId', -1)) for item_data in grouped_items)
                        
                    for id in group_ids:
                        items_url = f'https://tradeit.gg/api/v2/inventory/data?gameId=730&offset=0&limit=500&sortType=Price+-+high&searchValue=&minPrice={self.skin_min_price}&maxPrice={self.skin_max_price}&minFloat=0&maxFloat=1&sticker=true&showTradeLock=true&onlyTradeLock=true&colors=&showUserListing=true&stickerName=&tradeLockDays[]=7&tradeLockDays[]=8&context=trade&fresh=true&groupId={id}&isForStore=0'
                        items_response = requests.get(items_url, headers=self.headers)
                        #print(items_url)
                        time.sleep(random.uniform(0.7, 1.7))  # Random sleep to avoid rate limiting
                        if items_response.status_code == 200:

                            items = items_response.json().get('items', [])
                            for item in items:
                                self.get_item_details(item)
                        else:
                            print(f"Failed to retrieve items for group ID {id}: code {items_response.status_code}: {items_response.text}")
                else:
                    print("No items found in the response.")
                    break
            else:
                print(f"Failed to retrieve data: code: {response.status_code}: {response.text}")
            
            self.start += self.limit
            self.limit = 160
            