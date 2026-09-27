from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database import set_log_channel
from permissions import require
from utils.logger import log_action
from backup import save_backup

router = Router()


@router.message(Command("setlog"))
async def cmd_setlog(message: Message):
    if not await require(message, 3):
        return
    args = message.text.split()
    if len(args) < 2:
        return await message.reply(
            "Использование: <code>/setlog -1001234567890</code>\n"
            "Добавьте бота админом в канал логов и скопируйте его ID.",
            parse_mode="HTML",
        )
    try:
        cid = int(args[1])
    except ValueError:
        return await message.reply("ID должен быть числом.")
    await set_log_channel(message.chat.id, cid)
    await message.reply("✅ Лог-канал установлен.")
    await log_action(message.bot, message.chat.id, "📝 Лог-канал подключён.")


@router.message(Command("unsetlog"))
async def cmd_unsetlog(message: Message):
    if not await require(message, 3):
        return
    await set_log_channel(message.chat.id, 0)
    await message.reply("✅ Лог-канал отключён.")


@router.message(Command("backup"))
async def cmd_backup(message: Message):
    if not await require(message, 3):
        return
    await message.reply("⏳ Сохраняю...")
    try:
        await save_backup(message.bot, force=True)
        await message.reply("✅ Бэкап сохранён.")
        await log_action(message.bot, message.chat.id,
            f"💾 Ручной бэкап от {message.from_user.full_name}")
    except Exception as e:
        await message.reply(f"❌ Ошибка: <code>{e}</code>", parse_mode="HTML")
