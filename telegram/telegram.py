import os

from aiogram import Bot, F
from aiogram.types import Message
from structlog import get_logger

from database.models import GroupInfo, User
from telegram import dispatcher
from telegram.middlewares import UserMiddleware
from telegram.keyboard import get_main_menu_keyboard

logger = get_logger()

# Register the UserMiddleware
dispatcher.message.middleware(UserMiddleware())

bot: Bot


async def init_telegram():
    global bot

    bot = Bot(token=os.getenv("BOT_TOKEN"))

    await dispatcher.start_polling(bot)


@dispatcher.message(F.chat.func(lambda chat: chat.id > 0))  # For private chats
async def start_command(message: Message, db_user: User) -> None:
    groups = await GroupInfo.filter(owner_id=db_user.id)
    await message.answer(
        "Hello. How can I assist you?",
        reply_markup=get_main_menu_keyboard(groups)
    )
