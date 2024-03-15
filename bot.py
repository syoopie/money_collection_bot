import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

with open("./token.txt", "r") as file:
    token = file.read().strip()


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


with open("./bot_messages.json", "r") as file:
    messages = json.load(file)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=messages["start"],
    )


async def get_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Load the user data
    try:
        with open("data.json", "r") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"users": {}}

    # Get the user's groups
    user = update.effective_user
    if str(user.id) in data["users"]:
        groups: dict = data["users"][str(user.id)]["groups"]
        buttons = []
        for groupID in groups:
            button = InlineKeyboardButton(
                groups[str(groupID)]["title"],
                callback_data=f"sendToGroup:{groupID}",
            )
            buttons.append([button])
        reply_markup = InlineKeyboardMarkup(buttons)
        message = "Here are the groups you are in:"
    else:
        message = "You are not in any groups."

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=reply_markup,
    )


async def parse_and_check_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    input_lines = update.message.text.strip().split("\n")
    user_id = str(update.effective_user.id)  # Convert user ID to string for JSON keys

    # Initialize a structure to hold the parsed data including the new fields
    temp_parsed_data = {"debtName": "", "phoneNumber": "", "debtEntries": {}}

    # Validate input: should have at least 4 lines (name, phone number, and at least one debt entry)
    if len(input_lines) < 3:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=messages["invalidFormat"],
        )
        return

    # Parse and validate the name of the debt and phone number
    temp_parsed_data["debtName"] = input_lines[0].strip()
    phone_number = input_lines[1].strip()
    if not phone_number.isdigit():  # Validate phone number format
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=messages["invalidFormat"],
        )
        return
    temp_parsed_data["phoneNumber"] = phone_number

    # Validate and parse debt entries
    valid_input = True
    for line in input_lines[2:]:
        if line == "":
            continue
        key_value_pair = line.split()
        if (
            not line.startswith("@")
            or len(key_value_pair) != 2
            or not key_value_pair[1]
            .replace(".", "", 1)  # This allows for decimal numbers
            .isdigit()
        ):
            valid_input = False
            break
        key, value = key_value_pair
        temp_parsed_data["debtEntries"][key] = value

    if not valid_input:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=messages["invalidFormat"],
        )
        return

    # Load or initialize the data structure
    try:
        with open("data.json", "r") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"users": {}, "pending": {}}

    # Update the pending input for the user
    if "pending" not in data:
        data["pending"] = {}
    data["pending"][user_id] = temp_parsed_data

    # Write the updated data back to the file
    try:
        with open("data.json", "w") as file:
            json.dump(data, file, indent=4)
    except Exception as e:
        logging.error(f"Failed to save data.json: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=messages["saveError"],
        )
        return

    formatted_data = f"Name: {temp_parsed_data['debtName']}\n"
    formatted_data += f"Number: {temp_parsed_data['phoneNumber']}\n\n"
    formatted_data += "\n".join(
        [f"{key} - {value}" for key, value in temp_parsed_data["debtEntries"].items()]
    )
    message = (
        "Please confirm your input. If it is incorrect, resend it again.\n\n"
        + formatted_data
    )

    # Create inline keyboard with confirm button
    confirm_button = InlineKeyboardButton("Confirm ✅", callback_data="confirmInput")
    keyboard = [[confirm_button]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=reply_markup,
    )


async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    callback_query = update.callback_query
    await callback_query.answer()  # Answer the callback query to stop the loading animation on the button.

    user_id = str(update.effective_user.id)

    # Load the data structure from 'data.json'
    try:
        with open("data.json", "r") as file:
            data: dict = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Error loading data. Please try again.",
        )
        return

    # Ensure there's pending data for the user to confirm
    if user_id not in data.get("pending", {}):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="No pending input to confirm.",
        )
        return

    # Check if the user is part of any groups
    if str(user_id) in data.get("users", {}) and data["users"][str(user_id)]["groups"]:
        groups = data["users"][str(user_id)]["groups"]
        buttons = [
            [
                InlineKeyboardButton(
                    groups[group_id]["name"], callback_data=f"sendToGroup:{group_id}:{groups[group_id]["name"]}"
                )
            ]
            for group_id in groups
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        message = "Choose a group to send the message to:"
    else:
        message = "You are not in any groups. Please add me to a group and send a message to the group."
        reply_markup = None

    # Send the confirmation message along with the group choices (if available)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=reply_markup,
    )


