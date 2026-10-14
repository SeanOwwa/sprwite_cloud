from sqlmodel import SQLModel, create_engine, Session
from src.services.project_service import ProjectService
from src.models.project_model import Project

def test_tree_and_move():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as s:
        p = Project(title="T", author="A"); s.add(p); s.commit(); s.refresh(p)
        svc = ProjectService(s)
        f = svc.create_folder(p.id, "Act One")
        svc.create_document(p.id, "Scene 1", fold_id=f.id)
        svc.create_document(p.id, "Loose")
        d = svc.create_document(p.id, "Scene 2", fold_id=f.id)

        tree = svc.get_project_tree(p.id)
        assert [fo.name for fo in tree["folders"]] == ["Act One"]
        assert [x.name for x in tree["folders"][0].documents] == ["Scene 1", "Scene 2"]
        assert [x.name for x in tree["loose_documents"]] == ["Loose"]

        # move Scene 2 out of the folder to the top
        svc.move_document(d.id, fold_id=None, position=0)
        tree = svc.get_project_tree(p.id)
        assert [x.name for x in tree["loose_documents"]] == ["Scene 2", "Loose"]
