from turtle import st
import requests

def get_item_details(item):

    # Extracting item details
    id = item.get('id', 'Unknown')
    name = item.get('name', 'Unknown')
    price = item.get('price', 0)
    store_price = item.get('storePrice', 0)
    group_id = item.get('groupId', -1)
    stickers = item.get('stickers', [])
    print(f"ID: {id}, Name: {name}, Price: {price}, Store Price: {store_price}, Group ID: {group_id}")

    # Extracting sticker details
    for sticker in stickers:

        sticker_name = sticker.get('name', 'Unknown')
        sticker_link = sticker.get('link', 'No link')
        sticker_price = sticker.get('price', 0)
        print(f'\nStickers: {sticker_name}')



if __name__ == "__main__":

    start = 0
    limit = 5
    minPrice = 5
    maxPrice = 10
    url = f'https://tradeit.gg/api/v2/inventory/data?gameId=730&offset={start}&limit={limit}&sortType=Price+-+high&searchValue=&minPrice={minPrice}&maxPrice={maxPrice}&minFloat=0&maxFloat=1&sticker=true&showTradeLock=true&onlyTradeLock=true&colors=&showUserListing=true&stickerName=&tradeLockDays[]=7&tradeLockDays[]=8&context=trade&fresh=true&isForStore=0'
    #print(url)

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
                    get_item_details(item)

           
    