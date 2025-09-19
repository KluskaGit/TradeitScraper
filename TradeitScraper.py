import asyncio
import random
import os

from aiohttp import ClientSession, ClientTimeout
from dotenv import load_dotenv
from asyncio import Task

from typing import Dict, List

from SeenItemsDB import SeenDB


class TradeitScraper:
    def __init__(self, skin_min_price, skin_max_price, stickers_to_lookup, logger):
        self.start = 0
        self.limit = 120
        self.skin_min_price = skin_min_price
        self.skin_max_price = skin_max_price
        self.stickers_to_lookup = stickers_to_lookup
        self.logger = logger

        # Env

        load_dotenv()
        self.telegram_token = os.environ.get('TOKEN')
        self.telegram_chat_id = os.environ.get('CHAT_ID')

        # Headers

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

        # Asyncio

        self.q_groups = asyncio.Queue()
        self.q_items = asyncio.Queue()
        self.q_images = asyncio.Queue()

        self.sem = asyncio.Semaphore(3)

        # Database

        self.db = SeenDB(path='SeenItems.db', logger=self.logger)


    async def send_img_with_caption(self, session: ClientSession, img_path: str, message: str):
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

    async def lookup_for_stickers(self, stickers: List[Dict], stickers_names: List[str]) -> bool:
        """
        This function checks if any of the stickers in the provided list match the names in stickers_names.
        If a match is found, it returns True; otherwise, it returns False.
        """
        
        for sticker_name in stickers_names:
            for sticker in stickers:
                if sticker_name.lower() in sticker.get('name', 'Unknown').lower():
                    return True
        return False

    async def fetch(self, session: ClientSession, url: str) -> Dict:
        await asyncio.sleep(random.uniform(0.3, 1))
        async with self.sem:
            try:
                async with session.get(url, headers=self.headers, timeout=ClientTimeout(total=30)) as response:
                    if response.status!=200:
                        text = await response.text()
                        self.logger.error(f'GET {response.status}, something went wrong.\n{text}')
                        raise ValueError(f'Unexpected satatus code: {response.status}, {text}')
                    #self.logger.info(f'GET {response.status}, Fetching {url}')
                    return await response.json()

            except Exception as e:
                #self.logger.error(f'An error occured while fetching {url},\nMessage: {e}')
                raise ValueError(f'An error occured while fetching {url},\nMessage: {e}')
    
    async def worker_image(self, session: ClientSession):
        while True:
            alert = await self.q_images.get()

            if alert is None:
                break

            await self.send_img_with_caption(session, alert['img'], alert['msg'])
            self.q_images.task_done()



    async def worker_item(self, session: ClientSession):
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

            if not await self.db.isInDB(id) and await self.lookup_for_stickers(stickers, self.stickers_to_lookup):
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
                await self.db.add_item(id)

            self.q_items.task_done()


    async def worker_group(self, session: ClientSession):
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
        
        async with ClientSession() as session:
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
                    #self.logger.info("No more grouped items in the response")
                    break

                #await asyncio.sleep(random.uniform(5, 10))
                
                self.start += self.limit
                self.limit = 160
            
            # worker startup
            tasks: List[Task] = []
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

            try:
                await asyncio.gather(*tasks)
            except ValueError as e:
                self.logger.error(f'Error, stopping scraper, {e}')
                for task in tasks:
                    task.cancel()
            await self.db.close()

            