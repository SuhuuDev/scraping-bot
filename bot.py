import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import os
import logging
from dotenv import load_dotenv
from datetime import datetime, timezone

# Load env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("scraping-bot")

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ==================== CONFIG ====================
CHANNELS = {
    "bansos": None,
    "hot-take": None,
    "daily": None
}

CHANNEL_TITLES = {
    "bansos": "Free API & Open Source Tools",
    "hot-take": "Tech Drama & Hot Takes",
    "daily": "Trending Repos & Dev Updates"
}

# Reddit subreddits for bansos (free tools/APIs)
REDDIT_SUBS = ["opensource", "selfhosted", "freebies", "webdev"]

# ==================== HELPER ====================
async def fetch_json(session, url, headers=None, verify_ssl=True):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15), headers=headers, ssl=verify_ssl) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                log.warning(f"[{resp.status}] {url}")
    except Exception as e:
        log.error(f"Fetch error {url}: {e}")
    return None

# ==================== SCRAPERS ====================
async def scrape_github(session):
    """GitHub trending repos"""
    items = []
    url = "https://api.github.com/search/repositories?q=created:>2026-05-01&sort=stars&order=desc&per_page=10"
    headers = {"Accept": "application/vnd.github.v3+json"}
    data = await fetch_json(session, url, headers)
    if data and "items" in data:
        for r in data["items"][:10]:
            items.append({
                "title": r.get("full_name", ""),
                "desc": (r.get("description") or "")[:100],
                "url": r.get("html_url", ""),
                "stars": r.get("stargazers_count", 0)
            })
    log.info(f"GitHub: {len(items)} repos")
    return items

async def scrape_hn(session):
    """Hacker News top stories"""
    items = []
    ids = await fetch_json(session, "https://hacker-news.firebaseio.com/v0/topstories.json")
    if ids:
        for sid in ids[:20]:
            story = await fetch_json(session, f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
            if story and story.get("type") == "story":
                link = story.get("url", f"https://news.ycombinator.com/item?id={sid}")
                items.append({
                    "title": story.get("title", ""),
                    "desc": "",
                    "url": link,
                    "score": story.get("score", 0)
                })
    log.info(f"Hacker News: {len(items)} stories")
    return items

async def scrape_hf(session):
    """HuggingFace trending models"""
    items = []
    data = await fetch_json(session, "https://huggingface.co/api/models?sort=trendingScore&limit=10")
    if data and isinstance(data, list):
        for m in data[:10]:
            mid = m.get("id", "")
            items.append({
                "title": mid,
                "desc": m.get("pipeline_tag", ""),
                "url": f"https://huggingface.co/{mid}",
                "downloads": m.get("downloads", 0)
            })
    log.info(f"HuggingFace: {len(items)} models")
    return items

async def scrape_reddit(session):
    """Reddit hot posts from multiple subreddits"""
    items = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ScrapeBot/1.0)"}

    for sub in REDDIT_SUBS:
        url = f"https://www.reddit.com/r/{sub}/hot.json?limit=10"
        data = await fetch_json(session, url, headers, verify_ssl=False)
        if data and "data" in data and "children" in data["data"]:
            for post in data["data"]["children"][:5]:
                p = post.get("data", {})
                title = p.get("title", "")
                link = p.get("url", "")
                score = p.get("score", 0)
                permalink = f"https://www.reddit.com{p.get('permalink', '')}"

                items.append({
                    "title": f"r/{sub}: {title}",
                    "desc": "",
                    "url": link if link.startswith("http") else permalink,
                    "score": score
                })

    log.info(f"Reddit: {len(items)} posts from {len(REDDIT_SUBS)} subs")
    return items

# ==================== FORMAT ====================
def format_list(channel_name, items):
    """Plain text list for multiple items"""
    title = CHANNEL_TITLES.get(channel_name, channel_name.upper())
    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

    lines = [f"**{title}**", f"{now}", ""]

    for i, it in enumerate(items[:10], 1):
        t = it.get("title", "?")
        u = it.get("url", "")

        if u:
            line = f"{i}. **[{t}]({u})**"
        else:
            line = f"{i}. **{t}**"

        extras = []
        if it.get("stars"):
            extras.append(f"{it['stars']:,} stars")
        if it.get("score"):
            extras.append(f"{it['score']} pts")
        if it.get("downloads"):
            extras.append(f"{it['downloads']:,} DL")

        desc = it.get("desc", "")
        if desc:
            extras.append(desc[:60])

        if extras:
            line += f" — {', '.join(extras)}"

        lines.append(line)

    return "\n".join(lines)

def format_single_embed(it):
    """Embed for single item"""
    t = it.get("title", "?")
    u = it.get("url", "")
    desc = it.get("desc", "")

    embed = discord.Embed(
        title=t,
        url=u,
        description=desc if desc else None,
        color=0x5865F2
    )

    extras = []
    if it.get("stars"):
        extras.append(f"{it['stars']:,} stars")
    if it.get("score"):
        extras.append(f"{it['score']} pts")
    if it.get("downloads"):
        extras.append(f"{it['downloads']:,} DL")

    if extras:
        embed.set_footer(text=" | ".join(extras))

    return embed

