import uuid
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Project, ProjectMember, User
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)

DbDep = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: DbDep,
) -> User:
    if creds is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = decode_token(creds.credentials, "access")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Unknown user")
    return user


UserDep = Annotated[User, Depends(get_current_user)]


async def get_project_with_role(
    db: AsyncSession,
    user: User,
    project_id: uuid.UUID,
    need_owner: bool = False,
) -> tuple[Project, ProjectMember]:
    """Load a project the user belongs to; optionally require the owner role."""
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    member = (
        await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id, ProjectMember.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this project")
    if need_owner and member.role != "owner":
        raise HTTPException(status_code=403, detail="Only the project owner can do this")
    return project, member
