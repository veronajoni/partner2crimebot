# bot.py
import os, logging
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, Update
from aiogram.filters import CommandStart
from openai import OpenAI

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "").rstrip("/")
PORT = int(os.environ.get("PORT", "8080"))

bot = Bot(TELEGRAM_TOKEN)
dp = Dispatcher()
client = OpenAI(api_key=OPENAI_API_KEY)

async def ask_gpt(prompt: str) -> str:
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content": prompt or "Say hi"}],
        )
        return resp.choices[0].message.content
    except Exception as e:
        logging.exception("OpenAI error")
        return "Oops, I had a brain freeze. Try again in a sec 🧊"

@dp.message(CommandStart())
async def on_start(m: Message):
    await m.answer("Hi 👋 I’m your Partner2Crime bot. Send me anything!")

@dp.message(F.text)
async def on_text(m: Message):
    reply = await ask_gpt(m.text)
    await m.answer(reply)

# --- aiohttp routes ---
async def health(request: web.Request):
    return web.Response(text="ok")

async def telegram_webhook(request: web.Request):
    try:
        data = await request.json()
        logging.info(f"Incoming update: {data}")
        update = Update.model_validate(data)
        await dp.feed_update(bot, update)
        # Always reply 200 quickly so Telegram doesn't retry
        return web.Response(text="ok")
    except Exception:
        logging.exception("Webhook handler error")
        # Still return 200 to prevent Telegram retries storm
        return web.Response(text="ok")

async def set_webhook():
    await bot.delete_webhook(drop_pending_updates=True)
    if WEBHOOK_URL:
        url = f"{WEBHOOK_URL}/webhook"
        await bot.set_webhook(url=url)
        logging.info(f"Webhook set to: {url}")
    else:
        logging.warning("WEBHOOK_URL not set; Telegram won't deliver updates.")

def make_app():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_post("/webhook", telegram_webhook)
    app.on_startup.append(lambda app: set_webhook())
    app.on_cleanup.append(lambda app: bot.session.close())
    return app

if __name__ == "__main__":
    web.run_app(make_app(), host="0.0.0.0", port=PORT)


