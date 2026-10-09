import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from app.deps import DbDep
from app.deps import UserDep, get_project_with_role
from app.models import Project, ProjectMember, Stage, Task, TaskTransition
from app.schemas import BoardOut, MemberOut, ProjectCreate, ProjectOut, ProjectUpdate
from app.ws import manager

router = APIRouter(prefix="/api/projects", tags=["projects"])

# Every new board starts with these. Backlog is always first and cannot be
# deleted; Done is the system completion stage and is hidden by default.
DEFAULT_STAGES: list[dict] = [
    {"name": "Backlog", "is_backlog": True},
    {"name": "ToDo"},
    {"name": "Active"},
    {"name": "Done", "is_done": True, "is_hidden": True},
]


def member_out(member: ProjectMember) -> MemberOut:
    return MemberOut(
        user_id=member.user_id,
        role=member.role,
        username=member.user.username if member.user else None,
        first_name=member.user.first_name if member.user else None,
        last_name=member.user.last_name if member.user else None,
        photo_url=member.user.photo_url if member.user else None,
    )


async def members_payload(db, project_id: uuid.UUID) -> list[MemberOut]:
    members = (
        await db.execute(
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .options(selectinload(ProjectMember.user))
            .order_by(ProjectMember.created_at)
        )
    ).scalars().all()
    return [member_out(m) for m in members]


@router.get("", response_model=list[ProjectOut])
async def list_projects(user: UserDep, db: DbDep):
    rows = (
        await db.execute(
            select(Project, ProjectMember.role)
            .join(ProjectMember, (ProjectMember.project_id == Project.id) & (ProjectMember.user_id == user.id))
            .order_by(Project.created_at.desc())
        )
    ).all()

    counts: dict[uuid.UUID, dict[str, int]] = {}
    if rows:
        stat_rows = (
            await db.execute(
                select(Task.project_id, Stage.is_done, func.count(Task.id))
                .join(Stage, Task.stage_id == Stage.id)
                .where(Task.project_id.in_([p.id for p, _ in rows]))
                .group_by(Task.project_id, Stage.is_done)
            )
        ).all()
        for project_id, is_done, count in stat_rows:
            bucket = counts.setdefault(project_id, {"total": 0, "done": 0})
            bucket["total"] += count
            if is_done:
                bucket["done"] += count

    return [
        ProjectOut(
            id=p.id,
            name=p.name,
            owner_id=p.owner_id,
            created_at=p.created_at,
            role=role,
            task_count=counts.get(p.id, {}).get("total", 0),
            done_count=counts.get(p.id, {}).get("done", 0),
        )
        for p, role in rows
    ]


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(body: ProjectCreate, user: UserDep, db: DbDep):
    project = Project(name=body.name.strip(), owner_id=user.id)
    db.add(project)
    await db.flush()
    for position, spec in enumerate(DEFAULT_STAGES):
        db.add(
            Stage(
                project_id=project.id,
                name=spec["name"],
                position=position,
                is_done=spec.get("is_done", False),
                is_hidden=spec.get("is_hidden", False),
                is_backlog=spec.get("is_backlog", False),
            )
        )
    db.add(ProjectMember(project_id=project.id, user_id=user.id, role="owner"))
    await db.commit()
    await db.refresh(project)
    return ProjectOut(
        id=project.id,
        name=project.name,
        owner_id=project.owner_id,
        created_at=project.created_at,
        role="owner",
    )


@router.get("/{project_id}", response_model=BoardOut)
async def get_board(project_id: uuid.UUID, user: UserDep, db: DbDep):
    project, member = await get_project_with_role(db, user, project_id)

    stages = (
        await db.execute(select(Stage).where(Stage.project_id == project_id).order_by(Stage.position))
    ).scalars().all()
    tasks = (
        await db.execute(
            select(Task)
            .where(Task.project_id == project_id)
            .options(selectinload(Task.assignee), selectinload(Task.checklist))
            .order_by(Task.position, Task.created_at)
        )
    ).scalars().all()
    members = await members_payload(db, project_id)

    done_stage_ids = {s.id for s in stages if s.is_done}
    done_count = sum(1 for t in tasks if t.stage_id in done_stage_ids)

    return BoardOut(
        project=ProjectOut(
            id=project.id,
            name=project.name,
            owner_id=project.owner_id,
            created_at=project.created_at,
            role=member.role,
            task_count=len(tasks),
            done_count=done_count,
        ),
        stages=stages,
        tasks=tasks,
        members=members,
    )


@router.patch("/{project_id}", response_model=ProjectOut)
async def rename_project(project_id: uuid.UUID, body: ProjectUpdate, user: UserDep, db: DbDep):
    project, member = await get_project_with_role(db, user, project_id, need_owner=True)
    project.name = body.name.strip()
    await db.commit()
    await manager.broadcast(
        project_id,
        {"type": "project.updated", "project": {"id": str(project.id), "name": project.name}},
    )
    return ProjectOut(
        id=project.id,
        name=project.name,
        owner_id=project.owner_id,
        created_at=project.created_at,
        role=member.role,
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: uuid.UUID, user: UserDep, db: DbDep):
    project, _ = await get_project_with_role(db, user, project_id, need_owner=True)

    # Boards can only be deleted once no active work is left: a task is done
    # when it sits in a Done stage or in the done sub-stage of a split stage.
    active_count = (
        await db.execute(
            select(func.count(Task.id))
            .join(Stage, Task.stage_id == Stage.id)
            .where(Task.project_id == project_id)
            .where(Stage.is_done.is_(False), Task.stage_done.is_(False))
        )
    ).scalar_one()
    if active_count:
        raise HTTPException(
            status_code=409,
            detail="The project still has active tasks — finish or delete them first",
        )

    await manager.broadcast(project_id, {"type": "project.deleted", "project_id": str(project_id)})
    await manager.close_room(project_id)
    # Explicit deletes keep behaviour identical on databases without FK cascades.
    await db.execute(delete(TaskTransition).where(TaskTransition.project_id == project_id))
    await db.execute(delete(Task).where(Task.project_id == project_id))
    await db.execute(delete(Stage).where(Stage.project_id == project_id))
    await db.execute(delete(ProjectMember).where(ProjectMember.project_id == project_id))
    await db.delete(project)
    await db.commit()


@router.post("/{project_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_project(project_id: uuid.UUID, user: UserDep, db: DbDep):
    _, member = await get_project_with_role(db, user, project_id)
    if member.role == "owner":
        raise HTTPException(status_code=400, detail="The owner cannot leave a project — delete it instead")
    await db.delete(member)
    await db.commit()
    members = await members_payload(db, project_id)
    await manager.broadcast(
        project_id,
        {"type": "members.changed", "members": [m.model_dump(mode="json") for m in members]},
    )
    await manager.kick_user(project_id, user.id)