async def send_to_group_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    callback_query = update.callback_query
    await callback_query.answer()  # Answer the callback query to stop the loading animation on the button.
    user_id = str(update.effective_user.id)
    group_id = callback_query.data.split(":")[1]
    group_name = callback_query.data.split(":")[2]

    # Load the data from data.json
    try:
        with open("data.json", "r") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        logging.error("Failed to read data.json or data.json is corrupted.")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'{messages["genericError"]} (Error 101)',
        )
        return

    # Check if there's a pending message for the user
    if user_id not in data.get("pending", {}):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'{messages["genericError"]} (Error 102)',
        )
        return

    # Retrieve the pending message data
    pending_message_data = data["pending"][user_id]
    debt_name = pending_message_data["debtName"]
    phone_number = pending_message_data["phoneNumber"]
    debt_entries = pending_message_data["debtEntries"]

    # Transform debt entries to include "paid" flag
    transformed_debt_entries = {
        key: {"amount": value, "paid": "false"} for key, value in debt_entries.items()
    }

    # Format the message to include debt name, phone number, and entries
    message_text = f"{debt_name}\nPay to {phone_number}\n\n"
    for key, entry in transformed_debt_entries.items():
        message_text += f"{key} - {entry['amount']} ❌\n"

    try:
        # Move the message from "pending" to "inProgress" and save which group it was sent to
        if "inProgress" not in data:
            data["inProgress"] = {}
        data["inProgress"][user_id] = {
            "debtName": debt_name,
            "phoneNumber": phone_number,
            "debtEntries": transformed_debt_entries,
            "groupInfo": {"id": group_id, "name": group_name}
        }
        del data["pending"][user_id]

        # Save the updated data back to data.json
        with open("data.json", "w") as file:
            json.dump(data, file, indent=4)
            
        # Send the formatted message to the specified group
        pay_button = InlineKeyboardButton("✅", callback_data=f"pay:{user_id}:{group_id}")
        unpay_button = InlineKeyboardButton("❌", callback_data=f"unpay:{user_id}:{group_id}")
        buttons = [[pay_button, unpay_button]]
        reply_markup = InlineKeyboardMarkup(buttons)

        await context.bot.send_message(
            chat_id=group_id,
            text=message_text,
            reply_markup=reply_markup
        )

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=messages["messageSent"],
        )
        
    except Exception as e:
        logging.error(f"Failed to send message to group {group_id}: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'{messages["genericError"]} (Error 103)',
        )



async def pay_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    callback_query = update.callback_query
    await callback_query.answer()  # Answer the callback query to stop the loading animation on the button.
    _, user_id, group_id = callback_query.data.split(":")
    payer_id = update.effective_user.id
    payer_username = "@" + update.effective_user.username

    # Load the data from data.json
    try:
        with open("data.json", "r") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        logging.error("Failed to read data.json or data.json is corrupted.")
        await context.bot.send_message(
            chat_id=payer_id, # Send error to user, NOT to group
            text=f'{messages["genericError"]} (Error 104)',
        )
        return

    # Check if there's a in progress payment for the user
    if user_id not in data.get("inProgress", {}):
        await context.bot.send_message(
            chat_id=payer_id, # Send error to user, NOT to group
            text=f'{messages["genericError"]} (Error 105)',
        )
        return

    # Retrieve the pending message data
    pending_message_data = data["inProgress"][user_id]
    debt_name = pending_message_data["debtName"]
    phone_number = pending_message_data["phoneNumber"]
    debt_entries = pending_message_data["debtEntries"]
    group_id = pending_message_data["groupInfo"]["id"]
    group_name = pending_message_data["groupInfo"]["name"]

        
    if not payer_username in debt_entries:
        await context.bot.send_message(
            chat_id=payer_id,
            text=f'You don\'t have any debt to pay in that list!',
        )
        return
        
    debt_entries[payer_username]["paid"] = "true"
    # Save the updated data back to data.json
    with open("data.json", "w") as file:
        json.dump(data, file, indent=4)
        
    # Editing the original message in the group
    message_text = f"{debt_name}\nPay to {phone_number}\n\n"
    for key, entry in debt_entries.items():
        paid_status = "✅" if entry["paid"] == "true" else "❌"
        message_text += f"{key} - {entry['amount']} {paid_status}\n"
    try:
        await context.bot.edit_message_text(
            chat_id=group_id,
            message_id=callback_query.message.message_id,
            text=message_text,
            reply_markup=callback_query.message.reply_markup  # Keep the same inline keyboard
        )
    except Exception as e:
        logging.error(f"Failed to edit message in group {group_id}: {e}")
    
    # Send confirmation message to payer
    await context.bot.send_message(
        chat_id=payer_id,
        text=f"You have paid the debt for {debt_name}."
    )
    

