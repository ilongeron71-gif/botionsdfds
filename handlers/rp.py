import re

from aiogram import Router, F
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command
from aiogram.types import Message

from database import add_rp, del_rp, get_rp, list_all_rp
from permissions import get_level

router = Router()

RESERVED = {
    "start", "help", "ban", "unban", "mute", "unmute", "warn", "unwarn",
    "setwarnlimit", "profile", "me", "title", "position", "call", "link",
    "setlink", "setrole", "delrole", "roles", "setlog", "unsetlog",
    "addrp", "delrp", "rps", "game", "stopgame", "mystats", "topgame",
    "myrights", "backup", "помощь", "профиль", "созыв", "игра",
}

TRIGGER_RE = re.compile(r"^/?([a-zA-Zа-яА-Я0-9_]{2,30})(\s|$)", re.UNICODE)


@router.message(Command("addrp"))
async def cmd_addrp(message: Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return await message.reply(
            "📝 Использование: <code>/addrp &lt;триггер&gt; &lt;текст&gt;</code>\n"
            "Доступно: <code>{user}</code> — вы, <code>{target}</code> — цель (reply)\n\n"
            "<b>Пример:</b>\n<code>/addrp обнять {user} обнял(а) {target} 🤗</code>",
            parse_mode="HTML",
        )
    trigger = args[1].lower().lstrip("/")
    text = args[2]
    if trigger in RESERVED:
        return await message.reply("❌ Триггер занят системной командой.")
    if not re.fullmatch(r"[a-zA-Zа-яА-Я0-9_]{2,30}", trigger):
        return await message.reply("❌ Триггер: буквы, цифры, _ (2–30 символов).")
    await add_rp(message.chat.id, trigger, text, message.from_user.id)
    await message.reply(f"✅ РП-команда <code>/{trigger}</code> добавлена.", parse_mode="HTML")


@router.message(Command("delrp"))
async def cmd_delrp(message: Message):
    args = message.text.split()
    if len(args) < 2:
        return await message.reply("Использование: /delrp <триггер>")
    trigger = args[1].lower().lstrip("/")
    is_admin = await get_level(message.bot, message.chat.id, message.from_user.id) >= 3
    ok = await del_rp(message.chat.id, trigger, message.from_user.id, is_admin)
    await message.reply("✅ Удалено." if ok else "❌ Не найдено или нет прав.")


@router.message(Command("rps"))
async def cmd_rps(message: Message):
    rows = await list_all_rp(message.chat.id)
    if not rows:
        return await message.reply("РП-команд нет. Создать: /addrp")
    lines = ["🎭 <b>РП-команды:</b>"]
    for trigger, _, _ in rows:
        lines.append(f"• <code>/{trigger}</code>")
    await message.reply("\n".join(lines), parse_mode="HTML")


@router.message(F.text.regexp(TRIGGER_RE))
async def rp_trigger(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        raise SkipHandler
    if not message.text:
        raise SkipHandler

    text = message.text.strip()
    m = TRIGGER_RE.match(text)
    if not m:
        raise SkipHandler
    trigger = m.group(1).lower()

    rp = await get_rp(message.chat.id, trigger)
    if not rp:
        raise SkipHandler

    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply("↩️ Ответьте на сообщение, к кому применить.")
        return

    user = message.from_user.first_name or "кто-то"
    target = message.reply_to_message.from_user.first_name or "кого-то"
    result = rp.replace("{user}", user).replace("{target}", target)
    await message.reply(result)
