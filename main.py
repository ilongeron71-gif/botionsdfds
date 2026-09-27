import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

from config import BOT_TOKEN
from database import init_db
from handlers import (
    moderation,
    profile,
    call,
    links,
    help as help_h,
    roles,
    logs_cmd,
    game,
    rp,
    watchdog,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "👋 Бот запущен.\nСписок команд: /help\nВаши права: /myrights"
    )


async def main():
    await init_db()

    # 1) Команды (все конкретные хендлеры)
    dp.include_router(moderation.router)
    dp.include_router(profile.router)
    dp.include_router(call.router)
    dp.include_router(links.router)
    dp.include_router(roles.router)
    dp.include_router(logs_cmd.router)
    dp.include_router(help_h.router)
    dp.include_router(game.router)

    # 2) РП-триггеры (свободный текст), с SkipHandler для не-РП
    dp.include_router(rp.router)

    # 3) Счётчик + анти-спам (ловит всё остальное)
    dp.include_router(watchdog.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())