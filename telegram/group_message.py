import asyncio
from datetime import datetime, timezone, timedelta

from aiogram import F
from aiogram.types import Message
from structlog import get_logger
from typing_extensions import List, Any, Dict

from database.models import GroupInfo, UserGroupMessage
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


@dispatcher.message(is_group_chat)
async def handle_message(message: Message) -> None:
    group_info, _ = await GroupInfo.get_or_create(id=message.chat.id, defaults={
        "name": message.chat.title,
        "description": message.chat.description or "",
    })

    user_message_history_qs = await UserGroupMessage.filter(
        user=message.from_user.id,
        group=group_info,
        message_created_at__gte=datetime.now(timezone.utc) - timedelta(minutes=5)
    ).order_by("-db_created_at").limit(10)

    # Await both tasks
    await asyncio.gather(
        process_flag_message(message, group_info, user_message_history_qs),
        log_current_chat_in_history(message)
    )


async def process_flag_message(message: Message, group: GroupInfo, messages_history: list[UserGroupMessage]):
    current_time_utc = datetime.now(timezone.utc)
    user_message_history: List[Dict[str, Any]] = [
        {
            "text": msg.text,
            "created_at": msg.message_created_at.isoformat(),
            "replied_to_text": msg.replied_to_message_text
        }
        for msg in messages_history
    ]

    (flag, action) = await associate_flag(
        first_name=message.from_user.first_name,
        message=message.text,
        group_title=group.name,
        group_context=group.rules_context,
        user_message_history=user_message_history,
        current_time=current_time_utc
    )

    logger.info("flag handled",
                message_text=message.text,
                reason=flag.classification if flag else None,
                action=action.user_message_action if action else None,
                action_message=action.message_to_user if action else None,
                confidence=action.confidence if action else None,
                )
    if action and action.user_message_action != "DISMISS":

        if flag.classification == "IRRELEVANT_TO_GROUP" and int(action.confidence) <= 3:
            return

        if int(action.confidence) <= 2:
            return

        await message.delete()
        await message.bot.send_message(
            chat_id=message.chat.id,
            text=f"""{message.from_user.first_name} - پیام سیستم:

{action.message_to_user}"""
        )


async def log_current_chat_in_history(message: Message):
    await UserGroupMessage.create(
        user_id=message.from_user.id,
        group_id=message.chat.id,
        message_id=message.message_id,
        text=message.text or message.caption or "",
        message_created_at=message.date,
        replied_to_message_id=message.reply_to_message.message_id if message.reply_to_message else None,
        replied_to_message_text=message.reply_to_message.text if message.reply_to_message else None,
    )

    logger.info("message logged", text=message.text)
