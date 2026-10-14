from datetime import datetime, timezone
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from src.models.project_model import Document, Folder

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class ProjectService():
    def __init__(self, session: Session):
        self.session = session

    def _next_position(
        self, 
        proj_id: int, 
        fold_id: int | None
    ) -> int:
        stmt = select(Document).where(
            Document.proj_id == proj_id,
            Document.is_del == False
        )

        stmt = stmt.where(Document.fold_id.is_(None)) if fold_id is None \
            else stmt.where(Document.fold_id == fold_id)
        
        return len(self.session.exec(stmt).all())
    
    def _renumber(
        self, 
        proj_id: int, 
        fold_id: int, 
        move_id = None, 
        insert_at = None
    ) -> None:
        stmt = select(Document).where(
            Document.proj_id == proj_id,
            Document.is_del == False
        )

        stmt = stmt.where(Document.fold_id.is_(None)) if fold_id is None \
            else stmt.where(Document.fold_id == fold_id)

        items = self.session.exec(
            stmt.order_by(Document.position)
        ).all()

        if move_id is not None and insert_at is not None:
            items = [d for d in items if d.id != move_id]
            moved = self.session.get(Document, move_id)
            insert_at = max(0, min(insert_at, len(items)))
            items.insert(insert_at, moved)
        
        for i, d in enumerate(items):
            if d.position != i:
                d.position = i
                d.updated = utcnow()
                self.session.add(d)

        self.session.commit()
    
    def create_folder(
        self, 
        proj_id: int, 
        name: str
    ) -> Folder:
        count = len(self.session.exec(
            select(Folder).where(
                Folder.proj_id == proj_id,
                Folder.is_del == False
            )
        ).all())
        folder = Folder(
            proj_id = proj_id,
            name = name,
            position = count
        )
        self.session.add(folder)
        self.session.commit()
        self.session.refresh(folder)
        return folder

    def create_document(
        self,
        proj_id: int,
        name: str,
        fold_id: int | 
        None = None
    ) -> Document:

        position = self._next_position(proj_id, fold_id)
        
        doc = Document(
            proj_id=proj_id,
            name=name,
            fold_id=fold_id,
            position=position
        )
        self.session.add(doc)
        self.session.commit()
        self.session.refresh(doc)

        return doc

    def get_project_tree(
        self,
        proj_id: int
    ) -> dict: 
        folder = self.session.exec(
            select(Folder)
            .where(
                Folder.proj_id == proj_id,
                Folder.is_del == False
            )
            .order_by(Folder.position)
            .options(selectinload(Folder.documents))
        ).all()

        loose_docs = self.session.exec(
            select(Document)
            .where(
                Document.proj_id == proj_id,
                Document.fold_id.is_(None),
                Document.is_del == False
            )
            .order_by(Document.position)
        ).all()
        return {
            "folders": folder,
            "loose_documents": loose_docs
        }

    def move_document(
        self, 
        doc_id: int,
        fold_id: int |
        None, 
        position: int
    ) -> Document:
        doc: Document = self.session.get(
            Document,
            doc_id
        )

        if not doc or doc.is_del:
            raise ValueError("Document not found.")
        
        source_fold = doc.fold_id
        doc.fold_id = fold_id
        doc.updated = utcnow()
        doc.version += 1
        self.session.add(doc)
        self.session.commit()

        self._renumber(
            doc.proj_id,
            fold_id,
            move_id=doc.id,
            insert_at=position
        )
        if source_fold != fold_id:
            self._renumber(doc.proj_id, source_fold)
        
        self.session.refresh(doc)

        return doc

    def reorder_folder(
        self,
        fold_id: int,
        position: int
    ) -> Folder:
        folder: Folder = self.session.get(
            Folder, 
            fold_id
        )
        if not folder or folder.is_del:
            raise ValueError("Folder not Found")
        
        others = self.session.exec(
            select(Folder)
            .where(
                Folder.proj_id == folder.proj_id,
                Folder.is_del == False,
                Folder.id != fold_id
            )
            .order_by(Folder.position)
        ).all()

        position = max(0, min(position, len(others)))

        others.insert(
            position, 
            folder
        )
        
        for i, f in enumerate(others):
            if f.position != i:
                f.position = i
                f.updated = utcnow()
                self.session.add(f)
        self.session.commit()
        self.session.refresh(folder)
        return folder