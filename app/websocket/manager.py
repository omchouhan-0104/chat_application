from fastapi import WebSocket
class ConnectionManager:

    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(
        self,
        user_id: int,
        websocket: WebSocket
    ):

        await websocket.accept()

        self.active_connections[user_id] = websocket


    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]



    def is_online(self, user_id: int) -> bool:
        return user_id in self.active_connections


    async def send_to_user(
        self,
        user_id: int,
        data: dict
    ):
        websocket = self.active_connections.get(user_id)

        if not websocket:
            return

        try:

            await websocket.send_json(data)
        except Exception:
            self.disconnect(user_id)

    async def send_to_group(
        self,
        member_ids: list[int],
        data: dict
    ):
        for user_id in member_ids:

            await self.send_to_user(
                user_id,
                data
            )

    async def broadcast(
        self,
        data: dict
    ):
        disconnected_users = []
        for user_id, websocket in list(
            self.active_connections.items()
        ):

            try:
                await websocket.send_json(data)
            except Exception:
                disconnected_users.append(user_id)
        for user_id in disconnected_users:
            self.disconnect(user_id)

manager = ConnectionManager()


# from fastapi import WebSocket


# class ConnectionManager:

#     def __init__(self):

#         self.active_connections: dict[
#             int,
#             WebSocket
#         ] = {}

#     async def connect(
#         self,
#         user_id: int,
#         websocket: WebSocket
#     ):

#         await websocket.accept()

#         self.active_connections[user_id] = websocket


#     def disconnect(
#         self,
#         user_id: int
#     ):

#         if user_id in self.active_connections:

#             del self.active_connections[user_id]

#     def is_online(
#         self,
#         user_id: int
#     ) -> bool:

#         return user_id in self.active_connections


#     async def send_to_user(
#         self,
#         user_id: int,
#         data: dict
#     ):

#         websocket = self.active_connections.get(
#             user_id
#         )

#         if not websocket:
#             return

#         try:

#             await websocket.send_json(
#                 data
#             )

#         except Exception:

#             self.disconnect(
#                 user_id
#             )

#     async def broadcast(
#         self,
#         data: dict
#     ):

#         disconnected_users = []

#         for user_id, websocket in list(
#             self.active_connections.items()
#         ):

#             try:

#                 await websocket.send_json(
#                     data
#                 )

#             except Exception:

#                 disconnected_users.append(
#                     user_id
#                 )

#         for user_id in disconnected_users:

#             self.disconnect(
#                 user_id
#             )

# manager = ConnectionManager()