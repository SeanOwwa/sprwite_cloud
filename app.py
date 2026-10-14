from fastapi import FastAPI
from nicegui import ui
from src.core.database import create_db_and_tables as create_tables
from src.api.router import api_router
from src.ui.pages import dashboard, editor

app: FastAPI = FastAPI(title="Spwrite Cloud API")

create_tables()

# FastAPI endpoints
app.include_router(api_router, prefix="/api")

# NiceGUI pages
editor.editor_page()
dashboard.dashboard_page()

# Mount NiceGUI onto FastAPI
ui.run_with(
    app,
    mount_path="/",
    title="Spwrite Cloud",
)