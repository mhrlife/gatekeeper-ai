from aiogram import F
from aiogram.types import Message
from structlog import get_logger

from database.models import GroupInfo
from evaluation.flag import associate_flag
from telegram.dispatcher import dispatcher

logger = get_logger()

is_group_chat = F.chat.func(lambda chat: chat.id < 0)


@dispatcher.message(is_group_chat & F.text == "warden:gp_id")
async def get_group_id(message: Message) -> None:
    await message.bot.send_message(
        chat_id=message.from_user.id,
        text=f"Your group ID is: {message.chat.id}",
    )

    await message.delete()

    print("alo?")


@dispatcher.message(is_group_chat)
async def handle_message(message: Message) -> None:
    group_info = await GroupInfo.get_or_none(id=message.chat.id)

    group_title = "Unknown Group"
    group_context = "No specific context provided for this group."

    if group_info:
        group_title = group_info.name
        group_context = group_info.rules_context or "No specific context provided for this group."
    else:
        logger.warning("GroupInfo not found for chat ID", chat_id=message.chat.id, chat_title=message.chat.title)
        if message.chat.title:
            group_title = message.chat.title

    reason, action = await associate_flag(
        message.from_user.first_name,
        message.text,
        group_title=group_title,
        group_context=group_context,
    )

    action_text = None
    if action:
        action_text = action.model_dump_json(indent=2)

    if action and action.severity_assessment != "DISMISS":
        await message.reply(f"""مدیر هوشمند:

{action.message_to_user}""")

    logger.info("Message handled", message=message.text)
