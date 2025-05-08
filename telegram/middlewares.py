from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message

from database.models import User


class UserMiddleware(BaseMiddleware):
    """
    This middleware saves the user to the database if they don't exist,
    or updates their first name if it has changed.
    """

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
            current_first_name = event.from_user.first_name

            user, created = await User.update_or_create(
                id=user_id,
                defaults={"first_name": current_first_name}
            )

            data["db_user"] = user
            data["user_created"] = created

        return await handler(event, data)
