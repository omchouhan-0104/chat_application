from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

class MessageResponse(BaseModel):
    id: int
    conversation_id: int | None = None
    group_id: int | None = None
    sender_id: int
    content: str
    is_read: bool
    created_at: datetime
    model_config = ConfigDict(
        from_attributes=True
    )

class ConversationResponse(BaseModel):
    id: int
    user1_id: int
    user2_id: int
    created_at: datetime
    model_config = ConfigDict(
        from_attributes=True
    )

class GroupMemberResponse(BaseModel):
    id: int
    group_id: int
    user_id: int
    joined_at: datetime
    last_read_at: datetime | None = None
    username: str | None = None

    model_config = ConfigDict(
        from_attributes=True
    )

class GroupResponse(BaseModel):
    id: int
    name: str
    created_by: int
    created_at: datetime
    members: list[GroupMemberResponse] = Field(
        default_factory=list
    )

    model_config = ConfigDict(
        from_attributes=True
    )

class GroupCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=100
    )

    member_ids: list[int] = Field(
        default_factory=list
    )

class UnreadCountResponse(BaseModel):
    unread_count: int


# from datetime import datetime

# from pydantic import BaseModel


# class MessageResponse(BaseModel):

#     id: int

#     conversation_id: int

#     sender_id: int

#     content: str

#     is_read: bool

#     created_at: datetime


# class ConversationResponse(BaseModel):

#     id: int

#     user1_id: int

#     user2_id: int

#     created_at: datetime