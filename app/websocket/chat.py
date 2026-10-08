from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.database.models import (
    User,
    Conversation,
    Message,
    Group,
    GroupMember,
)
from app.websocket.manager import manager


router = APIRouter()

@router.websocket("/ws/{user_id}")
async def websocket_chat(
    websocket: WebSocket,
    user_id: int
):
    """
    Main WebSocket endpoint.

    Handles:

    - private messages
    - group messages
    - typing
    - stop typing
    - read receipts
    - group read state
    - online/offline status
    """

    db: Session = SessionLocal()
    user = None

    try:
        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user:
            await websocket.close(
                code=1008
            )
            return

        await manager.connect(
            user_id,
            websocket
        )

        user.is_online = True

        db.commit()

        await manager.broadcast({
            "type": "user_status",
            "user_id": user_id,
            "is_online": True
        })

        while True:

            data = await websocket.receive_json()

            message_type = data.get("type")

            if message_type == "message":

                conversation_id = data.get(
                    "conversation_id"
                )

                group_id = data.get(
                    "group_id"
                )

                content = data.get(
                    "content"
                )

                if not content:
                    continue

                content = content.strip()

                if not content:
                    continue

                if conversation_id:

                    conversation = (
                        db.query(Conversation)
                        .filter(
                            Conversation.id
                            == conversation_id
                        )
                        .first()
                    )

                    if not conversation:

                        await manager.send_to_user(
                            user_id,
                            {
                                "type": "error",
                                "message":
                                    "Conversation not found"
                            }
                        )

                        continue

                    if user_id not in [
                        conversation.user1_id,
                        conversation.user2_id
                    ]:

                        await manager.send_to_user(
                            user_id,
                            {
                                "type": "error",
                                "message":
                                    "You are not part of this conversation"
                            }
                        )

                        continue

                    if conversation.user1_id == user_id:

                        receiver_id = (
                            conversation.user2_id
                        )

                    else:

                        receiver_id = (
                            conversation.user1_id
                        )

                    message = Message(
                        conversation_id=conversation_id,
                        group_id=None,
                        sender_id=user_id,
                        content=content
                    )

                    db.add(message)
                    db.commit()
                    db.refresh(message)

                    message_data = {
                        "type": "message",

                        "id": message.id,

                        "conversation_id":
                            conversation_id,

                        "group_id": None,

                        "sender_id":
                            user_id,

                        "receiver_id":
                            receiver_id,

                        "content":
                            message.content,

                        "is_read":
                            message.is_read,

                        "created_at":
                            message.created_at.isoformat()
                    }


                    await manager.send_to_user(
                        user_id,
                        message_data
                    )

                    await manager.send_to_user(
                        receiver_id,
                        message_data
                    )

                    continue

                if group_id:

                    group = (
                        db.query(Group)
                        .filter(
                            Group.id == group_id
                        )
                        .first()
                    )

                    if not group:

                        await manager.send_to_user(
                            user_id,
                            {
                                "type": "error",
                                "message":
                                    "Group not found"
                            }
                        )

                        continue

                    membership = (
                        db.query(GroupMember)
                        .filter(
                            GroupMember.group_id
                            == group_id,

                            GroupMember.user_id
                            == user_id
                        )
                        .first()
                    )

                    if not membership:

                        await manager.send_to_user(
                            user_id,
                            {
                                "type": "error",
                                "message":
                                    "You are not a member of this group"
                            }
                        )

                        continue

                    message = Message(
                        conversation_id=None,
                        group_id=group_id,
                        sender_id=user_id,
                        content=content
                    )

                    db.add(message)

                    db.commit()

                    db.refresh(message)

                    memberships = (
                        db.query(GroupMember)
                        .filter(
                            GroupMember.group_id
                            == group_id
                        )
                        .all()
                    )

                    member_ids = [
                        member.user_id
                        for member in memberships
                    ]

                    message_data = {
                        "type": "group_message",

                        "id":
                            message.id,

                        "group_id":
                            group_id,

                        "conversation_id":
                            None,

                        "sender_id":
                            user_id,

                        "content":
                            message.content,

                        "is_read":
                            message.is_read,

                        "created_at":
                            message.created_at.isoformat()
                    }

                    await manager.send_to_group(
                        member_ids,
                        message_data
                    )

                    continue

                await manager.send_to_user(
                    user_id,
                    {
                        "type": "error",
                        "message":
                            "conversation_id or group_id is required"
                    }
                )

            elif message_type == "typing":

                receiver_id = data.get(
                    "receiver_id"
                )

                group_id = data.get(
                    "group_id"
                )

                conversation_id = data.get(
                    "conversation_id"
                )


                if group_id:

                    membership = (
                        db.query(GroupMember)
                        .filter(
                            GroupMember.group_id
                            == group_id,

                            GroupMember.user_id
                            == user_id
                        )
                        .first()
                    )

                    if not membership:
                        continue

                    memberships = (
                        db.query(GroupMember)
                        .filter(
                            GroupMember.group_id
                            == group_id,

                            GroupMember.user_id
                            != user_id
                        )
                        .all()
                    )

                    member_ids = [
                        member.user_id
                        for member in memberships
                    ]

                    await manager.send_to_group(
                        member_ids,
                        {
                            "type":
                                "group_typing",

                            "group_id":
                                group_id,

                            "user_id":
                                user_id
                        }
                    )

                    continue

                if receiver_id:

                    if conversation_id:

                        conversation = (
                            db.query(Conversation)
                            .filter(
                                Conversation.id
                                == conversation_id
                            )
                            .first()
                        )

                        if not conversation:
                            continue

                        if user_id not in [
                            conversation.user1_id,
                            conversation.user2_id
                        ]:
                            continue

                    
                        if receiver_id not in [
                            conversation.user1_id,
                            conversation.user2_id
                        ]:
                            continue

                    await manager.send_to_user(
                        receiver_id,
                        {
                            "type":
                                "typing",

                            "user_id":
                                user_id,

                            "conversation_id":
                                conversation_id
                        }
                    )

            elif message_type == "stop_typing":

                receiver_id = data.get(
                    "receiver_id"
                )

                group_id = data.get(
                    "group_id"
                )

                conversation_id = data.get(
                    "conversation_id"
                )

                if group_id:

                    membership = (
                        db.query(GroupMember)
                        .filter(
                            GroupMember.group_id
                            == group_id,

                            GroupMember.user_id
                            == user_id
                        )
                        .first()
                    )

                    if not membership:
                        continue

                    memberships = (
                        db.query(GroupMember)
                        .filter(
                            GroupMember.group_id
                            == group_id,

                            GroupMember.user_id
                            != user_id
                        )
                        .all()
                    )

                    member_ids = [
                        member.user_id
                        for member in memberships
                    ]

                    await manager.send_to_group(
                        member_ids,
                        {
                            "type":
                                "group_stop_typing",

                            "group_id":
                                group_id,

                            "user_id":
                                user_id
                        }
                    )

                    continue

                if receiver_id:

                    if conversation_id:

                        conversation = (
                            db.query(Conversation)
                            .filter(
                                Conversation.id
                                == conversation_id
                            )
                            .first()
                        )

                        if not conversation:
                            continue

                        if user_id not in [
                            conversation.user1_id,
                            conversation.user2_id
                        ]:
                            continue

                        if receiver_id not in [
                            conversation.user1_id,
                            conversation.user2_id
                        ]:
                            continue

                    await manager.send_to_user(
                        receiver_id,
                        {
                            "type":
                                "stop_typing",

                            "user_id":
                                user_id,

                            "conversation_id":
                                conversation_id
                        }
                    )
            elif message_type == "read":

                message_id = data.get(
                    "message_id"
                )

                if not message_id:
                    continue

                message = (
                    db.query(Message)
                    .filter(
                        Message.id == message_id
                    )
                    .first()
                )

                if not message:
                    continue


                if not message.conversation_id:
                    continue

                if message.sender_id == user_id:
                    continue

                conversation = (
                    db.query(Conversation)
                    .filter(
                        Conversation.id
                        == message.conversation_id
                    )
                    .first()
                )

                if not conversation:
                    continue

                if user_id not in [
                    conversation.user1_id,
                    conversation.user2_id
                ]:
                    continue

                message.is_read = True

                db.commit()

                await manager.send_to_user(
                    message.sender_id,
                    {
                        "type":
                            "read",

                        "message_id":
                            message.id,

                        "reader_id":
                            user_id
                    }
                )

            elif message_type == "group_read":

                group_id = data.get(
                    "group_id"
                )

                if not group_id:
                    continue


                membership = (
                    db.query(GroupMember)
                    .filter(
                        GroupMember.group_id
                        == group_id,

                        GroupMember.user_id
                        == user_id
                    )
                    .first()
                )

                if not membership:
                    continue

                membership.last_read_at = (
                    datetime.now(timezone.utc)
                )

                db.commit()
                
                memberships = (
                    db.query(GroupMember)
                    .filter(
                        GroupMember.group_id
                        == group_id,

                        GroupMember.user_id
                        != user_id
                    )
                    .all()
                )

                member_ids = [
                    member.user_id
                    for member in memberships
                ]

                await manager.send_to_group(
                    member_ids,
                    {
                        "type":
                            "group_read",

                        "group_id":
                            group_id,

                        "reader_id":
                            user_id
                    }
                )

    except WebSocketDisconnect:

        manager.disconnect(
            user_id
        )

        if user:

            user.is_online = False

            db.commit()

            await manager.broadcast({
                "type":
                    "user_status",

                "user_id":
                    user_id,

                "is_online":
                    False
            })

    except Exception as e:

        print(
            f"WebSocket error for user {user_id}: {e}"
        )

        try:

            manager.disconnect(
                user_id
            )

        except Exception:
            pass
    finally:

        db.close()



