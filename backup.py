import asyncio
import json
import logging

import aiosqlite
from aiogram import Bot
from aiogram.types import FSInputFile, InputMediaDocument

from config import BACKUP_CHAT_ID, BACKUP_INTERVAL
from database import DB_PATH
from state import is_dirty, clear_dirty

logger = logging.getLogger(__name__)

BACKUP_FILE = "backup.json"
TABLES = ("users", "chats", "roles", "log_channels", "rp_commands", "game_stats")

_backup_msg_id = None
_save_lock = asyncio.Lock()


async def export_db() -> dict:
    data = {}
    async with aiosqlite.connect(DB_PATH) as db:
        for table in TABLES:
            try:
                async with db.execute(f"SELECT * FROM {table}") as cur:
                    cols = [d[0] for d in cur.description]
                    rows = await cur.fetchall()
                    data[table] = [dict(zip(cols, r)) for r in rows]
            except Exception as e:
                logger.warning(f"Не смог прочитать {table}: {e}")
                data[table] = []
    return data


async def import_db(data: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        for table, rows in data.items():
            if not rows:
                continue
            await db.execute(f"DELETE FROM {table}")
            cols = list(rows[0].keys())
            placeholders = ",".join("?" * len(cols))
            col_names = ",".join(cols)
            values = [tuple(r.get(c) for c in cols) for r in rows]
            await db.executemany(
                f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})",
                values,
            )
        await db.commit()


async def load_backup(bot: Bot):
    global _backup_msg_id
    if not BACKUP_CHAT_ID:
        logger.warning("BACKUP_CHAT_ID не задан — авто-бэкап выключен")
        return
    try:
        chat = await bot.get_chat(BACKUP_CHAT_ID)
        pinned = getattr(chat, "pinned_message", None)
        if not pinned or not pinned.document:
            logger.info("Запиненного бэкапа нет — стартуем с пустой БД")
            return
        if pinned.document.file_name != BACKUP_FILE:
            logger.warning(f"Запинено не то: {pinned.document.file_name}")
            return
        file = await bot.get_file(pinned.document.file_id)
        await bot.download_file(file.file_path, BACKUP_FILE)
        with open(BACKUP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        await import_db(data)
        _backup_msg_id = pinned.message_id
        logger.info(f"✅ Бэкап загружен: msg_id={pinned.message_id}")
    except Exception as e:
        logger.exception(f"Ошибка загрузки бэкапа: {e}")


async def save_backup(bot: Bot, force: bool = False):
    global _backup_msg_id
    if not BACKUP_CHAT_ID:
        return
    async with _save_lock:
        if not is_dirty() and not force:
            return
        try:
            data = await export_db()
            with open(BACKUP_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)

            doc = FSInputFile(BACKUP_FILE)

            if _backup_msg_id:
                try:
                    await bot.edit_message_media(
                        chat_id=BACKUP_CHAT_ID,
                        message_id=_backup_msg_id,
                        media=InputMediaDocument(media=doc),
                    )
                except Exception as e:
                    logger.warning(f"edit_message_media не сработал: {e}")
                    _backup_msg_id = None

            if not _backup_msg_id:
                msg = await bot.send_document(BACKUP_CHAT_ID, doc, caption="📦 Backup")
                _backup_msg_id = msg.message_id
                try:
                    await bot.pin_chat_message(
                        BACKUP_CHAT_ID, msg.message_id, disable_notification=True
                    )
                except Exception as e:
                    logger.warning(f"Не смог закрепить бэкап: {e}")

            clear_dirty()
            logger.info("💾 Бэкап сохранён")
        except Exception as e:
            logger.exception(f"Ошибка сохранения бэкапа: {e}")


async def backup_loop(bot: Bot):
    while True:
        await asyncio.sleep(BACKUP_INTERVAL)
        await save_backup(bot, force=False)