from datetime import datetime, timedelta
from typing import List, Tuple, Union

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.database import (
    delete_debt_list_message_info,
    get_all_debt_lists,
    get_debt_list_info,
    update_debt_list_message_info,
)
from datetime import datetime
from pytz import timezone

from bot.models import DebtList


def parse_debt_list(
    input_text: str,
) -> Tuple[bool, Union[str, Tuple[str, str, List[Tuple[str, float]]]]]:
    """
    Parses the input text and extracts the debt name, phone number, and debts.

    Args:
        input_text (str): The input text containing the debt information.

    Returns:
        Tuple[bool, Union[str, Tuple[str, str, List[Tuple[str, float]]]]]: A tuple containing a boolean value indicating whether the parsing was successful, and either an error message (if parsing failed) or a tuple containing the debt name, phone number, and a list of debts.

    Raises:
        None

    Examples:
        >>> input_text = "AMEENS\\n912847392\\n@Alice 10.5\\n@Bob 20.0"
        >>> parse_debt_list(input_text)
        (True, ('AMEENS', '912847392', [('@Alice', 10.5), ('@Bob', 20.0)]))
    """
    lines: List[str] = input_text.strip().split("\n")

    # Validate the number of lines
    if len(lines) < 3:
        return (
            False,
            "Input must have at least three lines. Make sure there is a name, phone number, and at least one debt. Example:\n\nMacDonalds\n98765432\n@user1 9.6\n@user2 5.4\n@user3 3.0",
        )

    # Extract debt name and phone number
    debt_name = lines[0].strip()
    phone_number = lines[1].strip()
    # Validate phone number
    if not phone_number.isdigit():
        return False, "Phone number must contain only numbers"

    # Extract debts
    debts = []
    for line in lines[2:]:
        line = line.strip()
        if line == "":
            continue
        if line.startswith("@"):
            try:
                username, amount_owed = line.split(" ", 1)
                debts.append((username[1:], float(amount_owed)))
            except ValueError:
                return False, f"Failed to parse debt entry: '{line}'."

    return True, (debt_name, phone_number, debts)


def get_debt_list_string(debt_list_id: int) -> str:
    debt_list_info = get_debt_list_info(debt_list_id)
    debt_name = debt_list_info.get("debt_name")
    phone_number = debt_list_info.get("phone_number")
    debts = debt_list_info.get("debts")
    last_updated: datetime = debt_list_info.get("last_updated")
    # Convert the last_updated time to Singapore time
    last_updated = (
        timezone("UTC").localize(last_updated).astimezone(timezone("Asia/Singapore"))
    ).strftime("%Y-%m-%d %H:%M:%S")

    # Continue with the rest of the code
    message = f"{debt_name}\nPay to: {phone_number}\n\n"
    message += "\n".join(
        [
            f"{'' if debt.get('paid') else '@'}{debt.get('owed_by_user_name')} - {debt.get('amount')} {'✅' if debt.get('paid') else '❌'}"
            for debt in debts
        ]
    )

    message += f"\n\nMessage last updated at {last_updated}"

    return message


def is_all_debt_paid(debt_list_id: int) -> bool:
    debt_list_info = get_debt_list_info(debt_list_id)
    debts = debt_list_info.get("debts")
    return all(debt.get("paid") for debt in debts)


async def delete_message(
    bot: Bot, debt_list_id: int, group_id: int, message_id: int
) -> None:
    """
    Deletes a message from a chat and removes the associated debt list message info.

    Args:
        bot (Bot): The bot instance used to delete the message.
        debt_list_id (int): The ID of the debt list associated with the message.
        chat_id (int): The ID of the chat where the message is located.
        message_id (int): The ID of the message to be deleted.
    """
    try:
        # This is in a try-finally block to ensure that the debt list message info is deleted even if an exception occurs (usually because the message does not exist)
        await bot.delete_message(chat_id=group_id, message_id=message_id)
    finally:
        delete_debt_list_message_info(debt_list_id)


async def check_and_resend_debt_lists(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(timezone("UTC"))
    threshold = now - timedelta(hours=16)  # Abstract this into config file
    debt_lists: List[DebtList] = get_all_debt_lists()

    for debt_list in debt_lists:
        if timezone("UTC").localize(debt_list.last_updated) < threshold:
            await delete_message(
                context.bot, debt_list.list_id, debt_list.group_id, debt_list.message_id
            )

            # TODO: Abstract this out along with the one in callback_handlers.py
            message = get_debt_list_string(debt_list.list_id)
            pay_button = InlineKeyboardButton(
                "✅", callback_data=f"pay:{debt_list.list_id}"
            )
            unpay_button = InlineKeyboardButton(
                "❌", callback_data=f"unpay:{debt_list.list_id}"
            )
            buttons = [[pay_button, unpay_button]]
            reply_markup = InlineKeyboardMarkup(buttons)

            new_message = await context.bot.send_message(
                chat_id=debt_list.group_id,
                text=message,
                reply_markup=reply_markup,
            )

            new_message_id = new_message.message_id
            update_debt_list_message_info(debt_list.list_id, new_message_id)
