# Discord Scraping Bot

A Discord bot that scrapes GitHub, Hacker News, HuggingFace, and Reddit, then categorizes content into 3 topics:
- **Bansos** (Free API/Tools)
- **Hot-Take** (Tech News/Drama)
- **Daily** (Dev Activity)

## Setup

### 1. Create `.env`
```
DISCORD_TOKEN=your_bot_token_here
```

### 2. Enable Intents
In Discord Developer Portal:
- Tab **Bot** → **Privileged Gateway Intents**
- Enable:
  - **Message Content Intent**
  - **Server Members Intent** (optional)

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Channels
Create these channels in your Discord server:
- `#bansos`
- `#hot-take`
- `#daily`

### 5. Invite Bot to Server
1. Developer Portal → **OAuth2** → **URL Generator**
2. Scopes: `bot`
3. Permissions:
   - Send Messages
   - Read Message History

### 6. Run
```bash
python bot.py
```

Auto-scrapes daily at 7 AM WITA (UTC+8). Manual trigger: `!scrape`

## Sources
| Source | Channel |
|---|---|
| GitHub trending | #daily |
| Hacker News | #hot-take |
| HuggingFace | #bansos |
| Reddit (opensource, selfhosted, freebies, webdev) | #bansos |
