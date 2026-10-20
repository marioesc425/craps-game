# Craps — The Golden Rail

A Pygame craps table with direct on-table betting for Pass Line, Don't Pass, Come, Don't Come, Place, Field, Hardway, and line-bet odds.

## Run

From the project root, install Python 3.11+ and Pygame 2.6.1, then run:

```sh
python3 -m venv venv  # skip if the project's venv already exists
./venv/bin/python -m pip install -r requirements.txt
./venv/bin/python -m craps.ui.main
```

## Play

Choose a chip from the tray at the upper right (mouse click or **1–6**), then click a printed betting area. The board areas map to Pass Line, Don't Pass, Come, Don't Come, Field, Place 4/5/6/8/9/10, and Hard 4/6/8/10. The $6 chip lets Place 6 and Place 8 pay exactly in whole dollars. Click a wager's on-table chip stack to add the selected amount to it; after its number is established, the same click adds odds to that specific line wager. Chip stacks show the base amount and odds separately.

Click **Roll Dice** or press **Space** when wagers are active. **Undo Chip** or **Z** refunds the most recent wager change made since the last roll. Use **R** to start a fresh game and **Escape** to quit. Hover a betting zone to see its valid-phase highlight; invalid clicks show a brief status message.

Base wagers are at least $5. Whole-dollar chip amounts that cannot produce exact Place or odds payouts are rejected. Odds have a 3x maximum by default. Field 2 pays 2:1 by default (the engine supports 3:1), and Don't Pass/Don't Come 12 pushes by default.

The table uses a 1400×700 design canvas and resizes to fit the window while preserving its layout. Dice use a 2D rotation and bounce animation, without 3D physics or drag-to-roll. Run the deterministic rules and betting interaction tests with:

```sh
./venv/bin/python -m unittest discover -s tests
```
