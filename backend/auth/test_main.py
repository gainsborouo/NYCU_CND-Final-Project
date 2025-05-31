import pytest
import os
from fastapi.testclient import TestClient
from dotenv import load_dotenv
from sqlmodel import Session, create_engine, select, SQLModel
from jose import jwt
from datetime import datetime, timezone, timedelta
from time import sleep

from main import app, get_session, create_user, hash_password
from models import User, UserCreate, Group, GroupCreate, UserGroupRole, GroupRoleAssignment, GlobalRole, GroupRole

# --- Test Database Setup ---
TEST_DATABASE_URL = "sqlite:///./test_auth_microservice.db"
test_engine = create_engine(TEST_DATABASE_URL, echo=False)

@pytest.fixture(name="session")
def session_fixture():
    # Create tables for the test database
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session
    SQLModel.metadata.drop_all(test_engine)

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def override_get_session():
        yield session
    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()

# --- Constants ---
TEST_ADMIN_USERNAME = "admin"
TEST_USER_USERNAME = "testuser"
TEST_GROUP_NAME = "testgroup"
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")  # Fallback for testing
ALGORITHM = os.getenv("ALGORITHM")  # Fallback for testing
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

# --- Test Cases ---

def test_create_db_and_tables(session: Session):
    """Test that the database and tables are created correctly with an admin user."""
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        admin_user = session.exec(select(User).where(User.username == "admin")).first()
        if not admin_user:
            admin_create = UserCreate(
                username="admin",
                password="admin",  # Hash the admin password
                global_role=GlobalRole.ADMIN
            )
            create_user(admin_create, session)
    user = session.exec(select(User).where(User.username == "admin")).first()
    assert user is not None
    assert user.global_role == GlobalRole.ADMIN
    assert user.password is not None  # Password should be hashed

def test_google_oauth_login_redirect(client: TestClient):
    """Test the /oauth/google/login endpoint redirects correctly."""
    response = client.get("/oauth/google/login", follow_redirects=False)
    assert response.status_code == 307  # Temporary redirect
    assert response.headers["location"].startswith("https://accounts.google.com/o/oauth2/auth")
    assert f"client_id={GOOGLE_CLIENT_ID}" in response.headers["location"]
    assert f"redirect_uri={GOOGLE_REDIRECT_URI}" in response.headers["location"]
    assert "response_type=code" in response.headers["location"]

