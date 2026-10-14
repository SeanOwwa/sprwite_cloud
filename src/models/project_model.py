from sqlalchemy import Column, Text
from sqlmodel import Field, Relationship
from src.models.based_model import BaseModel

class Project(BaseModel, table=True):
    title: str
    author: str
    cover: str | None = None
    position: int = Field(default=0)

    folders: list["Folder"] = Relationship(back_populates="project")
    documents: list["Document"] = Relationship(back_populates="project")

class Folder(BaseModel, table=True):
    proj_id: int = Field(foreign_key="project.id", index=True)
    name: str
    position: int = Field(default=0)

    project: Project | None = Relationship(back_populates="folders")
    documents: list["Document"] = Relationship(back_populates="folder")

class Document(BaseModel, table=True):

    proj_id: int = Field(foreign_key="project.id", index=True)
    fold_id: int | None = Field(default=None, foreign_key="folder.id", index=True)
    name: str
    written_text: str = Field(default="", sa_column=Column(Text))
    position: int = Field(default=0)

    folder: Folder | None = Relationship(back_populates="documents")
    project: Project | None = Relationship(back_populates="documents")
