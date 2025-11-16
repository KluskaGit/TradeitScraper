# TradeitScraper

A Python-based web scraper for monitoring CS2 skin listings on tradeit.gg. The scraper searches for items with specific stickers within a defined price range and sends notifications via Telegram when matching items are found.

## Features

- 🔍 Monitors tradeit.gg for CS2 skins with specific stickers
- 💰 Filter by price range
- 📱 Telegram notifications with item details and images
- 🗄️ SQLite database to track seen items and avoid duplicates
- 📝 Logging with rotating file handler
- ⚡ Asynchronous processing for efficient scraping

## Requirements

- Python 3.13+
- uv package manager

## Installation

1. Clone the repository:
```bash
git clone https://github.com/KluskaGit/TradeitScraper.git
cd TradeitScraper
```

2. Install dependencies using uv:
```bash
uv sync
```

## Configuration

1. Create a `.env` file in the project root with your Telegram bot credentials:
```env
TOKEN=your_telegram_bot_token
CHAT_ID=your_telegram_chat_id
```

2. Edit `stickers.txt` to include the sticker names you want to search for (one per line):
```
Katowice 2014
Titan
iBUYPOWER
```

3. (Optional) Adjust price range in `main.py`:
```python
minPrice = 5   # Minimum price in USD
maxPrice = 10  # Maximum price in USD
```

## Usage

Run the scraper:
```bash
uv run main.py
```

The scraper will:
1. Load sticker names from `stickers.txt`
2. Search for items in the specified price range
3. Check if items have matching stickers
4. Send Telegram notifications for new matches
5. Log activity to `logs.log`

## Project Structure

```
TradeitScraper/
├── main.py                 # Entry point
├── stickers.txt           # List of sticker names to search for
├── pyproject.toml         # Project dependencies
├── .env                   # Environment variables (not tracked)
├── scraper/
│   ├── TradeitScraper.py  # Main scraper logic
│   └── database/
│       └── SeenItemsDB.py # SQLite database handler
└── logs.log               # Application logs
```

## License

This project is open source and available under the MIT License.