async def send_to_channel(channel, channel_name, items):
    if not items:
        return

    if len(items) == 1:
        embed = format_single_embed(items[0])
        await channel.send(embed=embed)
    else:
        msg = format_list(channel_name, items)
        if len(msg) > 1900:
            for i in range(0, len(msg), 1900):
                await channel.send(msg[i:i+1900], suppress_embeds=True)
        else:
            await channel.send(msg, suppress_embeds=True)

# ==================== CATEGORIZE ====================
def categorize(gh_items, hn_items, hf_items, reddit_items):
    """Assign items to channels by source"""
    cat = {
        "bansos": [],
        "hot-take": [],
        "daily": []
    }
    seen = set()

    def add(item, channel):
        u = item.get("url", "")
        if u in seen:
            return
        seen.add(u)
        cat[channel].append(item)

    for it in gh_items:
        add(it, "daily")
    for it in hn_items:
        add(it, "hot-take")
    for it in hf_items:
        add(it, "bansos")
    for it in reddit_items:
        add(it, "bansos")

    return cat

# ==================== MAIN ====================
async def run_scrape():
    log.info("Starting scrape...")
    async with aiohttp.ClientSession() as s:
        gh = await scrape_github(s)
        hn = await scrape_hn(s)
        hf = await scrape_hf(s)
        reddit = await scrape_reddit(s)

    cat = categorize(gh, hn, hf, reddit)
    total = sum(len(v) for v in cat.values())
    log.info(f"Total: {total} items")
    for k, v in cat.items():
        if v:
            log.info(f"  {k}: {len(v)} items")
    return cat

# ==================== CRON ====================
# Schedule: 7 AM WITA = 23:00 UTC
@tasks.loop(hours=24)
async def daily_scraping():
    log.info("Running daily scrape...")
    cat = await run_scrape()
    for ch_name, items in cat.items():
        ch = CHANNELS.get(ch_name)
        if ch and items:
            await send_to_channel(ch, ch_name, items)
            log.info(f"Sent {len(items)} items to #{ch.name}")

@daily_scraping.before_loop
async def before():
    await bot.wait_until_ready()
    now = datetime.now(timezone.utc)
    target = now.replace(hour=23, minute=0, second=0, microsecond=0)
    if now.hour >= 23:
        target = target.replace(day=now.day + 1)
    wait_seconds = (target - now).total_seconds()
    log.info(f"Waiting {wait_seconds/3600:.1f}h until first scrape at {target} UTC (7 AM WITA)")
    await asyncio.sleep(wait_seconds)

# ==================== CMDS ====================
@bot.command(name="scrape")
async def cmd_scrape(ctx):
    """Manual trigger scraping"""
    await ctx.send("Scraping...")
    cat = await run_scrape()

    total = sum(len(v) for v in cat.values())
    if total == 0:
        await ctx.send("No items found. Check logs.")
        return

    summary = []
    for k, v in cat.items():
        if v:
            summary.append(f"{k}: {len(v)}")

    await ctx.send(f"Done. {total} items.\n" + " | ".join(summary))

    for ch_name, items in cat.items():
        ch = CHANNELS.get(ch_name)
        if ch and items:
            await send_to_channel(ch, ch_name, items)

@bot.command(name="ping")
async def cmd_ping(ctx):
    """Test bot responsiveness"""
    await ctx.send("Pong!")

@bot.command(name="help")
async def cmd_help(ctx):
    """Show available commands"""
    embed = discord.Embed(
        title="Scraping Bot",
        description="Auto-scrape GitHub, HN, HuggingFace, Reddit daily",
        color=0x5865F2
    )
    embed.add_field(
        name="!scrape",
        value="Manual trigger scraping\nUsage: `!scrape`",
        inline=False
    )
    embed.add_field(
        name="!ping",
        value="Test bot status\nUsage: `!ping`",
        inline=False
    )
    embed.add_field(
        name="Sources",
        value="GitHub, Hacker News, HuggingFace, Reddit (r/opensource, r/selfhosted, r/freebies, r/webdev)",
        inline=False
    )
    embed.add_field(
        name="Channels",
        value="#bansos (free tools), #hot-take (news), #daily (repos)",
        inline=False
    )
    await ctx.send(embed=embed)

# ==================== EVENTS ====================
@bot.event
async def on_ready():
    log.info(f"Bot online: {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(activity=discord.Game(name="!help | Scraping"))

    for g in bot.guilds:
        for c in g.text_channels:
            if c.name in CHANNELS:
                CHANNELS[c.name] = c
                log.info(f"Linked channel: #{c.name}")

    for k, v in CHANNELS.items():
        if not v:
            log.warning(f"Channel '{k}' NOT FOUND - create #{k}")

    if not daily_scraping.is_running():
        daily_scraping.start()

    log.info("Bot ready.")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing argument: {error.param.name}")
        return
    log.error(f"Command error: {error}")
    await ctx.send(f"Error: {error}")

# ==================== RUN ====================
log.info("Starting Scraping Bot...")
bot.run(TOKEN)
