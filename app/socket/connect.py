import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect
from app.services.redis_common_state import get_session_data,save_session_data
from app.utils.logger import logger
from typing import Optional


class WebSocketConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, socket_session_id: str):
        await websocket.accept()
        if socket_session_id not in self.active_connections:
            self.active_connections[socket_session_id] = set()
        self.active_connections[socket_session_id].add(websocket)
        logger.info(f"WebSocket connection established for socket_id: {socket_session_id}")
        await self.send_json(websocket, {"status": "success", "message": f"WebSocket connected successfully"})


    def disconnect(self, websocket: WebSocket,user_id:Optional[str]=None,socket_session_id:Optional[str]=None, app_name: Optional[str] = None):
        if user_id and socket_session_id and app_name:
            raw_data = get_session_data(user_id, app_name)
            if not raw_data:
                return

            if isinstance(raw_data, str):
                session_data = json.loads(raw_data)
            else:
                session_data = raw_data
            socket_ids_json = session_data.get("socket_session_ids")
            if not socket_ids_json:
                return

            socket_ids = json.loads(socket_ids_json)
            logger.info(f"before removing socket_ids: {socket_ids} for app_name: {app_name}")
            if socket_session_id in socket_ids:
                socket_ids.remove(socket_session_id)
                session_data["socket_session_ids"] = json.dumps(socket_ids)
                save_session_data(user_id, session_data,app_name)
            socket_ids=get_session_data(user_id, app_name)
            logger.info(f"after removing socket_ids: {socket_ids} for app_name: {app_name}")
        for session_id, connections in list(self.active_connections.items()):
            if websocket in connections:
                connections.remove(websocket)
                logger.info(f"WebSocket disconnected for session_id: {session_id}")
                if not connections:
                    del self.active_connections[session_id]
                break


    async def send_json(self, websocket: WebSocket, data):
        try:
            await websocket.send_json(data)
        except Exception as e:
            logger.error(f"Error sending JSON over WebSocket: {e}")
            raise

    async def receive_text(self, websocket: WebSocket):
        try:
            return await websocket.receive_text()
        except WebSocketDisconnect:
            self.disconnect(websocket)
            raise
        except Exception as e:
            logger.error(f"Error receiving text over WebSocket: {e}")
            raise


    async def broadcast_message_to_socket_session(self, session_id: str, data):
        connections = self.active_connections.get(session_id, set())
        logger.info(f"Broadcasting to session {session_id} with {len(connections)} connection(s): {data}")
        disconnected = []
        for conn in connections:
            try:
                await conn.send_json(data)
            except Exception as e:
                logger.error(f"Error sending to session {session_id} WebSocket: {e}")
                disconnected.append(conn)

        for conn in disconnected:
            connections.remove(conn)
        if not connections:
            self.active_connections.pop(session_id, None)

        logger.info(f"Broadcast to session {session_id} complete.")

    
    async def broadcast_json_to_user(self, user_id: str, data: dict, app_name: Optional[str] = None):
        raw_data = get_session_data(user_id, app_name)
        print("user_id:",user_id)
        print("app_name:",app_name)
        # print("raw_data:",raw_data)
        
        if not raw_data:
            return

        if isinstance(raw_data, str):
            session_data = json.loads(raw_data)
        else:
            session_data = raw_data

        socket_ids_json = session_data.get("socket_session_ids")
        if not socket_ids_json:
            return

        socket_ids = json.loads(socket_ids_json)

        for session_id in socket_ids:
            await self.broadcast_message_to_socket_session(session_id, data)



    async def handle_reconnection(self, websocket: WebSocket, handler, *args, **kwargs):
        reconnect_attempts = 0
        max_reconnect_attempts = 3
        while reconnect_attempts < max_reconnect_attempts:
            try:
                await handler(websocket, *args, **kwargs)
                break
            except WebSocketDisconnect:
                reconnect_attempts += 1
                logger.warning(f"WebSocket disconnected. Attempting to reconnect ({reconnect_attempts}/{max_reconnect_attempts})...")
                await asyncio.sleep(2 ** reconnect_attempts)  # Exponential backoff
            except Exception as e:
                logger.error(f"Unexpected error in WebSocket handler: {e}")
                break
        else:
            logger.error("Max reconnection attempts reached. Giving up.")

    async def heartbeat(self, websocket: WebSocket, interval: int = 20):
        """
        Periodically send a ping to the client to keep the connection alive.
        """
        try:
            while True:
                await asyncio.sleep(interval)
                try:
                    await websocket.send_text("__ping__")
                    logger.debug("Sent heartbeat ping to client.")
                except Exception as e:
                    logger.error(f"Heartbeat failed: {e}")
                    break
        except asyncio.CancelledError:
            logger.info("Heartbeat task cancelled.") 

manager = WebSocketConnectionManager()
