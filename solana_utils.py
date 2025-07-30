from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.instruction import Instruction, AccountMeta
from solders.transaction import Transaction
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solana.rpc.commitment import Confirmed
from spl.token.client import Token
import borsh
from construct import Struct, Bytes, Int64ul, Int64sl, Flag
import db  # Для получения адреса кошелька пользователя
from typing import Optional, Tuple

# --- КОНСТАНТЫ ---
import config

PROGRAM_ID = Pubkey.from_string(config.PROGRAM_ID)
TOKEN_MINT_ADDRESS = Pubkey.from_string(config.TOKEN_MINT_ADDRESS)

# Подключение к сети Solana
solana_client = Client(config.RPC_URL)

# --- СХЕМА ДАННЫХ КОНТРАКТА ---

LOCK_DETAILS_SCHEMA = Struct(
    "is_initialized" / Flag,
    "user_pubkey" / Bytes(32),
    "amount_locked" / Int64ul,
    "lock_date" / Int64sl,
    "unlock_date" / Int64sl,
    "last_reward_claim_date" / Int64sl,
)

class LockDetails:
    def __init__(self, is_initialized, user_pubkey, amount_locked, lock_date, unlock_date, last_reward_claim_date):
        self.is_initialized = is_initialized
        self.user_pubkey = user_pubkey
        self.amount_locked = amount_locked
        self.lock_date = lock_date
        self.unlock_date = unlock_date
        self.last_reward_claim_date = last_reward_claim_date

# --- ОСНОВНЫЕ ФУНКЦИИ ---

def get_lock_pda(user_pubkey: Pubkey) -> Tuple[Pubkey, int]:
    """Находит адрес PDA (Program Derived Address) для хранения данных о блокировке."""
    return Pubkey.find_program_address(
        seeds=[b"lock", bytes(user_pubkey)],
        program_id=PROGRAM_ID
    )

async def get_lock_details(pda: Pubkey) -> Optional[LockDetails]:
    """Получает и десериализует данные о блокировке из PDA."""
    try:
        acc_info_res = solana_client.get_account_info(pda)
        if acc_info_res.value is None:
            return None
        
        data = acc_info_res.value.data
        
        deserialized_data = LOCK_DETAILS_SCHEMA.parse(data)
        
        return LockDetails(
            is_initialized=deserialized_data.is_initialized,
            user_pubkey=Pubkey(deserialized_data.user_pubkey),
            amount_locked=deserialized_data.amount_locked,
            lock_date=deserialized_data.lock_date,
            unlock_date=deserialized_data.unlock_date,
            last_reward_claim_date=deserialized_data.last_reward_claim_date,
        )

    except Exception as e:
        print(f"Error getting lock details: {e}")
        return None

async def get_token_decimals(mint_pubkey: Pubkey) -> int:
    """Получает количество десятичных знаков для токена."""
    try:
        mint_info = solana_client.get_account_info(mint_pubkey)
        if mint_info.value is None:
            raise ValueError("Mint account not found")
        
        # Десериализуем данные аккаунта минта, чтобы получить decimals
        # Структура Mint account: https://spl.solana.com/token#show-layout
        # decimals находятся в байте 44 (индекс 44)
        data = mint_info.value.data
        decimals = data[44]
        return decimals
    except Exception as e:
        print(f"Error getting token decimals for {mint_pubkey}: {e}")
        # Возвращаем значение по умолчанию, если не удалось получить
        return 9 

