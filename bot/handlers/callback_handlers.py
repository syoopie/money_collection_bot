from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.utils import get_debt_list_string

from bot.database import (
    delete_debt_list,
    get_debt_lists_by_user_id,
    get_user_groups,
    update_debt_list_status,
    update_debt_list_group,
    get_group_name,
    get_debt_list_pending_status,
    get_debt_list_name,
    get_debt_status,
    update_debt_status,
)


async def handle_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the callback for confirming a debt list.

    Args:
        update (Update): The update object containing the callback data.
        context (ContextTypes.DEFAULT_TYPE): The context object for handling the callback.

    Returns:
        None
    """
    callback_query = update.callback_query
    await callback_query.answer()  # Answer the callback query to stop the loading animation on the button.

    # Pull out the debt list ID from the callback data
    debt_list_id = callback_query.data.split(":")[1]

    if not get_debt_list_pending_status(debt_list_id):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="That debt list does not exist or has already been confirmed",
        )
        return

    # Get all the group the user is in and create a button for each group
    user_id = update.effective_user.id
    groups = get_user_groups(user_id)

    if not groups:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You are not in any groups. Add me to a group and send a message to the group (so I know you are in the group)",
        )
        return

    buttons = [
        [
            InlineKeyboardButton(
                group.get("group_name"),
                callback_data=f"sendToGroup:{group.get('group_id')}:{debt_list_id}",
            )
        ]
        for group in groups
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Choose which group to send this list to:",
        reply_markup=reply_markup,
    )

    # Update the debt list status to confirmed in the database
    update_debt_list_status(debt_list_id, is_pending=False)

    # Remove last line from original message
    message: str = callback_query.message.text
    message = message[: message.rfind("\n")]

    # Remove confirm button from the message
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=callback_query.message.message_id,
        text=message,
    )


async def handle_send_to_group_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """
    Handles the callback when a user chooses which group to send a debt list to.

    Args:
        update (Update): The update object containing information about the callback query.
        context (ContextTypes.DEFAULT_TYPE): The context object containing the bot and other information.

    Returns:
        None
    """
    await update.callback_query.answer()  # Answer the callback query to stop the loading animation on the button.

    _, group_id, debt_list_id = update.callback_query.data.split(":")

    message = get_debt_list_string(debt_list_id)
    pay_button = InlineKeyboardButton("✅", callback_data=f"pay:{debt_list_id}")
    unpay_button = InlineKeyboardButton("❌", callback_data=f"unpay:{debt_list_id}")
    buttons = [[pay_button, unpay_button]]
    reply_markup = InlineKeyboardMarkup(buttons)

    await context.bot.send_message(
        chat_id=group_id,
        text=message,
        reply_markup=reply_markup,
    )

    update_debt_list_group(debt_list_id, group_id)

    # Modify the message to indicate that the debt list has been sent to the group
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=update.callback_query.message.message_id,
        text="The debt list has been sent to:\n\n" + get_group_name(group_id),
    )


async def handle_pay_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the callback when a user marks a debt as paid.

    Args:
        update (Update): The update object containing information about the callback query.
        context (ContextTypes.DEFAULT_TYPE): The context object for handling the callback.

    Returns:
        None
    """
    await update.callback_query.answer()  # Answer the callback query to stop the loading animation on the button.

    _, list_id = update.callback_query.data.split(":")
    user_name = "@" + update.effective_user.username

    if get_debt_status(list_id, user_name):
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text=f"You have already marked this debt ({get_debt_list_name(list_id)}) as paid.",
        )
        return

    group_id = update.effective_chat.id
    user_id = update.effective_user.id

    update_debt_status(list_id, user_name, True)

    message = get_debt_list_string(list_id)
    await context.bot.edit_message_text(
        chat_id=group_id,
        message_id=update.callback_query.message.message_id,
        text=message,
        reply_markup=update.callback_query.message.reply_markup,  # Keep the same inline keyboard
    )

    # Send message to user to confirm payment
    await context.bot.send_message(
        chat_id=user_id,
        text=f"You have marked the debt ({get_debt_list_name(list_id)}) as paid.",
    )


async def handle_unpay_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the callback when a user marks a debt as unpaid.

    Args:
        update (Update): The update object containing information about the callback query.
        context (ContextTypes.DEFAULT_TYPE): The context object containing the bot's context.

    Returns:
        None
    """
    await update.callback_query.answer()  # Answer the callback query to stop the loading animation on the button.

    _, list_id = update.callback_query.data.split(":")
    user_name = "@" + update.effective_user.username

    if not get_debt_status(list_id, user_name):
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text=f"You have already marked this debt ({get_debt_list_name(list_id)}) as unpaid.",
        )
        return

    group_id = update.effective_chat.id
    user_id = update.effective_user.id

    update_debt_status(list_id, user_name, False)

    message = get_debt_list_string(list_id)
    await context.bot.edit_message_text(
        chat_id=group_id,
        message_id=update.callback_query.message.message_id,
        text=message,
        reply_markup=update.callback_query.message.reply_markup,  # Keep the same inline keyboard
    )

    # Send message to user to confirm payment
    await context.bot.send_message(
        chat_id=user_id,
        text=f"You have marked the debt ({get_debt_list_name(list_id)}) as unpaid.",
    )


async def handle_confirm_clear_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """
    Handles the callback when a user confirms using the /clear command.

    Args:
        update (Update): The update object containing information about the callback query.
        context (ContextTypes.DEFAULT_TYPE): The context object containing the bot's context.

    Returns:
        None
    """
    await update.callback_query.answer()  # Answer the callback query to stop the loading animation on the button.

    debt_lists = get_debt_lists_by_user_id(update.effective_user.id)
    if debt_lists:
        for list_id in debt_lists:
            delete_debt_list(list_id)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="All your debt lists have been cleared.",
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You have no debt lists to clear.",
        )
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=update.callback_query.message.message_id,
        text=update.callback_query.message.text,
    )
