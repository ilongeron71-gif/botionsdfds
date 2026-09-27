from datetime import datetime, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ChatPermissions
from aiogram.exceptions import TelegramBadRequest

from database import (
    add_warn, reset_warns, set_warn_limit, get_warn_limit,
    ensure_user, ensure_chat,
)
from permissions import require
from utils.logger import log_action

router = Router()

MUTE_PERMS = ChatPermissions(can_send_messages=False)
UNMUTE_PERMS = ChatPermissions(
    can_send_messages=True,
    can_send_media_messages=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
)


def parse_time(s: str) -> int:
    if not s:
        return 0
    unit = s[-1]
    try:
        n = int(s[:-1])
    except ValueError:
        return 0
    return n * {"s": 1, "m": 60, "h": 3600, "d": 86400}.get(unit, 0)


def get_target(message: Message):
    args = message.text.split()[1:]
    if message.reply_to_message and message.reply_to_message.from_user:
        user = message.reply_to_message.from_user
        reason = " ".join(args) if args else "не указана"
        return user.id, user.full_name, reason, None
    if not args:
        return None, None, None, None
    try:
        uid = int(args[0])
    except ValueError:
        return None, None, None, None
    time_str = args[1] if len(args) > 1 else None
    reason = " ".join(args[2:]) if len(args) > 2 else "не указана"
    return uid, str(uid), reason, time_str


@router.message(Command("ban"))
async def cmd_ban(message: Message):
    if not await require(message, 2):
        return
    uid, name, reason, time_str = get_target(message)
    if not uid:
        return await message.reply("Использование: /ban <id|reply> [10m|2h|1d] [причина]")
    until = None
    if time_str:
        sec = parse_time(time_str)
        if sec:
            until = datetime.now() + timedelta(seconds=sec)
    try:
        await message.chat.ban(user_id=uid, until_date=until)
        await message.reply(f"🔨 {name} забанен.\nПричина: {reason}")
        await log_action(message.bot, message.chat.id,
            f"🔨 <b>Бан</b>\nМодератор: {message.from_user.full_name}\n"
            f"Цель: <code>{uid}</code>\nСрок: {time_str or 'навсегда'}\nПричина: {reason}")
    except TelegramBadRequest as e:
        await message.reply(f"Ошибка: {e}")


@router.message(Command("unban"))
async def cmd_unban(message: Message):
    if not await require(message, 2):
        return
    uid, name, _, _ = get_target(message)
    if not uid:
        return await message.reply("Использование: /unban <id|reply>")
    try:
        await message.chat.unban(uid)
        await message.reply(f"✅ {name} разбанен.")
        await log_action(message.bot, message.chat.id,
            f"✅ <b>Разбан</b>\nМодератор: {message.from_user.full_name}\nЦель: <code>{uid}</code>")
    except TelegramBadRequest as e:
        await message.reply(f"Ошибка: {e}")


@router.message(Command("mute"))
async def cmd_mute(message: Message):
    if not await require(message, 2):
        return
    uid, name, reason, time_str = get_target(message)
    if not uid:
        return await message.reply("Использование: /mute <id|reply> [10m|2h|1d] [причина]")
    until = None
    if time_str:
        sec = parse_time(time_str)
        if sec:
            until = datetime.now() + timedelta(seconds=sec)
    try:
        await message.chat.restrict(user_id=uid, permissions=MUTE_PERMS, until_date=until)
        dur = f"на {time_str}" if time_str else "навсегда"
        await message.reply(f"🔇 {name} замучен {dur}.\nПричина: {reason}")
        await log_action(message.bot, message.chat.id,
            f"🔇 <b>Мут</b>\nМодератор: {message.from_user.full_name}\n"
            f"Цель: <code>{uid}</code>\nСрок: {dur}\nПричина: {reason}")
    except TelegramBadRequest as e:
        await message.reply(f"Ошибка: {e}")


@router.message(Command("unmute"))
async def cmd_unmute(message: Message):
    if not await require(message, 2):
        return
    uid, name, _, _ = get_target(message)
    if not uid:
        return await message.reply("Использование: /unmute <id|reply>")
    try:
        await message.chat.restrict(user_id=uid, permissions=UNMUTE_PERMS)
        await message.reply(f"🔊 {name} размучен.")
        await log_action(message.bot, message.chat.id,
            f"🔊 <b>Размут</b>\nМодератор: {message.from_user.full_name}\nЦель: <code>{uid}</code>")
    except TelegramBadRequest as e:
        await message.reply(f"Ошибка: {e}")


@router.message(Command("warn"))
async def cmd_warn(message: Message):
    if not await require(message, 2):
        return
    uid, name, reason, _ = get_target(message)
    if not uid:
        return await message.reply("Использование: /warn <id|reply> [причина]")
    await ensure_chat(message.chat.id)
    await ensure_user(uid, message.chat.id)
    warns = await add_warn(uid, message.chat.id)
    limit = await get_warn_limit(message.chat.id)
    await message.reply(f"⚠️ {name} получил предупреждение ({warns}/{limit}).\nПричина: {reason}")
    await log_action(message.bot, message.chat.id,
        f"⚠️ <b>Варн</b> ({warns}/{limit})\nМодератор: {message.from_user.full_name}\n"
        f"Цель: <code>{uid}</code>\nПричина: {reason}")
    if warns >= limit:
        try:
            await message.chat.ban(uid)
            await message.reply(f"🚫 {name} достиг лимита варнов и был забанен.")
            await log_action(message.bot, message.chat.id,
                f"🚫 <b>Автобан по варнам</b>\nЦель: <code>{uid}</code>")
        except TelegramBadRequest:
            pass


@router.message(Command("unwarn"))
async def cmd_unwarn(message: Message):
    if not await require(message, 2):
        return
    uid, name, _, _ = get_target(message)
    if not uid:
        return await message.reply("Использование: /unwarn <id|reply>")
    await reset_warns(uid, message.chat.id)
    await message.reply(f"✅ Варны {name} сброшены.")
    await log_action(message.bot, message.chat.id,
        f"✅ <b>Сброс варнов</b>\nЦель: <code>{uid}</code>")


@router.message(Command("setwarnlimit"))
async def cmd_setwarnlimit(message: Message):
    if not await require(message, 3):
        return
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.reply("Использование: /setwarnlimit <число>")
    await set_warn_limit(message.chat.id, int(args[1]))
    await message.reply(f"✅ Лимит варнов: {args[1]}")
