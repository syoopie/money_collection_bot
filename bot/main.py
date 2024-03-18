from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config.config import BOT_TOKEN
from bot.database import initialize_database
from utils.utils import check_and_resend_debt_lists

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from bot.handlers.command_handlers import (
    handle_command_example,
    handle_command_start,
    handle_command_get_groups,
    handle_command_show,
    handle_command_clear,
    handle_command_help,
    handle_resend_all_command,
    handle_unknown_command,
)
from bot.handlers.callback_handlers import (
    handle_confirm_callback,
    handle_confirm_clear_callback,
    handle_send_to_group_callback,
    handle_pay_callback,
    handle_unpay_callback,
)
from bot.handlers.message_handlers import (
    handle_parse_and_check_input,
    handle_save_user_group_info,
)


if __name__ == "__main__":
    # Initialize the database
    initialize_database()

    # Create the Application and pass it your bot's token.
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Setup APScheduler to check every 2 hours whether or not to resend debt lists
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_and_resend_debt_lists, "interval", hours=2, args=[app]
    )  # Abstract the interval into a config file
    scheduler.start()

    # Register command handlers
    app.add_handler(
        CommandHandler("start", handle_command_start, filters.ChatType.PRIVATE)
    )
    app.add_handler(
        CommandHandler("example", handle_command_example, filters.ChatType.PRIVATE)
    )
    app.add_handler(
        CommandHandler("getgroups", handle_command_get_groups, filters.ChatType.PRIVATE)
    )
    app.add_handler(
        CommandHandler("show", handle_command_show, filters.ChatType.PRIVATE)
    )
    app.add_handler(
        CommandHandler("clear", handle_command_clear, filters.ChatType.PRIVATE)
    )
    app.add_handler(
        CommandHandler("help", handle_command_help, filters.ChatType.PRIVATE)
    )
    app.add_handler(
        CommandHandler("resendall", handle_resend_all_command, filters.ChatType.PRIVATE)
    )

    # Register message handlers
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.TEXT & (~filters.COMMAND),
            handle_parse_and_check_input,
        )
    )

    # Register callback query handlers
    app.add_handler(
        CallbackQueryHandler(handle_confirm_callback, pattern="^confirmInput:")
    )
    app.add_handler(
        CallbackQueryHandler(handle_send_to_group_callback, pattern="sendToGroup:.*:.*")
    )
    app.add_handler(CallbackQueryHandler(handle_pay_callback, pattern="^pay:"))
    app.add_handler(CallbackQueryHandler(handle_unpay_callback, pattern="^unpay:"))
    app.add_handler(
        CallbackQueryHandler(handle_confirm_clear_callback, pattern="confirmClear")
    )

    # Unknown command handler as the last handler for commands
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.COMMAND, handle_unknown_command
        )
    )

    # Add a handler for saving user group info on every message received.
    # Make sure this is after specific command handlers to avoid overshadowing them.
    app.add_handler(
        MessageHandler(~filters.ChatType.PRIVATE, handle_save_user_group_info)
    )

    # Start the bot
    app.run_polling()
