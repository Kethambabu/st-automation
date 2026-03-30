from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI()

class Item(BaseModel):
    id: int = Field(..., gt=0, description='Unique numeric identifier')
    name: str = Field(..., min_length=1, description='Human-readable item name')
    description: str | None = Field(None, description='Optional item description')

# in-memory sample data
items = {
    1: Item(id=1, name="Widget", description="A useful widget."),
    2: Item(id=2, name="Gadget", description="A handy gadget."),
}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    return items[item_id]

@app.post("/items")
async def create_item(item: Item):
    if item.id in items:
        raise HTTPException(status_code=400, detail="Item already exists")
    items[item.id] = item
    return item
