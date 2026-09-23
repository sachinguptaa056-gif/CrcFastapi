from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from sqlmodel import Session, select

from database import create_db_and_tables, get_session
from models import Item, ItemCreate, ItemUpdate, ItemStatus

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables when application starts
    create_db_and_tables()
    yield

app = FastAPI(
    title="College Lost & Found API",
    description="A digital Lost & Found REST API built with FastAPI, SQLModel, and SQLite.",
    version="1.0.0",
    lifespan=lifespan,
)

# 1. POST /items - Create a new lost/found item
@app.post("/items", response_model=Item, status_code=status.HTTP_201_CREATED, tags=["Items"])
def create_item(item: ItemCreate, session: Session = Depends(get_session)):
    db_item = Item.model_validate(item)
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item

# 2. GET /items - Return all reported items
@app.get("/items", response_model=List[Item], tags=["Items"])
def read_items(session: Session = Depends(get_session)):
    items = session.exec(select(Item)).all()
    return items

# 6. GET /items/status/{status} - Return items based on their status
@app.get("/items/status/{status_val}", response_model=List[Item], tags=["Filtering"])
def read_items_by_status(status_val: str, session: Session = Depends(get_session)):
    # Validate status value against ItemStatus Enum
    matched_status = None
    for s in ItemStatus:
        if s.value.lower() == status_val.lower():
            matched_status = s
            break
    
    if not matched_status:
        valid_statuses = ", ".join([s.value for s in ItemStatus])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{status_val}'. Status must be one of: {valid_statuses}"
        )
    
    items = session.exec(select(Item).where(Item.status == matched_status)).all()
    return items

# 7. GET /items/category/{category} - Return all items belonging to a particular category
@app.get("/items/category/{category_val}", response_model=List[Item], tags=["Filtering"])
def read_items_by_category(category_val: str, session: Session = Depends(get_session)):
    # Case-insensitive category match
    all_items = session.exec(select(Item)).all()
    filtered_items = [
        item for item in all_items 
        if item.category.lower() == category_val.lower()
    ]
    return filtered_items

# 3. GET /items/{item_id} - Return a specific item using its ID
@app.get("/items/{item_id}", response_model=Item, tags=["Items"])
def read_item(item_id: int, session: Session = Depends(get_session)):
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} does not exist."
        )
    return item

# 4. PUT /items/{item_id} - Update details/status of an existing item
@app.put("/items/{item_id}", response_model=Item, tags=["Items"])
def update_item(item_id: int, item_update: ItemUpdate, session: Session = Depends(get_session)):
    db_item = session.get(Item, item_id)
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} does not exist."
        )
    
    update_data = item_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)
        
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item

# 5. DELETE /items/{item_id} - Delete an item report
@app.delete("/items/{item_id}", tags=["Items"])
def delete_item(item_id: int, session: Session = Depends(get_session)):
    db_item = session.get(Item, item_id)
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} does not exist."
        )
    
    session.delete(db_item)
    session.commit()
    return {"message": f"Item report with ID {item_id} has been successfully deleted.", "deleted_id": item_id}
