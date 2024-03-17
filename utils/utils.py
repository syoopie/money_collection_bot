from datetime import datetime
from typing import List, Tuple, Union

from telegram import Bot

from bot.database import get_debt_list_info
from datetime import datetime
from pytz import timezone


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
        return False, "Input must have at least three lines."

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
                debts.append((username, float(amount_owed)))
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
            f"{debt.get('owed_by_user_name')} - {debt.get('amount')} {'✅' if debt.get('paid') else '❌'}"
            for debt in debts
        ]
    )

    message += f"\n\nMessage last updated at {last_updated}"

    return message


async def delete_message(bot: Bot, chat_id: int, message_id: int):
    """
    Deletes a message from a chat.

    Args:
        chat_id (int): The ID of the chat where the message is located.
        message_id (int): The ID of the message to delete.

    Returns:
        None
    """
    await bot.delete_message(chat_id=chat_id, message_id=message_id)
