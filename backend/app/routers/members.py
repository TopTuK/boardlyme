import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, update

from app.deps import DbDep
from app.deps import UserDep, get_project_with_role
from app.models import ProjectMember, Task, User
from app.routers.projects import members_payload
from app.schemas import MemberAddIn, MemberOut, MemberSearchItem
from app.ws import manager

router = APIRouter(prefix="/api/projects/{project_id}/members", tags=["members"])


@router.get("", response_model=list[MemberOut])
async def list_members(project_id: uuid.UUID, user: UserDep, db: DbDep):
    await get_project_with_role(db, user, project_id)
    return await members_payload(db, project_id)


@router.get("/search", response_model=list[MemberSearchItem])
async def search_users(project_id: uuid.UUID, user: UserDep, db: DbDep, q: str = ""):
    """Find users by Telegram username so the owner can share the board."""
    await get_project_with_role(db, user, project_id, need_owner=True)
    query = q.strip().lstrip("@")
    if len(query) < 2:
        return []

    member_ids = set(
        (
            await db.execute(
                select(ProjectMember.user_id).where(ProjectMember.project_id == project_id)
            )
        ).scalars().all()
    )
    users = (
        await db.execute(
            select(User)
            .where(User.username.is_not(None), User.username.ilike(f"{query}%"))
            .order_by(User.username)
            .limit(10)
        )
    ).scalars().all()

    return [
        MemberSearchItem(
            id=u.id,
            username=u.username,
            first_name=u.first_name,
            last_name=u.last_name,
            photo_url=u.photo_url,
            is_member=u.id in member_ids,
        )
        for u in users
    ]


@router.post("", response_model=list[MemberOut], status_code=status.HTTP_201_CREATED)
async def add_member(project_id: uuid.UUID, body: MemberAddIn, user: UserDep, db: DbDep):
    await get_project_with_role(db, user, project_id, need_owner=True)
    target = await db.get(User, body.user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    existing = (
        await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id, ProjectMember.user_id == target.id
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(ProjectMember(project_id=project_id, user_id=target.id, role="editor"))
        await db.commit()

    members = await members_payload(db, project_id)
    await manager.broadcast(
        project_id,
        {"type": "members.changed", "members": [m.model_dump(mode="json") for m in members]},
    )
    return members


@router.delete("/{member_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(project_id: uuid.UUID, member_user_id: uuid.UUID, user: UserDep, db: DbDep):
    await get_project_with_role(db, user, project_id, need_owner=True)
    member = (
        await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id, ProjectMember.user_id == member_user_id
            )
        )
    ).scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    if member.role == "owner":
        raise HTTPException(status_code=400, detail="The owner cannot be removed")

    # Detach the member's tasks first so behaviour is identical on databases
    # without FK "SET NULL" enforcement.
    await db.execute(update(Task).where(Task.assignee_id == member_user_id).values(assignee_id=None))
    await db.delete(member)
    await db.commit()
    members = await members_payload(db, project_id)
    await manager.broadcast(
        project_id,
        {"type": "members.changed", "members": [m.model_dump(mode="json") for m in members]},
    )
    await manager.kick_user(project_id, member_user_id)
