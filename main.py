import asyncio
from scraper.TradeitScraper import TradeitScraper

import logging
from logging.handlers import RotatingFileHandler

if __name__ == "__main__":
    minPrice = 5
    maxPrice = 10

    # Logger
    handler = RotatingFileHandler(
        'logs.log',
        maxBytes=5*1024*1024,  # 5 MB per file
        backupCount=3          # Keep last 3 backups
    )
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger = logging.getLogger("TradeitScraper")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    with open("stickers.txt", "r") as file:
        stickers_to_lookup = file.read().splitlines()

    scraper = TradeitScraper(skin_min_price=minPrice, skin_max_price=maxPrice, stickers_to_lookup=stickers_to_lookup, logger=logger)
    asyncio.run(scraper.run())
    logger.info('All tasks finished')
    