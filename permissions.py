from config import OWNER_IDS
from database import get_role

LEVELS = {"user": 1, "moderator": 2, "admin": 3, "owner": 4}
NAMES = {1: "👤 Участник", 2: "🛡 Модератор", 3: "⚙️ Админ", 4: "👑 Владелец"}


async def get_level(bot, chat_id, user_id) -> int:
    if user_id in OWNER_IDS:
        return 4
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        if member.status == "creator":
            return 4
        if member.status == "administrator":
            r = await get_role(user_id, chat_id)
            if r == "owner":
                return 4
            return 3
    except Exception:
        pass
    r = await get_role(user_id, chat_id)
    return LEVELS.get(r, 1)


async def require(message, level: int) -> bool:
    lvl = await get_level(message.bot, message.chat.id, message.from_user.id)
    if lvl >= level:
        return True
    await message.reply(f"🚫 Недостаточно прав. Требуется уровень: {NAMES[level]}.")
    return False
