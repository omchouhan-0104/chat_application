from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.database import get_db
from app.database.models import (
    Conversation,
    Group,
    GroupMember,
    Message,
    User,
)
from app.schemas.chat import (
    ConversationResponse,
    GroupCreate,
    GroupMemberResponse,
    GroupResponse,
    MessageResponse,
    UnreadCountResponse,
)

router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"]
)

def get_group_or_404(
    group_id: int,
    db: Session
):

    group = (
        db.query(Group)
        .filter(Group.id == group_id)
        .first()
    )

    if not group:

        raise HTTPException(
            status_code=404,
            detail="Group not found"
        )

    return group

def get_group_membership(
    group_id: int,
    user_id: int,
    db: Session
):

    membership = (
        db.query(GroupMember)
        .filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id
        )
        .first()
    )

    if not membership:

        raise HTTPException(
            status_code=403,
            detail="You are not a member of this group"
        )

    return membership


def build_group_response(
    group: Group,
    db: Session
):

    rows = (
        db.query(
            GroupMember,
            User.username
        )
        .join(
            User,
            User.id == GroupMember.user_id
        )
        .filter(
            GroupMember.group_id == group.id
        )
        .all()
    )

    members = []

    for membership, username in rows:

        members.append({
            "id": membership.id,
            "group_id": membership.group_id,
            "user_id": membership.user_id,
            "joined_at": membership.joined_at,
            "last_read_at": membership.last_read_at,
            "username": username,
        })

    return {
        "id": group.id,
        "name": group.name,
        "created_by": group.created_by,
        "created_at": group.created_at,
        "members": members,
    }

@router.post(
    "/groups",
    response_model=GroupResponse
)
def create_group(
    group_data: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    group_name = group_data.name.strip()

    if not group_name:

        raise HTTPException(
            status_code=400,
            detail="Group name cannot be empty"
        )

    if len(group_name) > 100:

        raise HTTPException(
            status_code=400,
            detail="Group name cannot exceed 100 characters"
        )

    member_ids = set(
        group_data.member_ids
    )

    member_ids.add(
        current_user.id
    )

    users = (
        db.query(User)
        .filter(
            User.id.in_(member_ids)
        )
        .all()
    )

    existing_user_ids = {
        user.id
        for user in users
    }

    missing_user_ids = (
        member_ids -
        existing_user_ids
    )

    if missing_user_ids:

        raise HTTPException(
            status_code=404,
            detail={
                "message": "One or more users were not found",
                "user_ids": sorted(
                    missing_user_ids
                )
            }
        )

    group = Group(
        name=group_name,
        created_by=current_user.id
    )

    db.add(group)

    db.flush()

    for user_id in member_ids:

        member = GroupMember(
            group_id=group.id,
            user_id=user_id
        )

        db.add(member)
    db.commit()
    db.refresh(group)

    return build_group_response(
        group,
        db
    )

@router.get(
    "/groups",
    response_model=list[GroupResponse]
)
def get_my_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):


    groups = (
        db.query(Group)
        .join(
            GroupMember,
            GroupMember.group_id == Group.id
        )
        .filter(
            GroupMember.user_id == current_user.id
        )
        .order_by(
            Group.created_at.desc()
        )
        .all()
    )

    return [
        build_group_response(
            group,
            db
        )
        for group in groups
    ]


@router.get(
    "/groups/{group_id}",
    response_model=GroupResponse
)
def get_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    group = get_group_or_404(
        group_id,
        db
    )

    get_group_membership(
        group_id,
        current_user.id,
        db
    )

    return build_group_response(
        group,
        db
    )

