from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List, Dict
from datetime import datetime, timezone
from enum import Enum

# --- Enums ---
class GlobalRole(str, Enum):
    USER = "user"
    ADMIN = "admin"

class GroupRole(str, Enum):
    USER = "user"
    REVIEWER = "reviewer"
    ADMIN = "admin"

# --- Models ---
class UserBase(SQLModel):
    username: str = Field(index=True, sa_column_kwargs={"unique": True})
    password: Optional[str] = None
    global_role: GlobalRole = GlobalRole.USER

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": datetime.now(timezone.utc)}
    )
    groups: List["UserGroupRole"] = Relationship(back_populates="user")

class UserCreate(SQLModel):
    username: str
    password: Optional[str] = None
    global_role: Optional[GlobalRole] = GlobalRole.USER

class UserRead(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

class PasswordUpdate(SQLModel):
    username: str
    new_password: str

class GroupBase(SQLModel):
    group_name: str = Field(
        index=True, sa_column_kwargs={"unique": True}
    )

class Group(GroupBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": datetime.now(timezone.utc)}
    )
    users: List["UserGroupRole"] = Relationship(back_populates="group")

class GroupCreate(SQLModel):
    group_name: str

class GroupRead(GroupBase):
    id: int
    created_at: datetime
    updated_at: datetime

class UserGroupRole(SQLModel, table=True):
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    group_id: int = Field(foreign_key="group.id", primary_key=True)
    role: GroupRole = Field(primary_key=True)
    user: User = Relationship(back_populates="groups")
    group: Group = Relationship(back_populates="users")

class GroupRoleAssignment(SQLModel):
    username: str
    group_name: str
    roles: List[GroupRole]