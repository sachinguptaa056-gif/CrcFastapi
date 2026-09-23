from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field
from pydantic import field_validator

class ItemStatus(str, Enum):
    LOST = "Lost"
    FOUND = "Found"
    RETURNED = "Returned"

class ItemBase(SQLModel):
    title: str = Field(..., description="Title/name of the lost or found item")
    description: str = Field(..., description="Description of the item")
    category: str = Field(..., description="Category such as Electronics, Documents, Accessories, etc.")
    location: str = Field(..., description="Location where the item was lost or found")
    reported_by: str = Field(..., description="Name of the person reporting the item")
    status: ItemStatus = Field(..., description="Status of the item: Lost, Found, or Returned")

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Title must not be empty.")
        return v.strip()

    @field_validator("description")
    @classmethod
    def description_must_be_meaningful(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Description must not be empty.")
        if len(v.strip()) < 3:
            raise ValueError("Description must contain meaningful text.")
        return v.strip()

    @field_validator("category", "location", "reported_by")
    @classmethod
    def field_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field must not be empty.")
        return v.strip()

class Item(ItemBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class ItemCreate(ItemBase):
    pass

class ItemUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    reported_by: Optional[str] = None
    status: Optional[ItemStatus] = None

    @field_validator("title")
    @classmethod
    def check_title(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v or not v.strip():
                raise ValueError("Title must not be empty.")
            return v.strip()
        return v

    @field_validator("description")
    @classmethod
    def check_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v or not v.strip():
                raise ValueError("Description must not be empty.")
            if len(v.strip()) < 3:
                raise ValueError("Description must contain meaningful text.")
            return v.strip()
        return v

    @field_validator("category", "location", "reported_by")
    @classmethod
    def check_fields(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v or not v.strip():
                raise ValueError("Field must not be empty.")
            return v.strip()
        return v
