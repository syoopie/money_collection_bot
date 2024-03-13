# Import the required modules
import logging
from telegram import Update  # This module helps to handle updates from Telegram
from telegram.ext import (
    ApplicationBuilder,  # Helps to build the bot application
    CommandHandler,  # Handles command messages
    ContextTypes,  # Provides context for callbacks
    MessageHandler,  # Handles messages
    filters,  # Used to filter incoming messages based on certain criteria
)

# Read the bot token from a file and assign it to TOKEN variable
# The token is unique to your bot and is used to authenticate API requests
with open("./token.txt", "r") as file:
    TOKEN = file.read().strip()

# Set up logging to help with debugging. Logs will show info like time, name, and level of log messages
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


# Define an asynchronous function 'start' that sends a welcome message
# 'update' contains information about the incoming update
# 'context' allows you to send messages and access other useful data
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!"
    )


# Define an asynchronous function 'echo' to echo back any text messages that are not commands
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(update.message.text)  # Print the received message to the console
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=update.message.text,  # Echo back the received text
    )


# Define an asynchronous function 'caps' to convert messages to uppercase
# This demonstrates how to process command arguments (text following the command)
async def caps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(context.args)  # Print command arguments to the console
    text_caps = " ".join(context.args).upper()  # Convert the args to uppercase
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text_caps)


# Define an asynchronous function 'unknown' to handle unknown commands
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Sorry, I didn't understand that command.",
    )


# The entry point of the bot application
if __name__ == "__main__":
    # Create an application using the bot token
    application = ApplicationBuilder().token(TOKEN).build()

    # Define handlers for different command and message types
    start_handler = CommandHandler("start", start)  # Handles the /start command
    echo_handler = MessageHandler(
        filters.TEXT & (~filters.COMMAND), echo
    )  # Handles text messages that are not commands
    caps_handler = CommandHandler("caps", caps)  # Handles the /caps command
    unknown_handler = MessageHandler(
        filters.COMMAND, unknown
    )  # Handles unknown commands

    # Add the defined handlers to the application
    application.add_handler(start_handler)
    application.add_handler(echo_handler)
    application.add_handler(caps_handler)
    application.add_handler(unknown_handler)

    # Start polling Telegram for updates. The bot will remain active and respond to messages
    application.run_polling()
