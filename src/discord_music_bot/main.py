from __future__ import annotations

import logging

from dotenv import load_dotenv

from discord_music_bot.adapters.discord import create_bot
from discord_music_bot.config import ConfigurationError, Settings


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main() -> int:
    load_dotenv()
    configure_logging()
    try:
        settings = Settings.from_env()
        bot = create_bot(settings)
    except ConfigurationError as exc:
        logging.getLogger(__name__).error("Configuration error: %s", exc)
        return 2
    bot.run(settings.discord_token, log_handler=None)
    return 0
