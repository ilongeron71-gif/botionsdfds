from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from permissions import get_level, NAMES

router = Router()

HELP = """📚 <b>Доступные команды</b>

🛡 <b>Модерация</b> <i>(модератор+)</i>
• /ban &lt;id|reply&gt; [10m|2h|1d] [причина]
• /unban &lt;id|reply&gt;
• /mute &lt;id|reply&gt; [время] [причина]
• /unmute &lt;id|reply&gt;
• /warn &lt;id|reply&gt; [причина] — при лимите автобан
• /unwarn &lt;id|reply&gt;
• /setwarnlimit &lt;n&gt; <i>(админ+)</i>
• /title &lt;текст&gt; [reply]
• /position &lt;текст&gt; [reply]

👤 <b>Профиль</b>
• /profile (/me) [reply] — титул, должность, активность

🎭 <b>РП-команды</b>
• /addrp &lt;триггер&gt; &lt;текст&gt;
• /delrp &lt;триггер&gt;
• /rps — список
• Использование: <code>/имя_триггера</code> (reply)

🎮 <b>Игра</b>
• /game — новая игра (поле 9×9)
• /stopgame — завершить
• /mystats — статистика
• /topgame — топ игроков

📢 <b>Общее</b>
• /call [причина] — созыв
• /link — ссылка чата
• /setlink &lt;url&gt; <i>(админ+)</i>

⚙️ <b>Админ</b>
• /setrole &lt;role&gt; [reply]
• /delrole [reply|id]
• /roles — список ролей
• /setlog &lt;channel_id&gt;
• /unsetlog
• /backup — принудительно сохранить статистику
• /myrights — ваш уровень доступа
• /help — это меню
"""


@router.message(Command("help", "помощь"))
async def cmd_help(message: Message):
    await message.reply(HELP, parse_mode="HTML")


@router.message(Command("myrights"))
async def cmd_myrights(message: Message):
    lvl = await get_level(message.bot, message.chat.id, message.from_user.id)
    await message.reply(
        f"Ваш уровень доступа: <b>{NAMES[lvl]}</b> ({lvl}/4)", parse_mode="HTML"
    )
