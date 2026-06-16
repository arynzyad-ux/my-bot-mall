# AGENTS.md — AI agent guidance

Short, actionable instructions for AI coding agents working in this repository.

## Quick summary
- Purpose: Telegram bot for selling VPN/V2ray subscriptions (Persian market).
- Run: `source venv/bin/activate` then `python bot.py`.
- No tests, no packaging; code is single-file-ish and monolithic.

## Key files
- [bot.py](bot.py) — application entry, registers handlers and starts polling.
- [handlers.py](handlers.py) — main bot logic (menus, purchases, admin flows).
- [config.py](config.py) — configuration constants and transient in-memory state.
- [database.py](database.py) — JSON-backed persistence (`database.json`).
- [CLAUDE.md](CLAUDE.md) — detailed human-oriented notes about architecture and pitfalls.

## Important conventions & pitfalls (brief)
- All user-facing strings are in Persian (Farsi). Keep translations/edits in Persian.
- Many runtime states (stock, queues, blacklist, global discount) are stored in module-level globals in `config.py` and are NOT persisted. Restarting the bot loses this data.
- Prefer editing `database.py` and `database.json` for persistent changes; be cautious when modifying `config.py` globals.
- There are no tests or CI; run manual checks and use the bot runtime to validate behavior.

## Guidance for AI agents
- Link, don't duplicate: refer to [CLAUDE.md](CLAUDE.md) for long-form notes.
- Make minimal, focused changes. Avoid sweeping refactors without the user's approval.
- Avoid committing secrets or tokens. If a `.env` or token is missing, ask the user.
- When adding dependencies, update a `requirements.txt` file and provide install instructions.
- For runtime validation, provide run steps and small reproducible examples.

## Suggested next customizations (ask the user before applying)
- Add `requirements.txt` to document dependencies and enable reproducible setup.
- Add simple unit tests for `database.py` and key `handlers.py` functions.
- Replace in-memory stocks with persisted storage, or document the intended operational behavior.

---

If you want, I can: create `requirements.txt`, add a small test for `database.py`, or convert these notes into `.github/copilot-instructions.md` instead.