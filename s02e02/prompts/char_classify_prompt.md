You are analyzing a single cell of an electrical wiring diagram.
Your task is to identify which of the four edges have a cable connection
and return exactly one Unicode character.

## Step 1 — Check each edge

Look at the image and answer for each edge:
- LEFT edge: does a cable exit through the left side? YES or NO
- RIGHT edge: does a cable exit through the right side? YES or NO
- TOP edge: does a cable exit through the top side? YES or NO
- BOTTOM edge: does a cable exit through the bottom side? YES or NO

## Step 2 — Match to character

Use your edge answers to find the matching character below.

| Character | LEFT | RIGHT | TOP  | BOTTOM | Description                        |
|-----------|------|-------|------|--------|------------------------------------|
| ─         | YES  | YES   | NO   | NO     | Horizontal bar, left to right      |
| │         | NO   | NO    | YES  | YES    | Vertical bar, top to bottom        |
| └         | NO   | YES   | YES  | NO     | Corner: stem goes RIGHT and UP     |
| ┌         | NO   | YES   | NO   | YES    | Corner: stem goes RIGHT and DOWN   |
| ┐         | YES  | NO    | NO   | YES    | Corner: stem goes LEFT and DOWN    |
| ┘         | YES  | NO    | YES  | NO     | Corner: stem goes LEFT and UP      |
| ├         | NO   | YES   | YES  | YES    | T-junction: vertical bar on LEFT side, branch goes RIGHT   |
| ┤         | YES  | NO    | YES  | YES    | T-junction: vertical bar on RIGHT side, branch goes LEFT   |
| ┬         | YES  | YES   | NO   | YES    | T-junction: horizontal bar at TOP, stem goes DOWN          |
| ┴         | YES  | YES   | YES  | NO     | T-junction: horizontal bar at BOTTOM, stem goes UP         |
| ┼         | YES  | YES   | YES  | YES    | Cross: all four edges connected    |
| (space)   | NO   | NO    | NO   | NO     | Empty cell, no cable               |

## Critical rules — most common mistakes

- ┬ has the horizontal bar at the TOP, the stem points DOWN (exits BOTTOM).
  If the stem points UP instead → it is ┴, not ┬.

- ┴ has the horizontal bar at the BOTTOM, the stem points UP (exits TOP).
  If the stem points DOWN instead → it is ┬, not ┴.

- ├ has the vertical bar on the LEFT side, the branch exits RIGHT only.
  If the branch exits LEFT only → it is ┤, not ├.

- ┤ has the vertical bar on the RIGHT side, the branch exits LEFT only.
  If the branch exits RIGHT only → it is ├, not ┤.

- │ connects ONLY top and bottom. If you also see a horizontal line → ┼
- ─ connects ONLY left and right. If you also see a vertical line → ┼
- ┼ requires ALL FOUR edges connected. If any single edge is missing → not ┼

## Step 3 — Output

Reply with ONLY the single Unicode character that matches.
No explanation. No spaces. No punctuation. Just the character.
