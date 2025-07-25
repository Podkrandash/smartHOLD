import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

import config
import db
import solana_utils
from solders.pubkey import Pubkey
import datetime

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для диалога
WALLET_CONNECT = 1
LOCK_AMOUNT = 2

# --- Функции-обработчики ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение и главное меню."""
    user = update.effective_user
    db.init_db() # Убедимся, что БД инициализирована
    
    wallet_address = db.get_wallet(user.id)
    
    if wallet_address:
        text = f"Здравствуйте, {user.first_name}! Ваш кошелек {wallet_address[:6]}...{wallet_address[-4:]} уже подключен."
        keyboard = [
            [KeyboardButton("🔒 Заморозить токены")],
            [KeyboardButton("📊 Мои замороженные токены")],
            [KeyboardButton("💰 Получить награду")],
        ]
    else:
        text = f"Здравствуйте, {user.first_name}! Для начала работы, пожалуйста, подключите ваш кошелек Solana."
        keyboard = [
            [KeyboardButton("🔗 Подключить кошелек")],
        ]
        
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(text, reply_markup=reply_markup)


async def connect_wallet_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрашивает у пользователя адрес кошелька."""
    await update.message.reply_text(
        "Пожалуйста, отправьте мне адрес вашего кошелька Solana."
    )
    return WALLET_CONNECT

async def connect_wallet_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет адрес кошелька."""
    wallet_address = update.message.text.strip()
    user_id = update.effective_user.id

    # Валидация адреса Solana
    try:
        _ = Pubkey.from_string(wallet_address)
    except Exception:
        await update.message.reply_text("Похоже, это некорректный адрес Solana. Попробуйте ещё раз.")
        return WALLET_CONNECT

    db.link_wallet(user_id, wallet_address)

    await update.message.reply_text(
        f"Ваш кошелек {wallet_address} успешно подключен!"
    )
    
    # Возвращаемся в главное меню
    await start(update, context)
    return ConversationHandler.END


