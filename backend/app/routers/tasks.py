import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.deps import DbDep
from app.deps import UserDep, get_project_with_role
from app.models import ProjectMember, Stage, Task
from app.schemas import ReorderOut, TaskBrief, TaskCreate, TaskMoveIn, TaskOut, TaskUpdate
from app.ws import manager

router = APIRouter(prefix="/api", tags=["tasks"])


async def _serialize_task(db, task_id: uuid.UUID) -> TaskOut:
    task = (
        await db.execute(select(Task).where(Task.id == task_id).options(selectinload(Task.assignee)))
    ).scalar_one()
    return TaskOut.model_validate(task)


async def _assert_assignee_is_member(db, project_id: uuid.UUID, assignee_id: uuid.UUID | None) -> None:
    if assignee_id is None:
        return
    member = (
        await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id, ProjectMember.user_id == assignee_id
            )
        )
    ).scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=400, detail="Assignee must be a member of the project")


async def _next_position(db, stage_id: uuid.UUID, lane: bool) -> int:
    current = (
        await db.execute(
            select(func.coalesce(func.max(Task.position), -1)).where(
                Task.stage_id == stage_id, Task.stage_done == lane
            )
        )
    ).scalar_one()
    return current + 1


def _brief(task: Task) -> dict:
    return TaskBrief(
        id=task.id,
        stage_id=task.stage_id,
        position=task.position,
        stage_done=bool(task.stage_done),
        completed_at=task.completed_at,
    ).model_dump(mode="json")


async def _lane_tasks(db, stage_id: uuid.UUID, lane: bool) -> list[Task]:
    """Tasks of one (stage, sub-stage) lane in display order."""
    return list(
        (
            await db.execute(
                select(Task)
                .where(Task.stage_id == stage_id, Task.stage_done == lane)
                .order_by(Task.position, Task.created_at)
            )
        ).scalars().all()
    )


async def _check_wip(db, stage: Stage) -> None:
    """Reject entering a full active lane (409). Done sub-lane is never limited."""
    if stage.wip_limit is None or stage.is_done or stage.is_backlog:
        return
    active_count = len(await _lane_tasks(db, stage.id, False))
    if active_count >= stage.wip_limit:
        raise HTTPException(
            status_code=409,
            detail=f'WIP limit of {stage.wip_limit} reached for stage "{stage.name}"',
        )


async def _apply_move(db, task: Task, target_stage: Stage, index: int, target_lane: bool = False) -> list[Task]:
    """Move `task` into a (stage, sub-stage) lane at `index`, resequencing positions.

    Returns every task whose stage/lane/position changed (including the moved one).
    Raises 409 when the move would exceed the target stage's WIP limit.
    """
    same_lane = task.stage_id == target_stage.id and bool(task.stage_done) == bool(target_lane)

    # WIP limits guard the active lane only; the done sub-lane is never limited.
    if not same_lane and not target_lane:
        await _check_wip(db, target_stage)

    source_tasks = [t for t in await _lane_tasks(db, task.stage_id, task.stage_done) if t.id != task.id]
    target_tasks = source_tasks if same_lane else await _lane_tasks(db, target_stage.id, target_lane)
    index = max(0, min(index, len(target_tasks)))
    target_tasks.insert(index, task)

    affected: list[Task] = []
    for position, t in enumerate(source_tasks):
        t.position = position
        affected.append(t)
    if not same_lane:
        for position, t in enumerate(target_tasks):
            t.position = position
            affected.append(t)

    task.stage_id = target_stage.id
    task.stage_done = bool(target_lane) and not target_stage.is_done
    if target_stage.is_done:
        if task.completed_at is None:
            task.completed_at = datetime.now(timezone.utc)
    else:
        task.completed_at = None
    return affected


