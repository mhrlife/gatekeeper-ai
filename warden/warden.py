from typing import Any

from structlog import get_logger
from typing_extensions import Callable

logger = get_logger()


class Warden:
    init_db: Callable[..., Any]
    telegram: Callable[..., Any]

    def __init__(self, init_telegram: Callable, init_db: Callable):
        self.telegram = init_telegram
        self.init_db = init_db

    async def start(self):
        logger.info("Starting Warden")

        await self.init_db()
        logger.info("Database initialized")

        await self.telegram()
