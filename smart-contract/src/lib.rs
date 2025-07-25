use solana_program::{
    account_info::{next_account_info, AccountInfo},
    entrypoint,
    entrypoint::ProgramResult,
    msg,
    program_error::ProgramError,
    program::invoke,
    pubkey::Pubkey,
    clock::Clock,
    sysvar::Sysvar,
    program_pack::{Pack, IsInitialized},
};
use borsh::{BorshDeserialize, BorshSerialize};
use spl_token::state::Account as TokenAccount;

pub mod error;
use error::TokenError;

// Константы для периодов блокировки в секундах
const ONE_YEAR: i64 = 31_536_000; // 365 * 24 * 3600
const TWO_YEARS: i64 = 63_072_000; // 2 * 365 * 24 * 3600  
const THREE_YEARS: i64 = 94_608_000; // 3 * 365 * 24 * 3600

const DAILY_REWARD_PERCENTAGE: u64 = 1; // 0.1% в день, для расчетов (1/1000)
const OWNER_FEE_PERCENTAGE: u64 = 1; // 1% комиссия основателю

#[derive(BorshSerialize, BorshDeserialize, Debug, Default)]
pub struct LockDetails {
    pub is_initialized: bool,
    pub user_pubkey: Pubkey,
    pub amount_locked: u64,
    pub lock_date: i64,
    pub unlock_date: i64,
    pub last_reward_claim_date: i64,
}

impl IsInitialized for LockDetails {
    fn is_initialized(&self) -> bool {
        self.is_initialized
    }
}

entrypoint!(process_instruction);

pub fn process_instruction(
    _program_id: &Pubkey,
    accounts: &[AccountInfo],
    instruction_data: &[u8],
) -> ProgramResult {
    let instruction = TokenInstruction::try_from_slice(instruction_data)
        .map_err(|_| ProgramError::InvalidInstructionData)?;

    match instruction {
        TokenInstruction::LockTokens { amount } => {
            process_lock_tokens(_program_id, accounts, amount)
        }
        TokenInstruction::UnlockTokens => {
            process_unlock_tokens(_program_id, accounts)
        }
        TokenInstruction::ClaimRewards => {
            process_claim_rewards(_program_id, accounts)
        }
        // Другие инструкции (например, ClaimRewards) будут добавлены здесь
    }
}

#[derive(BorshSerialize, BorshDeserialize, Debug)]
pub enum TokenInstruction {
    /// 0. Блокирует токены пользователя на случайный срок.
    ///
    /// Аккаунты:
    /// 1. `[signer]` Аккаунт пользователя, который блокирует токены.
    /// 2. `[writable]` PDA аккаунт для хранения информации о блокировке.
    /// 3. `[writable]` Токен-аккаунт пользователя (ATA) - источник.
    /// 4. `[writable]` Токен-аккаунт PDA контракта - получатель.
    /// 5. `[]` Authority пользователя (обычно его основной аккаунт).
    /// 6. `[]` Token program.
    /// 7. `[]` Rent sysvar.
    /// 8. `[]` Clock sysvar.
    LockTokens { amount: u64 },

    /// 1. Разблокирует токены пользователя.
    ///
    /// Аккаунты:
    /// 1. `[signer]` Аккаунт пользователя, который разблокирует токены.
    /// 2. `[writable]` PDA аккаунт с информацией о блокировке.
    /// 3. `[]` Clock sysvar.
    UnlockTokens,

    /// 2. Получить награды за стейкинг.
    ///
    /// Аккаунты:
    /// 1. `[signer]` Аккаунт пользователя.
    /// 2. `[writable]` PDA аккаунт с информацией о блокировке.
    /// 3. `[writable]` Токен-аккаунт пользователя (ATA).
    /// 4. `[writable]` Токен-аккаунт владельца для комиссии.
    /// 5. `[]` Mint токена.
    /// 6. `[signer]` Mint authority (обычно сама программа через PDA).
    /// 7. `[]` Token program.
    /// 8. `[]` Clock sysvar.
    ClaimRewards,
}

