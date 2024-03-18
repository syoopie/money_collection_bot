from sqlalchemy.orm import Session
from .models import engine, SessionLocal, User, Group, DebtList, Debt


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# User operations
def add_or_update_user(
    user_id: int, username: str, first_name: str, last_name: str
) -> int:
    db: Session = next(get_db())
    # Try to fetch the existing user
    user = db.query(User).filter(User.user_id == user_id).first()
    if user:
        # Update existing user details
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
    else:
        # Create a new User instance and add it to the session
        user = User(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        db.add(user)

    # Commit the session to save changes
    db.commit()

    return user.user_id


def get_user_groups(user_id: int) -> list:
    """
    Retrieve the groups that a user belongs to.

    Args:
        user_id (int): The ID of the user.

    Returns:
        list: A list of dictionaries containing the group ID and group name.

    """
    db: Session = next(get_db())
    user: User = db.query(User).filter(User.user_id == user_id).first()
    # check if user is not associated with any group
    if not user:
        return []
    return [
        {"group_id": group.group_id, "group_name": group.group_name}
        for group in user.groups
    ]


def is_user_in_group(user_id: int, group_id: int) -> bool:
    """
    Check if a user is a member of a specific group.

    Args:
        user_id (int): The ID of the user.
        group_id (int): The ID of the group.

    Returns:
        bool: True if the user is a member of the group, False otherwise.
    """
    db: Session = next(get_db())
    user = db.query(User).filter(User.user_id == user_id).first()
    group = db.query(Group).filter(Group.group_id == group_id).first()
    if user and group:
        return group in user.groups
    return False


def add_or_update_group(group_id: int, group_name: str, group_type: str) -> Group:
    """
    Add or update a group in the database.

    Args:
        group_id (int): The ID of the group.
        group_name (str): The name of the group.
        group_type (str): The type of the group.

    Returns:
        Group: The updated or newly created group object.
    """
    db: Session = next(get_db())
    group = db.query(Group).filter(Group.group_id == group_id).first()
    if group:
        group.group_name = group_name
        group.group_type = group_type
    else:
        group = Group(group_id=group_id, group_name=group_name, group_type=group_type)
        db.add(group)
    db.commit()
    return group


def associate_user_with_group(user_id: int, group_id: int) -> None:
    db: Session = next(get_db())
    user = db.query(User).filter(User.user_id == user_id).first()
    group = db.query(Group).filter(Group.group_id == group_id).first()
    if not user or not group:
        # TODO: Do something better with the error
        print("User or Group does not exist.")
        return

    # Check if the user is already associated with the group
    if group not in user.groups:
        # If not, add the group to the user's groups collection
        user.groups.append(group)
        db.commit()


def get_group_name(group_id: int) -> str:
    db: Session = next(get_db())
    group = db.query(Group).filter(Group.group_id == group_id).first()
    if group:
        return group.group_name
    return ""  # TODO: Should return some error instead


def add_debt_list(
    user_id: int,
    debt_name: str,
    phone_number: str,
    group_id: int = None,
) -> int:
    """
    Adds a debt list for a user in the database.

    Args:
        user_id (int): The ID of the user.
        debt_name (str): The name of the debt.
        phone_number (str): The phone number associated with the debt.
        group_id (int, optional): The ID of the group the debt belongs to. Defaults to None.

    Returns:
        DebtList: The ID of the newly created debt list.

    """
    db: Session = next(get_db())
    debt_list = DebtList(
        user_id=user_id,
        group_id=group_id,
        debt_name=debt_name,
        phone_number=phone_number,
    )
    db.add(debt_list)
    db.commit()
    return debt_list.list_id


def update_debt_list_group(list_id: int, group_id: int) -> None:
    db: Session = next(get_db())
    debt_list = db.query(DebtList).filter(DebtList.list_id == list_id).first()
    if debt_list:
        debt_list.group_id = group_id
        db.commit()
    else:
        # TODO
        pass


def get_debt_list_info(list_id: int) -> dict:
    db: Session = next(get_db())
    debt_list = db.query(DebtList).filter(DebtList.list_id == list_id).first()
    if debt_list:
        return {
            "debt_name": debt_list.debt_name,
            "phone_number": debt_list.phone_number,
            "debts": [
                {
                    "owed_by_user_name": debt.owed_by_user_name,
                    "amount": debt.amount,
                    "paid": debt.paid,
                }
                for debt in debt_list.debts
            ],
            "last_updated": debt_list.last_updated,
        }
    return []


def get_debt_lists_by_user_id(user_id: int) -> list:
    """
    Retrieve a list of debt lists by user ID.

    Args:
        user_id (int): The ID of the user.

    Returns:
        list: A list of debt list IDs associated with the user.
    """
    db: Session = next(get_db())
    debt_lists = db.query(DebtList).filter(DebtList.user_id == user_id).all()
    return [debt_list.list_id for debt_list in debt_lists]


def get_debt_list_pending_status(list_id: int) -> bool:
    db: Session = next(get_db())
    debt_list = db.query(DebtList).filter(DebtList.list_id == list_id).first()
    if debt_list:
        return debt_list.is_pending
    return False  # TODO: Should return some error instead


def update_debt_list_status(list_id: int, is_pending: bool) -> None:
    db: Session = next(get_db())
    debt_list = db.query(DebtList).filter(DebtList.list_id == list_id).first()
    if debt_list:
        debt_list.is_pending = is_pending
        db.commit()
    else:
        # TODO: Do something with error
        pass


def update_debt_list_message_info(list_id: int, chat_id: int, message_id: int) -> None:
    db: Session = next(get_db())
    debt_list = db.query(DebtList).filter(DebtList.list_id == list_id).first()
    if debt_list:
        debt_list.chat_id = chat_id
        debt_list.message_id = message_id
        db.commit()
    else:
        # TODO: Do something with error
        pass


def get_debt_list_name(list_id: int) -> str:
    db: Session = next(get_db())
    debt_list = db.query(DebtList).filter(DebtList.list_id == list_id).first()
    if debt_list:
        return debt_list.debt_name
    return ""  # TODO: Should return some error instead


def get_debt_list_message_info(list_id: int) -> int:
    db: Session = next(get_db())
    debt_list = db.query(DebtList).filter(DebtList.list_id == list_id).first()
    if debt_list:
        return debt_list.chat_id, debt_list.message_id
    return 0, 0  # TODO: Should return some error instead


def delete_debt_list_message_info(list_id: int) -> None:
    db: Session = next(get_db())
    debt_list = db.query(DebtList).filter(DebtList.list_id == list_id).first()
    if debt_list:
        debt_list.chat_id = None
        debt_list.message_id = None
        db.commit()
    else:
        pass  # TODO: Do something with error


def get_debt_list_user_id(list_id: int) -> int:
    db: Session = next(get_db())
    debt_list = db.query(DebtList).filter(DebtList.list_id == list_id).first()
    if debt_list:
        return debt_list.user_id
    return 0  # TODO: Should return some error instead


def delete_debt_list(list_id: int) -> None:
    db: Session = next(get_db())
    debt_list = db.query(DebtList).filter(DebtList.list_id == list_id).first()
    if debt_list:
        db.delete(debt_list)
        db.commit()
    else:
        # TODO: Do something with error
        pass


def add_or_update_debt(
    list_id: int, owed_by_user_name: int, amount: float, paid: bool = False
) -> int:
    db: Session = next(get_db())
    debt = (
        db.query(Debt)
        .filter(Debt.list_id == list_id, Debt.owed_by_user_name == owed_by_user_name)
        .first()
    )
    if debt:
        debt.owed_by_user_name = owed_by_user_name
        debt.amount = amount
        debt.paid = paid
    else:
        debt = Debt(
            list_id=list_id,
            owed_by_user_name=owed_by_user_name,
            amount=amount,
            paid=paid,
        )
        db.add(debt)
    db.commit()
    return debt.debt_id


def associate_debt_with_debt_list(debt_id: int, list_id: int) -> None:
    db: Session = next(get_db())
    debt = db.query(Debt).filter(Debt.debt_id == debt_id).first()
    debt_list = db.query(DebtList).filter(DebtList.list_id == list_id).first()
    if not debt or not debt_list:
        # TODO: Do something better with the error
        print("Debt or DebtList does not exist.")
        return

    if debt not in debt_list.debts:
        debt_list.debts.append(debt)
        db.commit()


def update_debt_status(list_id: int, user_name: str, paid: bool):
    db: Session = next(get_db())

    debt = db.query(Debt).filter(Debt.list_id == list_id)
    if not debt.first():
        return False, "That debt list does not exist"

    debt = debt.filter(Debt.owed_by_user_name == user_name).first()
    if not debt:
        return False, "You are not in that debt list"

    debt.paid = paid
    db.commit()
    return True, "No Error"


def get_debt_status(list_id: int, user_name: str) -> bool:
    db: Session = next(get_db())

    debt = db.query(Debt).filter(Debt.list_id == list_id)
    if not debt.first():
        return False, "That debt list does not exist"

    debt = debt.filter(Debt.owed_by_user_name == user_name).first()
    if not debt:
        return False, "You are not in that debt list"

    return True, debt.paid


def initialize_database():
    from .models import Base

    # Create all database tables that are defined by classes in models.py
    Base.metadata.create_all(bind=engine)
