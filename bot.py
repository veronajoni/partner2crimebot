# bot.py — hardened webhook server for Railway (aiogram 3 + aiohttp + OpenAI v1)
import os, logging
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, Update
from aiogram.filters import CommandStart
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("p2c")

# --- Env (do NOT crash if missing; log instead) ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL    = (os.getenv("WEBHOOK_URL") or "").rstrip("/")
PORT           = int(os.getenv("PORT", "8080"))

def mask(s: str, keep=4):
    if not s:
        return "MISSING"
    return s[:keep] + "…" if len(s) > keep else "****"

log.info(f"ENV -> TELEGRAM_TOKEN={mask(TELEGRAM_TOKEN)}  "
         f"OPENAI_API_KEY={mask(OPENAI_API_KEY)}  "
         f"WEBHOOK_URL={WEBHOOK_URL or 'MISSING'}  PORT={PORT}")

# If Telegram token is missing, create a dummy bot to keep server up
bot = Bot(TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None
dp = Dispatcher()

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

async def ask_gpt(prompt: str) -> str:
    if not client:
        log.error("OPENAI_API_KEY missing")
        return "Server missing OPENAI key. Please try again later."
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt or "Say hi"}],
        )
        return resp.choices[0].message.content
    except Exception:
        log.exception("OpenAI error")
        return "Oops, brain freeze 🧊 Try again in a sec."

@dp.message(CommandStart())
async def on_start(m: Message):
    await m.answer("Hi 👋 I’m your Partner2Crime bot. Send me anything!")

@dp.message(F.text)
async def on_text(m: Message):
    reply = await ask_gpt(m.text)
    await m.answer(reply)

# --- aiohttp routes ---
async def health(_: web.Request):
    return web.Response(text="ok")

async def envinfo(_: web.Request):
    # quick introspection
    body = (f"token={mask(TELEGRAM_TOKEN)}\n"
            f"openai={mask(OPENAI_API_KEY)}\n"
            f"webhook_url={WEBHOOK_URL or 'MISSING'}\n"
            f"port={PORT}\n")
    return web.Response(text=body)

async def telegram_webhook(request: web.Request):
    # Always 200 so Telegram doesn’t retry with 502
    try:
        data = await request.json()
        log.info(f"Incoming update: {data}")
        if not bot:
            log.error("TELEGRAM_TOKEN missing; cannot feed update")
            return web.Response(text="ok")
        update = Update.model_validate(data)
        await dp.feed_update(bot, update)
        return web.Response(text="ok")
    except Exception:
        log.exception("Webhook handler error")
        return web.Response(text="ok")

async def set_webhook():
    if not bot:
        log.error("TELEGRAM_TOKEN missing; skip set_webhook")
        return
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        if WEBHOOK_URL:
            url = f"{WEBHOOK_URL}/webhook"
            await bot.set_webhook(url=url)
            log.info(f"Webhook set to: {url}")
        else:
            log.warning("WEBHOOK_URL not set; Telegram will not deliver updates.")
    except Exception:
        log.exception("Failed to set webhook")

def make_app():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/env", envinfo)
    app.router.add_post("/webhook", telegram_webhook)
    app.on_startup.append(lambda app: set_webhook())
    app.on_cleanup.append(lambda app: bot and bot.session.close())
    return app

if __name__ == "__main__":
    web.run_app(make_app(), host="0.0.0.0", port=PORT)
