from aiogram import F, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message


class ManageGroupContext(StatesGroup):
    context = State()  # Changed to proper assignment


async def on_manage_group_pressed(
        cq: CallbackQuery, state: FSMContext
):
    print("alo?")
    await cq.message.answer("Please provide your group context:")
    await state.set_state(ManageGroupContext.context)


async def process_name(message: Message, state: FSMContext) -> None:
    await message.answer("Group context received. Thank you!")
    await state.clear()


def register_handlers(dp: Dispatcher):
    dp.callback_query.register(on_manage_group_pressed, F.data == "manage_group")
    dp.message.register(process_name, ManageGroupContext.context)
