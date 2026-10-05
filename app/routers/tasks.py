from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskResponse, TaskStatus, TaskUpdate
from app.security.dependencies import get_current_user

router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"],
    responses={401: {"description": "Missing, invalid or expired token"}},
)


def _get_owned_task(task_id: int, db: Session, current_user: User) -> Task:
    """AUTORIZACION: el usuario autenticado, puede operar sobre ESTA tarea?"""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.user_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="You do not own this task")
    return task


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task",
    description="The owner is taken from the JWT; any user_id sent by the client is ignored.",
)
def create_task(
    data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = Task(**data.model_dump(), user_id=current_user.id)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get(
    "",
    response_model=list[TaskResponse],
    summary="List my tasks",
    description="Returns only the tasks that belong to the authenticated user.",
)
def list_tasks(
    status_filter: TaskStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Task).where(Task.user_id == current_user.id).order_by(Task.id)
    if status_filter is not None:
        query = query.where(Task.status == status_filter)
    return db.execute(query).scalars().all()


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get a task",
    responses={403: {"description": "The task belongs to another user"}, 404: {"description": "Task not found"}},
)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_owned_task(task_id, db, current_user)


@router.put(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Replace a task",
    description="Full update: title is required, description/status take the values sent (or defaults).",
    responses={403: {"description": "The task belongs to another user"}, 404: {"description": "Task not found"}},
)
def replace_task(
    task_id: int,
    data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_owned_task(task_id, db, current_user)
    task.title = data.title
    task.description = data.description
    task.status = data.status
    db.commit()
    db.refresh(task)
    return task


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Partially update a task",
    description="Only the fields sent in the body are modified.",
    responses={403: {"description": "The task belongs to another user"}, 404: {"description": "Task not found"}},
)
def update_task(
    task_id: int,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_owned_task(task_id, db, current_user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
    responses={403: {"description": "The task belongs to another user"}, 404: {"description": "Task not found"}},
)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_owned_task(task_id, db, current_user)
    db.delete(task)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
