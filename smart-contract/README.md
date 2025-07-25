# Summit Digital Crypto Bank Token (SDCB)

Смарт-контракт токена SDCB для блокчейна Solana с поддержкой автоматической блокировки, стейкинга и начисления наград.

## Основные возможности
- Автоматическая блокировка токенов на случайный срок (1–3 года)
- Ежедневное начисление 0.1% от заблокированной суммы
- Получение наград и автоматическая разблокировка по истечении срока

## Технические параметры
- Общее количество токенов: 10,000,000,000 SDCB
- Распределение: 20% — основатель, 80% — DEX

## Сборка и деплой

1. Установите Rust и Solana CLI:
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
sh -c "$(curl -sSfL https://release.solana.com/v1.17.0/install)"
```

2. Соберите контракт:
```bash
cargo build-sbf
```

3. Запустите локальный валидатор:
```bash
solana-test-validator
```

4. Деплой программы:
```bash
solana program deploy target/deploy/sdcb_token.so
```

## Работа с токеном

- Создание токена:
```bash
spl-token create-token
```
- Создание аккаунта для токенов:
```bash
spl-token create-account <TOKEN_ADDRESS>
```
- Минтинг токенов:
```bash
spl-token mint <TOKEN_ADDRESS> <AMOUNT> <ACCOUNT_ADDRESS>
```

## Проверка баланса и состояния

- Проверка баланса токенов:
```bash
spl-token balance <TOKEN_ADDRESS>
```
- Проверка состояния программы:
```bash
solana program show <PROGRAM_ID>
```

## Вызов функций смарт-контракта

Для взаимодействия с программой используйте кастомные скрипты или Anchor/JS-интерфейс для отправки инструкций (Initialize, LockTokens, ClaimRewards, UnlockTokens, MintOwnerTokens).

## Лицензия
MIT 