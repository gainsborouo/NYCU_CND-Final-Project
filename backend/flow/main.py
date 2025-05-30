from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials # Import for JWT handling
from sqlmodel import Session, SQLModel, create_engine, select
from typing import Dict, List, Optional
from sqlalchemy import or_ # Needed for combining multiple OR conditions in WHERE clauses
from datetime import datetime,timezone
# Import all necessary models from your models.py file
from models import (
    Document,
    DocumentCreate,
    DocumentRead,
    UserRoles,
    DocumentStatus,
    DocumentUpdate, # Assuming you have a DocumentUpdate model for PATCH requests
    ReviewActionResult,
    ReviewRecord,
    ReviewRecordRead,
    ReviewAction,
    ReviewActionRequest,
    NotificationRead,
    NotificationType,
    Notification,
    NotificationMarkReadRequest,
    DocumentWrite
)
from minio import get_upload_s3_url, get_read_s3_url
import jwt # pip install python-jose[cryptography] or pyjwt
from jwt import PyJWTError
import os
# --- Configuration (IMPORTANT: Replace with environment variables in production) ---
# This is a dummy secret key for DEMONSTRATION.
# In production, this would be a real secret from your auth microservice,
# or better yet, a public key/certificate for JWT signature verification.
SECRET_KEY = os.getenv("SECRET_KEY", "your-very-secret-jwt-signing-key")  # SHOULD BE FROM ENV VAR
ALGORITHM = os.getenv("ALGORITHM", "HS256")  # Or RS256, ES256 if using asymmetric keys

# --- Database Setup ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database.db")
engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

# --- JWT Security Scheme ---
# This tells FastAPI to expect an "Authorization: Bearer <token>" header
oauth2_scheme = HTTPBearer()

