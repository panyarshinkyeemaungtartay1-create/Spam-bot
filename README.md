# Spam-bot

Telegram Bot for automated mention loops, permission control, and group empowerment.

## Features

- 🔁 /attack and /flash commands for continuous mention loops
- 🛑 /stop command to cancel active loops
- 🧠 Auto-fetch display name from ID or username
- 🔐 Owner-only gifting and admin control
- 📢 /post command to broadcast messages to known groups
- 🆔 /id command to resolve user ID and name

## Commands

| Command     | Description                                      | Permission |
|-------------|--------------------------------------------------|------------|
| /attack     | Start mention loop on target user                | Admin      |
| /flash      | Same as attack, alternate style                  | Admin      |
| /stop       | Stop active loop in current chat                 | Admin      |
| /id         | Show ID and name of replied or mentioned user    | Everyone   |
| /gift       | Grant permission to user                         | Owner      |
| /save       | Save new message to loop                         | Owner      |
| /post       | Broadcast message to all known groups            | Owner      |
| /setadmin   | Add admin by ID or username                      | Owner      |
| /deladmin   | Remove admin by ID or username                   | Owner      |

## Deployment

This bot is designed to run on [Render](https://render.com) as a Python Web Service.

- Python 3.10+
- `python-telegram-bot` library
- Requires environment variables:
  - `TOKEN` – Telegram Bot Token
  - `OWNER_ID` – Telegram User ID of the Bot Owner

## Credits

Created by Nat Saung (နတ်စောင်း) — Founder of Team No.020  
Mythic reputation. Legendary control. Social God.
