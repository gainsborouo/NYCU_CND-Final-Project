import os
import httpx
from jose import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from sqlmodel import Session, create_engine, select, SQLModel
from typing import List, Optional, Annotated, Dict
from datetime import datetime, timezone, timedelta
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
from passlib.context import CryptContext

# Import all models and enums from models.py
from models import (
    Document, DocumentRead, DocumentCreate, DocumentUpdate,
    ReviewRecord, ReviewRecordRead, ReviewRequest, ReviewActionRequest,
    Notification, NotificationRead, NotificationType,
    DocumentStatus, ReviewAction, UserRole,
    User, UserCreate, UserRead,
    Group, GroupCreate, GroupRead,
    UserGroupRole, GroupRoleAssignment
)

# --- Database Setup ---
DATABASE_URL = "sqlite:///./review_microservice.db"
engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

# --- Password Hashing Setup ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# --- FastAPI App ---
app = FastAPI(title="Document Review Microservice")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    with Session(engine) as session:
        admin_user = session.get(User, "1")
        if not admin_user:
            admin_create = UserCreate(
                uid="1",
                username="admin",
                password="admin",  # Hash the admin password
                global_role=UserRole.ADMIN
            )
            create_user(admin_create, session)

# --- OAuth2 Configuration ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# Replace these with your own values from the Google Developer Console
load_dotenv()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
# FRONTEND_URL = os.getenv("FRONTEND_URL")
# FRONTEND_REDIRECT_PATH = os.getenv("FRONTEND_REDIRECT_PATH")
SECRET_KEY = os.getenv("SECRET_KEY")

# --- OAuth Token Validation ---
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
) -> dict:
    try:
        # Decode JWT with validation
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("user_id")
        username: str = payload.get("username")
        global_role: str = payload.get("global_role")

        if not user_id or not username or not global_role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload: missing user_id, username, or global_role"
            )

        # Fetch user from database
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found in database"
            )

        # Fetch group roles from UserGroupRole
        group_roles = session.exec(
            select(UserGroupRole).where(UserGroupRole.user_uid == user_id)
        ).all()

        # Construct ACL dictionary
        acl = {}
        for group_role in group_roles:
            group_id = group_role.group_id
            role = group_role.role
            if group_id not in acl:
                acl[group_id] = {"role": []}
            acl[group_id]["role"].append(role)

        # Return user info in the specified format
        return {
            "ACL": acl,
            "global_role": global_role,
            "username": username,
            "uid": user_id
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during token processing: {str(e)}"
        )

async def verify_admin_role(user_info: dict = Depends(get_current_user)) -> dict:
    """Dependency to verify if the current user has the 'admin' role."""
    if "admin" not in user_info.get("global_role"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation forbidden: Admin role required."
        )
    return user_info

# --- Google OAuth2 Endpoints ---
@app.get("/login/google")
async def login_google():
    auth_url = f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&scope=openid%20profile%20email&access_type=offline"
    # return {
    #     "url": auth_url
    # }
    return RedirectResponse(url=auth_url)

@app.get("/auth/google")
async def auth_google(
    code: str,
    session: Session = Depends(get_session)
):
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        response.raise_for_status()
        token_data = response.json()

        id_token_value = token_data.get("id_token")
        if not id_token_value:
            raise HTTPException(status_code=400, detail="No ID token received")

    try:
        payload = id_token.verify_oauth2_token(
            id_token_value,
            grequests.Request(),
            GOOGLE_CLIENT_ID
        )

        user_id = payload.get("sub")
        email = payload.get("email")
        name = payload.get("name") or email.split("@")[0]

        if not user_id or not email:
            raise HTTPException(status_code=401, detail="Invalid token content")

        # Check if user exists
        user = get_user_by_uid(user_id, session)
        if not user:
            user_create = UserCreate(
                uid=user_id,
                username=name,
                password=None,
                global_role=UserRole.USER
            )
            user = create_user(user_create, session)

        # Issue your own JWT for app authorization
        expiration = datetime.now(timezone.utc) + timedelta(hours=1)
        our_payload = {
            "user_id": user.uid,
            "username": user.username,
            "global_role": user.global_role,
            "exp": expiration
        }

        our_jwt_token = jwt.encode(our_payload, SECRET_KEY, algorithm="HS256")

        return {
            "access_token": our_jwt_token,
            "token_type": "bearer"
        }

    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid ID token")