@router.get(
    "/groups/{group_id}/messages",
    response_model=list[MessageResponse]
)
def get_group_messages(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    get_group_or_404(
        group_id,
        db
    )

    get_group_membership(
        group_id,
        current_user.id,
        db
    )

    messages = (
        db.query(Message)
        .filter(
            Message.group_id == group_id
        )
        .order_by(
            Message.created_at.asc()
        )
        .all()
    )

    return messages


@router.get(
    "/groups/{group_id}/unread-count",
    response_model=UnreadCountResponse
)
def get_group_unread_count(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    get_group_or_404(
        group_id,
        db
    )

    membership = get_group_membership(
        group_id,
        current_user.id,
        db
    )

    query = (
        db.query(
            func.count(Message.id)
        )
        .filter(
            Message.group_id == group_id,
            Message.sender_id != current_user.id
        )
    )

    if membership.last_read_at is not None:

        query = query.filter(
            Message.created_at >
            membership.last_read_at
        )

    unread_count = (
        query.scalar() or 0
    )

    return {
        "unread_count": unread_count
    }

@router.post(
    "/groups/{group_id}/read"
)
def mark_group_as_read(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    get_group_or_404(
        group_id,
        db
    )
    
    membership = get_group_membership(
        group_id,
        current_user.id,
        db
    )

    membership.last_read_at = (
        datetime.now(timezone.utc)
    )

    db.commit()

    return {
        "group_id": group_id,
        "message": "Group marked as read"
    }

@router.get(
    "/groups/{group_id}/members",
    response_model=list[GroupMemberResponse]
)
def get_group_members(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    get_group_or_404(
        group_id,
        db
    )


    get_group_membership(
        group_id,
        current_user.id,
        db
    )


    rows = (
        db.query(
            GroupMember,
            User.username
        )
        .join(
            User,
            User.id == GroupMember.user_id
        )
        .filter(
            GroupMember.group_id == group_id
        )
        .order_by(
            GroupMember.joined_at.asc()
        )
        .all()
    )

    result = []

    for membership, username in rows:

        result.append({
            "id": membership.id,
            "group_id": membership.group_id,
            "user_id": membership.user_id,
            "joined_at": membership.joined_at,
            "last_read_at": membership.last_read_at,
            "username": username,
        })

    return result


@router.post(
    "/{user_id}",
    response_model=ConversationResponse
)
def create_conversation(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    current_user_id = current_user.id

    if user_id == current_user_id:

        raise HTTPException(
            status_code=400,
            detail="Cannot chat with yourself"
        )

    target_user = (
        db.query(User)
        .filter(
            User.id == user_id
        )
        .first()
    )

    if not target_user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    user1 = min(
        current_user_id,
        user_id
    )

    user2 = max(
        current_user_id,
        user_id
    )

    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.user1_id == user1,
            Conversation.user2_id == user2
        )
        .first()
    )

    if conversation:

        return conversation

    conversation = Conversation(
        user1_id=user1,
        user2_id=user2
    )

    db.add(conversation)

    db.commit()

    db.refresh(conversation)

    return conversation


@router.get(
    "/{conversation_id}/messages",
    response_model=list[MessageResponse]
)
def get_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id
        )
        .first()
    )

    if not conversation:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    if current_user.id not in [
        conversation.user1_id,
        conversation.user2_id
    ]:

        raise HTTPException(
            status_code=403,
            detail="You are not part of this conversation"
        )

    messages = (
        db.query(Message)
        .filter(
            Message.conversation_id ==
            conversation_id
        )
        .order_by(
            Message.created_at.asc()
        )
        .all()
    )

    return messages



# from fastapi import (
#     APIRouter,
#     Depends,
#     HTTPException
# )

# from sqlalchemy.orm import Session

# from app.database.database import get_db

# from app.database.models import (
#     Conversation,
#     User,
#     Message
# )

# from app.schemas.chat import (
#     ConversationResponse,
#     MessageResponse
# )

# from app.core.security import get_current_user


# router = APIRouter(
#     prefix="/conversations",
#     tags=["Conversations"]
# )


# @router.post(
#     "/{user_id}",
#     response_model=ConversationResponse
# )
# def create_conversation(
#     user_id: int,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):

#     current_user_id = current_user.id

#     if user_id == current_user_id:

#         raise HTTPException(
#             status_code=400,
#             detail="Cannot chat with yourself"
#         )


#     target_user = (
#         db.query(User)
#         .filter(User.id == user_id)
#         .first()
#     )

#     if not target_user:

#         raise HTTPException(
#             status_code=404,
#             detail="User not found"
#         )

#     # -----------------------------------------
#     # Keep user IDs in fixed order
#     #
#     # Example:
#     # user 5 + user 2
#     #
#     # becomes:
#     # user1_id = 2
#     # user2_id = 5
#     #
#     # This prevents duplicate conversations.
#     # -----------------------------------------

#     user1 = min(
#         current_user_id,
#         user_id
#     )

#     user2 = max(
#         current_user_id,
#         user_id
#     )

#     conversation = (
#         db.query(Conversation)
#         .filter(
#             Conversation.user1_id == user1,
#             Conversation.user2_id == user2
#         )
#         .first()
#     )

#     if conversation:

#         return conversation


#     conversation = Conversation(
#         user1_id=user1,
#         user2_id=user2
#     )

#     db.add(conversation)

#     db.commit()

#     db.refresh(conversation)

#     return conversation


# @router.get(
#     "/{conversation_id}/messages",
#     response_model=list[MessageResponse]
# )
# def get_messages(
#     conversation_id: int,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):

#     conversation = (
#         db.query(Conversation)
#         .filter(
#             Conversation.id == conversation_id
#         )
#         .first()
#     )

#     if not conversation:

#         raise HTTPException(
#             status_code=404,
#             detail="Conversation not found"
#         )

#     if current_user.id not in [
#         conversation.user1_id,
#         conversation.user2_id
#     ]:

#         raise HTTPException(
#             status_code=403,
#             detail="You are not part of this conversation"
#         )
#     messages = (
#         db.query(Message)
#         .filter(
#             Message.conversation_id == conversation_id
#         )
#         .order_by(
#             Message.created_at.asc()
#         )
#         .all()
#     )

#     return messages