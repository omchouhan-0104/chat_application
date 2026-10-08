from datetime import datetime, timezone

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from app.database.database import Base

class User(Base):

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        index=True,
        nullable=False
    )

    password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    is_online: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    messages = relationship(
        "Message",
        back_populates="sender"
    )

    conversations_as_user1 = relationship(
        "Conversation",
        foreign_keys="Conversation.user1_id",
        back_populates="user1"
    )

    conversations_as_user2 = relationship(
        "Conversation",
        foreign_keys="Conversation.user2_id",
        back_populates="user2"
    )

    groups_created = relationship(
        "Group",
        foreign_keys="Group.created_by",
        back_populates="creator"
    )

    group_memberships = relationship(
        "GroupMember",
        back_populates="user",
        cascade="all, delete-orphan"
    )

class Conversation(Base):

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    user1_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    user2_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Prevent duplicate private conversations
    __table_args__ = (
        UniqueConstraint(
            "user1_id",
            "user2_id",
            name="unique_conversation"
        ),
    )

    user1 = relationship(
        "User",
        foreign_keys=[user1_id],
        back_populates="conversations_as_user1"
    )

    user2 = relationship(
        "User",
        foreign_keys=[user2_id],
        back_populates="conversations_as_user2"
    )

    messages = relationship(
        "Message",
        back_populates="conversation",
        foreign_keys="Message.conversation_id",
        cascade="all, delete-orphan"
    )

class Group(Base):

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    creator = relationship(
        "User",
        foreign_keys=[created_by],
        back_populates="groups_created"
    )

    members = relationship(
        "GroupMember",
        back_populates="group",
        cascade="all, delete-orphan"
    )

    messages = relationship(
        "Message",
        back_populates="group",
        foreign_keys="Message.group_id",
        cascade="all, delete-orphan"
    )

class GroupMember(Base):

    __tablename__ = "group_members"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id"),
        nullable=False,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    last_read_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "group_id",
            "user_id",
            name="unique_group_member"
        ),
    )

    group = relationship(
        "Group",
        back_populates="members"
    )

    user = relationship(
        "User",
        back_populates="group_memberships"
    )

class Message(Base):

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id"),
        nullable=True,
        index=True
    )

    group_id: Mapped[int | None] = mapped_column(
        ForeignKey("groups.id"),
        nullable=True,
        index=True
    )

    sender_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )


    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    sender = relationship(
        "User",
        back_populates="messages"
    )

    conversation = relationship(
        "Conversation",
        back_populates="messages",
        foreign_keys=[conversation_id]
    )

    group = relationship(
        "Group",
        back_populates="messages",
        foreign_keys=[group_id]
    )


    __table_args__ = (
        CheckConstraint(
            """
            (
                conversation_id IS NOT NULL
                AND
                group_id IS NULL
            )
            OR
            (
                conversation_id IS NULL
                AND
                group_id IS NOT NULL
            )
            """,
            name="check_message_parent"
        ),
    )


# from datetime import datetime, timezone
# from zoneinfo import ZoneInfo
# from datetime import timedelta

# from sqlalchemy import (
#     String,
#     Boolean,
#     DateTime,
#     ForeignKey,
#     Text,
#     UniqueConstraint
# )

# from sqlalchemy.orm import (
#     Mapped,
#     mapped_column,
#     relationship
# )

# from app.database.database import Base


# class User(Base):

#     __tablename__ = "users"

#     id: Mapped[int] = mapped_column(
#         primary_key=True,
#         index=True
#     )

#     username: Mapped[str] = mapped_column(
#         String(50),
#         unique=True,
#         index=True,
#         nullable=False
#     )

#     email: Mapped[str] = mapped_column(
#         String(150),
#         unique=True,
#         index=True,
#         nullable=False
#     )

#     password: Mapped[str] = mapped_column(
#         String(255),
#         nullable=False
#     )

#     is_online: Mapped[bool] = mapped_column(
#         Boolean,
#         default=False,
#         nullable=False
#     )

#     created_at: Mapped[datetime] = mapped_column(
#         DateTime,
#         default=lambda: datetime.now(timezone.utc),
#         nullable=False
#     )



#     messages = relationship(
#         "Message",
#         back_populates="sender"
#     )

#     conversations_as_user1 = relationship(
#         "Conversation",
#         foreign_keys="Conversation.user1_id",
#         back_populates="user1"
#     )


#     conversations_as_user2 = relationship(
#         "Conversation",
#         foreign_keys="Conversation.user2_id",
#         back_populates="user2"
#     )


# class Conversation(Base):

#     __tablename__ = "conversations"

#     id: Mapped[int] = mapped_column(
#         primary_key=True,
#         index=True
#     )

#     user1_id: Mapped[int] = mapped_column(
#         ForeignKey("users.id"),
#         nullable=False
#     )

#     user2_id: Mapped[int] = mapped_column(
#         ForeignKey("users.id"),
#         nullable=False
#     )

#     created_at: Mapped[datetime] = mapped_column(
#         DateTime,
#         default=lambda: datetime.now(timezone.utc),
#         nullable=False
#     )

#     # --------------------------------------------------------
#     # Prevent duplicate conversation
#     #
#     # Example:
#     # (1, 2) can exist only once
#     # --------------------------------------------------------

#     __table_args__ = (
#         UniqueConstraint(
#             "user1_id",
#             "user2_id",
#             name="unique_conversation"
#         ),
#     )

#     user1 = relationship(
#         "User",
#         foreign_keys=[user1_id],
#         back_populates="conversations_as_user1"
#     )

#     user2 = relationship(
#         "User",
#         foreign_keys=[user2_id],
#         back_populates="conversations_as_user2"
#     )


#     messages = relationship(
#         "Message",
#         back_populates="conversation",
#         cascade="all, delete-orphan"
#     )

# class Message(Base):

#     __tablename__ = "messages"

#     id: Mapped[int] = mapped_column(
#         primary_key=True,
#         index=True
#     )

#     conversation_id: Mapped[int] = mapped_column(
#         ForeignKey("conversations.id"),
#         nullable=False,
#         index=True
#     )

#     sender_id: Mapped[int] = mapped_column(
#         ForeignKey("users.id"),
#         nullable=False,
#         index=True
#     )

#     content: Mapped[str] = mapped_column(
#         Text,
#         nullable=False
#     )

#     is_read: Mapped[bool] = mapped_column(
#         Boolean,
#         default=False,
#         nullable=False
#     )

#     created_at: Mapped[datetime] = mapped_column(
#         DateTime,
#         default=lambda: datetime.now(timezone.utc),
#         nullable=False
#     )

#     sender = relationship(
#         "User",
#         back_populates="messages"
#     )

#     conversation = relationship(
#         "Conversation",
#         back_populates="messages"
#     )