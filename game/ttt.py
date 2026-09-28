"""Community tic-tac-toe played through GitHub issues.

Visitors are ❌ (all together), the bot is ⭕. A visitor clicks a cell in the
README, which opens an issue titled `ttt|move|<0-8>` (or `ttt|new`). The
workflow in .github/workflows/tictactoe.yml runs this script, which:

  1. validates the move and applies it,
  2. lets the bot answer (minimax, with the odd deliberate blunder),
  3. rewrites the README block between the TTT markers,
  4. writes a comment for the issue.

    python game/ttt.py --title "ttt|move|4" --player octocat --comment-file c.md
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "game" / "state.json"
README = ROOT / "README.md"
REPO = "jbeleno/jbeleno"
START, END = "<!-- TTT:START -->", "<!-- TTT:END -->"
BLUNDER_RATE = 0.2  # chance the bot plays a random move instead of the best one

LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
HUMAN, BOT = "X", "O"


# ---------------------------------------------------------------- game logic
def winner(board: list[str]) -> tuple[str, tuple[int, int, int]] | None:
    for a, b, c in LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a], (a, b, c)
    return None


def full(board: list[str]) -> bool:
    return all(board)


@lru_cache(maxsize=None)
def _minimax(board: tuple[str, ...], player: str) -> int:
    w = winner(list(board))
    if w:
        return 1 if w[0] == BOT else -1
    if all(board):
        return 0
    nxt = HUMAN if player == BOT else BOT
    scores = [_minimax(board[:i] + (player,) + board[i + 1:], nxt) for i in range(9) if not board[i]]
    return max(scores) if player == BOT else min(scores)


def minimax(board: list[str], player: str) -> tuple[int, None]:
    return _minimax(tuple(board), player), None


def bot_move(board: list[str], rng: random.Random) -> int:
    empty = [i for i, v in enumerate(board) if not v]
    if rng.random() < BLUNDER_RATE:
        return rng.choice(empty)
    # among equally good moves pick one at random so games don't repeat
    scores = {}
    for i in empty:
        board[i] = BOT
        scores[i] = minimax(board, HUMAN)[0]
        board[i] = ""
    top = max(scores.values())
    return rng.choice([i for i, s in scores.items() if s == top])


def outcome(board: list[str]) -> str | None:
    w = winner(board)
    if w:
        return "human" if w[0] == HUMAN else "bot"
    return "draw" if full(board) else None


# ---------------------------------------------------------------- state
def fresh_game(state: dict) -> None:
    state["board"] = [""] * 9
    state["game"] = state.get("game", 0) + 1
    state["result"] = None
    state["game_moves"] = []


def load() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    state = {"stats": {"games": 0, "human": 0, "bot": 0, "draw": 0, "moves": 0},
             "players": {}, "recent": []}
    fresh_game(state)
    return state


def save(state: dict) -> None:
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- rendering
def issue_link(title: str) -> str:
    body = "Just press **Submit new issue** — you don't need to write anything. A bot will play and update the README in ~30 seconds."
    return f"https://github.com/{REPO}/issues/new?title={quote(title)}&body={quote(body)}"


def render(state: dict) -> str:
    board = state["board"]
    w = winner(board)
    win_cells = set(w[1]) if w else set()
    over = state["result"] is not None

    rows = []
    for r in range(3):
        cells = []
        for c in range(3):
            i = r * 3 + c
            v = board[i]
            if v:
                name = ("x" if v == HUMAN else "o") + ("-win" if i in win_cells else "")
                cells.append(f'<td><img src="game/assets/{name}.svg" width="84" alt="{v}"/></td>')
            elif over:
                cells.append('<td><img src="game/assets/empty-dead.svg" width="84" alt=""/></td>')
            else:
                cells.append(f'<td><a href="{issue_link(f"ttt|move|{i}")}">'
                             f'<img src="game/assets/empty.svg" width="84" alt="play {i}"/></a></td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    table = '<table align="center">' + "".join(rows) + "</table>"

    res = state["result"]
    if res is None:
        headline = "<b>Your move.</b> Click any empty cell. You're ❌ (together with everyone who visits), the bot is ⭕."
    else:
        msg = {"human": "🏆 <b>Humans win!</b>", "bot": "🤖 <b>The bot wins.</b>", "draw": "🤝 <b>Draw.</b>"}[res]
        headline = f'{msg} &nbsp; <a href="{issue_link("ttt|new")}"><b>▶ Start a new game</b></a>'

    s = state["stats"]
    scoreboard = (f"Game #{state['game']} · all time: <b>{s['human']}</b> human wins · "
                  f"<b>{s['bot']}</b> bot wins · <b>{s['draw']}</b> draws · {s['moves']} moves played")

    recent = state["recent"][:5]
    recent_md = " · ".join(f'<a href="https://github.com/{m["player"]}">@{m["player"]}</a> → {m["cell"]}' for m in recent) or "<i>no moves yet, be the first</i>"

    top = sorted(state["players"].items(), key=lambda kv: (-kv[1]["wins"], -kv[1]["moves"], kv[0]))[:5]
    top_md = " · ".join(f'<a href="https://github.com/{p}">@{p}</a> ({d["wins"]}🏆 {d["moves"]} moves)' for p, d in top) or "<i>nobody yet</i>"

    return "\n".join([
        START,
        f'<p align="center">{headline}</p>',
        "",
        table,
        "",
        f'<p align="center"><sub>{scoreboard}</sub></p>',
        "",
        f'<p align="center"><sub>Last moves: {recent_md}<br/>Top players: {top_md}</sub></p>',
        END,
    ])


def write_readme(state: dict) -> None:
    text = README.read_text(encoding="utf-8")
    block = render(state)
    if START in text and END in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S)
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    README.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------- turn
def finish(state: dict, res: str, player: str) -> None:
    state["result"] = res
    state["stats"]["games"] += 1
    state["stats"][res] += 1
    if res == "human":
        state["players"][player]["wins"] += 1


def play(state: dict, title: str, player: str, rng: random.Random) -> str:
    title = title.strip()
    if re.fullmatch(r"ttt\|new", title):
        if state["result"] is None and any(state["board"]):
            return "There's a game in progress — finish it first! 😉 Pick a cell in the README."
        fresh_game(state)
        return f"🆕 Game #{state['game']} started. Your move — go back to the profile and pick a cell."

    m = re.fullmatch(r"ttt\|move\|([0-8])", title)
    if not m:
        return "I couldn't understand that move. Use the links on the profile README."
    cell = int(m.group(1))

    if state["result"] is not None:
        return "This game is already over. Click **Start a new game** on the profile."
    if state["board"][cell]:
        return f"Cell {cell} is already taken. Try another one!"

    board = state["board"]
    board[cell] = HUMAN
    p = state["players"].setdefault(player, {"moves": 0, "wins": 0})
    p["moves"] += 1
    state["stats"]["moves"] += 1
    state["game_moves"].append({"player": player, "cell": cell})
    state["recent"].insert(0, {"player": player, "cell": cell, "game": state["game"],
                               "at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    state["recent"] = state["recent"][:20]

    res = outcome(board)
    if res:
        finish(state, res, player)
        return {"human": f"🏆 You beat the bot with cell {cell}! You're on the leaderboard.",
                "draw": "🤝 Draw! The bot couldn't beat you."}[res]

    reply = bot_move(board, rng)
    board[reply] = BOT
    res = outcome(board)
    if res:
        finish(state, res, player)
        return f"You played {cell}, the bot answered {reply}… " + {
            "bot": "and won. 🤖 Start a new game and get revenge!",
            "draw": "and it's a draw. 🤝"}[res]
    return f"You played **{cell}**, the bot answered **{reply}**. Back to the profile for the next move!"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--player", required=True)
    ap.add_argument("--comment-file")
    ap.add_argument("--render-only", action="store_true")
    args = ap.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}(\[bot\])?", args.player):
        print("invalid player login", file=sys.stderr)
        return 1

    state = load()
    msg = "" if args.render_only else play(state, args.title, args.player, random.Random())
    save(state)
    write_readme(state)
    board = state["board"]
    preview = "\n".join(" ".join(v or "·" for v in board[r * 3:r * 3 + 3]) for r in range(3))
    comment = (f"{msg}\n\n```\n{preview}\n```\n\n"
               f"👉 [Back to the game](https://github.com/{REPO}#-play-with-me)")
    if args.comment_file:
        Path(args.comment_file).write_text(comment, encoding="utf-8")
    print(comment)
    return 0


if __name__ == "__main__":
    sys.exit(main())
