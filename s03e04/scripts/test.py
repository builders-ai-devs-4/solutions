import subprocess
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

HELP = """
Usage: python scripts/test.py [options] [-- pytest_args]

Options:
  -h, --help        Show this help message and exit

Pytest args:
  Everything after '--' is passed directly to pytest.

Examples:
  python scripts/test.py
  python scripts/test.py -- -k test_health_check
  python scripts/test.py -- -x --tb=short
""".strip()


def parse_args(argv: list[str]) -> list[str]:
    if "-h" in argv or "--help" in argv:
        print(HELP)
        sys.exit(0)

    separator = argv.index("--") if "--" in argv else len(argv)
    unknown = [a for a in argv[:separator] if a.startswith("-")]
    if unknown:
        print(f"Error: unknown option(s): {' '.join(unknown)}\n\n{HELP}")
        sys.exit(1)

    return argv[separator + 1:] if "--" in argv else []


def run_tests(pytest_args: list[str]) -> int:
    env = os.environ.copy()
    env["APP_ENV"] = "test"

    cmd = [sys.executable, "-m", "pytest", "tests/", "-v", *pytest_args]

    print(f"APP_ENV=test")
    print(f"Running: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, env=env, cwd=str(PROJECT_ROOT))
    return result.returncode


if __name__ == "__main__":
    pytest_args = parse_args(sys.argv[1:])
    sys.exit(run_tests(pytest_args))