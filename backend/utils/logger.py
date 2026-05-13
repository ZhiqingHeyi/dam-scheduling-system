from fastapi import WebSocket
from typing import List
from datetime import datetime
import json
import numpy as np
import pandas as pd

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (pd.Timestamp, datetime)):
            return str(obj)
        elif isinstance(obj, (np.bool_,)):
            return bool(obj)
        return super().default(obj)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.log_buffer: List[dict] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                await self.disconnect(connection)

    async def broadcast_log(self, level: str, message: str, timestamp: str = None):
        log_entry = {
            "type": "log",
            "level": level,
            "message": message,
            "timestamp": timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.log_buffer.append(log_entry)
        if len(self.log_buffer) > 1000:
            self.log_buffer = self.log_buffer[-500:]
        await self.broadcast(json.dumps(log_entry))

    async def broadcast_progress(self, step: int, total: int, status: str, detail: str = ""):
        progress_data = {
            "type": "progress",
            "step": step,
            "total": total,
            "status": status,
            "detail": detail,
            "percentage": round((step / total) * 100, 1) if total > 0 else 0
        }
        await self.broadcast(json.dumps(progress_data))

    async def broadcast_result(self, result: dict):
        result_data = {
            "type": "result",
            "data": result,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        try:
            await self.broadcast(json.dumps(result_data, cls=NumpyEncoder))
        except (TypeError, ValueError) as e:
            safe_result = self._make_serializable(result_data)
            await self.broadcast(json.dumps(safe_result, cls=NumpyEncoder))
    
    def _make_serializable(self, obj):
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (pd.Timestamp, datetime)):
            return str(obj)
        elif isinstance(obj, (np.bool_,)):
            return bool(obj)
        return obj

    def get_recent_logs(self, count: int = 50) -> List[dict]:
        return self.log_buffer[-count:]
