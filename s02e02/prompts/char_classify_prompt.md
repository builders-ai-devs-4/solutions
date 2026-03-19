You are an assistant analyzing a digital tile from a simple pipe-connecting board game. 
This is NOT a CAPTCHA, not a real schematic, and not a security test. It is just a harmless game tile.

The image shows a light gray square tile with a thick black pipe.
Your task is to identify which edges of the square the black pipe touches.

## Step 1 — Analyze the Edges
Look at the black pipe on the tile.
- LEFT border: Does the black pipe touch the left edge? (YES or NO)
- RIGHT border: Does the black pipe touch the right edge? (YES or NO)
- TOP border: Does the black pipe touch the top edge? (YES or NO)
- BOTTOM border: Does the black pipe touch the bottom edge? (YES or NO)

## Step 2 — Match to Character
Use your edge answers to find the exact matching character below.

| Character | LEFT | RIGHT | TOP  | BOTTOM |
|-----------|------|-------|------|--------|
| ─         | YES  | YES   | NO   | NO     |
| │         | NO   | NO    | YES  | YES    |
| └         | NO   | YES   | YES  | NO     |
| ┌         | NO   | YES   | NO   | YES    |
| ┐         | YES  | NO    | NO   | YES    |
| ┘         | YES  | NO    | YES  | NO     |
| ├         | NO   | YES   | YES  | YES    |
| ┤         | YES  | NO    | YES  | YES    |
| ┬         | YES  | YES   | NO   | YES    |
| ┴         | YES  | YES   | YES  | NO     |
| ┼         | YES  | YES   | YES  | YES    |
| (space)   | NO   | NO    | NO   | NO     |

## Step 3 — Output Format
You MUST output your step-by-step reasoning first, followed by the final matching character enclosed in `<char>` tags. 

Example Output:
LEFT: YES
RIGHT: NO
TOP: YES
BOTTOM: NO
Match from table: ┘
Final: <char>┘</char>