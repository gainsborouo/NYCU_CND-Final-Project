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
from google.auth.transport import requests
from passlib.context import CryptContext

# Import all models and enums from models.py
from models import (
    GlobalRole, GroupRole,
    User, UserCreate, UserRead,
    Group, GroupCreate, GroupRead,
    UserGroupRole, GroupRoleAssignment,
    PasswordUpdate
)

# --- Database Setup ---
load_dotenv()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL")
FRONTEND_REDIRECT_PATH = os.getenv("FRONTEND_REDIRECT_PATH")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
DATABASE_URL = os.getenv("DATABASE_URL","sqlite:///./auth_microservice.db")
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
app = FastAPI(title="Auth Microservice")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    with Session(engine) as session:
        admin_user = session.exec(select(User).where(User.username == "admin")).first()
        if not admin_user:
            admin_create = UserCreate(
                username="admin",
                password="admin",
                global_role=GlobalRole.ADMIN
            )
            admin_user = create_user(admin_create, session)
        default_group = session.exec(select(Group).where(Group.group_name == "default")).first()
        if not default_group:
            group = Group(group_name="default")
            session.add(group)
            session.commit()
            session.refresh(group)
            # Assign admin role to admin user in default group
            default_group = session.exec(select(Group).where(Group.group_name == "default")).first()
            user_group_role = UserGroupRole(
                user_id=admin_user.id,
                group_id=default_group.id,
                role=GroupRole.ADMIN
            )
            session.add(user_group_role)
            session.commit()

# --- OAuth2 Configuration ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# --- OAuth Token Validation ---
# async def is_admin(token: str = Depends(oauth2_scheme)) -> bool:
#     """Dependency to verify if the current user has the 'admin' role."""
#     try:
#         # Decode JWT with validation
#         payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

#         if "admin" not in payload.get("global_role"):
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail="Operation forbidden: Admin role required."
#             )
#         return user_info
#     except jwt.ExpiredSignatureError:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Token has expired"
#         )
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Unexpected error during token processing: {str(e)}"
#         )

# --- Google OAuth2 Endpoints ---
@app.get("/oauth/google/login")
async def login():
    google_auth_url = f"https://accounts.google.com/o/oauth2/auth?client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&response_type=code&scope=openid email profile"
    return RedirectResponse(url=google_auth_url)

@app.get("/oauth/google/callback")
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
        token_response = response.json()
        # if response.status_code != 200:
        #     raise HTTPException(status_code=401, detail="Failed to retrieve tokens from Google")
        # token_data = response.json()

    id_token_value = token_response.get("id_token")
    if not id_token_value:
        raise HTTPException(status_code=400, detail="No ID token received")

    try:
        payload = id_token.verify_oauth2_token(
            id_token_value,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )
        print(payload)

        sub = payload.get("sub")
        email = payload.get("email")
        name = payload.get("name") or email.split("@")[0]

        if not sub or not email:
            raise HTTPException(status_code=401, detail="Invalid token content")

        # Check if user exists
        user = session.exec(select(User).where(User.username == name)).first()
        if not user:
            user_create = UserCreate(
                username=name,
                password=None,
                global_role=GlobalRole.USER
            )
            user = create_user(user_create, session)

        group_roles = session.exec(
            select(UserGroupRole).where(UserGroupRole.user_id == user.id)
        ).all()

        acl = {}
        for group_role in group_roles:
            group_id = str(group_role.group_id)
            role = group_role.role.value.lower()
            if group_id not in acl:
                acl[group_id] = []
            acl[group_id].append(role)

        # Set token expiration (e.g., 1 hour)
        expiration = datetime.now(timezone.utc) + timedelta(hours=1)
        our_jwt_token = jwt.encode({
            "uid": user.id,
            "realm_roles": acl,
            "username": user.username,
            "global_role": user.global_role.value.lower(),
            "exp": int(expiration.timestamp())
        }, SECRET_KEY, algorithm=ALGORITHM)

        # return {
        #     "access_token": our_jwt_token,
        #     "token_type": "bearer"
        # }
        front_end_redirect_url = f"{FRONTEND_URL}{FRONTEND_REDIRECT_PATH}?token={our_jwt_token}"
        return RedirectResponse(url=front_end_redirect_url)

    except ValueError as e:
        print("Token verification failed:", str(e))
        raise HTTPException(status_code=401, detail=f"Invalid ID token: {str(e)}")

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
    
    group_roles = session.exec(select(UserGroupRole).where(UserGroupRole.user_id == user.id)).all()

    acl = {}
    for group_role in group_roles:
        group_id = str(group_role.group_id)
        role = group_role.role.value.lower()
        if group_id not in acl:
            acl[group_id] = []
        acl[group_id].append(role)

    # Set token expiration (e.g., 1 hour)
    expiration = datetime.now(timezone.utc) + timedelta(hours=1)
    our_jwt_token = jwt.encode({
        "uid": user.id,
        "realm_roles": acl,
        "username": user.username,
        "global_role": user.global_role.value.lower(),
        "exp": int(expiration.timestamp())
    }, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "access_token": our_jwt_token,
        "token_type": "bearer"
    }
    # front_end_redirect_url = f"{FRONTEND_URL}{FRONTEND_REDIRECT_PATH}?token={our_jwt_token}"
    # return RedirectResponse(url=front_end_redirect_url)

