"""
Sample Todo API for Testing
============================

A simple FastAPI application with basic CRUD operations.
Perfect for testing the AI Test Generation Platform.

Endpoints:
- GET /health - Health check
- GET /todos - Get all todos
- GET /todos/{todo_id} - Get a specific todo
- POST /todos - Create a new todo
- PUT /todos/{todo_id} - Update a todo
- DELETE /todos/{todo_id} - Delete a todo
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from uuid import uuid4

app = FastAPI(
    title="Sample Todo API",
    description="A simple API for testing the AI Test Generation Platform",
    version="1.0.0"
)

# ============================================================================
# DATA MODELS
# ============================================================================

class TodoItem(BaseModel):
    """A todo item."""
    id: str
    title: str
    description: Optional[str] = None
    completed: bool = False


class TodoCreate(BaseModel):
    """Request model for creating a todo."""
    title: str
    description: Optional[str] = None


class TodoUpdate(BaseModel):
    """Request model for updating a todo."""
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None


# ============================================================================
# IN-MEMORY STORAGE
# ============================================================================

# Simple in-memory storage (resets when server restarts)
todos_db: dict[str, dict] = {
    "1": {
        "id": "1",
        "title": "Learn FastAPI",
        "description": "Study FastAPI framework documentation",
        "completed": False
    },
    "2": {
        "id": "2",
        "title": "Build a REST API",
        "description": "Create a basic REST API",
        "completed": False
    },
}


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Sample Todo API"
    }


@app.get("/todos", response_model=List[TodoItem], tags=["Todos"])
def get_todos(
    completed: Optional[bool] = Query(None, description="Filter by completion status")
):
    """
    Get all todos.
    
    Query Parameters:
    - completed (optional): Filter by completion status (true/false)
    """
    todos_list = list(todos_db.values())
    
    if completed is not None:
        todos_list = [t for t in todos_list if t["completed"] == completed]
    
    return todos_list


@app.get("/todos/{todo_id}", response_model=TodoItem, tags=["Todos"])
def get_todo(todo_id: str):
    """Get a specific todo by ID."""
    if todo_id not in todos_db:
        raise HTTPException(
            status_code=404,
            detail=f"Todo with ID {todo_id} not found"
        )
    return todos_db[todo_id]


@app.post("/todos", response_model=TodoItem, status_code=201, tags=["Todos"])
def create_todo(todo: TodoCreate):
    """
    Create a new todo.
    
    Request body:
    - title (required): Title of the todo
    - description (optional): Detailed description
    """
    new_id = str(uuid4())
    new_todo = {
        "id": new_id,
        "title": todo.title,
        "description": todo.description or None,
        "completed": False
    }
    todos_db[new_id] = new_todo
    return new_todo


@app.put("/todos/{todo_id}", response_model=TodoItem, tags=["Todos"])
def update_todo(todo_id: str, todo_update: TodoUpdate):
    """
    Update a todo by ID.
    
    Request body (all fields optional):
    - title: New title
    - description: New description
    - completed: Mark as completed
    """
    if todo_id not in todos_db:
        raise HTTPException(
            status_code=404,
            detail=f"Todo with ID {todo_id} not found"
        )
    
    existing = todos_db[todo_id]
    
    if todo_update.title is not None:
        existing["title"] = todo_update.title
    if todo_update.description is not None:
        existing["description"] = todo_update.description
    if todo_update.completed is not None:
        existing["completed"] = todo_update.completed
    
    return existing


@app.delete("/todos/{todo_id}", status_code=204, tags=["Todos"])
def delete_todo(todo_id: str):
    """Delete a todo by ID."""
    if todo_id not in todos_db:
        raise HTTPException(
            status_code=404,
            detail=f"Todo with ID {todo_id} not found"
        )
    
    del todos_db[todo_id]
    return None


@app.post("/todos/bulk/clear", status_code=200, tags=["Todos"])
def clear_all_todos():
    """Clear all todos (for testing purposes)."""
    global todos_db
    count = len(todos_db)
    todos_db.clear()
    return {
        "message": f"Cleared {count} todos",
        "count": count
    }


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@app.get("/stats", tags=["Utils"])
def get_stats():
    """Get statistics about todos."""
    all_todos = list(todos_db.values())
    completed = sum(1 for t in all_todos if t["completed"])
    pending = sum(1 for t in all_todos if not t["completed"])
    
    return {
        "total_todos": len(all_todos),
        "completed": completed,
        "pending": pending,
        "completion_rate": f"{(completed / len(all_todos) * 100):.1f}%" if all_todos else "0%"
    }


@app.get("/info", tags=["Utils"])
def get_info():
    """Get API information."""
    return {
        "name": "Sample Todo API",
        "version": "1.0.0",
        "description": "A simple API for testing AI-driven test generation",
        "author": "Test Platform",
        "endpoints": {
            "health": "GET /health",
            "todos_list": "GET /todos",
            "get_todo": "GET /todos/{todo_id}",
            "create_todo": "POST /todos",
            "update_todo": "PUT /todos/{todo_id}",
            "delete_todo": "DELETE /todos/{todo_id}",
            "stats": "GET /stats",
            "info": "GET /info"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
