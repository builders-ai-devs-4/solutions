import json
from pydantic import BaseModel, Field
from typing import List

class ApiMethod(BaseModel):
    name: str = Field(description="Name of the method, e.g., set(mode)")
    description: str = Field(description="Description of the method and its parameters")
    example: str = Field(description="Usage example, e.g., set(engineON)")

class ApiCategory(BaseModel):
    category_name: str = Field(description="Name of the area/category from the table")
    methods: List[ApiMethod] = Field(description="List of methods belonging to this category")

class DroneDocumentation(BaseModel):
    device_name: str = Field(description="Name of the drone")
    manufacturer: str = Field(description="Software manufacturer")
    general_info: str = Field(description="Short description, endpoints, and request requirements")
    api_categories: List[ApiCategory] = Field(description="Grouped control methods")
    mission_objectives: List[str] = Field(description="List of possible mission objectives")
    
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

class HtmlToMarkdownInput(BaseModel):
    """Input parameters for the HTML-to-Markdown conversion tool.

    Only ``html_url`` is required. ``output_dir`` defaults to ``"output"``
    relative to the current working directory.

    The tool fetches the HTML document at ``html_url``, strips navigation,
    forms, and other non-content elements (aggressive preset), then converts
    the remaining content to clean Markdown using ATX-style headings.
    """

    html_url: str = Field(
        description=(
            "Fully qualified URL of the HTML page to download and convert. "
            "Must include the scheme (http:// or https://)."
        )
    )
    output_dir: str = Field(
        default="output",
        description=(
            "Directory where the resulting Markdown file will be saved. "
            "The filename is derived from the URL (e.g. 'page.html' → 'page.md'). "
            "The directory is created automatically if it does not exist."
        ),
    )

class HtmlToMarkdownOutput(BaseModel):
    """Structured output returned by the HTML-to-Markdown conversion tool.

    The ``markdown_file_path`` field contains the absolute path to the saved
    Markdown file and can be passed directly to downstream tools that need
    to read or process the converted content.
    """

    markdown_file_path: str = Field(
        description=(
            "Absolute path to the saved Markdown file on disk."
        )
    )
    filename: str = Field(
        description=(
            "Filename of the saved Markdown file, e.g. 'page.md'."
        )
    )
    html_url: str = Field(
        description="Original URL of the HTML source that was converted."
    )
