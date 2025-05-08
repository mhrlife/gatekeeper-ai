import asyncio
import os

from dotenv import load_dotenv
from structlog import get_logger

from database.database import init_db
from telegram.telegram import init_telegram
from warden.warden import Warden

logger = get_logger()

if __name__ == '__main__':
    load_dotenv()

    warden = Warden(
        init_telegram=init_telegram,
        init_db=init_db
    )
    asyncio.run(
        warden.start()
    )
