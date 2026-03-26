import json
from pydantic import BaseModel, Field
from typing import List

# Definiujemy pojedynczą metodę
class ApiMethod(BaseModel):
    nazwa: str = Field(description="Nazwa metody, np. set(mode)")
    opis: str = Field(description="Opis działania metody i jej parametrów")
    przyklad: str = Field(description="Przykład użycia, np. set(engineON)")

# Definiujemy kategorię (np. Sterowanie silnikami, Konfiguracja)
class ApiCategory(BaseModel):
    nazwa_kategorii: str = Field(description="Nazwa obszaru/kategorii z tabeli")
    metody: List[ApiMethod] = Field(description="Lista metod należących do tej kategorii")

# Definiujemy główny dokument
class DroneDocumentation(BaseModel):
    urzadzenie: str = Field(description="Nazwa drona")
    producent: str = Field(description="Producent oprogramowania")
    informacje_ogolne: str = Field(description="Krótki opis, endpointy i wymagania requestu")
    kategorie_api: List[ApiCategory] = Field(description="Pogrupowane metody sterowania")
    cele_misji: List[str] = Field(description="Lista możliwych celów misji")
    przykłady_uzycia: str = Field(description="Krótkie podsumowanie przykładów użycia w formacie tekstowym")

class DroneGridInput(BaseModel):
    """Input parameters for the drone grid splitter tool.

    Only ``image_path`` is required. ``output_dir`` defaults to ``"output"``
    relative to the current working directory.

    The tool expects the image to contain a **red** grid overlay drawn
    directly on top of the photograph (H: 0–10° and 170–180° in HSV).
    Detection parameters (margin, min_gap) are fixed internally and are
    not exposed here to keep the agent interface minimal.
    """

    image_path: str = Field(
        description=(
            "Absolute or relative path to the input drone photograph. "
            "Supported formats: JPG, PNG, BMP, TIFF (any format accepted by OpenCV)."
        )
    )
    output_dir: str = Field(
        default="output",
        description=(
            "Root output directory. The tool creates the following structure: "
            "``<output_dir>/cells/cell_RxC.png``, "
            "``<output_dir>/grid_visualization.png``, "
            "``<output_dir>/grid_cells.csv``. "
            "The directory is created automatically if it does not exist."
        ),
    )


class CellCoord(BaseModel):
    """Grid position of a single cell extracted from the drone image.

    Both indices are **1-based**: the top-left cell is (cell_y=1, cell_x=1),
    the cell to its right is (cell_y=1, cell_x=2), and the cell directly
    below is (cell_y=2, cell_x=1).

    The ``index`` field combines both axes into the canonical ``RxC`` string
    used as a filename suffix and as a human-readable reference throughout
    the pipeline (e.g. ``"2x3"`` means row 2, column 3).
    """

    index: str = Field(
        description=(
            "Canonical cell label in 'RxC' format (row x col, 1-based). "
            "Matches the filename suffix of the corresponding PNG, "
            "e.g. 'cell_2x3.png'."
        )
    )
    cell_x: int = Field(
        description=(
            "Column index of the cell within the grid, starting at 1. "
            "Increases from left to right."
        )
    )
    cell_y: int = Field(
        description=(
            "Row index of the cell within the grid, starting at 1. "
            "Increases from top to bottom."
        )
    )


class DroneGridOutput(BaseModel):
    """Structured output returned by the drone grid splitter tool.

    All file-system paths are **absolute** so downstream tools can use them
    directly regardless of the current working directory.

    ``cell_files`` and ``cell_coords`` are parallel lists of length
    ``n_rows * n_cols``, both ordered row-first:
    1x1, 1x2, …, 1xN, 2x1, …, NxM.
    Use ``cell_coords[i].index`` to match a path in ``cell_files[i]``
    to its grid position.
    """

    cells_dir: str = Field(
        description=(
            "Absolute path to the directory that contains all extracted cell "
            "images (``cells/`` sub-directory inside ``output_dir``)."
        )
    )
    cell_files: list[str] = Field(
        description=(
            "Sorted list of absolute paths to individual cell PNG images. "
            "Ordered row-first: cell_1x1.png, cell_1x2.png, …, cell_NxM.png. "
            "Each path corresponds to the CellCoord at the same list index."
        )
    )
    cell_coords: list[CellCoord] = Field(
        description=(
            "Grid position metadata for every extracted cell. "
            "Parallel to ``cell_files``: ``cell_coords[i]`` describes the "
            "cell whose image is at ``cell_files[i]``."
        )
    )
    grid_visualization: str = Field(
        description=(
            "Absolute path to the annotated grid overlay PNG. "
            "The image shows the original photograph with detected grid lines "
            "drawn in red and cell index labels (e.g. '2x3') drawn in green."
        )
    )
    n_rows: int = Field(
        description="Total number of rows detected in the grid (vertical cell count)."
    )
    n_cols: int = Field(
        description="Total number of columns detected in the grid (horizontal cell count)."
    )
