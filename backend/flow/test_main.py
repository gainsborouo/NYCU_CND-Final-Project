import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from main import app, get_session
from models import DocumentStatus, UserRoles, DocumentCreate

# --- Test Database Setup ---
TEST_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(TEST_DATABASE_URL, echo=False)

@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session
    SQLModel.metadata.drop_all(test_engine)

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
    # Override the get_session dependency to use the test session
    app.dependency_overrides[get_session] = get_session_override
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
def mock_user_context():
    def _mock_user_context_factory(user_id: int, realm_roles):
        return UserRoles(user_id=user_id, realm_roles=realm_roles)
    return _mock_user_context_factory

def set_user_context(mock_user_context_factory, user_id, realm_roles):
    def _get_current_user_context_mock():
        return mock_user_context_factory(user_id, realm_roles)
    from main import get_current_user_context
    app.dependency_overrides[get_current_user_context] = _get_current_user_context_mock

def test_create_and_get_document(client, session, mock_user_context):
    # Set user as 'user' in realm '1'
    set_user_context(mock_user_context, user_id=1, realm_roles={"1": ["user"]})

    # Create a document
    response = client.post(
        "/documents/1",
        json={"title": "Test Doc", "description": "pytest doc"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Doc"
    assert data["description"] == "pytest doc"
    assert data["creator_id"] == 1
    assert data["realm_id"] == 1

    # Now test GET
    response = client.get("/documents/1")
    assert response.status_code == 200
    docs = response.json()
    assert any(doc["title"] == "Test Doc" for doc in docs)

def test_create_document_unauthorized(client, session, mock_user_context):
    # Set user as 'user' in realm '2'
    set_user_context(mock_user_context, user_id=1, realm_roles={"2": ["user"]})

    # Attempt to create a document in realm '1' where the user has no access
    response = client.post(
        "/documents/1",
        json={"title": "Unauthorized Doc", "description": "pytest unauthorized doc"}
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "User not authorized to create documents in realm '1'."}

def test_get_document_details(client, session, mock_user_context):
    # Set user as 'user' in realm '1'
    set_user_context(mock_user_context, user_id=1, realm_roles={"1": ["user"]})

    # Create a document first
    response = client.post(
        "/documents/1",
        json={"title": "Test Doc", "description": "pytest doc"}
    )
    assert response.status_code == 201

    # Now test GET for the created document
    response = client.get("/documents/1/details")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Doc"
    assert data["description"] == "pytest doc"
    assert data["creator_id"] == 1
    assert data["realm_id"] == 1

def test_update_document(client, session, mock_user_context):
    # Set user as 'user' in realm '1'
    set_user_context(mock_user_context, user_id=1, realm_roles={"1": ["user"]})

    # Create a document first
    response = client.post(
        "/documents/1",
        json={"title": "Test Doc", "description": "pytest doc"}
    )
    assert response.status_code == 201

    # Now update the document
    update_data = {"title": "Updated Test Doc", "description": "Updated pytest doc"}
    response = client.patch("/documents/1", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Test Doc"
    assert data["description"] == "Updated pytest doc"
    assert data["creator_id"] == 1
    assert data["realm_id"] == 1    

def test_submit_document_for_review(client, session, mock_user_context):
    # Set user as 'user' in realm '1'
    set_user_context(mock_user_context, user_id=1, realm_roles={"1": ["user"]})

    # Create a document first
    response = client.post(
        "/documents/1",
        json={"title": "Test Doc", "description": "pytest doc"}
    )
    assert response.status_code == 201

    # Now submit the document for review
    response = client.post("/documents/1/submit-for-review", json={"reviewer_id": 2})
    assert response.status_code == 200
    data = response.json()
    print(data)
    assert data["id"] == 1
    assert data["current_reviewer_id"] == 2
    assert data["status"] == "pending_review"

def test_perform_review_action(client, session, mock_user_context):
    # Set user as 'reviewer' in realm '1'
    set_user_context(mock_user_context, user_id=2, realm_roles={"1": ["user", "reviewer"]})

    # Create a document first
    response = client.post(
        "/documents/1",
        json={"title": "Test Doc", "description": "pytest doc"}
    )
    assert response.status_code == 201

    # Submit the document for review
    response = client.post("/documents/1/submit-for-review", json={"reviewer_id": 2})
    assert response.status_code == 200

    # Now perform a review action
    review_action_data = {
        "action": "approve",
        "rejection_reason": None
    }
    response = client.post("/documents/1/review-action", json=review_action_data)
    assert response.status_code == 200
    data = response.json()
    print(data)
    assert data["review_record"]["action"] == "approve"
    assert data["updated_document"]["status"] == "published"

def test_get_document_review_history(client, session, mock_user_context):
    # Set user as 'reviewer' in realm '1'
    set_user_context(mock_user_context, user_id=2, realm_roles={"1": ["user", "reviewer"]})

    # Create a document first
    response = client.post(
        "/documents/1",
        json={"title": "Test Doc", "description": "pytest doc"}
    )
    assert response.status_code == 201

    # Submit the document for review
    response = client.post("/documents/1/submit-for-review", json={"reviewer_id": 2})
    assert response.status_code == 200

    # Perform a review action
    review_action_data = {
        "action": "approve",
        "rejection_reason": None
    }
    response = client.post("/documents/1/review-action", json=review_action_data)
    assert response.status_code == 200

    # Now get the review history
    response = client.get("/documents/1/review-history")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["action"] == "approve"

def test_get_user_notifications_notify_accepted(client, session, mock_user_context):
    # Set user as 'user' in realm '1'
    set_user_context(mock_user_context, user_id=1, realm_roles={"1": ["user"]})

    # Create a document first
    response = client.post(
        "/documents/1",
        json={"title": "Test Doc", "description": "pytest doc"}
    )
    assert response.status_code == 201

    response = client.post("/documents/1/submit-for-review", json={"reviewer_id": 1})
    assert response.status_code == 200

    # Perform a review action
    review_action_data = {
        "action": "approve",
        "rejection_reason": None
    }
    response = client.post("/documents/1/review-action", json=review_action_data)
    # Now get notifications for the user
    response = client.get("/notifications")
    assert response.status_code == 200
    data = response.json()
    print(data)
    assert len(data) > 0
    assert data[-1]["message"] == "Your document 'Test Doc' has been approved and published in realm '1'."
def test_get_user_notifications_notify_rejected(client, session, mock_user_context):
    # Set user as 'user' in realm '1'
    set_user_context(mock_user_context, user_id=1, realm_roles={"1": ["user"]})

    # Create a document first
    response = client.post(
        "/documents/1",
        json={"title": "Test Doc", "description": "pytest doc"}
    )
    assert response.status_code == 201

    response = client.post("/documents/1/submit-for-review", json={"reviewer_id": 1})
    assert response.status_code == 200

    # Perform a review action
    review_action_data = {
        "action": "reject",
        "rejection_reason": "Not up to standards"
    }
    response = client.post("/documents/1/review-action", json=review_action_data)
    # Now get notifications for the user
    response = client.get("/notifications")
    assert response.status_code == 200
    data = response.json()
    print(data)
    assert len(data) > 0
    assert data[-1]["message"] == "Your document 'Test Doc' has been rejected in realm '1'. Reason: Not up to standards"