async def lock_tokens_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает диалог заморозки токенов, запрашивая сумму."""
    user_id = update.effective_user.id
    wallet_address = db.get_wallet(user_id)

    if not wallet_address:
        await update.message.reply_text("Сначала подключите кошелек.")
        return ConversationHandler.END

    try:
        user_pubkey = Pubkey.from_string(wallet_address)
        balance = await solana_utils.get_token_balance(user_pubkey)
        
        # TODO: Учесть decimals
        await update.message.reply_text(
            f"Ваш текущий баланс: {balance} SDCB.\n\n"
            "Сколько токенов вы хотите заморозить? Отправьте сумму числом."
        )
        return LOCK_AMOUNT

    except Exception as e:
        logger.error(f"Ошибка при получении баланса для {wallet_address}: {e}")
        await update.message.reply_text("Произошла ошибка при получении баланса. Попробуйте позже.")
        return ConversationHandler.END


async def get_lock_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает сумму от пользователя и генерирует ссылку для подписи."""
    user_id = update.effective_user.id
    wallet_address = db.get_wallet(user_id)
    
    DECIMALS = 9  # TODO: получить динамически

    try:
        ui_amount = float(update.message.text.replace(',', '.'))
        if ui_amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное число (например: 100.5).")
        return LOCK_AMOUNT

    raw_amount = int(ui_amount * 10**DECIMALS)

    # Проверяем баланс
    user_pubkey = Pubkey.from_string(wallet_address)
    balance = await solana_utils.get_token_balance(user_pubkey)
    if raw_amount > balance:
        await update.message.reply_text("Недостаточно токенов на балансе. Введите сумму меньше.")
        return LOCK_AMOUNT
    
    # Замените на адрес вашего публичного сервера, когда он будет
    base_url = "http://127.0.0.1:8000" 
    
    # Формируем URL с параметрами
    import urllib.parse
    params = urllib.parse.urlencode({
        "tg_id": user_id,
        "user_wallet": wallet_address,
        "amount": raw_amount
    })
    sign_url = f"{base_url}/?{params}"

    keyboard = [
        [InlineKeyboardButton("✍️ Подписать транзакцию", url=sign_url)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Отлично! Теперь, пожалуйста, перейдите по ссылке ниже, чтобы подтвердить и подписать транзакцию в вашем кошельке.",
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END


async def show_locked_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для кнопки 'Мои замороженные токены'."""
    user_id = update.effective_user.id
    wallet_address = db.get_wallet(user_id)

    if not wallet_address:
        await update.message.reply_text("Сначала подключите кошелек.")
        return

    try:
        user_pubkey = Pubkey.from_string(wallet_address)
        lock_pda, _ = solana_utils.get_lock_pda(user_pubkey)
        
        lock_details = await solana_utils.get_lock_details(lock_pda)

        if lock_details and lock_details.is_initialized:
            lock_date = datetime.datetime.fromtimestamp(lock_details.lock_date).strftime('%Y-%m-%d %H:%M:%S')
            unlock_date = datetime.datetime.fromtimestamp(lock_details.unlock_date).strftime('%Y-%m-%d %H:%M:%S')
            amount = lock_details.amount_locked # TODO: Учесть decimals

            text = (
                f"✅ **Ваши токены заморожены**\n\n"
                f"🔢 **Сумма:** {amount} SDCB\n"
                f"🗓️ **Дата заморозки:** {lock_date}\n"
                f"⏳ **Дата разблокировки:** {unlock_date}\n\n"
                f"Награды за стейкинг будут реализованы в следующем шаге."
            )
        else:
            text = "У вас нет замороженных токенов."

        await update.message.reply_text(text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Ошибка при получении данных о блокировке для {wallet_address}: {e}")
        await update.message.reply_text("Произошла ошибка при получении данных о блокировке.")

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Я не знаю такой команды.")


async def claim_rewards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для кнопки 'Получить награду'."""
    user_id = update.effective_user.id
    wallet_address = db.get_wallet(user_id)

    if not wallet_address:
        await update.message.reply_text("Сначала подключите кошелек.")
        return

    try:
        user_pubkey = Pubkey.from_string(wallet_address)
        lock_pda, _ = solana_utils.get_lock_pda(user_pubkey)
        
        lock_details = await solana_utils.get_lock_details(lock_pda)

        if not lock_details or not lock_details.is_initialized:
            await update.message.reply_text("У вас нет замороженных токенов.")
            return
        
        # Проверяем есть ли доступные награды
        import time
        current_time = int(time.time())
        end_date = min(current_time, lock_details.unlock_date)
        days_elapsed = (end_date - lock_details.last_reward_claim_date) // 86400
        
        if days_elapsed <= 0:
            await update.message.reply_text("Нет доступных наград. Награды начисляются ежедневно.")
            return
        
        # Рассчитываем примерные награды
        rewards = (lock_details.amount_locked * days_elapsed) // 1000  # 0.1% в день
        rewards_display = rewards / 10**9
        
        # Генерируем ссылку для подписи
        base_url = "http://127.0.0.1:8000"
        
        import urllib.parse
        params = urllib.parse.urlencode({
            "tg_id": user_id,
            "user_wallet": wallet_address,
            "action": "claim"
        })
        sign_url = f"{base_url}/claim?{params}"

        keyboard = [
            [InlineKeyboardButton("💰 Получить награды", url=sign_url)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"Доступные награды: ~{rewards_display:.2f} SDCB за {days_elapsed} дней.\n\n"
            "Перейдите по ссылке для получения наград.",
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Ошибка при расчете наград для {wallet_address}: {e}")
        await update.message.reply_text("Произошла ошибка при расчете наград.")


def main() -> None:
    """Запуск бота."""
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()
    
    # Диалог для подключения кошелька
    wallet_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^🔗 Подключить кошелек$'), connect_wallet_prompt)],
        states={
            WALLET_CONNECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, connect_wallet_save)],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    # Диалог для заморозки токенов
    lock_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^🔒 Заморозить токены$'), lock_tokens_start)],
        states={
            LOCK_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_lock_amount)],
        },
        fallbacks=[CommandHandler('start', start)],
    )
    
    application.add_handler(wallet_conv_handler)
    application.add_handler(lock_conv_handler)

    # Обработчики кнопок главного меню
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex('^📊 Мои замороженные токены$'), show_locked_tokens))
    application.add_handler(MessageHandler(filters.Regex('^💰 Получить награду$'), claim_rewards))

    # Обработчик неизвестных команд
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # Запуск бота
    application.run_polling()


if __name__ == "__main__":
    main() 