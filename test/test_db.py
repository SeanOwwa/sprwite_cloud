from sqlmodel import Session, select, SQLModel, create_engine
from src.models.project_model import Project, Folder, Document

def test_can_save_and_read_a_project():
    # STEP 1 ARRANGE
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    # STEP 2 ACT
    with Session(engine) as session:
        projItem: Project = Project(
            title="Jaded Hound", 
            author="Seanless", 
            cover=None
        )
        session.add(projItem)
        session.commit()
        session.refresh(projItem)
        
        foldItem: Folder = Folder(
            name="Chapters",
            proj_id=projItem.id
        )
        session.add(foldItem)
        session.commit()
        session.refresh(foldItem)
        
        session.add(Document(
            name="Chapter 1",
            written_text="Hello Spwrite User!",
            proj_id=projItem.id,
            fold_id=foldItem.id
        ))
        session.add(Document(
            name="Overview",
            written_text="Jaded Hound Story, Theme Corruption",
            proj_id=projItem.id,
            fold_id=None
        ))
        session.commit()

    # STEP 3 ASSERTION
    with Session(engine) as session:
        proj: Project = session.exec(select(Project)).all()
        fold: Folder = session.exec(select(Folder)).all()
        doc: Document = session.exec(select(Document)).all()

    # Project Assertion
    assert len(proj) == 1
    assert proj[0].title == "Jaded Hound"
    assert proj[0].id is not None

    # Folder Assertion
    assert len(fold) == 1
    assert fold[0].name == "Chapters"
    assert fold[0].proj_id is not None

    # Document Assertion
    assert len(doc) == 2

    assert doc[0].name == "Chapter 1"
    assert doc[0].written_text == "Hello Spwrite User!"
    assert doc[0].proj_id is not None
    assert doc[0].fold_id is not None

    assert doc[1].name == "Overview"
    assert doc[1].written_text == "Jaded Hound Story, Theme Corruption"
    assert doc[1].proj_id is not None
    assert doc[1].fold_id is None



        