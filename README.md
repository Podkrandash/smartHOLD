# SDCB Telegram-бот + Web3-интерфейс

## Описание
Это Telegram-бот и веб-интерфейс для холдирования и стейкинга токена SDCB на блокчейне Solana (mainnet).

---

## Требования

- Python 3.8+
- Rust + Cargo (только если потребуется пересобрать смарт-контракт)
- Solana CLI (https://docs.solana.com/cli/install-solana-cli-tools)
- pip (Python package manager)
- Установленный кошелек Phantom или Solflare (для пользователей)

---

## Установка

1. **Склонируйте проект или распакуйте архив**
2. **Установите зависимости:**
    ```bash
    pip install -r requirements.txt
    ```

3. **Создайте файл `.env` в корне проекта:**
    ```
    TELEGRAM_TOKEN="ВАШ_ТОКЕН_ОТ_БОТА"
    ```
    (Токен можно получить у @BotFather в Telegram)

---

## Настройка сети и адресов

- **Сеть:** mainnet-beta
- **Program ID:** `8cSiKf4CX2gxSyvvWmNZRxRifqX7GUXHzwE3b1jmzfX4`
- **Token Mint Address:** `AKzCnZFRTab25UuN2iLTzgjoeDxJuBLCXZwchFTkAbWz`

**Проверьте, что в файлах:**
- `solana_utils.py` — строка подключения к сети:
    ```python
    RPC_URL = "https://api.mainnet-beta.solana.com"
    ```
- `templates/index.html` — все ссылки на explorer и cluster должны быть с `mainnet-beta`:
    ```js
    const connection = new solanaWeb3.Connection(solanaWeb3.clusterApiUrl('mainnet-beta'), 'confirmed');
    // и explorer: https://explorer.solana.com/tx/...
    ```

---

## Запуск

1. **Запустите веб-сервер:**
    ```bash
    uvicorn web_server:app --host 0.0.0.0 --port 8000
    ```
    (или на другом порту/домене, если нужно)

2. **Запустите Telegram-бота:**
    ```bash
    python bot.py
    ```

3. **Проверьте работу:**
    - Откройте бота в Telegram, подключите кошелек, попробуйте заморозить токены.
    - Бот сгенерирует ссылку на веб-страницу для подписи транзакции.
    - Подпишите транзакцию через Phantom/Solflare.

---

## Важно!

- **Никогда не передавайте приватные ключи от кошелька третьим лицам!**
- Для управления смарт-контрактом (mint, update) используйте тот же кошелек, с которого был деплоен контракт.
- Если потребуется обновить контракт — используйте Solana CLI и исходники из папки `smart-contract/`.

---

## Техническая поддержка

По всем вопросам — обращаться к разработчику проекта. 