import os, httpx
from nicegui import ui
from dotenv import load_dotenv

load_dotenv()
API_BASE_URL:str = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api")

async def fetchProject() -> list[dict]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/project/get_projects")
        response.raise_for_status()
        payload = response.json()
        return payload["data"]

@ui.page("/")
async def dashboard_page():
    ui.label("Dashboard").classes("text-2xl font-bold")
    projects: list[dict] = await fetchProject();

    if not projects:
        ui.label("No projects yet. Create your first novel!")
    
    with ui.grid(columns=6).classes("gap-4 p-4 w-full"):
        for proj_item in projects:
            with ui.card().on(
                "click", 
                lambda proj_item = proj_item: ui.navigate.to(f"/editor_page?project_id={proj_item["id"]}")
            ):
                ui.label(proj_item["title"]).classes("text-lg font-bold")
                ui.label(f"by {proj_item['author']}")
    
    # card.make_sortable(on_end=lambda e: ui.notify(f'Moved from {e.old_index} to {e.new_index}'))

    # ui.button(
    #     'Go to Editor', 
    #     on_click=lambda: ui.navigate.to('/editor_page')
    # )