import asyncio
import random
import os

from aiohttp import ClientSession, ClientTimeout
from dotenv import load_dotenv
from asyncio import Task
from logging import Logger
from typing import Dict, List, Any

from scraper.database.SeenItemsDB import SeenDB


class TradeitScraper:
    def __init__(
            self,
            stickers_to_lookup: list[str],
            logger: Logger,
            config: dict[str, Any]
        ):

        # Scraper setup

        self.config = config
        self.start = 0
        self.limit = 120
        self.skin_min_price = self.config['scraper']['skin_min_price']
        self.skin_max_price = self.config['scraper']['skin_max_price']
        self.stickers_to_lookup = stickers_to_lookup
        self.min_delay = self.config['scraper']['min_delay']
        self.max_delay = self.config['scraper']['max_delay']

        # Logger

        self.logger = logger

        # Env

        load_dotenv()
        self.telegram_token = os.environ.get('TOKEN')
        if not self.telegram_token:
            raise ValueError("No TOKEN env variable found")
        self.telegram_chat_id = os.environ.get('CHAT_ID')
        if not self.telegram_chat_id:
            raise ValueError("No CHAT_ID env variable found")

        # Headers

        self.headers: dict = self.config['scraper']['headers']
        self.user_agent: list[str] = self.headers.pop('User-Agent')

        # Asyncio

        self.q_groups = asyncio.Queue()
        self.q_items = asyncio.Queue()
        self.q_alerts = asyncio.Queue()

        self.semaphore = asyncio.Semaphore(3)

        # Database

        self.db = SeenDB(path='SeenItems.db', logger=self.logger)
    
    async def create_headers(self) -> None:
        self.headers['User-Agent'] = random.choice(self.user_agent)

    async def send_img_with_caption(self, session: ClientSession, img_path: str, message: str) -> None:
        await asyncio.sleep(random.uniform(0.3, 0.5))
        
        if img_path:
            endpoint = 'sendPhoto'
            payload = {
                'chat_id': self.telegram_chat_id,
                'photo': img_path, 
                'caption': message, 
                'parse_mode': 'HTML'}
        else:
            endpoint = 'sendMessage'
            payload = {
                'chat_id': self.telegram_chat_id, 
                'text': message, 
                'parse_mode': 'HTML'}

        url = f'https://api.telegram.org/bot{self.telegram_token}/{endpoint}'
        
        await self.create_headers()
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
        await asyncio.sleep(random.uniform(self.min_delay, self.max_delay))
        await self.create_headers()
        
        async with self.semaphore:
            async with session.get(url, headers=self.headers, timeout=ClientTimeout(total=30)) as response:
                if response.status!=200:
                    text = await response.text()
                    self.logger.error(f'GET {response.status}, something went wrong.\n{text}')
                    raise ValueError(f'Unexpected satatus code: {response.status}, {text}')
                #self.logger.info(f'GET {response.status}, Fetching {url}')
                return await response.json()
    
    async def worker_image(self, session: ClientSession):
        while True:
            alert = await self.q_alerts.get()

            if alert is None:
                self.q_alerts.task_done()
                break

            await self.send_img_with_caption(session, alert['img'], alert['msg'])

            self.q_alerts.task_done()



    async def worker_item(self, session: ClientSession):
        while True:
            # Extracting item details
            item = await self.q_items.get()

            if item is None:
                self.q_items.task_done()
                break

            id = item.get('id', 'Unknown')
            name = item.get('name', 'Unknown')
            price = item.get('price', 0)
            store_price = item.get('storePrice', 0)
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
                await self.q_alerts.put(alert)
                await self.db.add_item(id)

            self.q_items.task_done()


    async def worker_group(self, session: ClientSession):
        while True:
            group_id = await self.q_groups.get()

            if group_id is None:
                self.q_groups.task_done()
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

            n_group_tasks = 1
            n_items_tasks = 4
            n_image_tasks = 1

            for _ in range(n_group_tasks):
                tasks.append(asyncio.create_task(self.worker_group(session)))

            for _ in range(n_items_tasks):
                tasks.append(asyncio.create_task(self.worker_item(session)))
            for _ in range(n_image_tasks):
                tasks.append(asyncio.create_task(self.worker_image(session)))
            
            
            # Send sentinel values to stop workers
            for _ in range(n_group_tasks):
                await self.q_groups.put(None)
            for _ in range(n_items_tasks):
                await self.q_items.put(None)
            for _ in range(n_image_tasks):
                await self.q_alerts.put(None)


            await asyncio.gather(*tasks, return_exceptions=True)

            await self.db.close()

            