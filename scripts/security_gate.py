from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = (ROOT / "src", ROOT / "index.py")
FORBIDDEN_SOURCE_PATTERNS = {
    "TLS verification disabled": "verify" + "=False",
    "yt-dlp certificate checks disabled": "nocheck" + "certificate",
    "voice receive capability": "discord.ext." + "voice_recv",
    "shell execution enabled": "shell" + "=True",
}
REQUIRED_DOCKER_IGNORES = {".env", ".git", "venv", ".venv", "bot_env", "tests", "docs"}


def _python_files() -> list[Path]:
    files: list[Path] = []
    for root in SOURCE_ROOTS:
        files.extend(root.rglob("*.py") if root.is_dir() else [root])
    return files


def _tracked_files() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return {line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()}


def main() -> int:
    failures: list[str] = []

    for requirements_file in (ROOT / "requirements.txt", ROOT / "requirements-dev.txt"):
        for line_number, raw_line in enumerate(requirements_file.read_text(encoding="utf-8").splitlines(), 1):
            line = raw_line.strip()
            if line and not line.startswith("#") and "==" not in line:
                failures.append(f"{requirements_file.name}:{line_number}: dependency must use an exact pin")

    for path in _python_files():
        content = path.read_text(encoding="utf-8")
        for description, pattern in FORBIDDEN_SOURCE_PATTERNS.items():
            if re.search(re.escape(pattern), content, re.IGNORECASE):
                failures.append(f"{path.relative_to(ROOT)}: forbidden pattern: {description}")

    docker_ignores = {
        line.strip().rstrip("/")
        for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    missing_ignores = REQUIRED_DOCKER_IGNORES - docker_ignores
    if missing_ignores:
        failures.append(f".dockerignore is missing: {', '.join(sorted(missing_ignores))}")

    tracked = _tracked_files()
    forbidden_tracked = sorted(
        path for path in tracked if Path(path).name.startswith(".env") and Path(path).name != ".env.example"
    )
    if forbidden_tracked:
        failures.append(f"secret environment files are tracked: {', '.join(forbidden_tracked)}")

    if failures:
        print("Security gate failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Security gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
