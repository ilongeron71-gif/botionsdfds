import aiosqlite

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database import DB_PATH

router = Router()


@router.message(Command("call", "созыв"))
async def cmd_call(message: Message):
    args = message.text.split(maxsplit=1)
    reason = args[1] if len(args) > 1 else "общий сбор"

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM users WHERE chat_id=? AND messages > 0 "
            "ORDER BY messages DESC LIMIT 30",
            (message.chat.id,),
        ) as cur:
            rows = await cur.fetchall()

    if not rows:
        return await message.reply("📣 Пока некого звать — база пуста.")

    mentions = " ".join(f'<a href="tg://user?id={r[0]}">\u200b</a>' for r in rows)
    await message.answer(
        f"📣 <b>СОЗЫВ!</b>\n"
        f"Инициатор: {message.from_user.mention_html()}\n"
        f"Причина: {reason}\n\n"
        f"{mentions}",
        parse_mode="HTML",
    )
