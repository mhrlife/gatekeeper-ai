from aiogram.types import Message
from structlog import get_logger

from evaluation.flag import associate_flag
from telegram.telegram import dispatcher

logger = get_logger()


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
