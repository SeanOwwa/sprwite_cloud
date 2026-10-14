from fastapi import APIRouter
from sqlmodel import Session, select
from src.core.database import engine
from src.models.project_model import Project, Folder, Document

router: APIRouter = APIRouter()

# ~ ~ ~ PROJECT API ~ ~ ~
@router.post("/create_project")
def create_project(project: Project):
    with Session(engine) as session:
        session.add(project)
        session.commit()
        session.refresh(project)
    return {
        "success": True, 
        "message": "Project added", 
        "id": project.id
    }

@router.get("/get_projects")
def get_projects():
    with Session(engine) as session:
        projects = session.exec(select(Project)).all()
    return {
        "success": True,
        "data": projects
    }

@router.get("/get_project_tree/{id}")
def get_project_tree_by_id() -> dict:
    with Session(engine) as session:
        project = session.exec(select(Project).where(
            Project.id == id
        ))

        loose_docs = session.exec(
            select(Document).where(
                Document.proj_id == id,
                Document.fold_id.is_(None)
            )
        ).all()

        folders = session.exec(select(Folder).where(
            Folder.proj_id == id
        ))

        # for

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {
        "success": True,
        "project": project
        # ""

    }