# from fastapi import (
#     APIRouter,
#     WebSocket,
#     WebSocketDisconnect
# )

# from sqlalchemy.orm import Session
# from app.database.database import SessionLocal
# from app.database.models import (
#     User,
#     Conversation,
#     Message
# )

# from app.websocket.manager import manager
# router = APIRouter()

# @router.websocket("/ws/{user_id}")
# async def websocket_chat(
#     websocket: WebSocket,
#     user_id: int
# ):

#     db: Session = SessionLocal()
#     user = None
#     try:
#         user = (
#             db.query(User)
#             .filter(User.id == user_id)
#             .first()
#         )

#         if not user:
#             await websocket.close(
#                 code=1008
#             )
#             return

#         await manager.connect(
#             user_id,
#             websocket
#         )

#         user.is_online = True
#         db.commit()

#         await manager.broadcast(
#             {
#                 "type": "user_status",
#                 "user_id": user_id,
#                 "is_online": True
#             }
#         )

#         while True:
#             data = await websocket.receive_json()
#             message_type = data.get(
#                 "type"
#             )

#             if message_type == "message":
#                 conversation_id = data.get(
#                     "conversation_id"
#                 )
#                 content = data.get(
#                     "content"
#                 )

#                 if not content:
#                     continue
                
#                 content = content.strip()
#                 if not content:
#                     continue

