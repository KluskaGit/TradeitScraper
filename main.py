import asyncio
import logging
import yaml

from logging.handlers import RotatingFileHandler
from pathlib import Path

from scraper.TradeitScraper import TradeitScraper

def main()->None:
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

    with open(Path('appconfig.yaml'), 'r') as cfg:
        try:
            config = yaml.safe_load(cfg)
        except yaml.YAMLError as e:
            logger.error(f'Error occured while reading config file: {e}')
            raise yaml.YAMLError(e)

    scraper = TradeitScraper(stickers_to_lookup=stickers_to_lookup, logger=logger, config=config)
    asyncio.run(scraper.run())
    logger.info('All tasks finished')



if __name__ == "__main__":
    main()

    