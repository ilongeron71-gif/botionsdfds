import aiosqlite
from datetime import datetime
from functools import wraps
from state import mark_dirty

DB_PATH = "bot.db"


def dirty(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        mark_dirty()
        return result
    return wrapper


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER,
                chat_id INTEGER,
                username TEXT,
                title TEXT DEFAULT '',
                position TEXT DEFAULT '',
                messages INTEGER DEFAULT 0,
                joined_at TEXT,
                warns INTEGER DEFAULT 0,
                warn_limit INTEGER DEFAULT 3,
                PRIMARY KEY (user_id, chat_id)
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                chat_id INTEGER PRIMARY KEY,
                warn_limit INTEGER DEFAULT 3,
                link TEXT DEFAULT ''
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                user_id INTEGER,
                chat_id INTEGER,
                role TEXT,
                PRIMARY KEY (user_id, chat_id)
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS log_channels (
                chat_id INTEGER PRIMARY KEY,
                log_chat_id INTEGER
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS rp_commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                trigger TEXT,
                text TEXT,
                creator_id INTEGER
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS game_stats (
                user_id INTEGER PRIMARY KEY,
                games INTEGER DEFAULT 0,
                best_wave INTEGER DEFAULT 0,
                total_kills INTEGER DEFAULT 0
            )""")
        await db.commit()


@dirty
async def ensure_user(user_id, chat_id, username=""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, chat_id, username, joined_at) VALUES (?,?,?,?)",
            (user_id, chat_id, username, datetime.utcnow().isoformat()),
        )
        await db.execute(
            "UPDATE users SET username=? WHERE user_id=? AND chat_id=?",
            (username, user_id, chat_id),
        )
        await db.commit()


@dirty
async def ensure_chat(chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO chats (chat_id) VALUES (?)", (chat_id,))
        await db.commit()


@dirty
async def inc_messages(user_id, chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET messages = messages + 1 WHERE user_id=? AND chat_id=?",
            (user_id, chat_id),
        )
        await db.commit()


async def get_user(user_id, chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, username, title, position, messages, joined_at, warns, warn_limit "
            "FROM users WHERE user_id=? AND chat_id=?",
            (user_id, chat_id),
        ) as cur:
            return await cur.fetchone()


async def get_warn_limit(chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT warn_limit FROM chats WHERE chat_id=?", (chat_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else 3


@dirty
async def set_warn_limit(chat_id, limit):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO chats (chat_id, warn_limit) VALUES (?, ?) "
            "ON CONFLICT(chat_id) DO UPDATE SET warn_limit=excluded.warn_limit",
            (chat_id, limit),
        )
        await db.commit()


@dirty
async def add_warn(user_id, chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET warns = warns + 1 WHERE user_id=? AND chat_id=?",
            (user_id, chat_id),
        )
        await db.commit()
        async with db.execute(
            "SELECT warns FROM users WHERE user_id=? AND chat_id=?", (user_id, chat_id)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


@dirty
async def reset_warns(user_id, chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET warns=0 WHERE user_id=? AND chat_id=?", (user_id, chat_id)
        )
        await db.commit()


@dirty
async def set_title(user_id, chat_id, title):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET title=? WHERE user_id=? AND chat_id=?",
            (title, user_id, chat_id),
        )
        await db.commit()


@dirty
async def set_position(user_id, chat_id, position):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET position=? WHERE user_id=? AND chat_id=?",
            (position, user_id, chat_id),
        )
        await db.commit()


@dirty
async def set_chat_link(chat_id, link):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO chats (chat_id, link) VALUES (?, ?) "
            "ON CONFLICT(chat_id) DO UPDATE SET link=excluded.link",
            (chat_id, link),
        )
        await db.commit()


async def get_chat_link(chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT link FROM chats WHERE chat_id=?", (chat_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else ""


@dirty
async def set_role(user_id, chat_id, role):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO roles (user_id, chat_id, role) VALUES (?,?,?) "
            "ON CONFLICT(user_id, chat_id) DO UPDATE SET role=excluded.role",
            (user_id, chat_id, role),
        )
        await db.commit()


async def get_role(user_id, chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT role FROM roles WHERE user_id=? AND chat_id=?",
            (user_id, chat_id),
        ) as cur:
            r = await cur.fetchone()
            return r[0] if r else None


@dirty
async def remove_role(user_id, chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM roles WHERE user_id=? AND chat_id=?", (user_id, chat_id)
        )
        await db.commit()


async def list_roles(chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, role FROM roles WHERE chat_id=?", (chat_id,)
        ) as cur:
            return await cur.fetchall()


@dirty
async def set_log_channel(chat_id, log_chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        if not log_chat_id:
            await db.execute("DELETE FROM log_channels WHERE chat_id=?", (chat_id,))
        else:
            await db.execute(
                "INSERT INTO log_channels (chat_id, log_chat_id) VALUES (?,?) "
                "ON CONFLICT(chat_id) DO UPDATE SET log_chat_id=excluded.log_chat_id",
                (chat_id, log_chat_id),
            )
        await db.commit()


async def get_log_channel(chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT log_chat_id FROM log_channels WHERE chat_id=?", (chat_id,)
        ) as cur:
            r = await cur.fetchone()
            return r[0] if r else None


@dirty
async def add_rp(chat_id, trigger, text, creator_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM rp_commands WHERE chat_id=? AND trigger=?",
            (chat_id, trigger),
        )
        await db.execute(
            "INSERT INTO rp_commands (chat_id, trigger, text, creator_id) VALUES (?,?,?,?)",
            (chat_id, trigger, text, creator_id),
        )
        await db.commit()


@dirty
async def del_rp(chat_id, trigger, user_id, is_admin):
    async with aiosqlite.connect(DB_PATH) as db:
        if is_admin:
            cur = await db.execute(
                "DELETE FROM rp_commands WHERE chat_id=? AND trigger=?",
                (chat_id, trigger),
            )
        else:
            cur = await db.execute(
                "DELETE FROM rp_commands WHERE chat_id=? AND trigger=? AND creator_id=?",
                (chat_id, trigger, user_id),
            )
        await db.commit()
        return cur.rowcount > 0


async def get_rp(chat_id, trigger):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT text FROM rp_commands WHERE chat_id=? AND trigger=?",
            (chat_id, trigger),
        ) as cur:
            r = await cur.fetchone()
            return r[0] if r else None


async def list_all_rp(chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT trigger, text, creator_id FROM rp_commands "
            "WHERE chat_id=? ORDER BY trigger",
            (chat_id,),
        ) as cur:
            return await cur.fetchall()


@dirty
async def update_game_stats(user_id, wave, kills):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT games, best_wave, total_kills FROM game_stats WHERE user_id=?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            await db.execute(
                "INSERT INTO game_stats (user_id, games, best_wave, total_kills) VALUES (?,1,?,?)",
                (user_id, wave, kills),
            )
        else:
            games, best, tot = row
            await db.execute(
                "UPDATE game_stats SET games=?, best_wave=?, total_kills=? WHERE user_id=?",
                (games + 1, max(best, wave), tot + kills, user_id),
            )
        await db.commit()


async def get_game_stats(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT games, best_wave, total_kills FROM game_stats WHERE user_id=?",
            (user_id,),
        ) as cur:
            return await cur.fetchone()


async def get_game_top(limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, best_wave, total_kills FROM game_stats "
            "ORDER BY best_wave DESC, total_kills DESC LIMIT ?",
            (limit,),
        ) as cur:
            return await cur.fetchall()
