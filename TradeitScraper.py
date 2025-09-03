import asyncio
import aiohttp
import random
import os
import logging

from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler


class TradeitScraper:
    def __init__(self, skin_min_price, skin_max_price, stickers_to_lookup):
        self.start = 0
        self.limit = 120
        self.skin_min_price = skin_min_price
        self.skin_max_price = skin_max_price
        self.stickers_to_lookup = stickers_to_lookup

        load_dotenv()
        self.telegram_token = os.environ.get('TOKEN')
        self.telegram_chat_id = os.environ.get('CHAT_ID')

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            #'Referer': 'https://google.com/',
            'Connection': 'keep-alive',
            #'Cache-Control': 'max-age=0',
            #'Upgrade-Insecure-Requests': '1'
        }

        self.q_groups = asyncio.Queue()
        self.q_items = asyncio.Queue()
        self.q_images = asyncio.Queue()

        self.sem = asyncio.Semaphore(3)

        self.handler = RotatingFileHandler(
            'logs.log',
            maxBytes=5*1024*1024,  # 5 MB per file
            backupCount=3          # Keep last 3 backups
        )

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.handler.setFormatter(formatter)

        self.logger = logging.getLogger("TradeitScraper")
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(self.handler)


    async def send_img_with_caption(self, session, img_path, message):
        await asyncio.sleep(random.uniform(0.3, 0.5))
        endpoint = 'sendMessage'
        payload = {
            'chat_id': self.telegram_chat_id, 
            'text': message, 
            'parse_mode': 'HTML'}

        if img_path:
            endpoint = 'sendPhoto'
            payload = {
                'chat_id': self.telegram_chat_id,
                'photo': img_path, 
                'caption': message, 
                'parse_mode': 'HTML'}

        url = f'https://api.telegram.org/bot{self.telegram_token}/{endpoint}'
        
        
        async with session.post(url, data=payload, headers=self.headers) as response:
            if response.status != 200:
                text = await response.text()
                self.logger.error(f"Telegram send failed, status code: {response.status}\n{text}\n{message}\n{img_path}")
            #self.logger.info(f"Sent to Telegram: {message}, with url: {url}")

    async def lookup_for_stickers(self, stickers, stickers_names):
        """
        This function checks if any of the stickers in the provided list match the names in stickers_names.
        If a match is found, it returns True; otherwise, it returns False.
        """
        
        for sticker_name in stickers_names:
            for sticker in stickers:
                if sticker_name.lower() in sticker.get('name', 'Unknown').lower():
                    return True
        return False

    async def fetch(self, session, url):
        await asyncio.sleep(random.uniform(0.3, 1))
        async with self.sem:
            try:
                async with session.get(url, headers=self.headers, timeout=30) as response:
                    if response.status!=200:
                        text = await response.text()
                        self.logger.error(f'GET {response.status}, something went wrong.\n{text}')
                        return None
                    #self.logger.info(f'GET {response.status}, Fetching {url}')
                    return await response.json()

            except Exception as e:
                self.logger.error(f'An error occured while fetching {url},\nMessage: {e}')
        return None
    
    async def worker_image(self, session):
        while True:
            alert = await self.q_images.get()

            if alert is None:
                break

            await self.send_img_with_caption(session, alert['img'], alert['msg'])
            self.q_images.task_done()



    async def worker_item(self, session):
        while True:
            # Extracting item details
            item = await self.q_items.get()

            if item is None:
                break

            id = item.get('id', 'Unknown')
            name = item.get('name', 'Unknown')
            price = item.get('price', 0)
            store_price = item.get('storePrice', 0)
            group_id = item.get('groupId', -1)
            stickers = item.get('stickers', [])

            if await self.lookup_for_stickers(stickers, self.stickers_to_lookup):
                msg = f'<b>Name:</b> {name},\n<b>Price:</b> {price/100}$, <b>Store Price:</b> {store_price/100}$\n<b>Stickers:</b>'

                # Extracting sticker details
                for sticker in stickers:

                    sticker_name = sticker.get('name', 'Unknown')
                    #sticker_link = sticker.get('link', 'No link')
                    sticker_price = sticker.get('price', 0)
                    msg+=(f'\n      {sticker_name}, <b>Price:</b> {sticker_price/100}$')

                url = f'https://tradeit.gg/api/v2/inventory/csgo-full-img?assetId={id}'
                image_json = await self.fetch(session, url=url)
                image_data = image_json.get('data', {})
                    
                if not  image_data:
                    self.logger.info(f"No image data found for item ID {id}")

                image_path = image_data.get('front', 'No image found')
                alert = {'img': image_path, 'msg': msg}  
                await self.q_images.put(alert)
            self.q_items.task_done()


    async def worker_group(self, session):
        while True:
            group_id = await self.q_groups.get()

            if group_id is None:
                break
            items_url = f'https://tradeit.gg/api/v2/inventory/data?gameId=730&offset=0&limit=500&sortType=Price+-+high&searchValue=&minPrice={self.skin_min_price}&maxPrice={self.skin_max_price}minFloat=0&maxFloat=1&sticker=true&showTradeLock=true&onlyTradeLock=true&colors=&showUserListing=true&stickerName=&tradeLockDays[]=7&tradeLockDays[]=8&context=trade&fresh=true&groupId={group_id}&isForStore=0'
            site_data = await self.fetch(session, url=items_url)
            items = site_data.get('items', [])

            for item in items:
                # log
                #self.logger.info(f"Processing item ID: {item.get('id', 'Unknown')} from group ID: {group_id}")
                await self.q_items.put(item)
            self.q_groups.task_done()


    async def run(self):

        self.logger.info('Application started')
        
        async with aiohttp.ClientSession() as session:
            while True:
                url = f'https://tradeit.gg/api/v2/inventory/data?gameId=730&offset={self.start}&limit={self.limit}&sortType=Price+-+high&searchValue=&minPrice={self.skin_min_price}&maxPrice={self.skin_max_price}&minFloat=0&maxFloat=1&sticker=true&showTradeLock=true&onlyTradeLock=true&colors=&showUserListing=true&stickerName=&tradeLockDays[]=7&tradeLockDays[]=8&context=trade&fresh=true&isForStore=0'

                site_data = await self.fetch(session, url=url)
                grouped_items = site_data.get('items', [])
                for item_data in grouped_items:
                    group_id = str(item_data.get('groupId', -1))
                    # log
                    #self.logger.info(f"Found group ID: {group_id}")
                    await self.q_groups.put(group_id)
                if not grouped_items:
                    self.logger.info("No items found in the response.")
                    break

                #await asyncio.sleep(random.uniform(5, 10))
                
                self.start += self.limit
                self.limit = 160
            
            # worker startup
            tasks = []
            ##########
            # TODO
            # optimize number of workers to the min/max price
            ##########
            for _ in range(1):
                tasks.append(asyncio.create_task(self.worker_group(session)))

            for _ in range(2):
                tasks.append(asyncio.create_task(self.worker_item(session)))
            for _ in range(4):
                tasks.append(asyncio.create_task(self.worker_image(session)))
            
            await self.q_groups.join()
            await self.q_items.join()
            await self.q_images.join()
            
            for q in [self.q_groups, self.q_items, self.q_images]:
                for _ in range(len(tasks)):
                    await q.put(None)

            await asyncio.gather(*tasks)

            