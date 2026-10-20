# The Golden Rail — Craps

A playable craps game built with Python and Pygame. The table is the interface: choose a chip, click a printed betting area, and roll. The project combines a rules and bankroll engine with a casino-style, responsive table UI.

## What it does

- Implements Pass Line, Don't Pass, Come, Don't Come, Field, Place 4/5/6/8/9/10, Hard 4/6/8/10, and odds on eligible line bets.
- Enforces come-out and point phases, wager limits, exact whole-dollar payout amounts, and bankroll accounting.
- Shows wagers as chip stacks on their corresponding table areas. Click a stack to add to that wager or, when eligible, add odds to that specific bet.
- Provides chip selection, hover feedback, recent-roll status, undo before the next roll, and a roll animation.
- Resizes the table while preserving the layout.

## How it was built

I built the original game engine and core flow through Pass Line and Field bets. I then used AI assistance to help with the casino-style table design and UI, and to finish the remaining bet types, payout and settlement cases, and interaction details. The rules engine remains separate from the Pygame presentation so that wager resolution and bankroll behavior can be tested independently.

## Project structure

- `craps/engine/` — bet types, dice, game phase and roll history, wager validation, payout calculation, and bankroll settlement.
- `craps/ui/board.py` — table artwork and the geometry for its betting areas.
- `craps/ui/betting.py` — direct hit-testing against that same table geometry, wager placement helpers, and on-table chip stacks.
- `craps/ui/main.py` — Pygame event loop, controls, status display, and dice animation.
- `tests/` — deterministic tests for dice, game flow, bet rules, payouts, and table betting interactions.

## Rules and defaults

The game starts with a $100 bankroll and uses a $5 minimum base bet. Place payouts follow common craps payouts: 9:5 on 4/10, 7:5 on 5/9, and 7:6 on 6/8. A $6 chip is included so Place 6 and Place 8 can pay in whole dollars. Odds are capped at 3× the base wager by default. Field 2 pays 2:1 by default (the engine also supports 3:1), and Don't Pass/Don't Come 12 pushes by default. These values are configured in the engine and can be adjusted in code.

## Run

Requires Python 3.11+ and Pygame 2.6.1. From the repository root:

```sh
python3 -m venv venv  # skip if the project's venv already exists
./venv/bin/python -m pip install -r requirements.txt
./venv/bin/python -m craps.ui.main
```

## Controls

- Select a chip in the tray or use **1–6**.
- Click a betting area to place the selected chip.
- Click a wager's chip stack to add to it; after a number is established, that stack can also receive odds.
- Click **Roll Dice** or press **Space** to roll.
- Click **Undo Chip** or press **Z** to refund the latest wager change since the last roll.
- Press **R** to reset the game and **Escape** to quit.

Invalid wagers show a status message and do not charge the bankroll. The table uses a 1400×700 design canvas and scales to fit the window. Dice use a 2D rotation and bounce animation.

## Tests

Run the rules and interaction suite with:

```sh
./venv/bin/python -m unittest discover -s tests
```

## Play together online

The browser version is served by a small FastAPI WebSocket server. To run it locally:

```sh
python3 -m venv web-venv  # optional; the existing venv can also be used
./web-venv/bin/python -m pip install -r web/requirements.txt
./web-venv/bin/uvicorn web.server:app --reload
```

Open `http://127.0.0.1:8000`, create a table, then share its invite link. Players join the same room with separate bankrolls. The shooter keeps rolling until the hand ends, then the shooter role rotates. For a free Render deployment, connect this GitHub repository and deploy the included `render.yaml` Blueprint. The free service may take about a minute to wake after inactivity, and active rooms reset when its in-memory server restarts. The browser game uses play chips and does not require an account.
