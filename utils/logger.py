from config import OWNER_IDS
from database import get_log_channel


async def log_action(bot, chat_id, text: str):
    """Логи идут в лог-канал чата (если настроен) + в ЛС всем владельцам."""
    log_chat = await get_log_channel(chat_id)
    if log_chat:
        try:
            await bot.send_message(log_chat, text, parse_mode="HTML")
        except Exception:
            pass

    for owner_id in OWNER_IDS:
        try:
            await bot.send_message(owner_id, text, parse_mode="HTML")
        except Exception:
            pass
