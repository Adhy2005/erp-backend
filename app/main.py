"""
app/main.py
-----------
FastAPI app entry point.
Registers CORS middleware and all API routers created for Week 1 task.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

# Import all route files (Week 1 RBAC + Week 2 Auth & User Management)
from app.routes import projects, sprints, tasks, workspace, finance
from app.routes import auth, users, clients, attendance
from webhooks.jibble.router import router as jibble_router
from webhooks.github.router import router as github_router

API_PREFIX = "/api/v1"

app = FastAPI(
    title="ERP System API",
    version="1.0.0",
    description="ERP System — RBAC + Project System (Week 1, Leelavathi)",
)

# Allow the React frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(projects.router, prefix=API_PREFIX)
app.include_router(sprints.router,  prefix=API_PREFIX)
app.include_router(tasks.router,    prefix=API_PREFIX)
app.include_router(workspace.router, prefix=API_PREFIX)
app.include_router(finance.router,  prefix=API_PREFIX)
app.include_router(auth.router,     prefix=API_PREFIX)
app.include_router(users.router,    prefix=API_PREFIX)
app.include_router(clients.router,  prefix=API_PREFIX)
app.include_router(attendance.router, prefix=API_PREFIX)
app.include_router(jibble_router)
app.include_router(github_router)


@app.get("/")
def root():
    return {
        "message": "ERP System API is running",
        "docs": "/docs",
        "version": "1.0.0",
    }
