from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional

app = FastAPI()

# Подключаем шаблоны
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def read_root(
    request: Request,
    tg_id: Optional[int] = Query(None),
    user_wallet: Optional[str] = Query(None),
    amount: Optional[int] = Query(None)
):
    """
    Основной эндпоинт, который отдает главную HTML-страницу.
    Теперь он принимает user_wallet и amount из URL и передает их в шаблон.
    """
    amount_display = 0
    try:
        if amount is not None:
            amount_display = int(amount) / 10**9
    except Exception:
        pass

    context = {
        "request": request,
        "tg_id": tg_id,
        "user_wallet": user_wallet,
        "amount": amount,
        "amount_display": amount_display,
        "assoc_token_program_id": config.ASSOCIATED_TOKEN_PROGRAM_ID
    }
    return templates.TemplateResponse("index.html", context)

@app.get("/claim", response_class=HTMLResponse)
async def claim_page(
    request: Request,
    tg_id: Optional[int] = Query(None),
    user_wallet: Optional[str] = Query(None),
    action: Optional[str] = Query(None)
):
    """Страница для подписи транзакции получения наград."""
    context = {
        "request": request,
        "tg_id": tg_id,
        "user_wallet": user_wallet,
        "owner_wallet": config.OWNER_WALLET,
        "mint_address": config.TOKEN_MINT_ADDRESS,
        "program_id": config.PROGRAM_ID,
        "assoc_token_program_id": config.ASSOCIATED_TOKEN_PROGRAM_ID
    }
    return templates.TemplateResponse("claim.html", context)

# --- Callback от фронта после отправки транзакции ---
from telegram import Bot
import config

bot = Bot(token=config.TELEGRAM_TOKEN)

@app.post("/tx_callback")
async def tx_callback(request: Request):
    data = await request.json()
    telegram_id = data.get("tg_id")
    signature = data.get("signature")
    action = data.get("action", "lock")

    if not telegram_id or not signature:
        return {"status": "error", "reason": "missing fields"}

    try:
        explorer_link = f"https://explorer.solana.com/tx/{signature}?cluster=mainnet-beta"
        if action == "claim":
            text = f"✅ Награды получены!\nТранзакция: {explorer_link}"
        else:
            text = f"✅ Заморозка подтверждена!\nТранзакция: {explorer_link}"
        bot.send_message(chat_id=telegram_id, text=text)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "reason": str(e)}

# Чтобы запустить сервер, выполните в терминале:
# uvicorn web_server:app --reload 