fn process_lock_tokens(
    _program_id: &Pubkey,
    accounts: &[AccountInfo],
    amount: u64,
) -> ProgramResult {
    let accounts_iter = &mut accounts.iter();
    let user_account = next_account_info(accounts_iter)?;
    let lock_pda = next_account_info(accounts_iter)?;
    let user_token_account_info = next_account_info(accounts_iter)?;
    let pda_token_account_info = next_account_info(accounts_iter)?;
    let user_authority = next_account_info(accounts_iter)?;
    let token_program = next_account_info(accounts_iter)?;
    let _rent_sysvar_info = next_account_info(accounts_iter)?;
    let clock_sysvar_info = next_account_info(accounts_iter)?;

    if !user_account.is_signer {
        return Err(ProgramError::MissingRequiredSignature);
    }
    
    // Проверяем, что PDA еще не инициализирован
    let mut lock_details = LockDetails::try_from_slice(&lock_pda.data.borrow())?;
    if lock_details.is_initialized() {
        return Err(TokenError::AccountAlreadyLocked.into());
    }

    // Проверяем баланс токенов пользователя
    let user_token_account = TokenAccount::unpack(&user_token_account_info.data.borrow())?;
    if user_token_account.amount < amount {
        return Err(TokenError::InvalidAmount.into());
    }

    // Переводим токены с кошелька пользователя на PDA контракта
    invoke(
        &spl_token::instruction::transfer(
            token_program.key,
            user_token_account_info.key,
            pda_token_account_info.key,
            user_authority.key,
            &[user_authority.key],
            amount,
        )?,
        &[
            user_token_account_info.clone(),
            pda_token_account_info.clone(),
            user_authority.clone(),
            token_program.clone(),
        ],
    )?;

    let clock = Clock::from_account_info(clock_sysvar_info)?;
    let current_timestamp = clock.unix_timestamp;

    let lock_period = generate_random_lock_period(current_timestamp);
    let unlock_date = current_timestamp + lock_period;

    lock_details.is_initialized = true;
    lock_details.user_pubkey = *user_account.key;
    lock_details.amount_locked = amount;
    lock_details.lock_date = current_timestamp;
    lock_details.unlock_date = unlock_date;
    lock_details.last_reward_claim_date = current_timestamp;
    
    lock_details.serialize(&mut *lock_pda.data.borrow_mut())?;

    msg!("Tokens locked. Amount: {}, Unlock date: {}", amount, unlock_date);
    Ok(())
}

fn process_unlock_tokens(
    _program_id: &Pubkey,
    accounts: &[AccountInfo],
) -> ProgramResult {
    let accounts_iter = &mut accounts.iter();
    let user_account = next_account_info(accounts_iter)?;
    let lock_pda = next_account_info(accounts_iter)?;
    let clock_sysvar_info = next_account_info(accounts_iter)?;

    if !user_account.is_signer {
        return Err(ProgramError::MissingRequiredSignature);
    }
    
    let mut lock_details = LockDetails::try_from_slice(&lock_pda.data.borrow())?;
    if !lock_details.is_initialized() {
        return Err(TokenError::AccountNotLocked.into());
    }

    if lock_details.user_pubkey != *user_account.key {
        return Err(ProgramError::IllegalOwner);
    }

    let clock = Clock::from_account_info(clock_sysvar_info)?;
    if clock.unix_timestamp < lock_details.unlock_date {
        return Err(TokenError::LockupPeriodNotEnded.into());
    }

    // "Разблокировка" - это просто обнуление данных в PDA.
    // Или можно закрыть аккаунт и вернуть ренту, что более правильно.
    // Пока просто обнуляем для простоты.
    lock_details = LockDetails::default();
    lock_details.serialize(&mut *lock_pda.data.borrow_mut())?;

    msg!("Tokens unlocked for account {}", user_account.key);
    Ok(())
}

