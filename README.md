# Discord Scraping Bot

Bot Discord yang scrape GitHub, Hacker News, HuggingFace, dan Reddit, terus kategorikan jadi 3 topik:
- **Bansos** (Free API/Tools)
- **Hot-Take** (Tech News/Drama)
- **Daily** (Dev Activity)

## Setup

### 1. Buat `.env`
```
DISCORD_TOKEN=token_bot_lu_disini
```

### 2. Enable Intents
Di Discord Developer Portal:
- Tab **Bot** → **Privileged Gateway Intents**
- Enable:
  - **Message Content Intent**
  - **Server Members Intent** (optional)

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Channels
Buat channels ini di Discord server lu:
- `#bansos`
- `#hot-take`
- `#daily`

### 5. Invite Bot ke Server
1. Developer Portal → **OAuth2** → **URL Generator**
2. Scopes: `bot`
3. Permissions:
   - Send Messages
   - Read Message History

### 6. Run
```bash
python bot.py
```

Bot auto-scrape tiap hari jam 7 pagi WITA. Manual trigger: `!scrape`

## Sources
| Source | Channel |
|---|---|
| GitHub trending | #daily |
| Hacker News | #hot-take |
| HuggingFace | #bansos |
| Reddit (opensource, selfhosted, freebies, webdev) | #bansos |
