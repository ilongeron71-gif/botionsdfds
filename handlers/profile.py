from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database import get_user, set_title, set_position, get_role
from permissions import require

router = Router()


def fmt_joined(iso: str) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return "—"
    delta = datetime.utcnow() - dt
    d = delta.days
    hours = delta.seconds // 3600
    if d > 0:
        return f"{d} д. {hours} ч."
    return f"{hours} ч."


@router.message(Command("profile", "me", "профиль"))
async def cmd_profile(message: Message):
    target = (
        message.reply_to_message.from_user
        if message.reply_to_message and message.reply_to_message.from_user
        else message.from_user
    )
    row = await get_user(target.id, message.chat.id)
    if not row:
        return await message.reply("Пользователь не найден в базе чата.")
    _, username, title, position, messages, joined_at, warns, limit = row

    role = await get_role(target.id, message.chat.id) or "—"
    if role == "moderator":
        role = "🛡 Модератор"
    elif role == "admin":
        role = "⚙️ Админ"
    elif role == "owner":
        role = "👑 Владелец"

    text = (
        f"👤 <b>{target.full_name}</b>\n"
        f"🆔 <code>{target.id}</code>\n"
        f"🏷 Юзернейм: @{username or '—'}\n"
        f"🎖 Титул: {title or '—'}\n"
        f"💼 Должность: {position or '—'}\n"
        f"🎭 Роль: {role}\n"
        f"💬 Сообщений: <b>{messages}</b>\n"
        f"⏱ В чате: {fmt_joined(joined_at)}\n"
        f"⚠️ Варнов: {warns}/{limit}"
    )
    await message.reply(text, parse_mode="HTML")


@router.message(Command("title"))
async def cmd_title(message: Message):
    if not await require(message, 2):
        return
    if not message.reply_to_message or not message.reply_to_message.from_user:
        return await message.reply("Ответьте на сообщение пользователя.")
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply("Использование: /title <текст>")
    await set_title(message.reply_to_message.from_user.id, message.chat.id, args[1])
    await message.reply("✅ Титул обновлён.")


@router.message(Command("position"))
async def cmd_position(message: Message):
    if not await require(message, 2):
        return
    if not message.reply_to_message or not message.reply_to_message.from_user:
        return await message.reply("Ответьте на сообщение пользователя.")
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply("Использование: /position <текст>")
    await set_position(message.reply_to_message.from_user.id, message.chat.id, args[1])
    await message.reply("✅ Должность обновлена.")