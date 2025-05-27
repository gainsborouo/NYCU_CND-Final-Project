import httpx
from fastapi import FastAPI, Depends, HTTPException, status, Header
from sqlmodel import Session, create_engine, select, SQLModel
from typing import List, Optional, Annotated, Dict
from datetime import datetime, timezone
from enum import Enum

# Import all models and enums from models.py
from models import (
    Document, DocumentRead, DocumentCreate, DocumentUpdate,
    ReviewRecord, ReviewRecordRead, ReviewRequest, ReviewActionRequest,
    Notification, NotificationRead, NotificationType,
    DocumentStatus, ReviewAction
)

# --- Database Setup ---

DATABASE_URL = "sqlite:///./review_microservice.db"
engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

# --- FastAPI App ---
app = FastAPI(title="Document Review Microservice")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# --- External Service Configuration ---
AUTH_SERVICE_BASE_URL = "http://localhost:8000/auth" # Base URL for auth service

# --- RBAC and External Auth Integration ---

async def get_user_roles_and_groups_from_auth_service(user_id: int) -> dict:
    """
    Fetches user roles and groups from the external authentication service
    with the format: { "gid1": {"role": "admin"}, "gid2": {"role": "user"} }.
    
    Returns a dictionary with flattened lists of 'roles' and 'groups' for easier consumption.
    Example: {"roles": ["admin", "user"], "groups": ["gid1", "gid2"]}
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{AUTH_SERVICE_BASE_URL}/userinfo?user_id={user_id}")
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            data: Dict[str, Dict[str, str]] = response.json()

            if not isinstance(data, dict):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Invalid top-level response from authentication service: {data}. Expected a dictionary."
                )
            
            # Extract roles and groups from the new format
            user_roles = set()
            user_groups = set()
            
            for group_id, group_info in data.items():
                if not isinstance(group_info, dict) or "role" not in group_info:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Invalid group info from authentication service for group {group_id}: {group_info}. Expected a dictionary with 'role'."
                    )
                user_groups.add(group_id)
                user_roles.add(group_info["role"])
            
            return {"roles": list(user_roles), "groups": list(user_groups)}

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not connect to authentication service: {exc.request.url}"
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Authentication service returned an error: {exc.response.status_code} - {exc.response.text}"
        )

async def get_current_user_roles_and_groups(
    user_id: Annotated[int, Header(alias="X-User-Id")]
) -> dict:
    """Dependency to get roles and groups for the current user from the auth service."""
    return await get_user_roles_and_groups_from_auth_service(user_id)

async def verify_admin_role(
    user_id: Annotated[int, Header(alias="X-User-Id")],
    user_info: dict = Depends(get_current_user_roles_and_groups)
) -> int:
    """Dependency to verify if the current user has the 'admin' role (in any group)."""
    if "admin" not in user_info.get("roles", []): # This now checks the flattened list of roles
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation forbidden: Admin role required."
        )
    return user_id

# --- API Endpoints ---

@app.post("/documents/", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def create_document(
    user_id: Annotated[int, Header(alias="X-User-Id")],
    session: Session = Depends(get_session)
):
    document = Document(creator_id=user_id, last_editor_id=user_id)
    session.add(document)
    session.commit()
    session.refresh(document)
    return document

@app.get("/documents/", response_model=List[DocumentRead])
async def get_all_documents(
    user_id: Annotated[int, Header(alias="X-User-Id")],
    user_info: dict = Depends(get_current_user_roles_and_groups),
    session: Session = Depends(get_session)
):
    if "admin" in user_info.get("roles", []):
        documents = session.exec(select(Document)).all()
    else:
        user_groups = user_info.get("groups", [])
        
        all_documents = session.exec(select(Document)).all()
        filtered_documents = []
        for doc in all_documents:
            if doc.creator_id == user_id:
                filtered_documents.append(doc)
            elif doc.status == DocumentStatus.PUBLISHED:
                if not doc.allowed_groups: # Publicly viewable if no specific groups are set
                    filtered_documents.append(doc)
                else:
                    doc_allowed_groups = {g.strip() for g in doc.allowed_groups.split(",")}
                    if doc_allowed_groups.intersection(user_groups):
                        filtered_documents.append(doc)
        documents = filtered_documents
    return documents

@app.get("/documents/{document_id}", response_model=DocumentRead)
async def get_document_detail(
    document_id: int,
    user_id: Annotated[int, Header(alias="X-User-Id")],
    user_info: dict = Depends(get_current_user_roles_and_groups),
    session: Session = Depends(get_session)
):
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Admins and document creators always have access
    if "admin" in user_info.get("roles", []) or document.creator_id == user_id:
        return document
    
    # Assigned reviewer can see documents assigned to them
    if document.current_reviewer_id == user_id: # No 'reviewer' role check needed, just direct assignment
        return document

    # Group-based access for published documents
    if document.status == DocumentStatus.PUBLISHED:
        # If allowed_groups is not set or empty, assume it's public for published documents
        if not document.allowed_groups: # Handles None or empty string
            return document
        
        # Check if the user is part of any of the allowed groups
        allowed_groups = {g.strip() for g in document.allowed_groups.split(",")}
        user_groups = set(user_info.get("groups", []))
        
        if allowed_groups.intersection(user_groups):
            return document
        
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this document. Your groups do not match the required groups.")

    # For any other status or unhandled cases, access is forbidden
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this document.")


@app.put("/documents/{document_id}", response_model=DocumentRead)
async def update_document(
    document_id: int,
    document_update: DocumentUpdate,
    user_id: Annotated[int, Header(alias="X-User-Id")],
    user_info: dict = Depends(get_current_user_roles_and_groups),
    session: Session = Depends(get_session)
):
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Only creator or admin can update
    is_admin = "admin" in user_info.get("roles", [])
    is_creator = document.creator_id == user_id

    if not (is_admin or is_creator):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this document")

    # Handle allowed_groups update
    if document_update.allowed_groups is not None:
        if is_creator and document.status not in [DocumentStatus.DRAFT, DocumentStatus.REJECTED]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Creators can only modify groups for documents in DRAFT or REJECTED status."
            )
        # If not creator, it must be an admin, who can update groups regardless of status.
        # Convert list of strings to comma-separated string for storage
        document.allowed_groups = ",".join(document_update.allowed_groups) if document_update.allowed_groups else None
        # Remove from update_data so it's not processed again by model_dump
        document_update.allowed_groups = None # Set to None to exclude from model_dump

    # If the document is published or pending review, only an admin can update its status or re-assign reviewer.
    if document.status in [DocumentStatus.PUBLISHED, DocumentStatus.PENDING_REVIEW]:
        if not is_admin:
            if document_update.status is not None and document_update.status != document.status:
                 raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only admins can change status of published or pending review documents."
                )
            if document_update.current_reviewer_id is not None and document_update.current_reviewer_id != document.current_reviewer_id:
                 raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only admins can re-assign reviewers for pending review documents."
                )

    # Prevent direct setting of `published_at` via update
    # if document_update.published_at is not None:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot set 'published_at' directly.")

    update_data = document_update.model_dump(exclude_unset=True)
    # allowed_groups is already handled above, so no need to delete it from update_data anymore
    for key, value in update_data.items():
        if value is not None:
            setattr(document, key, value)
    
    document.last_editor_id = user_id

    session.add(document)
    session.commit()
    session.refresh(document)
    return document


@app.post("/documents/{document_id}/submit-for-review", response_model=DocumentRead)
async def submit_for_review(
    document_id: int,
    review_request: ReviewRequest,
    user_id: Annotated[int, Header(alias="X-User-Id")],
    session: Session = Depends(get_session),
    user_info: dict = Depends(get_current_user_roles_and_groups) # Included to trigger auth service call and ensure user exists
):
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if document.creator_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the document creator can submit for review")

    if document.status not in [DocumentStatus.DRAFT, DocumentStatus.REJECTED]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document must be in DRAFT or REJECTED status to submit for review")

    if review_request.reviewer_id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot assign self as reviewer.")
    
    # Validate that reviewer_id is a valid user by attempting to get their info from auth service
    # If auth service returns an error (e.g., 404), it will raise an HTTPException
    await get_user_roles_and_groups_from_auth_service(review_request.reviewer_id)
    # No explicit "reviewer" role check needed anymore, as any valid user can be a reviewer.

    document.status = DocumentStatus.PENDING_REVIEW
    document.current_reviewer_id = review_request.reviewer_id
    document.last_editor_id = user_id
    session.add(document)
    session.commit()
    session.refresh(document)

    notification = Notification(
        sender_id=user_id,
        recipient_id=review_request.reviewer_id,
        document_id=document.id,
        type=NotificationType.DOCUMENT_FOR_REVIEW,
        message=f"Document ID {document.id} has been submitted for your review."
    )
    session.add(notification)
    session.commit()

    return document

@app.post("/documents/{document_id}/review", response_model=DocumentRead)
async def review_document(
    document_id: int,
    review_action_request: ReviewActionRequest,
    user_id: Annotated[int, Header(alias="X-User-Id")],
    user_info: dict = Depends(get_current_user_roles_and_groups),
    session: Session = Depends(get_session)
):
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if document.status != DocumentStatus.PENDING_REVIEW:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document is not in pending review status.")

    # Authorization: Must be an admin OR the assigned reviewer
    if "admin" not in user_info.get("roles", []) and document.current_reviewer_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to review this document.")

    if review_action_request.action == ReviewAction.APPROVE:
        document.status = DocumentStatus.PUBLISHED
        document.published_at = datetime.now(timezone.utc)
    elif review_action_request.action == ReviewAction.REJECT:
        document.status = DocumentStatus.REJECTED
        if not review_action_request.rejection_reason:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rejection reason is required for rejection.")
    
    document.last_editor_id = user_id
    session.add(document)
    session.commit()
    session.refresh(document)

    review_record = ReviewRecord(
        document_id=document.id,
        reviewer_id=user_id,
        action=review_action_request.action,
        status=document.status,
        rejection_reason=review_action_request.rejection_reason
    )
    session.add(review_record)
    session.commit()

    notification_type = NotificationType.DOCUMENT_APPROVED if review_action_request.action == ReviewAction.APPROVE else NotificationType.DOCUMENT_REJECTED
    notification_message = (
        f"Document ID {document.id} has been approved and published."
        if review_action_request.action == ReviewAction.APPROVE
        else f"Document ID {document.id} has been rejected. Reason: {review_action_request.rejection_reason}"
    )
    notification = Notification(
        sender_id=user_id,
        recipient_id=document.creator_id,
        document_id=document.id,
        type=notification_type,
        message=notification_message
    )
    session.add(notification)
    session.commit()

    return document

@app.get("/notifications/", response_model=List[NotificationRead])
async def get_user_notifications(
    user_id: Annotated[int, Header(alias="X-User-Id")],
    session: Session = Depends(get_session)
):
    notifications = session.exec(
        select(Notification).where(Notification.recipient_id == user_id).order_by(Notification.created_at.desc())
    ).all()
    return notifications

@app.patch("/notifications/{notification_id}/mark-as-read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notification_as_read(
    notification_id: int,
    user_id: Annotated[int, Header(alias="X-User-Id")],
    session: Session = Depends(get_session)
):
    notification = session.get(Notification, notification_id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    
    if notification.recipient_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    notification.is_read = True
    session.add(notification)
    session.commit()

# --- Admin Endpoints ---

@app.patch("/admin/documents/{document_id}/assign-reviewer", response_model=DocumentRead)
async def admin_assign_reviewer(
    document_id: int,
    review_request: ReviewRequest,
    admin_user_id: Annotated[int, Depends(verify_admin_role)],
    session: Session = Depends(get_session)
):
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Validate that reviewer_id is a valid user by attempting to get their info from auth service
    await get_user_roles_and_groups_from_auth_service(review_request.reviewer_id)
    # No explicit "reviewer" role check needed, as any valid user can be a reviewer.

    document.current_reviewer_id = review_request.reviewer_id
    document.status = DocumentStatus.PENDING_REVIEW
    document.last_editor_id = admin_user_id

    session.add(document)
    session.commit()
    session.refresh(document)

    notification = Notification(
        sender_id=admin_user_id,
        recipient_id=review_request.reviewer_id,
        document_id=document.id,
        type=NotificationType.DOCUMENT_FOR_REVIEW,
        message=f"Document ID {document.id} has been assigned to you for review by an admin."
    )
    session.add(notification)
    session.commit()

    return document

@app.post("/admin/documents/{document_id}/set-groups", response_model=DocumentRead)
async def admin_set_document_groups(
    document_id: int,
    groups: List[str],
    admin_user_id: Annotated[int, Depends(verify_admin_role)],
    session: Session = Depends(get_session)
):
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    
    # Removed: if document.status != DocumentStatus.PUBLISHED:
    # Admins can set groups regardless of document status.

    document.allowed_groups = ",".join(groups) if groups else None
    document.last_editor_id = admin_user_id

    session.add(document)
    session.commit()
    session.refresh(document)
    return document


@app.get("/admin/documents/{document_id}/history", response_model=List[ReviewRecordRead])
async def admin_get_document_history(
    document_id: int,
    admin_user_id: Annotated[int, Depends(verify_admin_role)],
    session: Session = Depends(get_session)
):
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        
    history = session.exec(
        select(ReviewRecord).where(ReviewRecord.document_id == document_id).order_by(ReviewRecord.reviewed_at.asc())
    ).all()
    return history