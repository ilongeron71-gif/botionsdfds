from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database import set_role, remove_role, list_roles
from permissions import require, get_level
from utils.logger import log_action

router = Router()
VALID = ("moderator", "admin", "owner")


@router.message(Command("setrole"))
async def cmd_setrole(message: Message):
    if not await require(message, 3):
        return
    args = message.text.split()
    if message.reply_to_message and message.reply_to_message.from_user:
        if len(args) < 2:
            return await message.reply("Использование: /setrole (reply) <role>")
        uid = message.reply_to_message.from_user.id
        role = args[1].lower()
    else:
        if len(args) < 3:
            return await message.reply("Использование: /setrole <id> <role>")
        try:
            uid = int(args[1])
        except ValueError:
            return await message.reply("ID должен быть числом.")
        role = args[2].lower()

    if role not in VALID:
        return await message.reply(f"Доступные роли: {', '.join(VALID)}")

    if role == "owner":
        lvl = await get_level(message.bot, message.chat.id, message.from_user.id)
        if lvl < 4:
            return await message.reply("Только владелец может назначать owner.")

    await set_role(uid, message.chat.id, role)
    await message.reply(f"✅ Пользователь <code>{uid}</code> → <b>{role}</b>", parse_mode="HTML")
    await log_action(message.bot, message.chat.id,
        f"⚙️ {message.from_user.full_name} назначил <code>{uid}</code> роль <b>{role}</b>")


@router.message(Command("delrole"))
async def cmd_delrole(message: Message):
    if not await require(message, 3):
        return
    if message.reply_to_message and message.reply_to_message.from_user:
        uid = message.reply_to_message.from_user.id
    else:
        args = message.text.split()
        if len(args) < 2 or not args[1].lstrip("-").isdigit():
            return await message.reply("Использование: /delrole (reply) или /delrole <id>")
        uid = int(args[1])
    await remove_role(uid, message.chat.id)
    await message.reply(f"✅ Роль с <code>{uid}</code> снята.", parse_mode="HTML")
    await log_action(message.bot, message.chat.id,
        f"⚙️ {message.from_user.full_name} снял роль с <code>{uid}</code>")


@router.message(Command("roles"))
async def cmd_roles(message: Message):
    rows = await list_roles(message.chat.id)
    if not rows:
        return await message.reply("Кастомных ролей нет.")
    lines = ["🎭 <b>Роли в чате:</b>"]
    for uid, role in rows:
        try:
            m = await message.bot.get_chat_member(message.chat.id, uid)
            name = m.user.full_name
        except Exception:
            name = str(uid)
        lines.append(f"• {name} — <b>{role}</b>")
    await message.reply("\n".join(lines), parse_mode="HTML")
