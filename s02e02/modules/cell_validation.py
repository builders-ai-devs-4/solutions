# Mapowanie znak → które krawędzie są aktywne
CHAR_TO_EXITS: dict[str, set[str]] = {
    ' ': set(),
    '─': {'LEFT', 'RIGHT'},
    '│': {'TOP', 'BOTTOM'},
    '└': {'RIGHT', 'TOP'},
    '┌': {'RIGHT', 'BOTTOM'},
    '┐': {'LEFT', 'BOTTOM'},
    '┘': {'LEFT', 'TOP'},
    '├': {'RIGHT', 'TOP', 'BOTTOM'},
    '┤': {'LEFT', 'TOP', 'BOTTOM'},
    '┬': {'LEFT', 'RIGHT', 'BOTTOM'},
    '┴': {'LEFT', 'RIGHT', 'TOP'},
    '┼': {'LEFT', 'RIGHT', 'TOP', 'BOTTOM'},
}

def char_to_exits(char: str) -> set[str]:
    return CHAR_TO_EXITS.get(char, set())


def validate_grid(grid: list[list[str]]) -> list[dict]:
    """
    Sprawdza spójność topologiczną siatki.
    Zwraca listę konfliktów: [{'row', 'col', 'edge', 'char', 'neighbor_char'}]
    """
    errors = []
    n_rows = len(grid)
    n_cols = len(grid[0]) if n_rows > 0 else 0

    for r in range(n_rows):
        for c in range(n_cols):
            exits = char_to_exits(grid[r][c])

            # Sprawdź prawego sąsiada: mój RIGHT == jego LEFT
            if c + 1 < n_cols:
                neighbor_exits = char_to_exits(grid[r][c + 1])
                my_right       = 'RIGHT' in exits
                neighbor_left  = 'LEFT' in neighbor_exits

                if my_right != neighbor_left:
                    errors.append({
                        'row': r, 'col': c,
                        'edge': 'RIGHT',
                        'char': grid[r][c],
                        'neighbor': (r, c + 1),
                        'neighbor_char': grid[r][c + 1],
                        'detail': f"RIGHT={my_right} vs LEFT={neighbor_left}"
                    })

            # Sprawdź dolnego sąsiada: mój BOTTOM == jego TOP
            if r + 1 < n_rows:
                neighbor_exits  = char_to_exits(grid[r + 1][c])
                my_bottom       = 'BOTTOM' in exits
                neighbor_top    = 'TOP' in neighbor_exits

                if my_bottom != neighbor_top:
                    errors.append({
                        'row': r, 'col': c,
                        'edge': 'BOTTOM',
                        'char': grid[r][c],
                        'neighbor': (r + 1, c),
                        'neighbor_char': grid[r + 1][c],
                        'detail': f"BOTTOM={my_bottom} vs TOP={neighbor_top}"
                    })

    return errors

def get_conflict_context(grid: list[list[str]], row: int, col: int) -> str:
    """Buduje opis wymaganych krawędzi dla błędnej komórki (do promptu LLM)."""
    n_rows, n_cols = len(grid), len(grid[0])
    constraints = []

    neighbors = {
        'LEFT':   (row, col - 1, 'RIGHT'),
        'RIGHT':  (row, col + 1, 'LEFT'),
        'TOP':    (row - 1, col, 'BOTTOM'),
        'BOTTOM': (row + 1, col, 'TOP'),
    }

    for my_edge, (nr, nc, their_edge) in neighbors.items():
        if 0 <= nr < n_rows and 0 <= nc < n_cols:
            neighbor_exits = char_to_exits(grid[nr][nc])
            required = their_edge in neighbor_exits
            constraints.append(
                f"- {my_edge} edge: {'MUST be connected' if required else 'MUST be empty'} "
                f"(neighbor {grid[nr][nc]} at [{nr}][{nc}])"
            )

    return "Constraints from neighboring cells:\n" + "\n".join(constraints)
