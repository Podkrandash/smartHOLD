use solana_program::program_error::ProgramError;
use thiserror::Error;

#[derive(Error, Debug, Copy, Clone)]
pub enum TokenError {
    #[error("Account is already locked.")]
    AccountAlreadyLocked,
    #[error("Account is not locked.")]
    AccountNotLocked,
    #[error("Lockup period has not ended yet.")]
    LockupPeriodNotEnded,
    #[error("Invalid amount for operation.")]
    InvalidAmount,
}

impl From<TokenError> for ProgramError {
    fn from(e: TokenError) -> Self {
        ProgramError::Custom(e as u32)
    }
} 