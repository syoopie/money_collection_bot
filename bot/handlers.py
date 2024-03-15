from typing import List, Tuple
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.utils import parse_debt_list, get_debt_list_string

from bot.database import (
    add_or_update_user,
    add_or_update_group,
    get_user_groups,
    is_user_in_group,
    associate_user_with_group,
    add_or_update_debt_list,
    update_debt_list_status,
    update_debt_list_group,
    get_group_name,
    get_debt_lists_by_user_id,
    get_debt_list_pending_status,
    get_debt_list_name,
    get_debt_status,
    delete_debt_list,
    add_or_update_debt,
    associate_debt_with_debt_list,
    update_debt_status,
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
        text="Welcome to the Debt Tracker Bot! Start by sending a list of debts in this format:\n\n@user1 9.6\n@user2 5.4\n@user3 3.0",
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
        message += "\n##############\n".join(
            [get_debt_list_string(list_id) for list_id in debt_lists]
        )
    else:
        message = "You have not created any debt lists."

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
    # Delete all debt lists that are made by the user
    debt_lists = get_debt_lists_by_user_id(update.effective_user.id)
    if debt_lists:
        for list_id in debt_lists:
            # Delete the debt list
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
    user_id = update.effective_user.id  # Use integer ID directly

    if not success:
        await context.bot.send_message(chat_id=user_id, text=result)
        return

    # Add the debt list to the database
    debt_name, phone_number, debts = result
    # Create new debt list
    debt_list_id = add_or_update_debt_list(
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


async def handle_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the callback for confirming a debt list.

    Args:
        update (Update): The update object containing the callback data.
        context (ContextTypes.DEFAULT_TYPE): The context object for handling the callback.

    Returns:
        None
    """
    # Pull out the debt list ID from the callback data
    debt_list_id = update.callback_query.data.split(":")[1]

    if not get_debt_list_pending_status(debt_list_id):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="There is no pending debt list",
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
