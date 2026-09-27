import random

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import update_game_stats, get_game_stats, get_game_top

router = Router()

FIELD = 9
HP_MAX = 10

ENEMIES = {
    "sword": {"emoji": "🗡️", "name": "Мечник"},
    "squid": {"emoji": "🐙", "name": "Кальмар"},
    "slime": {"emoji": "🦠", "name": "Слизень"},
}

DIRS = [
    (-1, -1, "↖️"), (0, -1, "⬆️"), (1, -1, "↗️"),
    (-1,  0, "⬅️"), (0,  0, "⏺️"), (1,  0, "➡️"),
    (-1,  1, "↙️"), (0,  1, "⬇️"), (1,  1, "↘️"),
]

GAMES = {}


def keyboard():
    kb = InlineKeyboardBuilder()
    for dx, dy, emoji in DIRS:
        kb.button(text=emoji, callback_data=f"g:{dx}:{dy}")
    kb.adjust(3, 3, 3)
    return kb.as_markup()


def render(state) -> str:
    board = [["⬛"] * FIELD for _ in range(FIELD)]
    for e in state["enemies"]:
        board[e["y"]][e["x"]] = ENEMIES[e["type"]]["emoji"]
    board[state["py"]][state["px"]] = "⭐"
    lines = "\n".join("".join(r) for r in board)
    return (
        f"🎮 <b>Волна {state['wave']}</b>   "
        f"❤️ {state['hp']}/{HP_MAX}   "
        f"💀 {state['kills']}   "
        f"🏆 всего убито: {state['total_kills']}\n"
        f"🗡️ Мечник   🐙 Кальмар   🦠 Слизень\n\n"
        f"{lines}"
    )


def spawn_wave(wave: int, px: int, py: int):
    count = 3 if wave <= 2 else (4 if wave <= 4 else 5)
    enemies = []
    for _ in range(1000):
        if len(enemies) >= count:
            break
        x = random.randint(0, FIELD - 1)
        y = random.randint(0, FIELD - 1)
        if (x, y) == (px, py):
            continue
        if max(abs(x - px), abs(y - py)) < 3:
            continue
        if any(e["x"] == x and e["y"] == y for e in enemies):
            continue
        t = random.choice(list(ENEMIES.keys()))
        enemies.append({"type": t, "x": x, "y": y})
    return enemies


def in_attack_range(ex, ey, px, py, etype) -> bool:
    dx, dy = abs(px - ex), abs(py - ey)
    if etype == "squid":
        if dx == 0 and 1 <= dy <= 3:
            return True
        if dy == 0 and 1 <= dx <= 3:
            return True
        return False
    return dx <= 1 and dy <= 1 and (dx + dy) > 0


def move_enemies(state):
    px, py = state["px"], state["py"]
    occupied = {(px, py)}
    for e in state["enemies"]:
        occupied.add((e["x"], e["y"]))

    for e in state["enemies"]:
        cur = (e["x"], e["y"])
        best, best_d = None, max(abs(e["x"] - px), abs(e["y"] - py))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = e["x"] + dx, e["y"] + dy
                if not (0 <= nx < FIELD and 0 <= ny < FIELD):
                    continue
                if (nx, ny) in occupied:
                    continue
                d = max(abs(nx - px), abs(ny - py))
                if d < best_d:
                    best_d, best = d, (nx, ny)
        if best:
            occupied.discard(cur)
            occupied.add(best)
            e["x"], e["y"] = best


