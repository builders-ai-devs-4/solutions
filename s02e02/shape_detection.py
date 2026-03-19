import base64
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser

VALID_CHARS = set("│─└┘┌┐├┤┬┴┼ ")

PROMPT = """You are looking at a single cell of an electrical wiring diagram.
Inside the cell there is a path/line connecting the edges.
Reply with ONLY one Unicode character describing the shape of the path.
No other words.

Allowed characters and their meaning:
─  horizontal line (connects left and right edge)
│  vertical line (connects top and bottom edge)
┌  corner: goes right and down (top-left corner)
┐  corner: goes left and down (top-right corner)
└  corner: goes right and up (bottom-left corner)
┘  corner: goes left and up (bottom-right corner)
├  T-junction: goes right, up and down (from left edge)
┤  T-junction: goes left, up and down (from right edge)
┬  T-junction: goes left, right and down (from top edge)
┴  T-junction: goes left, right and up (from bottom edge)
┼  cross: connects all four edges
   space: empty cell, no line present

Examples (think of it as rectangle corners):
- Line exits ONLY to the right and downward → ┌
- Line exits ONLY to the left and downward → ┐
- Line exits ONLY to the right and upward → └
- Line exits ONLY to the left and upward → ┘
- Horizontal line from left to right → ─
- Vertical line from top to bottom → │
- No line present → (space)"""


def encode_image(image_path: str) -> tuple[str, str]:
    """Encode an image file to base64 and determine its MIME media type.

    The media type is required by the OpenAI vision API when sending
    base64-encoded images — omitting it results in a 400 error.

    Args:
        image_path: Path to the image file (jpg, jpeg, png, webp).

    Returns:
        A tuple of (base64_string, media_type), e.g.
        ("iVBOR...", "image/png").
    """
    ext = Path(image_path).suffix.lstrip(".").lower()
    media_type = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return b64, media_type


def classify_cell(image_path: str, model_name: str = "gpt-5-mini") -> str:
    """Classify a single wiring diagram cell image into a Unicode box-drawing character.

    Sends the image to the OpenAI vision model with a structured prompt and
    few-shot examples. Uses temperature=0 for deterministic output and
    max_tokens=5 to physically prevent the model from generating any
    explanation beyond the single character.

    Args:
        image_path: Path to the cell image file.
        model_name: OpenAI model to use. Defaults to "gpt-5-mini" which
            offers better accuracy and ~10× lower cost than gpt-4o for
            this type of classification task.

    Returns:
        A single Unicode character from VALID_CHARS, or a space if the
        cell is empty or the model returned an unexpected value.
    """
    llm = ChatOpenAI(
        model=model_name,
        max_tokens=10,   # single char = 1 token; hard limit prevents any explanation
        temperature=0,  # deterministic — same image always returns same result
    )

    b64, media_type = encode_image(image_path)

    message = HumanMessage(
        content=[
            {"type": "text", "text": PROMPT},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{b64}",
                    "detail": "low",  # sufficient for small tiles, saves ~75% image tokens
                },
            },
        ]
    )

    chain = llm | StrOutputParser()
    result = chain.invoke([message]).strip()

    if result and result[0] in VALID_CHARS:
        return result[0]
    return " "


def classify_grid(
    cell_paths: list[list[str]],
    model_name: str = "gpt-5-mini",
) -> list[list[str]]:
    """Classify all cells in a 2D grid of wiring diagram images.

    Processes cells row by row, left to right. For large grids consider
    switching to an async implementation to parallelize API calls.

    Args:
        cell_paths: 2D list of file paths, where cell_paths[row][col]
            points to the image for that grid position.
        model_name: OpenAI model passed to classify_cell for each cell.

    Returns:
        2D list of Unicode characters mirroring the shape of cell_paths.

    Example:
        grid = classify_grid([
            ["cell_0_0.jpg", "cell_0_1.jpg"],
            ["cell_1_0.jpg", "cell_1_1.jpg"],
        ])
        # grid → [['┌', '─'], ['│', ' ']]
    """
    return [
        [classify_cell(path, model_name) for path in row]
        for row in cell_paths
    ]
