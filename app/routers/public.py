from fastapi import APIRouter

router = APIRouter(prefix="/public", tags=["Public"])


@router.get(
    "/info",
    summary="Obtain public API information",
    description="Returns general information without requiring authentication.",
)
def public_info():
    return {
        "api": "Workshop API",
        "version": "1.0",
        "authentication_required": False,
    }


@router.get(
    "/task-statuses",
    summary="List the valid task statuses",
    description="Public reference data: the statuses a task can have. No JWT required.",
)
def task_statuses():
    return {"statuses": ["pending", "in_progress", "done"]}
