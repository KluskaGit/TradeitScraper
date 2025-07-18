from TradeitScraper import TradeitScraper


if __name__ == "__main__":
    minPrice = 5
    maxPrice = 10
    stickers_to_lookup=['Holo', 'Katowice 2015', 'Cologne 2014', 'Atlanta 2017']

    scraper = TradeitScraper(skin_min_price=minPrice, skin_max_price=maxPrice, stickers_to_lookup=stickers_to_lookup)
    scraper.scrape()
    