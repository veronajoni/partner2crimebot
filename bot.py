import asyncio, os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
import openai

# Tokens from environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(TELEGRAM_TOKEN)
dp = Dispatcher()
openai.api_key = OPENAI_API_KEY

async def ask_gpt(prompt: str) -> str:
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",  # can also use "gpt-4o"
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.choices[0].message["content"]

@dp.message(CommandStart())
async def start(m: types.Message):
    await m.answer("Hi 👋 I’m your Partner2Crime bot. Send me anything!")

@dp.message()
async def handle(m: types.Message):
    reply = await ask_gpt(m.text)
    await m.answer(reply)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