# --- Dependency to get User Context from JWT ---
async def get_current_user_context(
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme) # Get token from header
) -> UserRoles:
    """
    Extracts user_id and UserRoles from the JWT token.
    Validates the token (conceptually, in this example).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # --- CRITICAL SECURITY NOTE ---
        # In a real microservices setup, you would typically use an asymmetric algorithm (e.g., RS256)
        # and verify the token's signature using the PUBLIC KEY of the authentication microservice.
        # DO NOT use verify_signature=False in production. This is for demonstration ONLY.

        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_signature": False})
        # For production:
        # payload = jwt.decode(token.credentials, PUBLIC_KEY_FROM_AUTH_SERVICE, algorithms=[ALGORITHM], audience="your-api-audience")

        user_id: int = payload.get("uid") # 'sub' is standard for subject (user ID)
        if user_id is None:
            raise credentials_exception

        # Assume roles are passed as a 'realm_roles' claim in the JWT
        realm_roles_data: Dict[str, List[str]] = payload.get("realm_roles", {})
        if not isinstance(realm_roles_data, dict):
             # Handle cases where roles might be malformed
            print(f"Warning: realm_roles claim is not a dictionary: {realm_roles_data}")
            realm_roles_data = {} # Default to empty roles if malformed


        user_roles = UserRoles(user_id=user_id, realm_roles=realm_roles_data)
        return user_roles

    except PyJWTError:
        raise credentials_exception
    except Exception as e:
        # Catch any other unexpected errors during token processing
        print(f"Error processing token: {e}")
        raise credentials_exception

from sqlmodel import Session
from typing import Optional
from models import Notification, NotificationType # Assuming these are imported from models.py

def create_notification(
    session: Session,
    recipient_id: int,
    type: NotificationType,
    message: str,
    realm_id: str,
    sender_id: Optional[int] = None,
    document_id: Optional[int] = None,
    is_read: bool = False,
) -> Notification:
    """
    Creates and stores a new notification in the database.

    Args:
        session: The database session.
        recipient_id: The ID of the user who will receive the notification.
        type: The type of notification (e.g., DOCUMENT_FOR_REVIEW, DOCUMENT_APPROVED).
        message: The content of the notification message.
        realm_id: The realm ID associated with this notification.
        sender_id: (Optional) The ID of the user who initiated the notification.
        document_id: (Optional) The ID of the document related to the notification.
        is_read: (Optional) Initial read status of the notification. Defaults to False.

    Returns:
        The newly created Notification object.
    """
    new_notification = Notification(
        sender_id=sender_id,
        recipient_id=recipient_id,
        document_id=document_id,
        type=type,
        message=message,
        is_read=is_read,
        realm_id=realm_id
    )

    session.add(new_notification)
    session.commit()
    session.refresh(new_notification)

    return new_notification
# Initialize the FastAPI app
app = FastAPI()

# Event handler to create tables on startup
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# --- Create Document Endpoint (same as before, now using JWT context) ---
@app.post("/documents/{realm_id}", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_document(
    realm_id: str,
    document_create: DocumentCreate,
    session: Session = Depends(get_session),
    user_context: UserRoles = Depends(get_current_user_context) # This dependency now gets user info from JWT
):
    """
    Creates a new document under the specified realm.

    - **realm_id**: The ID of the realm where the document will be created.
    - **document_create**: The document's `title` and `description`.
    - **Authorization**: The authenticated user must have a 'user' or 'admin' role within the specified realm.
    """
    if not (user_context.has_role_in_realm(realm_id, "user") or
            user_context.has_role_in_realm(realm_id, "admin")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User not authorized to create documents in realm '{realm_id}'."
        )

    db_document = Document(
        **document_create.model_dump(),
        creator_id=user_context.user_id,
        realm_id=int(realm_id) # Convert realm_id to int, assuming your DB stores it as int
    )
    print(db_document)
    session.add(db_document)
    session.commit()
    session.refresh(db_document)

    return db_document

@app.get("/documents/{realm_id}", response_model=List[DocumentRead])
def get_documents_in_realm(
    realm_id: str,
    session: Session = Depends(get_session),
    user_context: UserRoles = Depends(get_current_user_context),
    status_filter: Optional[DocumentStatus] = Query(None, description="Filter by document status"),
    creator_id_filter: Optional[int] = Query(None, description="Filter by document creator ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of documents to return"),
    offset: int = Query(0, ge=0, description="Number of documents to skip")
):
    """
    Retrieves a list of documents in a specific realm that the current user has visibility to.

    - **realm_id**: The ID of the realm.
    - **status_filter**: Optional filter for document status (e.g., 'published', 'draft').
    - **creator_id_filter**: Optional filter for documents created by a specific user.
    - **limit, offset**: For pagination.
    - **Authorization**: Access is based on user's roles and document status:
        - `admin` in realm: Sees all documents.
        - `user` in realm: Sees own documents and published documents.
        - `reviewer` in realm: Sees documents assigned for review and published documents.
        - Other authenticated users or no specific role in realm: Only sees published documents.
    """
    query = select(Document).where(Document.realm_id == int(realm_id))

    # Determine user's roles in the specific realm
    is_admin = user_context.has_role_in_realm(realm_id, "admin")
    is_user = user_context.has_role_in_realm(realm_id, "user")
    is_reviewer = user_context.has_role_in_realm(realm_id, "reviewer")

    # Build authorization conditions
    auth_conditions = []

    if is_admin:
        # Admins can see everything in the realm, no further auth conditions needed
        pass
    else:
        # Non-admins always see published documents
        auth_conditions.append(Document.status == DocumentStatus.PUBLISHED)

        if is_user:
            # Users can see their own documents
            auth_conditions.append(Document.creator_id == user_context.user_id)

        if is_reviewer:
            # Reviewers can see documents assigned to them for review
            auth_conditions.append(Document.current_reviewer_id == user_context.user_id)

        # If no specific role in the realm (and not admin), they only see published (already added)
        # If user has no specific role and there are no published documents, the list will be empty.
        # No need to raise 403 here unless absolutely no documents are visible.

    # Apply authorization conditions if not admin
    if auth_conditions and not is_admin:
        query = query.where(or_(*auth_conditions))
    elif not auth_conditions and not is_admin:
        # This case implies no specific role and no condition to see published documents (unlikely with above logic)
        # Or if the realm_id is not in the user's roles at all and they are not an admin.
        # If no authorization condition is met, and not an admin, then nothing should be returned.
        # We can add a fail-safe here, though the `or_` with `Document.status == DocumentStatus.PUBLISHED` handles most.
        pass # The query will just return published documents if that's the only condition

    # Apply optional query filters
    if status_filter:
        query = query.where(Document.status == status_filter)
    if creator_id_filter:
        query = query.where(Document.creator_id == creator_id_filter)

    # Apply pagination
    query = query.offset(offset).limit(limit)

    documents = session.exec(query).all()

    return documents


# Assuming 'app' is your FastAPI application instance
# Assuming 'get_session' and 'get_current_user_context' dependencies are defined as before

@app.get("/documents/{document_id}/details", response_model=DocumentRead)
def get_document_detail(
    document_id: int, # The ID of the document to retrieve
    session: Session = Depends(get_session), # Database session dependency
    user_context: UserRoles = Depends(get_current_user_context) # Authenticated user context dependency
):
    """
    Retrieves the detailed information for a specific document.

    - **document_id**: The ID of the document to fetch.
    - **Authorization**: Access is based on user's roles and document status:
        - `admin` in document's realm: Sees the document.
        - `user` in document's realm: Sees the document if they are the creator, or if it's published.
        - `reviewer` in document's realm: Sees the document if they are the current reviewer, or if it's published.
        - Other authenticated users or no specific role in realm: Only sees the document if it's published.
    """
    # 1. Fetch the document from the database
    document = session.get(Document, document_id)

    # 2. Handle Document Not Found
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found."
        )

    # 3. Authorization Check
    # Get user's roles for the document's realm
    realm_id = str(document.realm_id)
    is_admin_in_realm = user_context.has_role_in_realm(realm_id, "admin")
    is_user_in_realm = user_context.has_role_in_realm(realm_id, "user")
    is_reviewer_in_realm = user_context.has_role_in_realm(realm_id, "reviewer")

    # Check if the user is authorized to view this specific document
    authorized = False

    if is_admin_in_realm:
        authorized = True # Admins can see any document in their realm
    elif document.status == DocumentStatus.PUBLISHED:
        authorized = True # Anyone can see published documents
    elif is_user_in_realm and document.creator_id == user_context.user_id:
        authorized = True # Users can see their own documents (even if not published)
    elif is_reviewer_in_realm and document.current_reviewer_id == user_context.user_id:
        authorized = True # Reviewers can see documents assigned to them for review

    if not authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User not authorized to view document with ID {document_id}."
        )

    # 4. Return the document details
    return document



@app.put("/documents/{document_id}", response_model=DocumentWrite)
def upload_document(
    document_id: int, # The ID of the document to update
    session: Session = Depends(get_session), # Database session dependency
    user_context: UserRoles = Depends(get_current_user_context) # Authenticated user context dependency
):
    """
    Upload specific fields of an existing document.
    """
    # 1. Fetch the document from the database
    db_document = session.get(Document, document_id)

    # 2. Handle Document Not Found
    if not db_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found."
        )

    # 3. Authorization Check
    realm_id = str(db_document.realm_id)
    is_admin_in_realm = user_context.has_role_in_realm(realm_id, "admin")
    is_creator = (user_context.user_id == db_document.creator_id)

    # Determine what the user is allowed to update
    allowed_to_update_all = is_admin_in_realm
    allowed_to_update_own_draft = is_creator and db_document.status == DocumentStatus.DRAFT

    # If not allowed to update anything, raise Forbidden
    if not allowed_to_update_all and not allowed_to_update_own_draft:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User not authorized to update document with ID {document_id} in its current state."
        )

    # 4. Apply Updates based on Authorization
    
    # 5. Save Changes to Database
    session.add(db_document)
    session.commit()
    session.refresh(db_document) # Refresh to get updated_at and any other auto-generated fields
    
    # 6. Return the updated document
    return db_document


@app.patch("/documents/{document_id}", response_model=DocumentRead)
def update_document(
    document_id: int, # The ID of the document to update
    document_update: DocumentUpdate, # Request body with fields to update
    session: Session = Depends(get_session), # Database session dependency
    user_context: UserRoles = Depends(get_current_user_context) # Authenticated user context dependency
):
    """
    Updates specific fields of an existing document.

    - **document_id**: The ID of the document to update.
    - **document_update**: The fields to update (e.g., title, description, status, current_reviewer_id).
    - **Authorization**:
        - `creator` of the document: Can update `title` and `description` if the document is in `DRAFT` status.
        - `admin` in the document's realm: Can update any field, including `status` and `current_reviewer_id`.
    """
    # 1. Fetch the document from the database
    db_document = session.get(Document, document_id)

    # 2. Handle Document Not Found
    if not db_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found."
        )

    # 3. Authorization Check
    realm_id = str(db_document.realm_id)
    is_admin_in_realm = user_context.has_role_in_realm(realm_id, "admin")
    is_creator = (user_context.user_id == db_document.creator_id)

    # Determine what the user is allowed to update
    allowed_to_update_all = is_admin_in_realm
    allowed_to_update_own_draft = is_creator and db_document.status == DocumentStatus.DRAFT

    # If not allowed to update anything, raise Forbidden
    if not allowed_to_update_all and not allowed_to_update_own_draft:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User not authorized to update document with ID {document_id} in its current state."
        )

    # 4. Apply Updates based on Authorization
    update_data = document_update.model_dump(exclude_unset=True) # Only get fields that were actually sent

    for key, value in update_data.items():
        if not allowed_to_update_all:
            # If not an admin, restrict updates to title/description only if it's their draft
            if key not in ["title", "description"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"User not authorized to update '{key}' field for document with ID {document_id}."
                )
            if db_document.status != DocumentStatus.DRAFT:
                 raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Document with ID {document_id} cannot be updated unless it is in DRAFT status by its creator."
                )
        # Apply the update
        setattr(db_document, key, value)

    # 5. Save Changes to Database
    session.add(db_document)
    session.commit()
    session.refresh(db_document) # Refresh to get updated_at and any other auto-generated fields
    
    # 6. Return the updated document
    return db_document

from models import Document, DocumentRead, DocumentStatus, ReviewRequest

# Assuming 'app' is your FastAPI application instance
# Assuming 'get_session' and 'get_current_user_context' dependencies are defined as before

@app.post("/documents/{document_id}/submit-for-review", response_model=DocumentRead)
def submit_document_for_review(
    document_id: int, # The ID of the document to submit
    review_request: ReviewRequest, # Request body containing the reviewer_id
    session: Session = Depends(get_session), # Database session dependency
    user_context: UserRoles = Depends(get_current_user_context) # Authenticated user context dependency
):
    """
    Submits a document for review, changing its status to PENDING_REVIEW and assigning a reviewer.

    - **document_id**: The ID of the document to submit.
    - **review_request**: Contains the `reviewer_id` to whom the document will be assigned.
    - **Authorization**:
        - User must be the `creator` of the document OR have `editor`/`admin` role in the document's realm.
        - Document must currently be in `DRAFT` status.
    """
    # 1. Fetch the document from the database
    db_document = session.get(Document, document_id)

    # 2. Handle Document Not Found
    if not db_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found."
        )

    # 3. Authorization Check
    realm_id = str(db_document.realm_id)
    is_admin_in_realm = user_context.has_role_in_realm(realm_id, "admin")
    is_creator = (user_context.user_id == db_document.creator_id)
    is_editor_in_realm = user_context.has_role_in_realm(realm_id, "editor") # Assuming 'editor' role exists

    # Only creator, editor, or admin can submit for review
    if not (is_creator or is_editor_in_realm or is_admin_in_realm):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User not authorized to submit document with ID {document_id} for review."
        )

    # Document must be in DRAFT status to be submitted for review
    if db_document.status != DocumentStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, # 409 Conflict indicates a conflict with current state
            detail=f"Document with ID {document_id} is not in DRAFT status and cannot be submitted for review."
        )

    # 4. Update Document Status and Reviewer
    db_document.status = DocumentStatus.PENDING_REVIEW
    db_document.current_reviewer_id = review_request.reviewer_id

    # 5. Save Changes to Database
    session.add(db_document)
    session.commit()
    session.refresh(db_document)

    create_notification(
        session=session,
        recipient_id=review_request.reviewer_id,
        sender_id=user_context.user_id,
        document_id=document_id,
        type=NotificationType.DOCUMENT_FOR_REVIEW,
        message=f"Document '{db_document.title}' assigned for your review in realm '{realm_id}'.",
        realm_id=realm_id
    )

    # 6. Return the updated document
    return db_document

@app.post("/documents/{document_id}/review-action", response_model=ReviewActionResult)
def perform_review_action(
    document_id: int, # The ID of the document being reviewed
    review_action_request: ReviewActionRequest, # Request body with action (approve/reject) and reason
    session: Session = Depends(get_session), # Database session dependency
    user_context: UserRoles = Depends(get_current_user_context) # Authenticated user context dependency
):
    """
    Records a review action (approve/reject) for a document and updates its status.

    - **document_id**: The ID of the document being reviewed.
    - **review_action_request**: Contains the `action` (APPROVE/REJECT) and optional `rejection_reason`.
    - **Authorization**:
        - User must be the `current_reviewer_id` for the document OR have `admin` role in the document's realm.
        - Document must currently be in `PENDING_REVIEW` status.
    """
    # 1. Fetch the document from the database
    db_document = session.get(Document, document_id)

    # 2. Handle Document Not Found
    if not db_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found."
        )

    # 3. Authorization Check
    realm_id = db_document.realm_id
    is_admin_in_realm = user_context.has_role_in_realm(realm_id, "admin")
    is_current_reviewer = (user_context.user_id == db_document.current_reviewer_id)

    if not (is_current_reviewer or is_admin_in_realm):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User not authorized to perform review action on document with ID {document_id}."
        )

    # Document must be in PENDING_REVIEW status
    if db_document.status != DocumentStatus.PENDING_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document with ID {document_id} is not in PENDING_REVIEW status."
        )

    # 4. Determine New Document Status and Handle Rejection Reason
    new_document_status: DocumentStatus
    notification_message: str
    notification_type: NotificationType

    if review_action_request.action == ReviewAction.APPROVE:
        new_document_status = DocumentStatus.PUBLISHED
        notification_type = NotificationType.DOCUMENT_APPROVED
        notification_message = f"Your document '{db_document.title}' has been approved and published in realm '{realm_id}'."
        rejection_reason = None # Clear rejection reason on approval
    elif review_action_request.action == ReviewAction.REJECT:
        new_document_status = DocumentStatus.REJECTED
        rejection_reason = review_action_request.rejection_reason
        if not rejection_reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rejection reason is required when rejecting a document."
            )
        notification_type = NotificationType.DOCUMENT_REJECTED
        notification_message = f"Your document '{db_document.title}' has been rejected in realm '{realm_id}'. Reason: {rejection_reason}"
    else:
        # This case should ideally be caught by Pydantic validation, but as a safeguard
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid review action."
        )

    # 5. Create Review Record
    review_record = ReviewRecord(
        document_id=document_id,
        reviewer_id=user_context.user_id,
        action=review_action_request.action,
        new_document_status=new_document_status,
        rejection_reason=rejection_reason,
        realm_id=realm_id # Associate review record with the realm
    )

    session.add(review_record)
    session.commit()
    session.refresh(review_record)

    # 6. Update Document Status and Clear Current Reviewer
    db_document.status = new_document_status
    db_document.current_reviewer_id = None # Review process for this stage is complete

    # If published, set published_at timestamp
    if new_document_status == DocumentStatus.PUBLISHED:
        db_document.published_at = datetime.now(timezone.utc)

    session.add(db_document)
    session.commit()
    session.refresh(db_document)

    create_notification(
        session=session,
        recipient_id=db_document.creator_id, # Notify the document creator
        sender_id=user_context.user_id,      # The reviewer/admin is the sender
        document_id=document_id,
        type=notification_type,              # Notification type based on action
        message=notification_message,        # Dynamic message
        realm_id=realm_id
    )

    # 7. Return the composite result
    return ReviewActionResult(
        review_record=review_record,
        updated_document=db_document
    )


# --- GET Review History Endpoint ---
@app.get("/documents/{document_id}/review-history", response_model=List[ReviewRecordRead])
def get_document_review_history(
    document_id: int, # The ID of the document
    session: Session = Depends(get_session), # Database session dependency
    user_context: UserRoles = Depends(get_current_user_context) # Authenticated user context dependency
):
    """
    Retrieves the review history for a specific document.

    - **document_id**: The ID of the document whose review history is requested.
    - **Authorization**: User must have `viewer`, `editor`, `reviewer`, or `admin` role in the document's realm.
    """
    # 1. Fetch the document to get its realm_id for authorization
    db_document = session.get(Document, document_id)

    # 2. Handle Document Not Found
    if not db_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found."
        )

    # 3. Authorization Check
    realm_id = int(db_document.realm_id)
    is_admin_in_realm = user_context.has_role_in_realm(realm_id, "admin")
    is_user_in_realm = user_context.has_role_in_realm(realm_id, "user")
    is_reviewer_in_realm = user_context.has_role_in_realm(realm_id, "reviewer")
    is_creator = (user_context.user_id == db_document.creator_id)

    # Any user with a role in the realm or the creator can view history
    if not (is_admin_in_realm or is_user_in_realm or is_reviewer_in_realm or is_creator):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User not authorized to view review history for document with ID {document_id}."
        )

    # 4. Query Review Records
    # Fetch all review records for this document, ordered by review time
    review_history_query = select(ReviewRecord).where(ReviewRecord.document_id == document_id).order_by(ReviewRecord.reviewed_at)
    review_records = session.exec(review_history_query).all()

    # 5. Return the list of review records
    return review_records

@app.get("/notifications/", response_model=List[NotificationRead])
def get_user_notifications(
    session: Session = Depends(get_session),
    user_context: UserRoles = Depends(get_current_user_context),
    is_read: Optional[bool] = Query(None, description="Filter by read status"),
    type: Optional[NotificationType] = Query(None, description="Filter by notification type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of notifications to return"),
    offset: int = Query(0, ge=0, description="Number of notifications to skip")
):
    """
    Retrieves a list of notifications for the authenticated user.

    - **is_read**: Optional filter to get only read (`true`) or unread (`false`) notifications.
    - **type**: Optional filter to get notifications of a specific type (e.g., 'document_approved').
    - **limit, offset**: For pagination.
    - **Authorization**: User must be authenticated.
    """
    # Start with a query for notifications belonging to the current user
    query = select(Notification).where(Notification.recipient_id == user_context.user_id)

    # Apply optional filters
    if is_read is not None:
        query = query.where(Notification.is_read == is_read)
    if type is not None:
        query = query.where(Notification.type == type)

    # Apply pagination
    query = query.offset(offset).limit(limit)

    notifications = session.exec(query).all()

    return notifications


@app.patch("/notifications/{notification_id}", response_model=NotificationRead)
def mark_notification_status(
    notification_id: int,
    status_update: NotificationMarkReadRequest,
    session: Session = Depends(get_session),
    user_context: UserRoles = Depends(get_current_user_context)
):
    """
    Marks a specific notification as read or unread.

    - **notification_id**: The ID of the notification to update.
    - **status_update**: Request body containing the `is_read` status (true/false).
    - **Authorization**: User must be the `recipient_id` of the notification or have `admin` role in the notification's `realm_id`.
    """
    # 1. Fetch the notification
    db_notification = session.get(Notification, notification_id)

    # 2. Handle Notification Not Found
    if not db_notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification with ID {notification_id} not found."
        )

    # 3. Authorization Check
    realm_id = str(db_notification.realm_id)
    is_admin_in_realm = user_context.has_role_in_realm(realm_id, "admin")
    is_recipient = (user_context.user_id == db_notification.recipient_id)

    if not (is_recipient or is_admin_in_realm):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User not authorized to modify notification with ID {notification_id}."
        )

    # 4. Apply Update
    db_notification.is_read = status_update.is_read

    # 5. Save Changes to Database
    session.add(db_notification)
    session.commit()
    session.refresh(db_notification)

    # 6. Return the updated notification
    return db_notification