#                 if not conversation_id:
#                     continue
                
#                 conversation = (
#                     db.query(Conversation)
#                     .filter(
#                         Conversation.id ==
#                         conversation_id
#                     )
#                     .first()
#                 )

#                 if not conversation:
#                     await manager.send_to_user(
#                         user_id,
#                         {
#                             "type": "error",
#                             "message":
#                                 "Conversation not found"
#                         }
#                     )
#                     continue

#                 if user_id not in [
#                     conversation.user1_id,
#                     conversation.user2_id
#                 ]:

#                     await manager.send_to_user(
#                         user_id,
#                         {
#                             "type": "error",
#                             "message":
#                                 "You are not part of this conversation"
#                         }
#                     )
#                     continue

#                 if conversation.user1_id == user_id:
#                     receiver_id = (
#                         conversation.user2_id
#                     )

#                 else:
#                     receiver_id = (
#                         conversation.user1_id
#                     )

#                 message = Message(
#                     conversation_id=conversation_id,
#                     sender_id=user_id,
#                     content=content
#                 )

#                 db.add(message)
#                 db.commit()
#                 db.refresh(message)

#                 message_data = {
#                     "type": "message",
#                     "id":
#                         message.id,
#                     "conversation_id":
#                         conversation_id,

#                     "sender_id":
#                         user_id,

#                     "receiver_id":
#                         receiver_id,

#                     "content":
#                         message.content,

#                     "created_at":
#                         message.created_at.isoformat()
#                 }

#                 await manager.send_to_user(
#                     user_id,
#                     message_data
#                 )

#                 await manager.send_to_user(
#                     receiver_id,
#                     message_data
#                 )

#             elif message_type == "typing":
#                 receiver_id = data.get(
#                     "receiver_id"
#                 )

#                 if not receiver_id:
#                     continue

#                 conversation_id = data.get(
#                     "conversation_id"
#                 )

#                 if conversation_id:
#                     conversation = (
#                         db.query(Conversation)
#                         .filter(
#                             Conversation.id ==
#                             conversation_id
#                         )
#                         .first()
#                     )

#                     if not conversation:
#                         continue

#                     if user_id not in [
#                         conversation.user1_id,
#                         conversation.user2_id
#                     ]:
#                         continue

#                     if receiver_id not in [
#                         conversation.user1_id,
#                         conversation.user2_id
#                     ]:
#                         continue

#                 await manager.send_to_user(
#                     receiver_id,
#                     {
#                         "type": "typing",

#                         "user_id":
#                             user_id
#                     }
#                 )
#             elif message_type == "stop_typing":

#                 receiver_id = data.get(
#                     "receiver_id"
#                 )

#                 if not receiver_id:
#                     continue

#                 await manager.send_to_user(
#                     receiver_id,
#                     {
#                         "type":
#                             "stop_typing",
#                         "user_id":
#                             user_id
#                     }
#                 )
#             elif message_type == "read":
#                 message_id = data.get(
#                     "message_id"
#                 )

#                 if not message_id:
#                     continue

#                 message = (
#                     db.query(Message)
#                     .filter(
#                         Message.id ==
#                         message_id
#                     )
#                     .first()
#                 )

#                 if not message:
#                     continue
#                 if message.sender_id == user_id:
#                     continue

#                 message.is_read = True
#                 db.commit()

#                 await manager.send_to_user(
#                     message.sender_id,
#                     {
#                         "type":
#                             "read",
#                         "message_id":
#                             message.id,
#                         "reader_id":
#                             user_id
#                     }
#                 )

#     except WebSocketDisconnect:
#         manager.disconnect(
#             user_id
#         )

#         if user:
#             user.is_online = False
#             db.commit()

#             await manager.broadcast(
#                 {
#                     "type":
#                         "user_status",
#                     "user_id":
#                         user_id,
#                     "is_online":
#                         False
#                 }
#             )

#     except Exception as e:
#         print(
#             f"WebSocket error for user {user_id}: {e}"
#         )

#         try:
#             manager.disconnect(
#                 user_id
#             )
#         except Exception:
#             pass
#     finally:
#         db.close()