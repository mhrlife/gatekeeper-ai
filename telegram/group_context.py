from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message

from database.models import GroupInfo
from telegram.dispatcher import dispatcher
from .keyboard import get_group_management_keyboard, get_edit_context_keyboard, get_main_menu_keyboard


###### Manage Group Context (New Implementation) #######

class ManageGroupContext(StatesGroup):
    viewing_group = State()
    editing_context = State()


@dispatcher.callback_query(F.data.startswith("manage_group_"))
async def on_group_selected_handler(cq: CallbackQuery, state: FSMContext):
    group_id = int(cq.data.split("_")[-1])
    group = await GroupInfo.get_or_none(id=group_id)

    if not group:
        await cq.answer("Group not found.", show_alert=True)
        return

    await state.update_data(current_group_id=group_id)
    await cq.message.edit_text(
        f"Group: {group.name}\n"
        f"Description: {group.description or 'N/A'}\n"
        f"Current Context: \n{group.rules_context or 'Not set'}",
        reply_markup=get_group_management_keyboard(group_id)
    )
    await state.set_state(ManageGroupContext.viewing_group)


@dispatcher.callback_query(F.data.startswith("edit_group_context_"), ManageGroupContext.viewing_group)
async def on_edit_context_pressed_handler(cq: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    group_id = data.get("current_group_id")

    if group_id is None:
        await cq.answer("Error: Group ID not found in state. Please go back and try again.", show_alert=True)
        try:
            group_id = int(cq.data.split("_")[-1])
            await state.update_data(current_group_id=group_id)
        except (IndexError, ValueError):
            await cq.message.edit_text("Could not identify the group. Please return to the main menu.")
            await state.clear()
            return

    group = await GroupInfo.get_or_none(id=group_id)
    if not group:
        await cq.answer("Group not found.", show_alert=True)
        await state.clear()
        groups = await GroupInfo.filter(owner_id=cq.from_user.id)
        await cq.message.edit_text("Please select a group:", reply_markup=get_main_menu_keyboard(groups))
        return

    await cq.message.edit_text(
        f"Current context for {group.name}:\n\n"
        f"{group.rules_context or 'Not set'}\n\n"
        f"Please send the new context for this group.",
        reply_markup=get_edit_context_keyboard()
    )
    await state.set_state(ManageGroupContext.editing_context)


@dispatcher.message(ManageGroupContext.editing_context)
async def process_new_context_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    group_id = data.get("current_group_id")

    if group_id is None:
        await message.answer("Error: Could not identify the group. Please start over.")
        await state.clear()
        return

    group = await GroupInfo.get_or_none(id=group_id)
    if not group:
        await message.answer("Error: Group not found. Please start over.")
        await state.clear()
        return

    group.rules_context = message.text
    await group.save()

    await message.answer("Group context updated successfully.")
    
    await message.answer(
        f"Group: {group.name}\n"
        f"Description: {group.description or 'N/A'}\n"
        f"Current Context: \n{group.rules_context or 'Not set'}",
        reply_markup=get_group_management_keyboard(group_id)
    )
    await state.set_state(ManageGroupContext.viewing_group)


@dispatcher.callback_query(F.data == "cancel_edit_context", ManageGroupContext.editing_context)
async def on_cancel_edit_context_handler(cq: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    group_id = data.get("current_group_id")

    if group_id is None:
        await cq.answer("Error: Could not identify the group. Please return to main menu.", show_alert=True)
        await state.clear()
        groups_list = await GroupInfo.filter(owner_id=cq.from_user.id)
        await cq.message.edit_text("Please select a group:", reply_markup=get_main_menu_keyboard(groups_list))
        return

    group = await GroupInfo.get_or_none(id=group_id)
    if not group:
        await cq.answer("Group not found.", show_alert=True)
        await state.clear()
        groups_list = await GroupInfo.filter(owner_id=cq.from_user.id)
        await cq.message.edit_text("Please select a group:", reply_markup=get_main_menu_keyboard(groups_list))
        return

    await cq.message.edit_text(
        f"Group: {group.name}\n"
        f"Description: {group.description or 'N/A'}\n"
        f"Current Context: \n{group.rules_context or 'Not set'}",
        reply_markup=get_group_management_keyboard(group_id)
    )
    await state.set_state(ManageGroupContext.viewing_group)


@dispatcher.callback_query(F.data == "back_to_main_menu", ManageGroupContext.viewing_group)
async def on_back_to_main_menu_handler(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    user_groups = await GroupInfo.filter(owner_id=cq.from_user.id)
    await cq.message.edit_text(
        "Hello. How can I assist you?",
        reply_markup=get_main_menu_keyboard(user_groups)
    )


###### Add Group #######

class AddGroup(StatesGroup):
    forward_message = State()


@dispatcher.callback_query(F.data == "add_group")
async def on_add_group_pressed(
        cq: CallbackQuery, state: FSMContext
):
    await cq.message.answer(
        "Please enter the group ID:\n"
        "To get the group ID, send this message to the group:\n\n"
        "warden:gp_id "
    )
    await state.set_state(AddGroup.forward_message)


@dispatcher.message(AddGroup.forward_message)
async def process_forward_message(
        message: Message, state: FSMContext
):
    try:
        group_id = int(message.text)
        if group_id >= 0:
            await message.answer("Please send me the group ID again. Group IDs are negative numbers.")
            return
    except ValueError:
        await message.answer("Invalid group ID. Please try again.")
        return

    try:
        admins = await message.bot.get_chat_administrators(
            chat_id=group_id,
        )
    except Exception as e:
        await message.answer(f"Could not verify admin status for group {group_id}. Ensure the bot is a member of the group. Error: {e}")
        return


    if not any(admin.user.id == message.from_user.id for admin in admins):
        await message.answer(
            "You are not an admin in this group. Please contact the group admin to add me, or ensure you are an admin."
        )
        return

    group = await GroupInfo.filter(id=group_id).first()
    if group:
        await message.answer("This group is already registered.")
        await state.clear()
        return

    try:
        tg_group = await message.bot.get_chat(group_id)
    except Exception as e:
        await message.answer(f"Could not fetch group information for {group_id}. Error: {e}")
        await state.clear()
        return


    group = await GroupInfo.create(
        id=group_id,
        name=tg_group.title or "Unknown Group",
        description=tg_group.description or "",
        rules_context="",
        owner_id=message.from_user.id,
    )

    await message.answer(
        f"Group {group.name} ({group_id}) has been added successfully."
    )
    await state.clear()
