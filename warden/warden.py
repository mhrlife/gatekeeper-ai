from typing import Callable, Any

from structlog import get_logger
from typing_extensions import Callable

from telegram.telegram import TelegramWarden

logger = get_logger()


class Warden:
    init_db: Callable[..., Any]
    telegram: TelegramWarden

    def __init__(self, telegram: TelegramWarden, init_db: Callable):
        self.telegram = telegram
        self.init_db = init_db

    async def start(self):
        logger.info("Starting Warden")

        await self.init_db()
        logger.info("Database initialized")

        await self.telegram.run()
