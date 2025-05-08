import os

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from structlog import get_logger

from telegram.group_context import register_handlers
from telegram.keyboard import main_menu

logger = get_logger()

dispatcher: Dispatcher = Dispatcher()

bot: Bot


async def init_telegram():
    global bot

    bot = Bot(token=os.getenv("BOT_TOKEN"))
    register_handlers(dispatcher)
    await dispatcher.start_polling(bot)


@dispatcher.message(Command("start"))
async def start(message: Message) -> None:
    await message.answer("Hello, I'm your assistant bot!", reply_markup=main_menu())
