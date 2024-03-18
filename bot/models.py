from sqlalchemy import (
    create_engine,
    event,
    Column,
    Integer,
    String,
    Float,
    Boolean,
    ForeignKey,
    Table,
    DateTime,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

DATABASE_URL = "sqlite:///./debt_tracker.db"
engine = create_engine(DATABASE_URL, echo=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Association table for the many-to-many relationship
user_group_association = Table(
    "user_group",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.user_id", ondelete="CASCADE")),
    Column("group_id", Integer, ForeignKey("groups.group_id", ondelete="CASCADE")),
)


class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    first_name = Column(String)
    last_name = Column(String)

    debt_lists = relationship("DebtList", back_populates="owner")
    # Define the relationship to Group, using back_populates for bidirectional relationship
    groups = relationship(
        "Group", secondary=user_group_association, back_populates="users"
    )


class Group(Base):
    __tablename__ = "groups"
    group_id = Column(Integer, primary_key=True, index=True)
    group_name = Column(String)
    group_type = Column(String)

    debt_lists = relationship("DebtList", back_populates="group")
    # Define the relationship to User, using back_populates for bidirectional relationship
    users = relationship(
        "User", secondary=user_group_association, back_populates="groups"
    )


class DebtList(Base):
    __tablename__ = "debt_lists"
    list_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    group_id = Column(Integer, ForeignKey("groups.group_id"), nullable=True)
    message_id = Column(Integer, nullable=True)
    debt_name = Column(String)
    phone_number = Column(String)
    is_pending = Column(Boolean, default=True)
    last_updated = Column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
    )

    owner = relationship("User", back_populates="debt_lists")
    group = relationship("Group", back_populates="debt_lists", uselist=False)
    # Add cascade="delete, delete-orphan" to automatically delete debts when the debt list is deleted
    debts = relationship(
        "Debt", back_populates="debt_list", cascade="delete, delete-orphan"
    )


class Debt(Base):
    __tablename__ = "debts"
    debt_id = Column(Integer, primary_key=True, index=True)
    list_id = Column(Integer, ForeignKey("debt_lists.list_id"))
    owed_by_user_name = Column(String)
    amount = Column(Float)
    paid = Column(Boolean, default=False)

    debt_list = relationship("DebtList", back_populates="debts")


# Automatically update the last_updated column in a debt list when a debt is updated
def debt_after_update_listener(mapper, connection, target):
    connection.execute(
        DebtList.__table__.update()
        .where(DebtList.list_id == target.list_id)
        .values(last_updated=func.now())
    )


event.listen(Debt, "after_update", debt_after_update_listener)
