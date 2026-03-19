You are analyzing a single cell of an electrical wiring diagram.
Identify which of the four edges (LEFT, RIGHT, TOP, BOTTOM) have a cable
connection, then output EXACTLY ONE Unicode character from the table below.

Character → connected edges:
─   LEFT + RIGHT            (NO top, NO bottom)
│   TOP + BOTTOM            (NO left, NO right)
└   RIGHT + TOP             (NO left, NO bottom)
┌   RIGHT + BOTTOM          (NO left, NO top)
┐   LEFT + BOTTOM           (NO right, NO top)
┘   LEFT + TOP              (NO right, NO bottom)
├   RIGHT + TOP + BOTTOM    (NO left)
┤   LEFT + TOP + BOTTOM     (NO right)
┬   LEFT + RIGHT + BOTTOM   (NO top)
┴   LEFT + RIGHT + TOP      (NO bottom)
┼   LEFT + RIGHT + TOP + BOTTOM  (all four)
    (space) no cable at all

CRITICAL — most common mistakes:
- │ connects ONLY top and bottom. If you also see a horizontal line → ┼
- ─ connects ONLY left and right. If you also see a vertical line → ┼
- ┼ requires ALL FOUR edges to be connected. If any edge is missing → not ┼
- Corners (└ ┌ ┐ ┘) connect exactly TWO edges at 90 degrees, never three.
- T-junctions (├ ┤ ┬ ┴) connect exactly THREE edges, always missing one.

Reply with ONLY the single Unicode character. No explanation, no spaces.
