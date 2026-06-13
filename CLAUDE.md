# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in this repository.

## Project Overview

This is a **Telegram bot for selling VPN/V2ray subscriptions** (Persian/Iranian market). It is built with Python using the `python-telegram-bot` library (v22.8) with long-polling. The bot sells V2ray configs and Express VPN accounts, manages a wallet system, referral program, admin panel, and waiting queues.

## Running the Bot

```bash
source venv/bin/activate
python bot.py
```

There is no build step. The bot uses `application.run_polling()`.

## Dependencies

Managed via the `venv/` virtual environment (no `requirements.txt` or `pyproject.toml`):

- `python-telegram-bot` 22.8 — core bot framework
- `httpx` 0.28.1 — HTTP client (transitive dependency)

Install new packages with:
```bash
venv/bin/pip install <package>
```

## Architecture

Flat, monolithic structure — all code is at the repository root with no sub-packages:

| File | Purpose |
|---|---|
| `bot.py` | Entry point. Builds the `Application`, registers all `CommandHandler`, `CallbackQueryHandler`, and `ConversationHandler` instances, starts polling. |
| `config.py` | All configuration constants and in-memory state: bot token, admin ID, required channels, bank card numbers, plan prices, referral rewards, global discount, blacklist, conversation states, in-memory storage lists (`V2RAY_STORAGE_*`, `EXPRESS_CENTRAL_STORAGE`, `WAITING_QUEUE`). |
| `database.py` | JSON-file-based persistence layer (`database.json`). CRUD for users (balance, referral info), orders, and system data. No ORM. |
| `handlers.py` | All bot logic (~730 lines): user menus, purchase flow, wallet/receipt system, admin panel, broadcast, stock management, queue delivery, referral rewards. |

### Data Flow

1. `bot.py` registers handlers and starts the Telegram polling loop
2. `handlers.py` contains all callback/query/command handler functions
3. Handlers read/write persistent data via `database.py` (JSON file)
4. Handlers read/write in-memory state (stock, queues, blacklist, discount) directly from `config.py` module-level globals

### Key Design Notes

- **In-memory storage**: Stock (`V2RAY_STORAGE_20/70/100`, `EXPRESS_CENTRAL_STORAGE`), waiting queues (`WAITING_QUEUE`), blacklist (`BLACKLISTED_USERS`), and global discount are module-level globals in `config.py`. They are **not persisted** to `database.json` — restarting the bot loses all stock/queue data. The `save_all_storages()` function in `config.py` is a no-op stub.
- **Conversation states**: Defined in `config.py` as integer constants (`GET_AMOUNT`, `GET_RECEIPT`, `ADMIN_GET_USER`, etc.). Two `ConversationHandler` instances exist: one for wallet top-up and one for the admin panel.
- **Central callback router**: `handle_main_menu_callbacks` in `handlers.py` is the catch-all `CallbackQueryHandler` that routes all inline keyboard button presses to the appropriate handler function.
- **Channel lock**: Most user-facing handlers check `check_joined_channels()` before proceeding, requiring membership in all `REQUIRED_CHANNELS`.
- **Referral system**: Tracked via `referred_by`, `reward_claimed`, and `total_invited` fields in the user's database record. Rewards are granted when the referred user joins all required channels.
- **Waiting queue**: When stock is empty for a plan, the user is added to `WAITING_QUEUE[plan_id]`. The queue is automatically drained via `check_and_deliver_queue()` when admin adds stock.
- **`bot_database.db`** exists but is **unused** — all persistence goes through `database.json`.

## Code Conventions

- All user-facing text is in **Persian (Farsi)** with Markdown or HTML formatting
- Comments in the source code are in Persian
- Telegram user IDs are converted to strings for JSON keys (`str(user_id)`)
- Farsi digits are translated to ASCII digits using `str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')` before numeric parsing
- There are **no tests**, **no linter config**, and **no CI/CD**
