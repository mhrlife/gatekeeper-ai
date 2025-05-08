import json
import os

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from structlog import get_logger

from evaluation.flag import flag, associate_flag

logger = get_logger()

dispatcher: Dispatcher = Dispatcher()

bot: Bot


async def init_telegram():
    global bot

    bot = Bot(token=os.getenv("BOT_TOKEN"))
    await dispatcher.start_polling(bot)


@dispatcher.message()
async def handle_message(message: Message) -> None:
    reason, action = await associate_flag(
        message.from_user.first_name,
        message.text,
    )

    action_text = None
    if action:
        action_text = action.model_dump_json(indent=2)

    if reason.classification != 'CLEAN':
        await message.reply(f"""
           ```json
           {reason.model_dump_json(indent=2)}
           ```

           ```json
           {action_text}
           ```

           """, parse_mode="MarkdownV2")

    logger.info("Message handled", message=message.text)