async def unpay_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    callback_query = update.callback_query
    await callback_query.answer()  # Answer the callback query to stop the loading animation on the button.
    
    _, user_id, group_id = callback_query.data.split(":")
    payer_id = update.effective_user.id
    payer_username = "@" + update.effective_user.username
    
    # Load the data from data.json
    try:
        with open("data.json", "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        # Use generic error
        await context.bot.send_message(
            chat_id=payer_id,
            text=f'{messages["genericError"]} (Error 106)',
        )
        return
    
    if not user_id in data.get("inProgress", {}):
        # Use generic error
        await context.bot.send_message(
            chat_id=payer_id,
            text=f'{messages["genericError"]} (Error 107)',
        )
        return
        

    # Retrieve the pending message data
    pending_message_data = data["inProgress"][user_id]
    debt_name = pending_message_data["debtName"]
    phone_number = pending_message_data["phoneNumber"]
    debt_entries = pending_message_data["debtEntries"]
    group_id = pending_message_data["groupInfo"]["id"]
    group_name = pending_message_data["groupInfo"]["name"]
    
    if not payer_username in debt_entries:
        await context.bot.send_message(
            chat_id=payer_id,
            text=f'You don\'t have any debt to pay in that list!',
        )
        return
    if debt_entries[payer_username]["paid"] == "false":
        await context.bot.send_message(
            chat_id=payer_id,
            text="You have not paid this debt yet.",
        )
        return

    # Mark the payment as unpaid
    debt_entries[payer_username]["paid"] = "false"
    # Save the updated data back to data.json
    with open("data.json", "w") as file:
        json.dump(data, file)
    # Editing the original message in the group
    message_text = f"{debt_name}\nPay to {phone_number}\n\n"
    for key, entry in debt_entries.items():
        paid_status = "✅" if entry["paid"] == "true" else "❌"
        message_text += f"{key} - {entry['amount']} {paid_status}\n"
        
    await context.bot.edit_message_text(
        chat_id=group_id,
        message_id=callback_query.message.message_id,
        text=message_text,
        reply_markup=callback_query.message.reply_markup  # Keep the same inline keyboard
    )
    # Send confirmation message to payer
    await context.bot.send_message(
        chat_id=payer_id,
        text=f"You have marked the payment for {debt_name} as unpaid.",
    )
        

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=messages["invalidCommand"],
    )


async def save_user_group_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Extract user and chat information from the update
    user = update.effective_user
    chat = update.effective_chat

    # Load or initialize the data structure
    try:
        with open("data.json", "r") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"users": {}}

    # If user data is present already, update the user
    if str(user.id) in data["users"]:
        data["users"][str(user.id)]["username"] = user.username
        data["users"][str(user.id)]["first_name"] = user.first_name
        data["users"][str(user.id)]["last_name"] = user.last_name
    else:
        data["users"][str(user.id)] = {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "groups": {},
        }

    # Append the group information to the user's groups
    data["users"][str(user.id)]["groups"][str(chat.id)] = {
        "name": chat.title,
        "type": chat.type,
    }

    try:
        with open("data.json", "w") as file:
            json.dump(data, file, indent=4)
    except Exception as e:
        logging.error(f"Failed to save data.json: {e}")


if __name__ == "__main__":
    application = ApplicationBuilder().token(token).build()

    # ALL PRIVATE COMMANDS ########################################################
    # /start
    start_handler = CommandHandler(
        "start", start, filters.ChatType.PRIVATE & filters.COMMAND
    )
    application.add_handler(start_handler)

    # /getGroups
    get_groups_handler = CommandHandler(
        "getGroups", get_groups, filters.ChatType.PRIVATE & filters.COMMAND
    )
    application.add_handler(get_groups_handler)

    # Unknown commands
    unknown_handler = MessageHandler(filters.ChatType.PRIVATE & filters.COMMAND, unknown)
    application.add_handler(unknown_handler)

    # ALL PRIVATE TEXT MESSAGES ###################################################
    parse_and_check_input_handler = MessageHandler(
        filters.ChatType.PRIVATE & filters.TEXT & (~filters.COMMAND), parse_and_check_input
    )
    application.add_handler(parse_and_check_input_handler)

    # ALL CALLBACK QUERIES #########################################################
    confirm_input_callback_handler = CallbackQueryHandler(confirm_callback, "confirmInput")
    application.add_handler(confirm_input_callback_handler)

    send_to_group_callback_handler = CallbackQueryHandler(
        send_to_group_callback, r"sendToGroup:.*"
    )
    application.add_handler(send_to_group_callback_handler)
    
    pay_callback_handler = CallbackQueryHandler(
        pay_callback, r"pay:.*:.*"
    )
    application.add_handler(pay_callback_handler)
    
    unpay_callback_handler = CallbackQueryHandler(
        unpay_callback, r"unpay:.*:.*"
    )
    application.add_handler(unpay_callback_handler)

    # Add a handler for saving user group info on every message received.
    # Make sure this is after specific command handlers to avoid overshadowing them.
    all_message_handler = MessageHandler(~filters.ChatType.PRIVATE, save_user_group_info)
    application.add_handler(all_message_handler)

    application.run_polling()





"""
# Inside send_to_group_callback, format the message_text
for key, entry in transformed_debt_entries.items():
    paid_status = "✅" if entry["paid"] == "true" else "❌"
    message_text += f"{key} - {entry['amount']} {paid_status}\n"
"""
