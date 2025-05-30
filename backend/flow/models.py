from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List, Dict
from datetime import datetime, timezone
from enum import Enum

# --- Enums ---
class DocumentStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    REJECTED = "rejected"
    PUBLISHED = "published"

class ReviewAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"

class NotificationType(str, Enum):
    DOCUMENT_FOR_REVIEW = "document_for_review"
    DOCUMENT_APPROVED = "document_approved"
    DOCUMENT_REJECTED = "document_rejection" # Corrected to be consistent
    DOCUMENT_STATE_CHANGE = "document_state_change" # For creator when review initiated, or admin changes things

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"

# --- Models ---
class DocumentBase(SQLModel):
    creator_id: int
    last_editor_id: Optional[int] = None
    status: DocumentStatus = DocumentStatus.DRAFT
    current_reviewer_id: Optional[int] = None
    published_at: Optional[datetime] = None
    # New field for group-based access control
    allowed_groups: Optional[str] = None # Comma-separated string of group names

class Document(DocumentBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column_kwargs={"onupdate": datetime.now(timezone.utc)})

class DocumentCreate(SQLModel):
    # No fields needed for creation, as creator_id comes from header
    pass

class DocumentUpdate(SQLModel):
    # Only status can be updated by certain roles, or current_reviewer_id
    status: Optional[DocumentStatus] = None
    current_reviewer_id: Optional[int] = None
    allowed_groups: Optional[List[str]] = None # Changed to List[str] for creator input

class DocumentRead(DocumentBase):
    id: int
    created_at: datetime
    updated_at: datetime

class ReviewRecordBase(SQLModel):
    document_id: int
    reviewer_id: int
    action: ReviewAction
    status: DocumentStatus # The status the document moved to after review
    rejection_reason: Optional[str] = None

class ReviewRecord(ReviewRecordBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ReviewRecordRead(ReviewRecordBase):
    id: int
    reviewed_at: datetime

class ReviewRequest(SQLModel):
    reviewer_id: int

class ReviewActionRequest(SQLModel):
    action: ReviewAction
    rejection_reason: Optional[str] = None

class NotificationBase(SQLModel):
    sender_id: Optional[int] = None
    recipient_id: int
    document_id: Optional[int] = None
    type: NotificationType
    message: str
    is_read: bool = False

class Notification(NotificationBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class NotificationRead(NotificationBase):
    id: int
    created_at: datetime

class UserBase(SQLModel):
    uid: str = Field(primary_key=True)  # OAuth-derived user ID
    username: str
    password: Optional[str] = None  # For admin accounts, None for OAuth accounts
    global_role: UserRole = UserRole.USER

class User(UserBase, table=True):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column_kwargs={"onupdate": datetime.now(timezone.utc)})
    groups: List["UserGroupRole"] = Relationship(back_populates="user")  # Relationship to UserGroupRole

class UserCreate(SQLModel):
    uid: str
    username: str
    password: Optional[str] = None
    global_role: Optional[UserRole] = UserRole.USER

class UserRead(UserBase):
    created_at: datetime
    updated_at: datetime

class GroupBase(SQLModel):
    group_id: str = Field(primary_key=True)
    group_name: str

class Group(GroupBase, table=True):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column_kwargs={"onupdate": datetime.now(timezone.utc)})
    users: List["UserGroupRole"] = Relationship(back_populates="group")  # Relationship to UserGroupRole

class GroupCreate(SQLModel):
    group_id: str
    group_name: str

class GroupRead(GroupBase):
    created_at: datetime
    updated_at: datetime

class UserGroupRole(SQLModel, table=True):
    user_uid: str = Field(foreign_key="user.uid", primary_key=True)
    group_id: str = Field(foreign_key="group.group_id", primary_key=True)
    role: UserRole = Field(primary_key=True)
    user: User = Relationship(back_populates="groups")
    group: Group = Relationship(back_populates="users")

class GroupRoleAssignment(SQLModel):
    username: str
    group_name: str
    roles: List[UserRole]