async def get_token_balance(user_pubkey: Pubkey) -> Tuple[Optional[int], int]:
    """Получает баланс токена SDCB и его decimals."""
    decimals = await get_token_decimals(TOKEN_MINT_ADDRESS)
    try:
        # Находим адрес связанного токен-аккаунта (ATA)
        ata_pubkey = Token.get_associated_token_address(
            owner=user_pubkey,
            mint=TOKEN_MINT_ADDRESS
        )
        print(f"INFO: Checking balance for ATA: {ata_pubkey}")
        
        # Запрашиваем баланс
        balance_response = solana_client.get_token_account_balance(ata_pubkey)
        
        if balance_response.value is None:
             print(f"WARNING: No balance found for ATA {ata_pubkey}. It might not exist.")
             return None, decimals

        balance = int(balance_response.value.amount)
        print(f"INFO: Raw balance for {user_pubkey} is {balance}")
        return balance, decimals

    except Exception as e:
        # Логируем ошибку, чтобы видеть, что пошло не так
        print(f"ERROR: Could not get token balance for wallet {user_pubkey}. Reason: {e}")
        import traceback
        traceback.print_exc()
        return None, decimals

# Другие функции для создания транзакций (lock, unlock, claim) будут добавлены здесь.
# Например, функция для создания инструкции блокировки:
def create_lock_instruction(user_pubkey: Pubkey, lock_pda: Pubkey, user_ata: Pubkey, amount: int) -> Instruction:
    """Создает инструкцию для вызова `LockTokens` в смарт-контракте."""
    
    TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
    SYSTEM_PROGRAM_ID = Pubkey.from_string("11111111111111111111111111111111")
    RENT_SYSVAR = Pubkey.from_string("SysvarRent111111111111111111111111111111111")
    CLOCK_SYSVAR = Pubkey.from_string("SysvarC1ock11111111111111111111111111111111")
    
    # PDA токен-аккаунт для хранения заблокированных токенов
    pda_ata = Token.get_associated_token_address(
        owner=lock_pda,
        mint=TOKEN_MINT_ADDRESS
    )
    
    # Аккаунты, которые требует наша инструкция в контракте
    accounts = [
        AccountMeta(pubkey=user_pubkey, is_signer=True, is_writable=False),
        AccountMeta(pubkey=lock_pda, is_signer=False, is_writable=True),
        AccountMeta(pubkey=user_ata, is_signer=False, is_writable=True),
        AccountMeta(pubkey=pda_ata, is_signer=False, is_writable=True),
        AccountMeta(pubkey=user_pubkey, is_signer=False, is_writable=False),  # authority
        AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
        AccountMeta(pubkey=RENT_SYSVAR, is_signer=False, is_writable=False),
        AccountMeta(pubkey=CLOCK_SYSVAR, is_signer=False, is_writable=False),
    ]

    # Данные для инструкции (сумма для блокировки)
    # TODO: Нужно будет правильно сериализовать данные согласно enum в контракте.
    # 0 - это индекс инструкции LockTokens в нашем enum TokenInstruction
    instruction_data = b'\x00' + amount.to_bytes(8, 'little')

    return Instruction(
        program_id=PROGRAM_ID,
        accounts=accounts,
        data=instruction_data
    ) 

def create_claim_instruction(
    user_pubkey: Pubkey, 
    lock_pda: Pubkey, 
    user_ata: Pubkey,
    owner_ata: Pubkey,
    mint: Pubkey,
    mint_authority: Pubkey
) -> Instruction:
    """Создает инструкцию для вызова ClaimRewards в смарт-контракте."""
    
    TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
    CLOCK_SYSVAR = Pubkey.from_string("SysvarC1ock11111111111111111111111111111111")
    
    accounts = [
        AccountMeta(pubkey=user_pubkey, is_signer=True, is_writable=False),
        AccountMeta(pubkey=lock_pda, is_signer=False, is_writable=True),
        AccountMeta(pubkey=user_ata, is_signer=False, is_writable=True),
        AccountMeta(pubkey=owner_ata, is_signer=False, is_writable=True),
        AccountMeta(pubkey=mint, is_signer=False, is_writable=True),
        AccountMeta(pubkey=mint_authority, is_signer=False, is_writable=False),
        AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
        AccountMeta(pubkey=CLOCK_SYSVAR, is_signer=False, is_writable=False),
    ]

    # 2 - это индекс инструкции ClaimRewards в enum
    instruction_data = b'\x02'

    return Instruction(
        program_id=PROGRAM_ID,
        accounts=accounts,
        data=instruction_data
    ) 