from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.utils import parse_debt_list

from bot.database import (
    add_or_update_user,
    add_or_update_group,
    is_user_in_group,
    associate_user_with_group,
    add_debt_list,
    add_or_update_debt,
    associate_debt_with_debt_list,
)


async def handle_parse_and_check_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """
    Handles the parsing and checking of user input for debt list creation.

    Args:
        update (Update): The update object containing the user's message.
        context (ContextTypes.DEFAULT_TYPE): The context object for handling the update.

    Returns:
        None
    """
    success, result = parse_debt_list(update.message.text)
    user_id = update.effective_user.id

    if not success:
        await context.bot.send_message(chat_id=user_id, text=result)
        return

    # Add the debt list to the database
    debt_name, phone_number, debts = result
    # Create new debt list
    debt_list_id = add_debt_list(
        user_id=user_id, debt_name=debt_name, phone_number=phone_number
    )

    # Create the debts
    for debt in debts:
        debt_id = add_or_update_debt(
            list_id=debt_list_id,
            owed_by_user_name=debt[0],
            amount=debt[1],
        )
        associate_debt_with_debt_list(debt_id, debt_list_id)

    message = "Here's the debt list you entered:\n\n"
    for debt in debts:
        message += f"{debt[0]} - {debt[1]}\n"
    message += "\nPlease confirm that the information is correct."

    # TODO: Abstract this?
    # Create inline keyboard with confirm button
    confirm_button = InlineKeyboardButton(
        "Confirm ✅", callback_data=f"confirmInput:{debt_list_id}"
    )
    keyboard = [[confirm_button]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=reply_markup,
    )


async def handle_save_user_group_info(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """
    Handles saving user and group information. This function should be called when a user sends a message in a group. It saves the user and group information in the database and associates the user with the group.

    Args:
        update (telegram.Update): The update object containing information about the incoming message.
        context (telegram.ext.CallbackContext): The context object for handling the callback.

    Returns:
        None
    """
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    last_name = update.effective_user.last_name
    group_id = update.effective_chat.id
    chat_title = update.effective_chat.title
    chat_type = (
        update.effective_chat.type
    )  # 'private', 'group', 'supergroup', or 'channel'

    if is_user_in_group(user_id=user_id, group_id=group_id):
        return

    add_or_update_user(
        user_id=user_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
    )

    add_or_update_group(
        group_id=group_id,
        group_name=chat_title,
        group_type=chat_type,
    )

    associate_user_with_group(user_id=user_id, group_id=group_id)
