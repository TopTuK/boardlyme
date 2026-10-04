import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _required_text(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("must not be blank")
    return value


# --------------------------------------------------------------------------- #
# Users / auth
# --------------------------------------------------------------------------- #


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    photo_url: str | None = None
    locale: str = "en"


class UserSettingsIn(BaseModel):
    locale: Literal["en", "ru"]


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    user: UserOut


class WidgetAuthIn(BaseModel):
    """Raw query string sent back by the Telegram Login Widget."""

    data: str


class MiniAppAuthIn(BaseModel):
    """Raw `initData` string provided by the Telegram Mini App."""

    init_data: str


class DevLoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=32)


class RefreshIn(BaseModel):
    refresh_token: str


# --------------------------------------------------------------------------- #
# Projects
# --------------------------------------------------------------------------- #


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)

    _strip_name = field_validator("name", mode="after")(_required_text)


class ProjectUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=200)

    _strip_name = field_validator("name", mode="after")(_required_text)


class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    created_at: datetime
    role: str = "editor"
    task_count: int = 0
    done_count: int = 0


# --------------------------------------------------------------------------- #
# Stages
# --------------------------------------------------------------------------- #


class StageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    wip_limit: int | None = Field(default=None, ge=1, le=999)

    _strip_name = field_validator("name", mode="after")(_required_text)


class StageUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_hidden: bool | None = None
    # Explicit `null` clears the WIP limit; omitting the field leaves it untouched.
    wip_limit: int | None = Field(default=None, ge=1, le=999)
    is_split: bool | None = None

    _strip_name = field_validator("name", mode="after")(_required_text)


class StageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    position: int
    is_done: bool
    is_hidden: bool
    is_backlog: bool
    is_split: bool
    wip_limit: int | None = None


class StageReorderIn(BaseModel):
    stage_ids: list[uuid.UUID]


# --------------------------------------------------------------------------- #
# Tasks
# --------------------------------------------------------------------------- #


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    deadline: date | None = None
    stage_id: uuid.UUID | None = None
    # True creates the task straight into the "done" sub-stage of a split stage.
    stage_done: bool = False
    assignee_id: uuid.UUID | None = None

    _strip_title = field_validator("title", mode="after")(_required_text)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    deadline: date | None = None
    assignee_id: uuid.UUID | None = None

    _strip_title = field_validator("title", mode="after")(_required_text)


class TaskMoveIn(BaseModel):
    stage_id: uuid.UUID
    index: int = 0
    # Target sub-stage when moving inside a split stage (False = active lane).
    stage_done: bool = False


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    stage_id: uuid.UUID
    title: str
    description: str | None = None
    deadline: date | None = None
    assignee_id: uuid.UUID | None = None
    position: int
    stage_done: bool = False
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    assignee: UserOut | None = None


class TaskBrief(BaseModel):
    """Minimal task shape used by reorder/complete events."""

    id: uuid.UUID
    stage_id: uuid.UUID
    position: int
    stage_done: bool = False
    completed_at: datetime | None = None


class ReorderOut(BaseModel):
    tasks: list[TaskBrief]


# --------------------------------------------------------------------------- #
# Board members
# --------------------------------------------------------------------------- #


class MemberOut(BaseModel):
    user_id: uuid.UUID
    role: str
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    photo_url: str | None = None


class MemberAddIn(BaseModel):
    user_id: uuid.UUID


class MemberSearchItem(BaseModel):
    id: uuid.UUID
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    photo_url: str | None = None
    is_member: bool


# --------------------------------------------------------------------------- #
# Full board payload
# --------------------------------------------------------------------------- #


class BoardOut(BaseModel):
    project: ProjectOut
    stages: list[StageOut]
    tasks: list[TaskOut]
    members: list[MemberOut]