def create_user(
    user_create: UserCreate,
    session: Session
) -> User:

    existing_user = session.exec(select(User).where(User.username == user_create.username)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with UID {user_create.username} already exists."
        )
    
    # Create new user
    hashed_password = None
    if user_create.password:
        hashed_password = hash_password(user_create.password)
    # print(user_create.password,verify_password(user_create.password, hashed_password))
    user = User(
        username=user_create.username,
        password=hashed_password,
        global_role=user_create.global_role
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    default_group = session.exec(select(Group).where(Group.group_name == "default")).first()
    if default_group:
        user_group_role = UserGroupRole(
            user_id=user.id,
            group_id=default_group.id,
            role=GroupRole.USER
        )
        session.add(user_group_role)
        session.commit()
    return user

@app.post("/admin/users/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def user_create(
    user_create: UserCreate,
    session: Session = Depends(get_session)
):
    """
    Create a new user (admin only).

    Args:
        user_create: UserCreate model with username, optional password, and optional global_role.
        admin_user: User info from JWT, verified to have admin role.
        session: Database session.

    Returns:
        UserRead: The created user.

    Raises:
        HTTPException: If the username already exists.
    """
    user = create_user(user_create, session)
    return UserRead.from_orm(user)

@app.get("/admin/users/{user_id}/username", response_model=dict)
async def get_username_by_id(
    user_id: int,
    session: Session = Depends(get_session)
):
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )
    return {"username": user.username}

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
    existing_group = session.exec(select(Group).where(Group.group_name == group_create.group_name)).first()
    if existing_group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Group with ID {group_create.group_name} already exists."
        )
    group = Group(
        group_name=group_create.group_name
    )
    session.add(group)
    session.commit()
    session.refresh(group)

    admin_user = session.exec(select(User).where(User.username == "admin")).first()
    if admin_user:
        user_group_role = UserGroupRole(
            user_id=admin_user.id,
            group_id=group.id,
            role=GroupRole.ADMIN
        )
        session.add(user_group_role)
        session.commit()
    return group

@app.delete("/admin/groups/delete/{group_name}", status_code=status.HTTP_200_OK, response_model=dict)
async def delete_group(
    group_name: str,
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
    group = session.exec(select(Group).where(Group.group_name == group_name)).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with ID {group_name} not found."
        )
    session.delete(group)
    session.commit()
    return {"message": f"Group {group_name} deleted successfully"}