@router.post("/projects/{project_id}/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(project_id: uuid.UUID, body: TaskCreate, user: UserDep, db: DbDep):
    await get_project_with_role(db, user, project_id)
    await _assert_assignee_is_member(db, project_id, body.assignee_id)

    if body.stage_id is not None:
        stage = await db.get(Stage, body.stage_id)
        if stage is None or stage.project_id != project_id:
            raise HTTPException(status_code=400, detail="stage_id does not belong to this project")
    else:
        stage = (
            (
                await db.execute(
                    select(Stage)
                    .where(Stage.project_id == project_id, Stage.is_backlog.is_(True))
                    .order_by(Stage.position)
                )
            )
            .scalars()
            .first()
        )
        if stage is None:
            raise HTTPException(status_code=409, detail="The project has no Backlog stage")

    # New work always starts in the Backlog. Other columns are reached by moving.
    if body.stage_done or not stage.is_backlog:
        raise HTTPException(status_code=400, detail="New tasks can only be created in the Backlog")

    task = Task(
        project_id=project_id,
        stage_id=stage.id,
        stage_done=False,
        title=body.title.strip(),
        description=body.description or None,
        deadline=body.deadline,
        assignee_id=body.assignee_id,
        position=await _next_position(db, stage.id, False),
        created_by=user.id,
    )
    db.add(task)
    await db.commit()

    task_out = await _serialize_task(db, task.id)
    await manager.broadcast(project_id, {"type": "task.created", "task": task_out.model_dump(mode="json")})
    return task_out


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def update_task(task_id: uuid.UUID, body: TaskUpdate, user: UserDep, db: DbDep):
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    await get_project_with_role(db, user, task.project_id)

    fields = body.model_fields_set
    if "title" in fields and body.title is not None:
        task.title = body.title.strip()
    if "description" in fields:
        task.description = body.description or None
    if "deadline" in fields:
        task.deadline = body.deadline
    if "assignee_id" in fields:
        await _assert_assignee_is_member(db, task.project_id, body.assignee_id)
        task.assignee_id = body.assignee_id
    await db.commit()

    task_out = await _serialize_task(db, task.id)
    await manager.broadcast(task.project_id, {"type": "task.updated", "task": task_out.model_dump(mode="json")})
    return task_out


@router.post("/tasks/{task_id}/move", response_model=ReorderOut)
async def move_task(task_id: uuid.UUID, body: TaskMoveIn, user: UserDep, db: DbDep):
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    await get_project_with_role(db, user, task.project_id)
    target_stage = await db.get(Stage, body.stage_id)
    if target_stage is None or target_stage.project_id != task.project_id:
        raise HTTPException(status_code=400, detail="stage_id does not belong to this project")

    affected = await _apply_move(db, task, target_stage, body.index, body.stage_done)
    await db.commit()

    briefs = [_brief(t) for t in affected]
    await manager.broadcast(task.project_id, {"type": "tasks.reordered", "tasks": briefs})
    return ReorderOut(tasks=briefs)


@router.post("/tasks/{task_id}/complete", response_model=ReorderOut)
async def complete_task(task_id: uuid.UUID, user: UserDep, db: DbDep):
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    await get_project_with_role(db, user, task.project_id)

    done_stage = (
        (
            await db.execute(
                select(Stage).where(Stage.project_id == task.project_id, Stage.is_done.is_(True))
            )
        )
        .scalars()
        .first()
    )
    if done_stage is None:
        raise HTTPException(status_code=409, detail="The project has no Done stage")

    affected = await _apply_move(db, task, done_stage, 10**9)  # append at the end
    await db.commit()

    briefs = [_brief(t) for t in affected]
    await manager.broadcast(task.project_id, {"type": "tasks.reordered", "tasks": briefs})
    return ReorderOut(tasks=briefs)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: uuid.UUID, user: UserDep, db: DbDep):
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    await get_project_with_role(db, user, task.project_id)
    project_id = task.project_id
    await db.delete(task)
    await db.commit()
    await manager.broadcast(project_id, {"type": "task.deleted", "task_id": str(task_id)})
