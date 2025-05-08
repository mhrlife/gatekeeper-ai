import asyncio
from datetime import datetime, timezone, timedelta

from aiogram import F
from aiogram.enums import ParseMode
from aiogram.types import Message
from structlog import get_logger

from database.models import GroupInfo, UserGroupMessage, User
from evaluation.flag import associate_flag
from evaluation.tools import invoke_react_agent_for_tool_use  # Updated import
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
    # Ensure the user exists in the User table. UserMiddleware should handle this for private chats.
    # For group messages, we might need to explicitly create/update the user if not already present.
    db_user, _ = await User.update_or_create(
        id=message.from_user.id,
        defaults={"first_name": message.from_user.first_name}
    )
    logger.debug("User retrieved/created for group message", user_id=db_user.id, group_id=message.chat.id)

    group_title = "Unknown Group"
    group_context = "No specific context provided for this group."
    user_message_history = []

    if group_info:
        group_title = group_info.name
        group_context = group_info.rules_context or "No specific context provided for this group."

        # Save the current message
        replied_to_message_id = None
        replied_to_message_text = None
        if message.reply_to_message:
            replied_to_message_id = message.reply_to_message.message_id
            replied_to_message_text = message.reply_to_message.text or message.reply_to_message.caption

        await UserGroupMessage.create(
            user=db_user,
            group=group_info,
            message_id=message.message_id,
            text=message.text or message.caption or "",  # Handle media captions
            message_created_at=message.date,  # This is already timezone-aware (UTC) from aiogram
            replied_to_message_id=replied_to_message_id,
            replied_to_message_text=replied_to_message_text
        )
        logger.debug("Message saved", user_id=db_user.id, group_id=group_info.id, message_id=message.message_id)

        # Prune old messages: Keep only the last 10 for this user in this group
        user_messages_in_group_qs = UserGroupMessage.filter(user=db_user, group=group_info).order_by("-db_created_at")
        count = await user_messages_in_group_qs.count()

        if count > 10:
            messages_to_delete_qs = user_messages_in_group_qs.offset(10)  # Get messages beyond the 10th
            async for msg_to_delete in messages_to_delete_qs:
                await msg_to_delete.delete()
            logger.debug(
                f"Pruned {await messages_to_delete_qs.count()} old messages for user {db_user.id} in group {group_info.id}")

        # User's messages in this group, in the last 5 minutes
        ordered_recent_messages = await UserGroupMessage.filter(
            user=db_user, group=group_info, message_created_at__gte=datetime.now(timezone.utc) - timedelta(minutes=5)
        ).order_by("-message_created_at").limit(10)

        ordered_recent_messages.reverse()

        user_message_history = [
            {
                "text": msg.text,
                "created_at": msg.message_created_at.isoformat(),
                "replied_to_text": msg.replied_to_message_text
            }
            for msg in ordered_recent_messages
        ]
        logger.debug(
            f"Fetched {len(user_message_history)} messages for history for user {db_user.id} in group {group_info.id}")

    else:
        logger.warning("GroupInfo not found for chat ID", chat_id=message.chat.id, chat_title=message.chat.title)
        if message.chat.title:
            group_title = message.chat.title

    current_time_utc = datetime.now(timezone.utc)
    user_input_text = message.text or message.caption or ""

    # Run flag association and tool call detection concurrently
    flag_task = associate_flag(
        first_name=message.from_user.first_name,
        message=user_input_text,
        group_title=group_title,
        group_context=group_context,
        user_message_history=user_message_history,
        current_time=current_time_utc
    )
    tool_call_task = invoke_react_agent_for_tool_use(user_input_text)  # Updated function call

    # Await both tasks
    results = await asyncio.gather(flag_task, tool_call_task, return_exceptions=True)

    # Process flag_task result
    flag_result = results[0]
    reason = None
    action = None
    if isinstance(flag_result, Exception):
        logger.error("Error in associate_flag", error=flag_result, exc_info=True)
    elif flag_result:
        reason, action = flag_result

    # Process tool_call_task result
    tool_response_str = None
    tool_call_result = results[1]
    if isinstance(tool_call_result, Exception):
        logger.error("Error in process_tool_call_if_detected", error=tool_call_result,
                     exc_info=True)  # Kept original log message for now
    elif tool_call_result:
        tool_response_str = tool_call_result

    # Handle tool response
    if tool_response_str:
        await message.reply(f"{tool_response_str}", parse_mode=ParseMode.MARKDOWN)
        logger.info("Tool call processed", tool_response_length=len(tool_response_str))

    # Handle moderation action
    if action and action.severity_assessment != "DISMISS":
        await message.reply(f"""مدیر هوشمند:

{action.message_to_user}""")

    logger.info("Message handled",
                message_text=user_input_text,
                reason=reason.classification if reason else None,
                action=action.severity_assessment if action else None,
                tool_called=bool(tool_response_str))
