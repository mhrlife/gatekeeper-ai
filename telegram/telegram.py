from aiogram import Bot, Dispatcher
from aiogram.types import Message
from structlog import get_logger

logger = get_logger()

dispatcher: Dispatcher = Dispatcher()


class TelegramWarden:
    def __init__(self, token: str):
        self.token = token
        self.bot = Bot(token=self.token)

    async def run(self) -> None:
        logger.info("Starting Telegram async worker")
        await dispatcher.start_polling(self.bot)

    @staticmethod
    @dispatcher.message()
    async def handle_message(message: Message) -> None:
        logger.debug("Received message",
                     message=message.text,
                     fromUser=message.from_user.id,
                     chatId=message.chat.id)

        await message.reply("Hello! I'm your Telegram bot.")
