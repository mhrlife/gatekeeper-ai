from aiogram import F
from aiogram.types import Message
from structlog import get_logger
from datetime import datetime, timezone

from database.models import GroupInfo, UserGroupMessage, User
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
            text=message.text or message.caption or "", # Handle media captions
            message_created_at=message.date, # This is already timezone-aware (UTC) from aiogram
            replied_to_message_id=replied_to_message_id,
            replied_to_message_text=replied_to_message_text
        )
        logger.debug("Message saved", user_id=db_user.id, group_id=group_info.id, message_id=message.message_id)

        # Prune old messages: Keep only the last 10 for this user in this group
        user_messages_in_group_qs = UserGroupMessage.filter(user=db_user, group=group_info).order_by("-db_created_at")
        count = await user_messages_in_group_qs.count()
        
        if count > 10:
            messages_to_delete_qs = user_messages_in_group_qs.offset(10) # Get messages beyond the 10th
            async for msg_to_delete in messages_to_delete_qs:
                 await msg_to_delete.delete()
            logger.debug(f"Pruned {await messages_to_delete_qs.count()} old messages for user {db_user.id} in group {group_info.id}")
        
        # Fetch the last 10 messages for context (ordered by message creation time, oldest of the 10 first)
        recent_messages_qs = await UserGroupMessage.filter(
            user=db_user, group=group_info
        ).order_by("message_created_at").limit(10) # Tortoise applies limit before ordering if not careful, but this should be fine.
                                                 # For safety, could do order_by("-message_created_at").limit(10) then reverse in Python.
                                                 # Let's stick to the user's provided logic for now.
        
        # The user's logic was: order_by("-message_created_at").limit(10) then reverse.
        # Let's refine to ensure we get the *actual* last 10 by creation time, then format.
        
        # Fetch the 10 most recent messages by their actual creation timestamp
        ordered_recent_messages = await UserGroupMessage.filter(
            user=db_user, group=group_info
        ).order_by("-message_created_at").limit(10)
        
        # Then reverse this list so the oldest of these 10 appears first for the LLM
        ordered_recent_messages.reverse()


        user_message_history = [
            {
                "text": msg.text,
                "created_at": msg.message_created_at.isoformat(), # Use ISO format for LLM
                "replied_to_text": msg.replied_to_message_text
            }
            for msg in ordered_recent_messages # Use the correctly ordered list
        ]
        logger.debug(f"Fetched {len(user_message_history)} messages for history for user {db_user.id} in group {group_info.id}")

    else:
        logger.warning("GroupInfo not found for chat ID", chat_id=message.chat.id, chat_title=message.chat.title)
        # If group_info is not found, we can't save the message to UserGroupMessage tied to a group
        # or retrieve history for that group.
        if message.chat.title:
            group_title = message.chat.title
        # user_message_history remains empty

    current_time_utc = datetime.now(timezone.utc)

    reason, action = await associate_flag(
        first_name=message.from_user.first_name,
        message=message.text or message.caption or "",
        group_title=group_title,
        group_context=group_context,
        user_message_history=user_message_history,
        current_time=current_time_utc
    )

    action_text = None
    if action:
        action_text = action.model_dump_json(indent=2)

    if action and action.severity_assessment != "DISMISS":
        await message.reply(f"""مدیر هوشمند:

{action.message_to_user}""")

    logger.info("Message handled", message_text=message.text, reason=reason.classification if reason else None, action=action.severity_assessment if action else None)
