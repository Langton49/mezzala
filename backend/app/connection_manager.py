from fastapi import WebSocket
from collections import defaultdict

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        
    async def connect(self, uuid: str, ws: WebSocket):
        await ws.accept()
        self.active_connections[uuid] = ws
        print(self.active_connections)
    
    def disconnect(self, uuid: str):
        self.active_connections.pop(uuid, None)
                                    
    async def broadcast(self, payload: dict):
       for uuid, con in list(self.active_connections.items()):
            try:
                await con.send_json(payload)
            except Exception:
                print(f"{Exception}. Could not reach connection for {uuid}. Disconnecting...")
                self.disconnect(uuid)
                
manager = ConnectionManager()