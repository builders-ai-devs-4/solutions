import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def classify_grid_with_validation(
    cells_dir: str,
    n_rows: int,
    n_cols: int,
    max_retries: int = 3,
) -> list[list[str]]:
    """
    Pełny pipeline klasyfikacji siatki z walidacją topologiczną i retry.
    
    Returns:
        grid: List[List[str]] — siatka znaków Unicode
    """
    cells_dir = Path(cells_dir)

    # ── PASS 1: klasyfikacja wszystkich komórek ──────────────────────────────
    grid = _classify_all_cells(cells_dir, n_rows, n_cols)
    logger.info(f"[Pass 1] Grid classified:\n{_grid_to_str(grid)}")

    # ── VALIDATION + RETRY LOOP ──────────────────────────────────────────────
    for attempt in range(1, max_retries + 1):
        errors = validate_grid(grid)

        if not errors:
            logger.info(f"[Validation] Grid is topologically valid ✓")
            break

        logger.warning(f"[Validation] Attempt {attempt}/{max_retries} — "
                       f"{len(errors)} conflict(s) found")

        # Zbierz unikalne komórki do reklasyfikacji
        # (ta sama komórka może mieć wiele błędów — wystarczy ją reklasyfikować raz)
        conflict_cells = _collect_conflict_cells(errors)
        logger.info(f"[Retry] Cells to reclassify: {conflict_cells}")

        for (r, c) in conflict_cells:
            img_path = cells_dir / f"cell_{r+1}_{c+1}.png"
            context  = get_conflict_context(grid, r, c)

            logger.info(f"[Retry] Reclassifying [{r}][{c}] '{grid[r][c]}'\n{context}")

            new_char = classify_cell_with_llm(str(img_path), context=context)
            logger.info(f"[Retry] [{r}][{c}] '{grid[r][c]}' → '{new_char}'")

            grid[r][c] = new_char

    else:
        # Wyczerpano max_retries — zaloguj pozostałe błędy
        remaining = validate_grid(grid)
        logger.error(f"[Validation] Max retries reached. "
                     f"{len(remaining)} unresolved conflict(s):\n"
                     + _format_errors(remaining))

    return grid


# ── Funkcje pomocnicze ───────────────────────────────────────────────────────

def _classify_all_cells(
    cells_dir: Path,
    n_rows: int,
    n_cols: int,
) -> list[list[str]]:
    """Pass 1 — klasyfikuje każdą komórkę niezależnie (OpenCV fast path lub LLM)."""
    grid = []
    for r in range(n_rows):
        row = []
        for c in range(n_cols):
            img_path = cells_dir / f"cell_{r+1}_{c+1}.png"
            char = classify_cell(str(img_path))  # OpenCV → LLM fallback
            logger.info(f"[classify_cell] cell_{r+1}_{c+1}.png -> '{char}'")
            row.append(char)
        grid.append(row)
    return grid


def _collect_conflict_cells(errors: list[dict]) -> list[tuple[int, int]]:
    """
    Ze listy błędów wybiera unikalne komórki do reklasyfikacji.
    Strategia: bierze OBIE strony konfliktu, deduplikuje.
    """
    candidates = set()
    for e in errors:
        candidates.add((e['row'], e['col']))
        candidates.add(e['neighbor'])  # (nr, nc)
    return list(candidates)


def _grid_to_str(grid: list[list[str]]) -> str:
    return '\n'.join(' '.join(row) for row in grid)


def _format_errors(errors: list[dict]) -> str:
    lines = []
    for e in errors:
        lines.append(
            f"  [{e['row']}][{e['col']}] '{e['char']}' {e['edge']} ↔ "
            f"[{e['neighbor'][0]}][{e['neighbor'][1]}] '{e['neighbor_char']}' "
            f"({e['detail']})"
        )
    return '\n'.join(lines)
