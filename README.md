<p align="center">
  <a href="https://t.me/OpenEvent_bot">
    <img src="https://img.shields.io/badge/Use%20Bot-Open%20Telegram-blue" alt="Use Bot">
  </a>
</p>

<h1 align="center">OpenEventBot</h1>

<p align="center">
  A Telegram bot for creating events in groups with RSVP support.<br>
  Group members can RSVP with a single tap — no more "I'm in" spam in the chat.
</p>

<p align="center">
  <img src="assets/demo_openevent.png" width="500" alt="Event Bot Screenshot">
</p>

## Features

- Create events with `/event <description>`
- Attach an image banner to events
- RSVP with inline buttons (Going / Can't go)
- Live attendee list updated in real time
- Admin-only event creation and deletion
- HTML formatting support in event descriptions
- SQLite-backed persistence
- Fully in English

## Setup

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- A Telegram bot token from [@BotFather](https://t.me/botfather)

### Local Development

1. Clone this repository.
2. Copy `.env.example` to `.env` and set your `BOT_TOKEN`:
   ```bash
   cp .env.example .env
   ```
3. Install dependencies and run:
   ```bash
   uv sync
   uv run openevent-bot
   ```

### Docker

```bash
cp .env.example .env
# Edit .env with your bot token
docker compose up -d
```

## Usage

### Adding to a group

1. Add the bot to your Telegram group.
2. Promote it to admin with **Delete Messages** permission (so it can replace `/event` messages).
3. Type `/event <description>` to create an event.

### Creating an event

```
/event Friday board game night at 7pm 🎲
```

Or attach a photo with the caption `/event <description>` to add an image banner.

Members then tap **Going** or **Can't go** to RSVP. The event message updates live with the attendee list.

### Commands

| Command | Description |
|---|---|
| `/start` | Introduction and help |
| `/help` | Show usage instructions |
| `/event <text>` | Create a new event (admins only) |

## Tech Stack

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- SQLite (stdlib)
- [uv](https://docs.astral.sh/uv/) for packaging
