from fastapi import APIRouter
# from src.api.routes import editor
from src.api.routes import project_api

api_router: APIRouter = APIRouter()

api_router.include_router(
    project_api.router,
    prefix="/project",
    tags=["Project"]
)


# api_router.include_router(
#     users.router,
#     prefix="/users",
#     tags=["Users"],
# )