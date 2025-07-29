from TradeitScraper import TradeitScraper



if __name__ == "__main__":
    minPrice = 10
    maxPrice = 20

    with open("stickers.txt", "r") as file:
        stickers_to_lookup = file.read().splitlines()

    scraper = TradeitScraper(skin_min_price=minPrice, skin_max_price=maxPrice, stickers_to_lookup=stickers_to_lookup)
    scraper.scrape()
    