import requests

class TradeitScraper:
    def __init__(self, skin_min_price, skin_max_price, stickers_to_lookup):
        self.start = 0
        self.limit = 5
        self.skin_min_price = skin_min_price
        self.skin_max_price = skin_max_price
        self.stickers_to_lookup = stickers_to_lookup
    
    
    def get_item_details(self, item):

        # Extracting item details
        id = item.get('id', 'Unknown')
        name = item.get('name', 'Unknown')
        price = item.get('price', 0)
        store_price = item.get('storePrice', 0)
        group_id = item.get('groupId', -1)
        stickers = item.get('stickers', [])
        if self.lookup_for_stickers(stickers, self.stickers_to_lookup):
            print(f"\nID: {id}, Name: {name}, Price: {price}, Store Price: {store_price}, Group ID: {group_id}")

            # Extracting sticker details
            for sticker in stickers:

                sticker_name = sticker.get('name', 'Unknown')
                sticker_link = sticker.get('link', 'No link')
                sticker_price = sticker.get('price', 0)
                print(f'\tStickers: {sticker_name}')


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
    

    def scrape(self):
        
        url = f'https://tradeit.gg/api/v2/inventory/data?gameId=730&offset={self.start}&limit={self.limit}&sortType=Price+-+high&searchValue=&minPrice={self.skin_min_price}&maxPrice={self.skin_max_price}&minFloat=0&maxFloat=1&sticker=true&showTradeLock=true&onlyTradeLock=true&colors=&showUserListing=true&stickerName=&tradeLockDays[]=7&tradeLockDays[]=8&context=trade&fresh=true&isForStore=0'
        
        response = requests.get(url)

        if response.status_code == 200:
            
            site_data = response.json()
            
            group_ids = (str(item_data.get('groupId', -1)) for item_data in site_data['items'])
            
            for id in group_ids:
                items_url = f'https://tradeit.gg/api/v2/inventory/data?gameId=730&offset=0&limit=500&sortType=Price+-+high&searchValue=&minPrice=5&maxPrice=10&minFloat=0&maxFloat=1&sticker=true&showTradeLock=true&onlyTradeLock=true&colors=&showUserListing=true&stickerName=&tradeLockDays[]=7&tradeLockDays[]=8&context=trade&fresh=true&groupId={id}&isForStore=0'
                items_response = requests.get(items_url)
                #print(items_url)
                if items_response.status_code == 200:

                    items = items_response.json().get('items', [])
                    for item in items:
                        self.get_item_details(item)