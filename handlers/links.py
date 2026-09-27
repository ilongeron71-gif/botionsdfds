
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database import set_chat_link, get_chat_link
from permissions import require

router = Router()


@router.message(Command("setlink"))
async def cmd_setlink(message: Message):
    if not await require(message, 3):
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply("Использование: /setlink <url>")
    await set_chat_link(message.chat.id, args[1])
    await message.reply("✅ Ссылка сохранена.")


@router.message(Command("link"))
async def cmd_link(message: Message):
    link = await get_chat_link(message.chat.id)
    if link:
        return await message.reply(f"🔗 {link}")
    try:
        chat = await message.bot.get_chat(message.chat.id)
        if chat.invite_link:
            return await message.reply(f"🔗 {chat.invite_link}")
    except Exception:
        pass
    await message.reply("Ссылка не задана. Админ: /setlink <url>")
