from typing import Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum
from sqlmodel import Field, SQLModel
from pydantic import BaseModel, Field as PydanticField, computed_field # Use alias for Pydantic's Field to avoid conflict with SQLModel's Field


# Placeholder for external S3 URL generation
from minio import get_s3_url_from_id
# def get_s3_url_from_id(document_id: int) -> str:
#     """
#     Placeholder for a function that generates a document URL (e.g., S3 pre-signed URL).
#     In a real application, this would interact with your storage service.
#     """
#     return f"https://your-s3-bucket.amazonaws.com/documents/{document_id}.pdf"


# --- Enums ---
class DocumentStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    REJECTED = "rejected"
    PUBLISHED = "published"
    ARCHIVED = "archived" # Added: A common state for documents that are no longer active

class ReviewAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"

class NotificationType(str, Enum):
    DOCUMENT_FOR_REVIEW = "document_for_review"
    DOCUMENT_APPROVED = "document_approved"
    DOCUMENT_REJECTED = "document_rejected"
    DOCUMENT_STATE_CHANGE = "document_state_change"
    REVIEW_REQUEST_CANCELLED = "review_request_cancelled" # Added: Useful if a review request is withdrawn

# --- Document Models ---
class DocumentBase(SQLModel):
    # These IDs refer to users managed by an external microservice
    creator_id: int = Field(index=True) # User ID from external auth service
    realm_id: int = Field(index=True) # Realm ID (can also be an external ID or internal to this service)
    title: str = Field(index=True)
    description: Optional[str] = None
    status: DocumentStatus = DocumentStatus.DRAFT
    current_reviewer_id: Optional[int] = Field(default=None, index=True) # User ID from external auth service
    published_at: Optional[datetime] = None

class Document(DocumentBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
        nullable=False
    )

class DocumentCreate(SQLModel):
    title: str = PydanticField(min_length=1)
    description: Optional[str] = None
    # Removed creator_id and realm_id from here.
    # These should be derived from the authenticated user's context and the path parameter respectively.

class DocumentUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[DocumentStatus] = None
    current_reviewer_id: Optional[int] = None

class DocumentRead(DocumentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def url(self) -> str:
        if self.id is None:
            return "" # Or raise an error if id is expected to always be present
        return get_s3_url_from_id(self.id)

# --- Review Models ---
class ReviewRecordBase(SQLModel):
    document_id: int = Field(index=True)
    reviewer_id: int = Field(index=True) # User ID from external auth service
    action: ReviewAction
    new_document_status: DocumentStatus # The status the document moved to after review
    rejection_reason: Optional[str] = None
    realm_id: int = Field(index=True) # Crucial for multi-realm context and auditing

class ReviewRecord(ReviewRecordBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)

class ReviewRecordRead(ReviewRecordBase):
    id: int
    reviewed_at: datetime

class ReviewActionResult(BaseModel):
    review_record: ReviewRecordRead
    updated_document: DocumentRead

class ReviewRequest(SQLModel):
    # This model is for submitting a document for review, potentially assigning a reviewer.
    reviewer_id: int # The ID of the user to whom the document is being assigned for review.
    # You might also want a message for the reviewer:
    # message: Optional[str] = None

class ReviewActionRequest(SQLModel):
    # This model is for a reviewer to send their decision.
    action: ReviewAction
    rejection_reason: Optional[str] = None
    # Consider adding a general comment field for both approve/reject actions
    # comment: Optional[str] = None

# --- Notification Models ---
class NotificationBase(SQLModel):
    sender_id: Optional[int] = Field(default=None, index=True) # User ID from external auth service
    recipient_id: int = Field(index=True) # User ID from external auth service
    document_id: Optional[int] = Field(default=None, index=True) # Allows linking to document
    type: NotificationType
    message: str
    is_read: bool = False
    realm_id: int = Field(index=True) # Crucial for multi-realm notifications

class Notification(NotificationBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)

class NotificationRead(NotificationBase):
    id: int
    created_at: datetime

class NotificationMarkReadRequest(BaseModel):
    # A simple model for marking a notification as read/unread
    is_read: bool = True # Default to true, but allows setting to false if needed

# --- UserRoles (Pydantic BaseModel, NOT persisted in this service's DB) ---
# Roles: guest, user, reviewer, admin
class UserRoles(BaseModel):
    user_id: int
    realm_roles: Dict[str, List[str]] = PydanticField(default_factory=dict)

    @property
    def is_global_admin(self) -> bool:
        return any("admin" in [role_name.lower() for role_name in roles] for roles in self.realm_roles.values())

    @property
    def realms(self) -> List[str]:
        return list(self.realm_roles.keys())

    def has_role_in_realm(self, realm_id: str, role_name: str) -> bool:
        roles_in_realm = self.realm_roles.get(realm_id,None)
        if roles_in_realm:
            return role_name.lower() in [r.lower() for r in roles_in_realm]
        return False

    def get_roles_in_realm(self, realm_id: str) -> List[str]:
        return self.realm_roles.get(realm_id, [])