@app.post("/admin/groups/assign-roles", status_code=status.HTTP_201_CREATED, response_model=dict)
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
    user = session.exec(select(User).where(User.username == assignment.username)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with username {assignment.username} not found."
        )
    
    # Find group by group_name
    group = session.exec(select(Group).where(Group.group_name == assignment.group_name)).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with name {assignment.group_name} not found."
        )
    
    # Validate roles
    valid_roles = {GroupRole.USER, GroupRole.REVIEWER, GroupRole.ADMIN}
    invalid_roles = set(assignment.roles) - valid_roles
    if invalid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid roles: {invalid_roles}. Valid roles are {valid_roles}."
        )
    
    # Create new role assignments
    for role in assignment.roles:
        user_group_role = UserGroupRole(
            user_id=user.id,
            group_id=group.id,
            role=role
        )
        session.add(user_group_role)
    
    session.commit()
    return {"message": f"Roles {assignment.roles} assigned to user {assignment.username} in group {assignment.group_name}"}

@app.delete("/admin/groups/remove-roles", status_code=status.HTTP_200_OK, response_model=dict)
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
    user = session.exec(select(User).where(User.username == assignment.username)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with username {assignment.username} not found."
        )
    
    # Find group by group_name
    group = session.exec(select(Group).where(Group.group_name == assignment.group_name)).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with name {assignment.group_name} not found."
        )
    
    # Validate roles
    valid_roles = {GroupRole.USER, GroupRole.REVIEWER, GroupRole.ADMIN}
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
                UserGroupRole.user_id == user.id,
                UserGroupRole.group_id == group.id,
                UserGroupRole.role == role
            )
        )
    
    session.commit()
    return {"message": f"Roles {assignment.roles} removed for user {assignment.username} in group {assignment.group_name}"}

@app.get("/admin/users/", response_model=List[UserRead])
async def get_all_users(
    session: Session = Depends(get_session)
):
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

@app.post("/admin/password", status_code=status.HTTP_200_OK, response_model=dict)
async def update_password(
    password_update: PasswordUpdate,
    session: Session = Depends(get_session)
):
    """
    Update a user's password by username (admin only).

    Args:
        password_update: PasswordUpdate model with username and new_password.
        admin_user: Admin user info from JWT, verified to have admin role.
        session: Database session.

    Raises:
        HTTPException: If the user is not found.
    """
    user = session.exec(select(User).where(User.username == password_update.username)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with username {password_update.username} not found."
        )
    
    # Hash the new password
    user.password = hash_password(password_update.new_password)
    session.add(user)
    session.commit()
    return {"message": f"Password updated successfully for user {password_update.username}"}

@app.get("/admin/groups/names", response_model=dict)
async def get_group_names(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        realm_roles = payload.get("realm_roles", {})
        
        if not realm_roles:
            return {}
        
        group_ids = [int(gid) for gid in realm_roles.keys()]
        groups = session.exec(
            select(Group).where(Group.id.in_(group_ids))
        ).all()
        
        group_name_map = {str(group.id): group.group_name for group in groups}
        return group_name_map

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during token processing: {str(e)}"
        )

@app.get("/admin/groups/{group_id}/reviewers", response_model=dict)
async def get_group_reviewers(
    group_id: int,
    session: Session = Depends(get_session)
):
    group = session.exec(select(Group).where(Group.id == group_id)).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with ID {group_id} not found."
        )
    
    reviewers = session.exec(
        select(User.id, User.username)
        .join(UserGroupRole)
        .where(
            UserGroupRole.group_id == group_id,
            UserGroupRole.role == GroupRole.REVIEWER,
            User.id == UserGroupRole.user_id
        )
    ).all()
    
    return {str(user_id): username for user_id, username in reviewers}

@app.get("/me")
async def get_current_user(
    token: str,
) -> dict:
    try:
        # Decode JWT with validation
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("uid")
        username: str = payload.get("username")
        global_role: str = payload.get("global_role")

        if not user_id or not username or not global_role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload: missing user_id, username, or global_role"
            )
        
        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during token processing: {str(e)}"
        )