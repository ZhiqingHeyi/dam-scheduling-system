from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import json
import os
from typing import List
from api import database, scheduling, files
from api.aiware_api import router as aiware_router
from utils.logger import ConnectionManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.connection_manager = ConnectionManager()
    yield

app = FastAPI(
    title="拱坝动态排仓系统 API",
    description="基于AHP-熵权法的智能拱坝施工排仓系统",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(database.router, prefix="/api/database", tags=["数据库管理"])
app.include_router(scheduling.router, prefix="/api/scheduling", tags=["排仓调度"])
app.include_router(files.router, prefix="/api/files", tags=["文件管理"])
app.include_router(aiware_router, tags=["AIWARE数据库"])

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "dist")

if os.path.exists(FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await app.state.connection_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await app.state.connection_manager.broadcast(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        app.state.connection_manager.disconnect(websocket)

@app.get("/")
async def root():
    if os.path.exists(FRONTEND_DIR):
        index_file = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
    return {
        "message": "拱坝动态排仓系统 API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "dam-scheduling-api"}

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if os.path.exists(FRONTEND_DIR):
        file_path = os.path.join(FRONTEND_DIR, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        index_file = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
    return {"error": "Frontend not built"}
