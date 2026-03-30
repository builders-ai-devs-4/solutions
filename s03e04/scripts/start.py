import subprocess
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent

HELP = """
Usage: python scripts/start.py [options]

Options:
  -h, --help        Show this help message and exit
  --reload          Enable auto-reload (development only)

Environment:
  Set APP_ENV before running to select config file:
    .env.development  (default)
    .env.test
    .env.production

  Windows PowerShell:
    $env:APP_ENV="production"; python scripts/start.py

  Linux/Mac:
    APP_ENV=production python scripts/start.py

Examples:
  python scripts/start.py
  python scripts/start.py --reload
  APP_ENV=production python scripts/start.py
""".strip()


def parse_args(argv: list[str]) -> bool:
    if "-h" in argv or "--help" in argv:
        print(HELP)
        sys.exit(0)

    unknown = [a for a in argv if a not in ("--reload",)]
    if unknown:
        print(f"Error: unknown option(s): {' '.join(unknown)}\n\n{HELP}")
        sys.exit(1)

    return "--reload" in argv


def start(reload: bool) -> int:
    app_env = os.getenv("APP_ENV", "development")

    # Load environment-specific config to get APP_HOST and APP_PORT
    load_dotenv(PROJECT_ROOT / f".env.{app_env}", override=False)
    # Load secrets — lowest priority, does not override env-specific values
    load_dotenv(PROJECT_ROOT / ".env", override=False)

    host = os.getenv("APP_HOST", "localhost")
    port = os.getenv("APP_PORT", "8000")

    cmd = [
        sys.executable, "-m", "uvicorn",
        "src.main:app",
        "--host", host,
        "--port", port,
        *(["--reload"] if reload else []),
    ]

    print(f"APP_ENV={app_env}")
    print(f"Running: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return result.returncode


if __name__ == "__main__":
    reload = parse_args(sys.argv[1:])
    sys.exit(start(reload))