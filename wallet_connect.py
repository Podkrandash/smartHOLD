import asyncio
import qrcode
from io import BytesIO
from typing import Optional, Dict, Any
import uuid
import time

class SimpleWalletConnect:
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
    def generate_session_id(self) -> str:
        """Генерирует уникальный ID сессии."""
        return str(uuid.uuid4())
    
    def create_deep_link(self, session_id: str) -> str:
        """Создает deep link для подключения кошелька."""
        # Создаем простой deep link для Solana кошельков
        # Это будет работать с Phantom, Solflare и другими кошельками
        deep_link = f"solana://connect?session={session_id}"
        return deep_link
    
    def create_qr_code(self, deep_link: str) -> BytesIO:
        """Создает QR-код для подключения кошелька."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(deep_link)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Сохраняем в BytesIO для отправки в Telegram
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return img_buffer
    
    def create_session(self, session_id: str) -> None:
        """Создает новую сессию."""
        self.sessions[session_id] = {
            'created_at': time.time(),
            'status': 'pending',
            'wallet_address': None
        }
    
    def complete_session(self, session_id: str, wallet_address: str) -> bool:
        """Завершает сессию с адресом кошелька."""
        if session_id in self.sessions:
            self.sessions[session_id]['status'] = 'completed'
            self.sessions[session_id]['wallet_address'] = wallet_address
            return True
        return False
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Получает статус сессии."""
        return self.sessions.get(session_id)

# Создаем глобальный экземпляр
wallet_connect = SimpleWalletConnect()

async def connect_wallet_via_qr() -> tuple[BytesIO, str, str]:
    """Создает QR-код для подключения кошелька."""
    session_id = wallet_connect.generate_session_id()
    deep_link = wallet_connect.create_deep_link(session_id)
    
    # Создаем сессию
    wallet_connect.create_session(session_id)
    
    # Создаем QR-код
    qr_code = wallet_connect.create_qr_code(deep_link)
    
    return qr_code, session_id, deep_link

async def simulate_wallet_connection(session_id: str) -> Optional[str]:
    """Симулирует подключение кошелька (для демонстрации)."""
    # В реальном приложении здесь должна быть логика ожидания
    # подключения через WebSocket или HTTP polling
    
    await asyncio.sleep(3)  # Имитируем время подключения
    
    # Генерируем тестовый адрес кошелька
    test_wallet = f"9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
    
    # Завершаем сессию
    if wallet_connect.complete_session(session_id, test_wallet):
        return test_wallet
    
    return None

def get_connection_instructions() -> str:
    """Возвращает инструкции по подключению."""
    return (
        "📱 **Как подключить кошелек:**\n\n"
        "1️⃣ Откройте ваш кошелек Solana (Phantom, Solflare, Backpack)\n"
        "2️⃣ Найдите функцию 'Подключить кошелек' или 'Connect Wallet'\n"
        "3️⃣ Отсканируйте QR-код или введите код подключения\n"
        "4️⃣ Подтвердите подключение в кошельке\n\n"
        "💡 **Поддерживаемые кошельки:**\n"
        "• Phantom\n"
        "• Solflare\n"
        "• Backpack\n"
        "• Slope\n"
        "• И другие кошельки Solana"
    ) 