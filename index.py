import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from discord_music_bot.main import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
