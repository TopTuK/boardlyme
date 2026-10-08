import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, func, select

from app.deps import DbDep
from app.deps import UserDep, get_project_with_role
from app.models import Stage, Task
from app.schemas import StageCreate, StageOut, StageReorderIn, StageUpdate
from app.ws import manager

router = APIRouter(prefix="/api", tags=["stages"])


def _dump(stage: Stage) -> dict:
    return StageOut.model_validate(stage).model_dump(mode="json")


def _brief(task: Task) -> dict:
    return {
        "id": str(task.id),
        "stage_id": str(task.stage_id),
        "position": task.position,
        "stage_done": bool(task.stage_done),
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


async def _get_stage(db, stage_id: uuid.UUID) -> Stage:
    stage = await db.get(Stage, stage_id)
    if stage is None:
        raise HTTPException(status_code=404, detail="Stage not found")
    return stage


@router.post("/projects/{project_id}/stages", response_model=StageOut, status_code=status.HTTP_201_CREATED)
async def create_stage(project_id: uuid.UUID, body: StageCreate, user: UserDep, db: DbDep):
    await get_project_with_role(db, user, project_id, need_owner=True)
    next_pos = (
        await db.execute(select(func.coalesce(func.max(Stage.position), -1)).where(Stage.project_id == project_id))
    ).scalar_one() + 1
    stage = Stage(project_id=project_id, name=body.name.strip(), position=next_pos, wip_limit=body.wip_limit)
    db.add(stage)
    await db.flush()
    # Keep Done as the last column: the new stage slots in right before it.
    ordered = sorted(
        (await db.execute(select(Stage).where(Stage.project_id == project_id))).scalars().all(),
        key=lambda s: (s.is_done, s.position),
    )
    for position, s in enumerate(ordered):
        s.position = position
    await db.commit()
    await db.refresh(stage)
    await manager.broadcast(project_id, {"type": "stage.created", "stage": _dump(stage)})
    return stage


@router.patch("/stages/{stage_id}", response_model=StageOut)
async def update_stage(stage_id: uuid.UUID, body: StageUpdate, user: UserDep, db: DbDep):
    stage = await _get_stage(db, stage_id)
    await get_project_with_role(db, user, stage.project_id, need_owner=True)

    fields = body.model_fields_set

    if "name" in fields and body.name is not None:
        stage.name = body.name.strip()
    if "is_hidden" in fields and body.is_hidden is not None:
        stage.is_hidden = body.is_hidden

    if "wip_limit" in fields:
        if body.wip_limit is not None and (stage.is_backlog or stage.is_done):
            raise HTTPException(status_code=400, detail="WIP limits apply only to regular stages")
        stage.wip_limit = body.wip_limit

    merged_tasks: list[Task] = []
    if "is_split" in fields and body.is_split is not None and body.is_split != stage.is_split:
        if body.is_split and (stage.is_backlog or stage.is_done):
            raise HTTPException(status_code=400, detail="Only regular stages can be split into sub-stages")
        stage.is_split = body.is_split
        if not body.is_split:
            # Merge the done sub-lane back into a single lane: active tasks keep
            # their order, done-lane tasks are appended, then everything renumbers.
            tasks = (
                await db.execute(
                    select(Task)
                    .where(Task.stage_id == stage.id)
                    .order_by(Task.stage_done, Task.position, Task.created_at)
                )
            ).scalars().all()
            for position, t in enumerate(tasks):
                t.stage_done = False
                t.position = position
                merged_tasks.append(t)

    await db.commit()
    await db.refresh(stage)

    await manager.broadcast(stage.project_id, {"type": "stage.updated", "stage": _dump(stage)})
    if merged_tasks:
        await manager.broadcast(
            stage.project_id, {"type": "tasks.reordered", "tasks": [_brief(t) for t in merged_tasks]}
        )
    return stage


@router.delete("/stages/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stage(stage_id: uuid.UUID, user: UserDep, db: DbDep):
    stage = await _get_stage(db, stage_id)
    await get_project_with_role(db, user, stage.project_id, need_owner=True)
    if stage.is_backlog:
        raise HTTPException(status_code=400, detail="The Backlog stage cannot be deleted")
    if stage.is_done:
        raise HTTPException(status_code=400, detail="The Done stage cannot be deleted")
    remaining = (
        await db.execute(
            select(func.count())
            .select_from(Stage)
            .where(Stage.project_id == stage.project_id, Stage.is_done.is_(False), Stage.id != stage.id)
        )
    ).scalar_one()
    if remaining == 0:
        raise HTTPException(status_code=400, detail="At least one work stage is required")

    project_id = stage.project_id
    # Explicit delete keeps behaviour identical on databases without FK cascades.
    await db.execute(delete(Task).where(Task.stage_id == stage_id))
    await db.delete(stage)
    await db.commit()
    await manager.broadcast(project_id, {"type": "stage.deleted", "stage_id": str(stage_id)})


@router.put("/projects/{project_id}/stages/reorder", response_model=list[StageOut])
async def reorder_stages(project_id: uuid.UUID, body: StageReorderIn, user: UserDep, db: DbDep):
    await get_project_with_role(db, user, project_id, need_owner=True)
    stages = (await db.execute(select(Stage).where(Stage.project_id == project_id))).scalars().all()
    by_id = {s.id: s for s in stages}
    if len(body.stage_ids) != len(by_id) or set(body.stage_ids) != set(by_id):
        raise HTTPException(status_code=400, detail="stage_ids must be a permutation of the project stages")
    backlog = next((s for s in stages if s.is_backlog), None)
    if backlog and body.stage_ids[0] != backlog.id:
        raise HTTPException(status_code=400, detail="The Backlog stage must stay first")
    done = next((s for s in stages if s.is_done), None)
    if done and body.stage_ids[-1] != done.id:
        raise HTTPException(status_code=400, detail="The Done stage must stay last")
    for position, stage_id in enumerate(body.stage_ids):
        by_id[stage_id].position = position
    await db.commit()
    ordered = sorted(stages, key=lambda s: s.position)
    await manager.broadcast(project_id, {"type": "stage.reordered", "stages": [_dump(s) for s in ordered]})
    return ordered