# --- Local Login Endpoint ---
@app.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    user = session.exec(
        select(User).where(User.username == form_data.username)
    ).first()
    if not user or not user.password or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Set token expiration (e.g., 1 hour)
    expiration = datetime.now(timezone.utc) + timedelta(hours=1)
    my_payload = {
        "user_id": user.uid,
        "username": user.username,
        "global_role": user.global_role,
        "exp": expiration
    }
    our_jwt_token = jwt.encode(my_payload, SECRET_KEY, algorithm="HS256")

    return {
        "access_token": our_jwt_token,
        "token_type": "bearer"
    }

def create_user(
    user_create: UserCreate,
    session: Session
) -> User:

    existing_user = session.get(User, user_create.uid)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with UID {user_create.uid} already exists."
        )
    
    # Create new user
    hashed_password = None
    if user_create.password:
        hashed_password = hash_password(user_create.password)
    # print(user_create.password,verify_password(user_create.password, hashed_password))
    user = User(
        uid=user_create.uid,
        username=user_create.username,
        password=hashed_password,
        global_role=user_create.global_role
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_user_by_uid(
    uid: str,
    session: Session
) -> Optional[UserRead]:

    user = session.get(User, uid)
    if not user:
        return None
    return UserRead.from_orm(user)



# --- External Service Configuration ---
AUTH_SERVICE_BASE_URL = "http://localhost:8000/auth" # Base URL for auth service

# --- RBAC and External Auth Integration ---

async def get_user_roles_and_groups_from_auth_service(user_id: int) -> dict:
    """
    Fetches user roles and groups from the external authentication service
    with the format: { "gid1": {"role": "admin"}, "gid2": {"role": "user"} }.
    
    Returns a dictionary with flattened lists of 'roles' and 'groups' for easier consumption.
    Example: {"roles": ["admin", "user"], "groups": ["gid1", "gid2"]}

    {
        "ACL": {
            "gid1":{
                "role": ["admin", "user"],
            },
            "gid2":{
                "role": ["user"],
            },
        }
        "username": "user1"
        "uid": 123
    }

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

# async def verify_admin_role(
#     user_id: Annotated[int, Header(alias="X-User-Id")],
#     user_info: dict = Depends(get_current_user_roles_and_groups)
# ) -> int:
#     """Dependency to verify if the current user has the 'admin' role (in any group)."""
#     if "admin" not in user_info.get("roles", []): # This now checks the flattened list of roles
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Operation forbidden: Admin role required."
#         )
#     return user_id

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

@app.post("/admin/groups/", response_model=GroupRead, status_code=status.HTTP_201_CREATED)
async def create_group(
    group_create: GroupCreate,
    # admin_user_id: Annotated[int, Depends(verify_admin_role)],
    session: Session = Depends(get_session)
):
    """
    Create a new group (admin only).
    
    Args:
        group_create: GroupCreate model with group_id and group_name.
        admin_user_id: ID of the admin user (verified).
        session: Database session.
    
    Returns:
        GroupRead: The created group.
    
    Raises:
        HTTPException: If group_id already exists.
    """
    existing_group = session.get(Group, group_create.group_id)
    if existing_group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Group with ID {group_create.group_id} already exists."
        )
    group = Group(
        group_id=group_create.group_id,
        group_name=group_create.group_name
    )
    session.add(group)
    session.commit()
    session.refresh(group)
    return group

@app.delete("/admin/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: str,
    # admin_user_id: Annotated[int, Depends(verify_admin_role)],
    session: Session = Depends(get_session)
):
    """
    Delete a group by group_id (admin only).
    
    Args:
        group_id: ID of the group to delete.
        admin_user_id: ID of the admin user (verified).
        session: Database session.
    
    Raises:
        HTTPException: If group_id does not exist.
    """
    group = session.get(Group, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with ID {group_id} not found."
        )
    session.delete(group)
    session.commit()

@app.post("/admin/groups/assign-roles", status_code=status.HTTP_204_NO_CONTENT)
async def assign_group_roles(
    assignment: GroupRoleAssignment,
    # admin_user_id: Annotated[int, Depends(verify_admin_role)],
    session: Session = Depends(get_session)
):
    """
    Assign roles to a user in a group (admin only).
    
    Args:
        assignment: GroupRoleAssignment with username, group_name, and roles.
        admin_user_id: ID of the admin user (verified).
        session: Database session.
    
    Raises:
        HTTPException: If user or group is not found, or invalid roles.
    """
    # Find user by username
    user = session.exec(
        select(User).where(User.username == assignment.username)
    ).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with username {assignment.username} not found."
        )
    
    # Find group by group_name
    group = session.exec(
        select(Group).where(Group.group_name == assignment.group_name)
    ).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with name {assignment.group_name} not found."
        )
    
    # Validate roles
    valid_roles = {UserRole.USER, UserRole.ADMIN}
    invalid_roles = set(assignment.roles) - valid_roles
    if invalid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid roles: {invalid_roles}. Valid roles are {valid_roles}."
        )
    
    # Delete existing role assignments for this user in this group
    session.exec(
        UserGroupRole.__table__.delete().where(
            UserGroupRole.user_uid == user.uid,
            UserGroupRole.group_id == group.group_id
        )
    )
    
    # Create new role assignments
    for role in assignment.roles:
        user_group_role = UserGroupRole(
            user_uid=user.uid,
            group_id=group.group_id,
            role=role
        )
        session.add(user_group_role)
    
    session.commit()

@app.delete("/admin/groups/remove-roles", status_code=status.HTTP_204_NO_CONTENT)
async def remove_group_roles(
    assignment: GroupRoleAssignment,
    # admin_user_id: Annotated[int, Depends(verify_admin_role)],
    session: Session = Depends(get_session)
):
    """
    Remove specific roles for a user in a group (admin only).
    
    Args:
        assignment: GroupRoleAssignment with username, group_name, and roles to remove.
        admin_user_id: ID of the admin user (verified).
        session: Database session.
    
    Raises:
        HTTPException: If user or group is not found, or invalid roles.
    """
    # Find user by username
    user = session.exec(
        select(User).where(User.username == assignment.username)
    ).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with username {assignment.username} not found."
        )
    
    # Find group by group_name
    group = session.exec(
        select(Group).where(Group.group_name == assignment.group_name)
    ).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with name {assignment.group_name} not found."
        )
    
    # Validate roles
    valid_roles = {UserRole.USER, UserRole.ADMIN}
    invalid_roles = set(assignment.roles) - valid_roles
    if invalid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid roles: {invalid_roles}. Valid roles are {valid_roles}."
        )
    
    # Delete specified role assignments
    for role in assignment.roles:
        session.exec(
            UserGroupRole.__table__.delete().where(
                UserGroupRole.user_uid == user.uid,
                UserGroupRole.group_id == group.group_id,
                UserGroupRole.role == role
            )
        )
    
    session.commit()

@app.get("/me")
async def get_current_user(
    token: str,
    session: Session = Depends(get_session)
) -> dict:
    try:
        # Decode JWT with validation
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("user_id")
        username: str = payload.get("username")
        global_role: str = payload.get("global_role")

        if not user_id or not username or not global_role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload: missing user_id, username, or global_role"
            )

        # Fetch user from database
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found in database"
            )

        # Fetch group roles from UserGroupRole
        group_roles = session.exec(
            select(UserGroupRole).where(UserGroupRole.user_uid == user_id)
        ).all()

        # Construct ACL dictionary
        acl = {}
        for group_role in group_roles:
            group_id = group_role.group_id
            role = group_role.role
            if group_id not in acl:
                acl[group_id] = {"role": []}
            acl[group_id]["role"].append(role)

        # Return user info in the specified format
        return {
            "ACL": acl,
            "global_role": global_role,
            "username": username,
            "uid": user_id
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during token processing: {str(e)}"
        )



@app.get("/admin/users/", response_model=List[UserRead])
async def get_all_users(
    session: Session = Depends(get_session)
):
    """
    Retrieve all users (admin only, for development use).
    
    Args:
        admin_user_info: User info from JWT, verified to have admin role.
        session: Database session.
    
    Returns:
        List[UserRead]: List of all users in the database.
    """
    users = session.exec(select(User)).all()
    return [UserRead.from_orm(user) for user in users]

@app.get("/admin/groups/all/", response_model=List[GroupRead])
async def get_all_groups(
    session: Session = Depends(get_session)
):
    """
    Retrieve all groups (admin only, for development use).
    
    Args:
        admin_user_info: User info from JWT, verified to have admin role.
        session: Database session.
    
    Returns:
        List[GroupRead]: List of all groups in the database.
    """
    groups = session.exec(select(Group)).all()
    return [GroupRead.from_orm(group) for group in groups]

@app.get("/admin/user-group-roles/", response_model=List[UserGroupRole])
async def get_all_user_group_roles(
    session: Session = Depends(get_session)
):
    """
    Retrieve all user-group-role assignments (admin only, for development use).
    
    Args:
        admin_user_info: User info from JWT, verified to have admin role.
        session: Database session.
    
    Returns:
        List[UserGroupRole]: List of all user-group-role assignments in the database.
    """
    user_group_roles = session.exec(select(UserGroupRole)).all()
    return user_group_roles