def test_create_user(client: TestClient, session: Session):
    """Test creating a new user via the /admin/users/ endpoint."""
    user_data = {
        "username": TEST_USER_USERNAME,
        "password": "testpassword",
        "global_role": GlobalRole.USER.value
    }
    response = client.post("/admin/users/", json=user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == TEST_USER_USERNAME
    assert data["global_role"] == GlobalRole.USER.value
    assert data["id"] is not None
    
    # Verify in database
    user = session.exec(select(User).where(User.username == TEST_USER_USERNAME)).first()
    assert user is not None
    assert user.password is not None  # Password should be hashed
    assert user.global_role == GlobalRole.USER

def test_create_user_duplicate_username(client: TestClient, session: Session):
    """Test that creating a user with a duplicate username fails."""
    user_create = UserCreate(username=TEST_USER_USERNAME, password="testpassword", global_role=GlobalRole.USER)
    create_user(user_create, session)
    
    response = client.post("/admin/users/", json={
        "username": TEST_USER_USERNAME,
        "password": "testpassword",
        "global_role": GlobalRole.USER.value
    })
    assert response.status_code == 400
    assert f"User with UID {TEST_USER_USERNAME} already exists" in response.json()["detail"]

def test_local_login_success(client: TestClient, session: Session):
    """Test successful local login with correct credentials."""
    user_create = UserCreate(username=TEST_USER_USERNAME, password="testpassword", global_role=GlobalRole.USER)
    create_user(user_create, session)
    
    response = client.post("/login", data={
        "username": TEST_USER_USERNAME,
        "password": "testpassword"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    
    # Verify JWT
    payload = jwt.decode(data["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["username"] == TEST_USER_USERNAME
    assert payload["global_role"] == GlobalRole.USER.value
    assert "uid" in payload
    assert "realm_roles" in payload

def test_local_login_invalid_credentials(client: TestClient, session: Session):
    """Test local login with incorrect credentials."""
    user_create = UserCreate(username=TEST_USER_USERNAME, password="testpassword", global_role=GlobalRole.USER)
    create_user(user_create, session)
    
    response = client.post("/login", data={
        "username": TEST_USER_USERNAME,
        "password": "wrongpassword"
    })
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]

def test_create_group(client: TestClient, session: Session):
    """Test creating a new group via the /admin/groups/ endpoint."""
    group_data = {"group_name": TEST_GROUP_NAME}
    response = client.post("/admin/groups/", json=group_data)
    assert response.status_code == 201
    data = response.json()
    assert data["group_name"] == TEST_GROUP_NAME
    assert data["id"] is not None
    
    # Verify in database
    group = session.exec(select(Group).where(Group.group_name == TEST_GROUP_NAME)).first()
    assert group is not None

def test_create_group_duplicate(client: TestClient, session: Session):
    """Test that creating a group with a duplicate name fails."""
    group_create = GroupCreate(group_name=TEST_GROUP_NAME)
    group = Group(group_name=group_create.group_name)
    session.add(group)
    session.commit()
    
    response = client.post("/admin/groups/", json={"group_name": TEST_GROUP_NAME})
    assert response.status_code == 400
    assert f"Group with ID {TEST_GROUP_NAME} already exists" in response.json()["detail"]

def test_delete_group(client: TestClient, session: Session):
    """Test deleting a group."""
    group = Group(group_name=TEST_GROUP_NAME)
    session.add(group)
    session.commit()
    session.refresh(group)
    
    response = client.delete(f"/admin/groups/delete/{TEST_GROUP_NAME}")
    assert response.status_code == 204
    
    # Verify deletion
    group = session.exec(select(Group).where(Group.group_name == TEST_GROUP_NAME)).first()
    assert group is None

def test_delete_nonexistent_group(client: TestClient, session: Session):
    """Test deleting a nonexistent group."""
    response = client.delete(f"/admin/groups/delete/nonexistent")
    assert response.status_code == 404
    assert "Group with ID nonexistent not found" in response.json()["detail"]

def test_assign_group_roles(client: TestClient, session: Session):
    """Test assigning roles to a user in a group."""
    # Create user and group
    user = User(username=TEST_USER_USERNAME, password=hash_password("testpassword"), global_role=GlobalRole.USER)
    group = Group(group_name=TEST_GROUP_NAME)
    session.add(user)
    session.add(group)
    session.commit()
    session.refresh(user)
    session.refresh(group)
    
    assignment = {
        "username": TEST_USER_USERNAME,
        "group_name": TEST_GROUP_NAME,
        "roles": [GroupRole.USER.value, GroupRole.REVIEWER.value]
    }
    response = client.post("/admin/groups/assign-roles", json=assignment)
    assert response.status_code == 204
    
    # Verify roles in database
    roles = session.exec(
        select(UserGroupRole).where(
            UserGroupRole.user_id == user.id,
            UserGroupRole.group_id == group.id
        )
    ).all()
    assert len(roles) == 2
    assert {r.role for r in roles} == {GroupRole.USER, GroupRole.REVIEWER}

def test_assign_group_roles_invalid_user(client: TestClient, session: Session):
    """Test assigning roles to a nonexistent user."""
    group = Group(group_name=TEST_GROUP_NAME)
    session.add(group)
    session.commit()
    
    assignment = {
        "username": "nonexistent",
        "group_name": TEST_GROUP_NAME,
        "roles": [GroupRole.USER.value]
    }
    response = client.post("/admin/groups/assign-roles", json=assignment)
    assert response.status_code == 404
    assert "User with username nonexistent not found" in response.json()["detail"]

def test_assign_group_roles_invalid_group(client: TestClient, session: Session):
    """Test assigning roles to a nonexistent group."""
    user = User(username=TEST_USER_USERNAME, password=hash_password("testpassword"), global_role=GlobalRole.USER)
    session.add(user)
    session.commit()
    
    assignment = {
        "username": TEST_USER_USERNAME,
        "group_name": "nonexistent",
        "roles": [GroupRole.USER.value]
    }
    response = client.post("/admin/groups/assign-roles", json=assignment)
    assert response.status_code == 404
    assert "Group with name nonexistent not found" in response.json()["detail"]

def test_assign_group_roles_invalid_roles(client: TestClient, session: Session):
    """Test assigning invalid roles to a user in a group."""
    user = User(username=TEST_USER_USERNAME, password=hash_password("testpassword"), global_role=GlobalRole.USER)
    group = Group(group_name=TEST_GROUP_NAME)
    session.add(user)
    session.add(group)
    session.commit()
    
    assignment = {
        "username": TEST_USER_USERNAME,
        "group_name": TEST_GROUP_NAME,
        "roles": ["invalid_role"]
    }
    response = client.post("/admin/groups/assign-roles", json=assignment)
    assert response.status_code == 422

def test_remove_group_roles(client: TestClient, session: Session):
    """Test removing roles from a user in a group."""
    # Setup user, group, and roles
    user = User(username=TEST_USER_USERNAME, password=hash_password("testpassword"), global_role=GlobalRole.USER)
    group = Group(group_name=TEST_GROUP_NAME)
    session.add(user)
    session.add(group)
    session.commit()
    session.refresh(user)
    session.refresh(group)
    
    user_group_role = UserGroupRole(user_id=user.id, group_id=group.id, role=GroupRole.USER)
    session.add(user_group_role)
    session.commit()
    
    assignment = {
        "username": TEST_USER_USERNAME,
        "group_name": TEST_GROUP_NAME,
        "roles": [GroupRole.USER.value]
    }
    response = client.request("DELETE", "/admin/groups/remove-roles", json=assignment)
    assert response.status_code == 204
    
    # Verify role removal
    roles = session.exec(
        select(UserGroupRole).where(
            UserGroupRole.user_id == user.id,
            UserGroupRole.group_id == group.id
        )
    ).all()
    assert len(roles) == 0

def test_remove_group_roles_invalid_user(client: TestClient, session: Session):
    """Test removing roles for a nonexistent user."""
    group = Group(group_name=TEST_GROUP_NAME)
    session.add(group)
    session.commit()
    
    assignment = {
        "username": "nonexistent",
        "group_name": TEST_GROUP_NAME,
        "roles": [GroupRole.USER.value]
    }
    response = client.request("DELETE", "/admin/groups/remove-roles", json=assignment)
    assert response.status_code == 404
    assert "User with username nonexistent not found" in response.json()["detail"]

def test_remove_group_roles_invalid_group(client: TestClient, session: Session):
    """Test removing roles for a nonexistent group."""
    user = User(username=TEST_USER_USERNAME, password=hash_password("testpassword"), global_role=GlobalRole.USER)
    session.add(user)
    session.commit()
    
    assignment = {
        "username": TEST_USER_USERNAME,
        "group_name": "nonexistent",
        "roles": [GroupRole.USER.value]
    }
    response = client.request("DELETE", "/admin/groups/remove-roles", json=assignment)
    assert response.status_code == 404
    assert "Group with name nonexistent not found" in response.json()["detail"]

def test_get_all_users(client: TestClient, session: Session):
    """Test retrieving all users."""
    user1 = User(username="user1", password=hash_password("testpassword"), global_role=GlobalRole.USER)
    user2 = User(username="user2", password=hash_password("testpassword"), global_role=GlobalRole.USER)
    session.add(user1)
    session.add(user2)
    session.commit()
    
    response = client.get("/admin/users/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert any(u["username"] == "user1" for u in data)
    assert any(u["username"] == "user2" for u in data)

def test_get_all_groups(client: TestClient, session: Session):
    """Test retrieving all groups."""
    group1 = Group(group_name="group1")
    group2 = Group(group_name="group2")
    session.add(group1)
    session.add(group2)
    session.commit()
    
    response = client.get("/admin/groups/all/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert any(g["group_name"] == "group1" for g in data)
    assert any(g["group_name"] == "group2" for g in data)

def test_get_all_user_group_roles(client: TestClient, session: Session):
    """Test retrieving all user-group-role assignments."""
    user = User(username=TEST_USER_USERNAME, password=hash_password("testpassword"), global_role=GlobalRole.USER)
    group = Group(group_name=TEST_GROUP_NAME)
    session.add(user)
    session.add(group)
    session.commit()
    session.refresh(user)
    session.refresh(group)
    
    user_group_role = UserGroupRole(user_id=user.id, group_id=group.id, role=GroupRole.USER)
    session.add(user_group_role)
    session.commit()
    
    response = client.get("/admin/user-group-roles/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(r["user_id"] == user.id and r["group_id"] == group.id and r["role"] == GroupRole.USER.value for r in data)

def test_update_password(client: TestClient, session: Session):
    """Test updating a user's password."""
    user = User(username=TEST_USER_USERNAME, password=hash_password("oldpassword"), global_role=GlobalRole.USER)
    session.add(user)
    session.commit()
    session.refresh(user)
    
    response = client.post("/admin/password", json={
        "username": TEST_USER_USERNAME,
        "new_password": "newpassword"
    })
    assert response.status_code == 204
    
    # Verify password update
    updated_user = session.exec(select(User).where(User.username == TEST_USER_USERNAME)).first()
    from main import verify_password
    assert verify_password("newpassword", updated_user.password)

def test_update_password_nonexistent_user(client: TestClient, session: Session):
    """Test updating password for a nonexistent user."""
    response = client.post("/admin/password", json={
        "username": "nonexistent",
        "new_password": "newpassword"
    })
    assert response.status_code == 404
    assert "User with username nonexistent not found" in response.json()["detail"]

def test_get_current_user(client: TestClient, session: Session):
    """Test the /me endpoint with a valid JWT."""
    user = User(username=TEST_USER_USERNAME, password=hash_password("testpassword"), global_role=GlobalRole.USER)
    session.add(user)
    session.commit()
    session.refresh(user)
    
    token = jwt.encode({
        "uid": user.id,
        "username": user.username,
        "global_role": user.global_role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }, SECRET_KEY, algorithm=ALGORITHM)
    
    response = client.get("/me", params={"token": token})
    assert response.status_code == 200
    data = response.json()
    assert data["uid"] == user.id
    assert data["username"] == TEST_USER_USERNAME
    assert data["global_role"] == GlobalRole.USER.value

def test_get_current_user_expired_token(client: TestClient):
    """Test the /me endpoint with an expired JWT."""
    token = jwt.encode({
        "uid": 1,
        "username": TEST_USER_USERNAME,
        "global_role": GlobalRole.USER.value,
        "exp": datetime.now(timezone.utc) - timedelta(hours=1)
    }, SECRET_KEY, algorithm=ALGORITHM)
    
    response = client.get("/me", params={"token": token})
    assert response.status_code == 401
    assert "Token has expired" in response.json()["detail"]

def test_get_current_user_invalid_token(client: TestClient):
    """Test the /me endpoint with an invalid JWT."""
    response = client.get("/me", params={"token": "invalid_token"})
    assert response.status_code == 500
    assert "Unexpected error during token processing" in response.json()["detail"]