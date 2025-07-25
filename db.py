import sqlite3
from typing import Optional

def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    # Создаем таблицу для хранения связи Telegram ID и адреса кошелька
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        wallet_address TEXT NOT NULL UNIQUE
    )
    ''')
    
    # Можно добавить другие таблицы, например, для отслеживания статуса холда
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_holds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_telegram_id INTEGER NOT NULL,
        lock_date TEXT NOT NULL,
        unlock_date TEXT NOT NULL,
        amount REAL NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT 1,
        FOREIGN KEY (user_telegram_id) REFERENCES users (telegram_id)
    )
    ''')
    
    conn.commit()
    conn.close()

def link_wallet(telegram_id: int, wallet_address: str):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR REPLACE INTO users (telegram_id, wallet_address) VALUES (?, ?)", (telegram_id, wallet_address))
        conn.commit()
    finally:
        conn.close()

def get_wallet(telegram_id: int) -> Optional[str]:
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT wallet_address FROM users WHERE telegram_id = ?", (telegram_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()
    print("База данных инициализирована.") 