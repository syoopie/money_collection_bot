from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from utils.utils import get_debt_list_string

from bot.database import (
    add_or_update_user,
    get_user_groups,
    get_debt_lists_by_user_id,
    delete_debt_list,
)


async def handle_command_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the '/start' command.

    Args:
        update (telegram.Update): The update object containing information about the incoming message.
        context (telegram.ext.CallbackContext): The context object for the handler.

    Returns:
        None

    """
    user_id = update.effective_user.id
    user_username = update.effective_user.username
    user_first_name = update.effective_user.first_name
    user_last_name = update.effective_user.last_name

    # Add or update the user in the database
    add_or_update_user(
        user_id=user_id,
        username=user_username,
        first_name=user_first_name,
        last_name=user_last_name,
    )

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Welcome to the Debt Tracker Bot! Start by sending a list of debts in this format:\n\nMacDonalds\n98765432\n@user1 9.6\n@user2 5.4\n@user3 3.0",
    )


async def handle_command_example(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Send a message with the following format:\n\nDEBT_NAME\nPHONE_NUMBER\n@user_handle AMOUNT_OWED\n@user_handle AMOUNT_OWED\n@user_handle AMOUNT_OWED\n\nExample:\n\nMacDonalds\n98765432\n@user1 9.6\n@user2 5.4\n@user3 3.0",
    )


async def handle_command_get_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the '/getgroups' command. This command is used to get a list of groups the user is in.

    Args:
        update (telegram.Update): The update object containing information about the incoming message.
        context (telegram.ext.CallbackContext): The context object for the handler.

    Returns:
        None
    """
    user_id = update.effective_user.id
    groups = get_user_groups(user_id)
    if groups:
        groups_message = "You're in the following groups:\n\n"
        groups_message += "\n".join([group.get("group_name") for group in groups])
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=groups_message,
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="I couldn't find any groups. If we are in the same group, please make sure I have access to messages and that you have sent a message in the group.",
        )


async def handle_command_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the '/show' command by retrieving the debt lists for the user and sending them as a message.

    Args:
        update (Update): The update object containing information about the incoming message.
        context (ContextTypes.DEFAULT_TYPE): The context object containing the bot's context.

    Returns:
        None
    """
    debt_lists = get_debt_lists_by_user_id(update.effective_user.id)
    if debt_lists:
        message = "Here are your debt lists:\n\n"
        message += "\n\n###################################\n\n".join(
            [get_debt_list_string(list_id) for list_id in debt_lists]
        )
    else:
        message = "You do not have any debt lists."

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
    )


async def handle_command_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the command "/clear" to clear all debt lists made by the user.

    Args:
        update (Update): The update object containing information about the incoming message.
        context (ContextTypes.DEFAULT_TYPE): The context object containing bot-related information.

    Returns:
        None
    """
    # Send a confirmation message to the user with a button to press to confirm the action
    confirm_button = InlineKeyboardButton("Confirm ✅", callback_data="confirmClear")
    keyboard = [[confirm_button]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Are you sure you want to delete all your debt lists?",
        reply_markup=reply_markup,
    )


async def handle_command_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the command "/help" to show the user a list of available commands.

    Args:
        update (Update): The update object containing information about the incoming message.
        context (ContextTypes.DEFAULT_TYPE): The context object containing bot-related information.

    Returns:
        None
    """
    message = "Here are the available commands:\n\n"
    message += "/getgroups - Get a list of groups you are in\n"
    message += "/show - Show all your debt lists\n"
    message += "/clear - Clear all your debt lists\n"
    message += "/help - Show this message\n"
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
    )


async def handle_unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle unknown commands.

    Args:
        update (Update): The update object containing information about the incoming message.
        context (ContextTypes.DEFAULT_TYPE): The context object for the current conversation.

    Returns:
        None
    """
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Sorry, I dont understand that command. Use /help for a list of commands",
    )
