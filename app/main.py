# main.py
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict
from enum import Enum
from abc import ABC, abstractmethod
import uuid
from datetime import datetime
import logging
from threading import Lock
from contextlib import asynccontextmanager

# ============= CONFIGURACIÓN =============
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lock para proteger operaciones concurrentes
SESSION_LOCK = Lock()

# ============= LIFESPAN =============
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 API iniciada correctamente")
    yield
    # Shutdown (si necesario)
    pass

app = FastAPI(
    title="Task Management API",
    description="API RESTful con principios SOLID y patrones de diseño",
    version="2.0.0",
    lifespan=lifespan
)

# ============= CORS CONFIGURACIÓN MEJORADA =============
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://proyecto-caso-testigo-perez-carvajal.vercel.app",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# ============= ENUMS Y CONSTANTES =============
class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class Priority(int, Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

# ============= MODELOS =============
class TaskBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    priority: int = Field(default=2, ge=1, le=4)
    
    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()

class TaskCreate(TaskBase):
    tags: Optional[List[str]] = []
    due_date: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[TaskStatus] = None
    priority: Optional[int] = Field(None, ge=1, le=4)
    tags: Optional[List[str]] = None
    due_date: Optional[str] = None
    
    @field_validator('title')
    @classmethod
    def title_not_empty_if_present(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Title cannot be empty')
        return v.strip() if v else v

class Task(TaskBase):
    id: str
    status: TaskStatus = TaskStatus.PENDING
    tags: List[str] = []
    due_date: Optional[str] = None
    created_at: str
    updated_at: str

class TaskStats(BaseModel):
    total: int
    pending: int
    in_progress: int
    completed: int
    cancelled: int

# ============= REPOSITORY PATTERN (Interface) =============
class IRepository(ABC):
    @abstractmethod
    def find_all(self, session_id: str) -> List[Dict]:
        pass
    
    @abstractmethod
    def find_by_id(self, session_id: str, task_id: str) -> Optional[Dict]:
        pass
    
    @abstractmethod
    def create(self, session_id: str, task: Dict) -> Dict:
        pass
    
    @abstractmethod
    def update(self, session_id: str, task_id: str, updates: Dict) -> Optional[Dict]:
        pass
    
    @abstractmethod
    def delete(self, session_id: str, task_id: str) -> bool:
        pass

# ============= REPOSITORY IMPLEMENTATION =============
class InMemoryTaskRepository(IRepository):
    def __init__(self):
        self._storage: Dict[str, List[Dict]] = {}
    
    def find_all(self, session_id: str) -> List[Dict]:
        return self._storage.get(session_id, [])
    
    def find_by_id(self, session_id: str, task_id: str) -> Optional[Dict]:
        tasks = self._storage.get(session_id, [])
        return next((t for t in tasks if t["id"] == task_id), None)
    
    def create(self, session_id: str, task: Dict) -> Dict:
        with SESSION_LOCK:
            if session_id not in self._storage:
                self._storage[session_id] = []
            self._storage[session_id].append(task)
        return task
    
    def update(self, session_id: str, task_id: str, updates: Dict) -> Optional[Dict]:
        with SESSION_LOCK:
            task = self.find_by_id(session_id, task_id)
            if task:
                task.update(updates)
                task["updated_at"] = datetime.utcnow().isoformat()
        return task
    
    def delete(self, session_id: str, task_id: str) -> bool:
        with SESSION_LOCK:
            tasks = self._storage.get(session_id, [])
            task = self.find_by_id(session_id, task_id)
            if task:
                tasks.remove(task)
                return True
        return False

# ============= SERVICE LAYER (Business Logic) =============
class TaskService:
    def __init__(self, repository: IRepository):
        self._repo = repository
    
    def get_all_tasks(self, session_id: str, status: Optional[str] = None) -> List[Task]:
        tasks = self._repo.find_all(session_id)
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        return [Task(**t) for t in tasks]
    
    def get_task_by_id(self, session_id: str, task_id: str) -> Task:
        task = self._repo.find_by_id(session_id, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return Task(**task)
    
    def create_task(self, session_id: str, task_data: TaskCreate) -> Task:
        now = datetime.utcnow().isoformat()
        task_dict = {
            "id": str(uuid.uuid4()),
            **task_data.model_dump(),
            "status": TaskStatus.PENDING.value,
            "created_at": now,
            "updated_at": now
        }
        created = self._repo.create(session_id, task_dict)
        logger.info(f"Task created: {created['id']}")
        return Task(**created)
    
    def update_task(self, session_id: str, task_id: str, updates: TaskUpdate) -> Task:
        update_dict = updates.model_dump(exclude_unset=True)
        if not update_dict:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        updated = self._repo.update(session_id, task_id, update_dict)
        if not updated:
            raise HTTPException(status_code=404, detail="Task not found")
        
        logger.info(f"Task updated: {task_id}")
        return Task(**updated)
    
    def delete_task(self, session_id: str, task_id: str) -> None:
        deleted = self._repo.delete(session_id, task_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Task not found")
        logger.info(f"Task deleted: {task_id}")
    
    def get_statistics(self, session_id: str) -> TaskStats:
        tasks = self._repo.find_all(session_id)
        stats = {
            "total": len(tasks),
            "pending": sum(1 for t in tasks if t["status"] == TaskStatus.PENDING.value),
            "in_progress": sum(1 for t in tasks if t["status"] == TaskStatus.IN_PROGRESS.value),
            "completed": sum(1 for t in tasks if t["status"] == TaskStatus.COMPLETED.value),
            "cancelled": sum(1 for t in tasks if t["status"] == TaskStatus.CANCELLED.value)
        }
        return TaskStats(**stats)
    
    def search_tasks(self, session_id: str, query: str) -> List[Task]:
        tasks = self._repo.find_all(session_id)
        query_lower = query.lower()
        filtered = [
            t for t in tasks 
            if query_lower in t["title"].lower() or 
               (t.get("description") and query_lower in t["description"].lower())
        ]
        return [Task(**t) for t in filtered]

# ============= SESSION MANAGEMENT =============
class SessionManager:
    @staticmethod
    def get_or_create_session(request: Request, response: Response) -> str:
        session_id = request.cookies.get("session_id")
        if not session_id:
            session_id = str(uuid.uuid4())
            response.set_cookie(
                key="session_id",
                value=session_id,
                httponly=True,
                samesite="none",
                secure=True,
                max_age=86400 * 30
            )
        return session_id

# ============= DEPENDENCY INJECTION =============
repository = InMemoryTaskRepository()
task_service = TaskService(repository)

def get_task_service() -> TaskService:
    return task_service

def get_session_id(request: Request, response: Response) -> str:
    return SessionManager.get_or_create_session(request, response)

# ============= ENDPOINTS =============

@app.get("/health")
def health_check(request: Request, response: Response):
    """Health check endpoint"""
    get_session_id(request, response)
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0"
    }

@app.get("/tasks", response_model=List[Task])
def list_tasks(
    status: Optional[str] = None,
    session_id: str = Depends(get_session_id),
    service: TaskService = Depends(get_task_service)
):
    """Lista todas las tareas"""
    return service.get_all_tasks(session_id, status)

@app.get("/tasks/search", response_model=List[Task])
def search_tasks(
    q: str,
    session_id: str = Depends(get_session_id),
    service: TaskService = Depends(get_task_service)
):
    """Busca tareas"""
    if len(q) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters")
    return service.search_tasks(session_id, q)

@app.get("/tasks/stats", response_model=TaskStats)
def get_stats(
    session_id: str = Depends(get_session_id),
    service: TaskService = Depends(get_task_service)
):
    """Obtiene estadísticas"""
    return service.get_statistics(session_id)

@app.get("/tasks/{task_id}", response_model=Task)
def get_task(
    task_id: str,
    session_id: str = Depends(get_session_id),
    service: TaskService = Depends(get_task_service)
):
    """Obtiene una tarea"""
    return service.get_task_by_id(session_id, task_id)

@app.post("/tasks", response_model=Task, status_code=201)
def create_task(
    task: TaskCreate,
    session_id: str = Depends(get_session_id),
    service: TaskService = Depends(get_task_service)
):
    """Crea una tarea"""
    return service.create_task(session_id, task)

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(
    task_id: str,
    task: TaskUpdate,
    session_id: str = Depends(get_session_id),
    service: TaskService = Depends(get_task_service)
):
    """Actualiza una tarea"""
    return service.update_task(session_id, task_id, task)

@app.patch("/tasks/{task_id}/status", response_model=Task)
def update_task_status(
    task_id: str,
    status: TaskStatus,
    session_id: str = Depends(get_session_id),
    service: TaskService = Depends(get_task_service)
):
    """Actualiza estado"""
    return service.update_task(session_id, task_id, TaskUpdate(status=status))

@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(
    task_id: str,
    session_id: str = Depends(get_session_id),
    service: TaskService = Depends(get_task_service)
):
    """Elimina una tarea"""
    service.delete_task(session_id, task_id)
    return Response(status_code=204)

@app.delete("/tasks", status_code=204)
def delete_all_tasks(
    session_id: str = Depends(get_session_id)
):
    """Elimina todas las tareas"""
    with SESSION_LOCK:
        if session_id in repository._storage:
            repository._storage[session_id] = []
    logger.info(f"All tasks deleted for session: {session_id}")
    return Response(status_code=204)

# ============= ERROR HANDLERS =============
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Maneja excepciones HTTP"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Maneja excepciones generales"""
    logger.error(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)