@router.message(Command("game", "игра"))
async def cmd_game(message: Message):
    key = (message.chat.id, message.from_user.id)
    if key in GAMES:
        return await message.reply("⚠️ Игра уже идёт. Ходите или /stopgame.")
    state = {
        "px": FIELD // 2,
        "py": FIELD // 2,
        "hp": HP_MAX,
        "wave": 1,
        "kills": 0,
        "total_kills": 0,
        "enemies": spawn_wave(1, FIELD // 2, FIELD // 2),
    }
    msg = await message.reply(render(state), reply_markup=keyboard(), parse_mode="HTML")
    state["msg_id"] = msg.message_id
    GAMES[key] = state


@router.callback_query(F.data.startswith("g:"))
async def cb_move(call: CallbackQuery):
    try:
        _, sdx, sdy = call.data.split(":")
        dx, dy = int(sdx), int(sdy)
    except ValueError:
        return await call.answer()

    key = (call.message.chat.id, call.from_user.id)
    state = GAMES.get(key)
    if not state:
        return await call.answer("Игра не найдена. /game", show_alert=True)
    if call.message.message_id != state.get("msg_id"):
        return await call.answer("Это старая игра.", show_alert=True)

    nx, ny = state["px"] + dx, state["py"] + dy
    if not (0 <= nx < FIELD and 0 <= ny < FIELD):
        return await call.answer("🚧 Граница поля")

    state["px"], state["py"] = nx, ny

    killed = None
    for e in list(state["enemies"]):
        if e["x"] == nx and e["y"] == ny:
            killed = e
            state["enemies"].remove(e)
            state["kills"] += 1
            state["total_kills"] += 1
            break

    dmg = 0
    for e in state["enemies"]:
        if in_attack_range(e["x"], e["y"], nx, ny, e["type"]):
            dmg = random.randint(1, 2)
            break

    if dmg:
        state["hp"] -= dmg

    if killed:
        msg = f"☠️ {ENEMIES[killed['type']]['name']} убит!"
        if dmg:
            msg += f" Но -{dmg} HP"
        await call.answer(msg)
    elif dmg:
        await call.answer(f"💥 -{dmg} HP")
    else:
        await call.answer("✅")

    if state["hp"] <= 0:
        await update_game_stats(call.from_user.id, state["wave"], state["total_kills"])
        del GAMES[key]
        try:
            await call.message.edit_text(
                render(state)
                + f"\n\n💀 <b>Поражение!</b>\n"
                  f"Волна: <b>{state['wave']}</b>  |  "
                  f"Всего убито: <b>{state['total_kills']}</b>",
                parse_mode="HTML",
            )
        except Exception:
            pass
        return

    move_enemies(state)

    if not state["enemies"]:
        state["wave"] += 1
        state["kills"] = 0
        state["hp"] = min(HP_MAX, state["hp"] + 3)
        state["enemies"] = spawn_wave(state["wave"], state["px"], state["py"])
        await call.answer(f"🌊 Волна {state['wave']}! +3 HP")

    try:
        await call.message.edit_text(render(state), reply_markup=keyboard(), parse_mode="HTML")
    except Exception:
        pass


@router.message(Command("stopgame"))
async def cmd_stopgame(message: Message):
    key = (message.chat.id, message.from_user.id)
    if key in GAMES:
        state = GAMES.pop(key)
        await update_game_stats(message.from_user.id, state["wave"], state["total_kills"])
        await message.reply("🏳 Игра завершена.")
    else:
        await message.reply("Активной игры нет.")


@router.message(Command("mystats"))
async def cmd_mystats(message: Message):
    row = await get_game_stats(message.from_user.id)
    if not row:
        return await message.reply("📊 Вы ещё не играли. /game")
    games, best, kills = row
    await message.reply(
        f"📊 <b>Ваша статистика</b>\n"
        f"🎮 Игр: {games}\n"
        f"🏆 Лучшая волна: {best}\n"
        f"💀 Всего убито: {kills}",
        parse_mode="HTML",
    )


@router.message(Command("topgame"))
async def cmd_topgame(message: Message):
    rows = await get_game_top(10)
    if not rows:
        return await message.reply("📊 Пока никто не играл.")
    lines = ["🏆 <b>Топ игроков</b>"]
    for i, (uid, best, kills) in enumerate(rows, 1):
        try:
            m = await message.bot.get_chat_member(message.chat.id, uid)
            name = m.user.full_name
        except Exception:
            name = str(uid)
        lines.append(f"{i}. {name} — волна {best}, убито {kills}")
    await message.reply("\n".join(lines), parse_mode="HTML")
