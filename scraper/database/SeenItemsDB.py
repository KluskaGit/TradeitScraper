import sqlite3
from logging import Logger

class SeenDB:
    def __init__(self, path: str, logger: Logger):
        self.logger = logger

        try:
            self.conn = sqlite3.connect(path)
            self.create_table()
            self.cleanup()
        except sqlite3.Error as error:
            self.logger.error(f'Error occured, {error}')


    def create_table(self):
        with self.conn:
            self.conn.execute('''
                            CREATE TABLE IF NOT EXISTS scrapedItems(
                                itemID TEXT NOT NULL PRIMARY KEY,
                                creation_date TEXT NOT NULL DEFAULT (datetime('now'))
                            )''')
        
    async def add_item(self, id: str):
        with self.conn:
            self.conn.execute('''
                            INSERT INTO scrapedItems (itemID) VALUES(?)
                            ''', (id,))
            
    async def isInDB(self, id: str) -> bool:
        with self.conn:
            result = self.conn.execute('''
                                            SELECT itemID from scrapedItems where itemID like ?
                                        ''', (id,))
        return True if result.fetchone() else False

    def cleanup(self):
        with self.conn:
            self.conn.execute('''
                                DELETE
                                FROM scrapedItems
                                WHERE creation_date < datetime('now', '-3 days');
                              ''')
    async def close(self):
        self.conn.close()
        
        
    


    
