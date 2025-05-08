from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List

from database.models import GroupInfo


def get_main_menu_keyboard(groups: List[GroupInfo]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    for group in groups:
        kb.button(text=group.name, callback_data=f"manage_group_{group.id}")

    kb.button(text="Add Group", callback_data="add_group")
    kb.adjust(1)  # Adjust to show one button per row for groups, then Add Group
    return kb.as_markup()


def get_group_management_keyboard(group_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Edit Context", callback_data=f"edit_group_context_{group_id}")
    kb.button(text="Back", callback_data="back_to_main_menu")
    kb.adjust(1)
    return kb.as_markup()


def get_edit_context_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Cancel", callback_data="cancel_edit_context")
    return kb.as_markup()
