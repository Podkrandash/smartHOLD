import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
PROGRAM_ID = os.getenv("PROGRAM_ID", "8cSiKf4CX2gxSyvvWmNZRxRifqX7GUXHzwE3b1jmzfX4")
TOKEN_MINT_ADDRESS = os.getenv("TOKEN_MINT_ADDRESS", "AKzCnZFRTab25UuN2iLTzgjoeDxJuBLCXZwchFTkAbWz")
RPC_URL = os.getenv("RPC_URL", "https://api.mainnet-beta.solana.com")
# официальный програм-ид Associated Token Account
ASSOCIATED_TOKEN_PROGRAM_ID = os.getenv("ASSOCIATED_TOKEN_PROGRAM_ID", "ATokenGPvbdGVxr1b2k1eVbWqBS7uJwHyGF7wwtTva2dr")
# Адрес кошелька владельца для получения 1% комиссии от стейкинга
OWNER_WALLET = os.getenv("OWNER_WALLET", "")  # Нужно установить реальный адрес
SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "http://127.0.0.1:8000")

if not TELEGRAM_TOKEN:
    raise ValueError("Необходимо установить переменную окружения TELEGRAM_TOKEN") 