fn process_claim_rewards(
    _program_id: &Pubkey,
    accounts: &[AccountInfo],
) -> ProgramResult {
    let accounts_iter = &mut accounts.iter();
    let user_account = next_account_info(accounts_iter)?;
    let lock_pda = next_account_info(accounts_iter)?;
    let user_token_account = next_account_info(accounts_iter)?;
    let owner_token_account = next_account_info(accounts_iter)?;
    let mint_account = next_account_info(accounts_iter)?;
    let mint_authority = next_account_info(accounts_iter)?;
    let token_program = next_account_info(accounts_iter)?;
    let clock_sysvar_info = next_account_info(accounts_iter)?;

    if !user_account.is_signer {
        return Err(ProgramError::MissingRequiredSignature);
    }

    let mut lock_details = LockDetails::try_from_slice(&lock_pda.data.borrow())?;
    if !lock_details.is_initialized() {
        return Err(TokenError::AccountNotLocked.into());
    }

    if lock_details.user_pubkey != *user_account.key {
        return Err(ProgramError::IllegalOwner);
    }

    let clock = Clock::from_account_info(clock_sysvar_info)?;
    let current_timestamp = clock.unix_timestamp;
    
    // Рассчитываем период для начисления наград
    let end_date = if current_timestamp > lock_details.unlock_date {
        lock_details.unlock_date // Награды не начисляются после разблокировки
    } else {
        current_timestamp
    };
    
    let days_elapsed = (end_date - lock_details.last_reward_claim_date) / 86400; // секунд в дне
    
    if days_elapsed <= 0 {
        msg!("No rewards to claim");
        return Ok(());
    }

    // Расчет наград: amount * days * 0.1% = amount * days / 1000
    let rewards = (lock_details.amount_locked as u128)
        .checked_mul(days_elapsed as u128)
        .and_then(|r| r.checked_mul(DAILY_REWARD_PERCENTAGE as u128))
        .and_then(|r| r.checked_div(1000))
        .ok_or(ProgramError::ArithmeticOverflow)? as u64;

    // Комиссия владельцу: 1% от наград
    let owner_fee = rewards
        .checked_mul(OWNER_FEE_PERCENTAGE)
        .and_then(|f| f.checked_div(100))
        .ok_or(ProgramError::ArithmeticOverflow)?;
        
    let user_rewards = rewards
        .checked_sub(owner_fee)
        .ok_or(ProgramError::ArithmeticOverflow)?;

    msg!("Claiming rewards: {} tokens (user: {}, owner fee: {})", 
         rewards, user_rewards, owner_fee);

    // Минтим токены пользователю
    if user_rewards > 0 {
        invoke(
            &spl_token::instruction::mint_to(
                token_program.key,
                mint_account.key,
                user_token_account.key,
                mint_authority.key,
                &[mint_authority.key],
                user_rewards,
            )?,
            &[
                mint_account.clone(),
                user_token_account.clone(),
                mint_authority.clone(),
                token_program.clone(),
            ],
        )?;
    }

    // Минтим комиссию владельцу
    if owner_fee > 0 {
        invoke(
            &spl_token::instruction::mint_to(
                token_program.key,
                mint_account.key,
                owner_token_account.key,
                mint_authority.key,
                &[mint_authority.key],
                owner_fee,
            )?,
            &[
                mint_account.clone(),
                owner_token_account.clone(),
                mint_authority.clone(),
                token_program.clone(),
            ],
        )?;
    }

    // Обновляем дату последнего получения наград
    lock_details.last_reward_claim_date = end_date;
    lock_details.serialize(&mut *lock_pda.data.borrow_mut())?;

    Ok(())
}

/// Генерирует случайный период блокировки на основе времени.
/// Это псевдослучайность, но для наших целей подходит.
fn generate_random_lock_period(timestamp: i64) -> i64 {
    let random_value = (timestamp % 100) as u8; // 0-99

    if random_value < 15 { // 15% шанс
        msg!("Lock period: 1 year");
        ONE_YEAR
    } else if random_value < 50 { // 35% шанс (15 + 35)
        msg!("Lock period: 2 years");
        TWO_YEARS
    } else { // 50% шанс
        msg!("Lock period: 3 years");
        THREE_YEARS
    }
} 