import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, select
import httpx
from pytest_httpx import HTTPXMock 

from main import app, get_session, AUTH_SERVICE_BASE_URL 
from models import (
    SQLModel,
    Document, ReviewRecord, Notification, DocumentStatus, NotificationType, ReviewAction
)

# --- Test Database Setup ---
TEST_DATABASE_URL = "sqlite:///./test_review_microservice.db"
test_engine = create_engine(TEST_DATABASE_URL, echo=False)

@pytest.fixture(name="session")
def session_fixture():
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
    
# --- User ID Constants ---
TEST_ADMIN_ID = 1001 
TEST_USER_ID_1 = 2001 # Can be a creator, assigned reviewer
TEST_USER_ID_2 = 2002 # General user, can be assigned reviewer
TEST_USER_ID_3 = 2003 # Another general user for reviewer assignment
TEST_GROUP_A_MEMBER_ID = 3001
TEST_GROUP_B_MEMBER_ID = 3002
TEST_GROUP_C_MEMBER_ID = 3003

# --- NEW RBAC Mocks for /auth/userinfo endpoint ---
@pytest.fixture
def mock_user_info(httpx_mock: HTTPXMock):
    """
    Mocks the auth service to return roles and groups based on user ID
    in the new `gid: {"role": "..."}` format.
    Roles are now restricted to 'admin' or 'user'.
    """
    for i in range(5):
        httpx_mock.add_response(
            method="GET",
            url=f"{AUTH_SERVICE_BASE_URL}/userinfo?user_id={TEST_ADMIN_ID}",
            json={
                "gid_admin_general": {"role": "admin"},
                "gid_all_users": {"role": "user"}
            },
            status_code=200,
            is_optional=True
        )
        for i in range(5):
            httpx_mock.add_response(
            method="GET",
            url=f"{AUTH_SERVICE_BASE_URL}/userinfo?user_id={TEST_USER_ID_1}",
            json={
                "gid_creators": {"role": "user"}, # Now 'user' role
                "gid_all_users": {"role": "user"},
                "gid_group_x": {"role": "user"}
            },
            status_code=200,
            is_optional=True,
            
        )
        httpx_mock.add_response(
            method="GET",
            url=f"{AUTH_SERVICE_BASE_URL}/userinfo?user_id={TEST_USER_ID_2}",
            json={
                "gid_all_users": {"role": "user"}
            },
            status_code=200,
            is_optional=True
        )
        httpx_mock.add_response(
            method="GET",
            url=f"{AUTH_SERVICE_BASE_URL}/userinfo?user_id={TEST_USER_ID_3}", # Used as a reviewer now
            json={
                "gid_all_users": {"role": "user"}
            },
            status_code=200,
            is_optional=True
        )
        httpx_mock.add_response(
            method="GET",
            url=f"{AUTH_SERVICE_BASE_URL}/userinfo?user_id={TEST_GROUP_A_MEMBER_ID}",
            json={
                "gid_all_users": {"role": "user"},
                "group_a": {"role": "user"} # Role 'user' in group_a
            },
            status_code=200,
            is_optional=True
        )
        httpx_mock.add_response(
            method="GET",
            url=f"{AUTH_SERVICE_BASE_URL}/userinfo?user_id={TEST_GROUP_B_MEMBER_ID}",
            json={
                "gid_all_users": {"role": "user"},
                "group_b": {"role": "user"} # Role 'user' in group_b
            },
            status_code=200,
            is_optional=True
        )
        httpx_mock.add_response(
            method="GET",
            url=f"{AUTH_SERVICE_BASE_URL}/userinfo?user_id={TEST_GROUP_C_MEMBER_ID}",
            json={
                "gid_all_users": {"role": "user"},
                "group_c": {"role": "user"} # Role 'user' in group_c
            },
            status_code=200,
            is_optional=True
        )
        # Mock for a non-existent user for specific negative tests
        httpx_mock.add_response(
            method="GET",
            url=f"{AUTH_SERVICE_BASE_URL}/userinfo?user_id=9999",
            status_code=404,
            json={"detail": "User not found"},
            is_optional=True
        )


@pytest.fixture(autouse=True)
def apply_mock_user_info(mock_user_info):
    """Ensure mock_user_info is applied to all tests."""
    pass

# --- Test Cases (updated to reflect new role behavior) ---

# Admin service failure tests (remain same as they check auth service connectivity/response format)
def test_auth_service_unavailable_for_userinfo(client: TestClient, httpx_mock: HTTPXMock):
    httpx_mock.add_exception(
        httpx.RequestError("Mock connection error", request=httpx.Request("GET", f"{AUTH_SERVICE_BASE_URL}/userinfo?user_id={TEST_ADMIN_ID+1}")),
        url=f"{AUTH_SERVICE_BASE_URL}/userinfo?user_id={TEST_ADMIN_ID+1}",
        method="GET"
    )

    response = client.get(
        "/admin/documents/1/history", 
        headers={"X-User-Id": str(TEST_ADMIN_ID+1)}
    )
    
    assert response.status_code == 503
    assert "Could not connect to authentication service" in response.json()["detail"]

def test_auth_service_internal_error_for_userinfo(client: TestClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{AUTH_SERVICE_BASE_URL}/userinfo?user_id={TEST_ADMIN_ID+1}",
        method="GET",
        status_code=500,
        json={"detail": "Internal Server Error from Auth Service"}
    )

    response = client.get(
        "/admin/documents/1/history",
        headers={"X-User-Id": str(TEST_ADMIN_ID+1)}
    )
    
    assert response.status_code == 500
    assert "Authentication service returned an error: 500" in response.json()["detail"]

def test_auth_service_invalid_format_for_userinfo(client: TestClient, httpx_mock: HTTPXMock):
    # Mock an invalid response, e.g., a list instead of a dict
    httpx_mock.add_response(
        url=f"{AUTH_SERVICE_BASE_URL}/userinfo?user_id={TEST_ADMIN_ID+1}",
        method="GET",
        status_code=200,
        json=["invalid_data"] # Invalid format
    )

    response = client.get(
        "/admin/documents/1/history",
        headers={"X-User-Id": str(TEST_ADMIN_ID+1)}
    )
    assert response.status_code == 500
    assert "Invalid top-level response from authentication service" in response.json()["detail"]

    # Mock an invalid nested format (missing 'role')
    httpx_mock.add_response(
        url=f"{AUTH_SERVICE_BASE_URL}/userinfo?user_id={TEST_ADMIN_ID+1}",
        method="GET",
        status_code=200,
        json={"gid1": {"bad_key": "bad_value"}} # Invalid nested format
    )

    response = client.get(
        "/admin/documents/1/history",
        headers={"X-User-Id": str(TEST_ADMIN_ID+1)}
    )
    assert response.status_code == 500
    assert "Invalid group info from authentication service" in response.json()["detail"]

# Document creation (any user can create)
def test_create_document_as_any_user(client: TestClient):
    response = client.post(
        "/documents/",
        headers={"X-User-Id": str(TEST_USER_ID_1)},
        json={}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["status"] == DocumentStatus.DRAFT.value
    assert data["creator_id"] == TEST_USER_ID_1
    assert data["last_editor_id"] == TEST_USER_ID_1
    assert data["allowed_groups"] is None # Initially no groups set

# Get all documents (Admin vs Regular User)
def test_get_all_documents_as_admin(client: TestClient, session: Session):
    doc1 = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.DRAFT)
    doc2 = Document(creator_id=TEST_USER_ID_2, status=DocumentStatus.PUBLISHED)
    doc3 = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.PUBLISHED, allowed_groups="group_a")
    session.add(doc1)
    session.add(doc2)
    session.add(doc3)
    session.commit()
    session.refresh(doc1)
    session.refresh(doc2)
    session.refresh(doc3)

    response = client.get(
        "/documents/",
        headers={"X-User-Id": str(TEST_ADMIN_ID)}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3 
    assert any(d["id"] == doc1.id for d in data)
    assert any(d["id"] == doc2.id for d in data)
    assert any(d["id"] == doc3.id for d in data)

def test_get_all_documents_as_regular_user(client: TestClient, session: Session):
    doc_published_public = Document(creator_id=TEST_USER_ID_2, status=DocumentStatus.PUBLISHED, allowed_groups=None)
    doc_published_group_a = Document(creator_id=TEST_USER_ID_2, status=DocumentStatus.PUBLISHED, allowed_groups="group_a")
    doc_published_group_b = Document(creator_id=TEST_USER_ID_2, status=DocumentStatus.PUBLISHED, allowed_groups="group_b")
    doc_draft_other = Document(creator_id=TEST_USER_ID_2, status=DocumentStatus.DRAFT)
    doc_draft_mine = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.DRAFT) # Creator is TEST_USER_ID_1
    session.add(doc_published_public)
    session.add(doc_published_group_a)
    session.add(doc_published_group_b)
    session.add(doc_draft_other)
    session.add(doc_draft_mine)
    session.commit()
    session.refresh(doc_published_public)
    session.refresh(doc_published_group_a)
    session.refresh(doc_published_group_b)
    session.refresh(doc_draft_other)
    session.refresh(doc_draft_mine)

    # TEST_GROUP_A_MEMBER_ID is a user and member of 'group_a'
    # We should see:
    # 1. doc_published_public (publicly viewable)
    # 2. doc_published_group_a (member of group_a)
    # 3. doc_draft_mine_by_group_a_member (as creator)
    doc_draft_mine_by_group_a_member = Document(creator_id=TEST_GROUP_A_MEMBER_ID, status=DocumentStatus.DRAFT)
    session.add(doc_draft_mine_by_group_a_member)
    session.commit()
    session.refresh(doc_draft_mine_by_group_a_member)

    response = client.get(
        "/documents/",
        headers={"X-User-Id": str(TEST_GROUP_A_MEMBER_ID)}
    )
    assert response.status_code == 200
    data = response.json()
    
    assert any(d["id"] == doc_published_public.id for d in data)
    assert any(d["id"] == doc_published_group_a.id for d in data)
    assert any(d["id"] == doc_draft_mine_by_group_a_member.id for d in data)
    assert not any(d["id"] == doc_published_group_b.id for d in data) # Not in group_b
    assert not any(d["id"] == doc_draft_other.id for d in data) # Not creator, not published, not relevant group
    assert not any(d["id"] == doc_draft_mine.id for d in data) # Not creator, not published, not relevant group

# Get document detail access control
def test_get_document_detail_access_control(client: TestClient, session: Session, httpx_mock: HTTPXMock):
    doc_draft = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.DRAFT)
    doc_published_public = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.PUBLISHED, allowed_groups=None)
    doc_published_group_a = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.PUBLISHED, allowed_groups="group_a")
    doc_published_group_b = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.PUBLISHED, allowed_groups="group_b")
    doc_pending_review_assigned = Document(creator_id=TEST_USER_ID_1, current_reviewer_id=TEST_USER_ID_3, status=DocumentStatus.PENDING_REVIEW)
    session.add(doc_draft)
    session.add(doc_published_public)
    session.add(doc_published_group_a)
    session.add(doc_published_group_b)
    session.add(doc_pending_review_assigned)
    session.commit()
    session.refresh(doc_draft)
    session.refresh(doc_published_public)
    session.refresh(doc_published_group_a)
    session.refresh(doc_published_group_b)
    session.refresh(doc_pending_review_assigned)

    # Creator can view their own draft
    response = client.get(
        f"/documents/{doc_draft.id}",
        headers={"X-User-Id": str(TEST_USER_ID_1)}
    )
    assert response.status_code == 200

    # Other user cannot view a draft
    response = client.get(
        f"/documents/{doc_draft.id}",
        headers={"X-USER-ID": str(TEST_USER_ID_2)}
    )
    assert response.status_code == 403

    # Any user can view a public published document
    response = client.get(
        f"/documents/{doc_published_public.id}",
        headers={"X-User-Id": str(TEST_USER_ID_2)}
    )
    assert response.status_code == 200
    
    # User in group_a can view document restricted to group_a
    # Explicitly mock user info for this specific request to ensure 'group_a' is present

    response = client.get(
        f"/documents/{doc_published_group_a.id}",
        headers={"X-User-Id": str(TEST_GROUP_A_MEMBER_ID)}
    )
    assert response.status_code == 200

    # User NOT in group_a cannot view document restricted to group_a
    # Explicitly mock user info for this specific request to ensure 'group_a' is NOT present

    response = client.get(
        f"/documents/{doc_published_group_a.id}",
        headers={"X-User-Id": str(TEST_GROUP_C_MEMBER_ID)} # Not a member of group_a
    )
    assert response.status_code == 403
    assert "Your groups do not match the required groups." in response.json()["detail"]

    # Assigned user (who is now reviewer) can view a pending review document
    response = client.get(
        f"/documents/{doc_pending_review_assigned.id}",
        headers={"X-User-Id": str(TEST_USER_ID_3)}
    )
    assert response.status_code == 200

    # Unassigned user cannot view a pending review document
    response = client.get(
        f"/documents/{doc_pending_review_assigned.id}",
        headers={"X-User-Id": str(TEST_USER_ID_2)}
    )
    assert response.status_code == 403


# Update document (creator vs other user vs admin)
def test_update_document_as_creator(client: TestClient, session: Session):
    doc = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.DRAFT)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    response = client.put(
        f"/documents/{doc.id}",
        headers={"X-User-Id": str(TEST_USER_ID_1)},
        json={} # No actual update here, just testing permission
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == doc.id
    assert data["last_editor_id"] == TEST_USER_ID_1
    assert data["status"] == DocumentStatus.DRAFT.value

    # Test creator cannot change status if published (handled by the app logic now)
    doc.status = DocumentStatus.PUBLISHED
    session.add(doc)
    session.commit()
    session.refresh(doc)

    response = client.put(
        f"/documents/{doc.id}",
        headers={"X-User-Id": str(TEST_USER_ID_1)},
        json={"status": DocumentStatus.DRAFT.value}
    )
    assert response.status_code == 403 # Only admins can change status of published docs
    assert "Only admins can change status of published or pending review documents." in response.json()["detail"]


def test_update_document_as_other_user_forbidden(client: TestClient, session: Session):
    doc = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.DRAFT)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    response = client.put(
        f"/documents/{doc.id}",
        headers={"X-User-Id": str(TEST_USER_ID_2)}, # Not creator
        json={}
    )
    assert response.status_code == 403

def test_update_document_as_admin(client: TestClient, session: Session):
    doc = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.DRAFT)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    # Admin can change status from DRAFT to PUBLISHED
    response = client.put(
        f"/documents/{doc.id}",
        headers={"X-User-Id": str(TEST_ADMIN_ID)},
        json={"status": DocumentStatus.PUBLISHED.value}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == DocumentStatus.PUBLISHED.value
    assert data["last_editor_id"] == TEST_ADMIN_ID

    # Admin can re-assign reviewer even if pending
    doc.status = DocumentStatus.PENDING_REVIEW
    doc.current_reviewer_id = TEST_USER_ID_3 # Set an initial reviewer
    session.add(doc)
    session.commit()
    session.refresh(doc)

    response = client.put(
        f"/documents/{doc.id}",
        headers={"X-User-Id": str(TEST_ADMIN_ID)},
        json={"current_reviewer_id": TEST_USER_ID_2} # Assign to TEST_USER_ID_2
    )
    assert response.status_code == 200
    data = response.json()
    assert data["current_reviewer_id"] == TEST_USER_ID_2
    assert data["last_editor_id"] == TEST_ADMIN_ID

def test_creator_can_modify_groups_on_draft(client: TestClient, session: Session):
    doc = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.DRAFT, allowed_groups=None)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    response = client.put(
        f"/documents/{doc.id}",
        headers={"X-User-Id": str(TEST_USER_ID_1)},
        json={"allowed_groups": ["group_a", "group_b"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["allowed_groups"] == "group_a,group_b"
    assert data["last_editor_id"] == TEST_USER_ID_1

def test_creator_can_modify_groups_on_rejected(client: TestClient, session: Session):
    doc = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.REJECTED, allowed_groups="old_group")
    session.add(doc)
    session.commit()
    session.refresh(doc)

    response = client.put(
        f"/documents/{doc.id}",
        headers={"X-User-Id": str(TEST_USER_ID_1)},
        json={"allowed_groups": ["new_group"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["allowed_groups"] == "new_group"
    assert data["last_editor_id"] == TEST_USER_ID_1

def test_creator_cannot_modify_groups_on_pending_review(client: TestClient, session: Session):
    doc = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.PENDING_REVIEW, allowed_groups=None)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    response = client.put(
        f"/documents/{doc.id}",
        headers={"X-User-Id": str(TEST_USER_ID_1)},
        json={"allowed_groups": ["group_a"]}
    )
    assert response.status_code == 403
    assert "Creators can only modify groups for documents in DRAFT or REJECTED status." in response.json()["detail"]

def test_creator_cannot_modify_groups_on_published(client: TestClient, session: Session):
    doc = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.PUBLISHED, allowed_groups=None)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    response = client.put(
        f"/documents/{doc.id}",
        headers={"X-User-Id": str(TEST_USER_ID_1)},
        json={"allowed_groups": ["group_a"]}
    )
    assert response.status_code == 403
    assert "Creators can only modify groups for documents in DRAFT or REJECTED status." in response.json()["detail"]

def test_admin_can_modify_groups_on_any_status(client: TestClient, session: Session):
    doc_draft = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.DRAFT, allowed_groups=None)
    doc_pending = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.PENDING_REVIEW, allowed_groups=None)
    doc_published = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.PUBLISHED, allowed_groups=None)
    session.add(doc_draft)
    session.add(doc_pending)
    session.add(doc_published)
    session.commit()
    session.refresh(doc_draft)
    session.refresh(doc_pending)
    session.refresh(doc_published)

    # Admin on DRAFT
    response = client.put(
        f"/documents/{doc_draft.id}",
        headers={"X-User-Id": str(TEST_ADMIN_ID)},
        json={"allowed_groups": ["admin_group_d"]}
    )
    assert response.status_code == 200
    assert response.json()["allowed_groups"] == "admin_group_d"

    # Admin on PENDING_REVIEW
    response = client.put(
        f"/documents/{doc_pending.id}",
        headers={"X-User-Id": str(TEST_ADMIN_ID)},
        json={"allowed_groups": ["admin_group_p"]}
    )
    assert response.status_code == 200
    assert response.json()["allowed_groups"] == "admin_group_p"

    # Admin on PUBLISHED
    response = client.put(
        f"/documents/{doc_published.id}",
        headers={"X-User-Id": str(TEST_ADMIN_ID)},
        json={"allowed_groups": ["admin_group_pub"]}
    )
    assert response.status_code == 200
    assert response.json()["allowed_groups"] == "admin_group_pub"


# Submit for review
def test_submit_for_review(client: TestClient, session: Session):
    doc = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.DRAFT)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    response = client.post(
        f"/documents/{doc.id}/submit-for-review",
        headers={"X-User-Id": str(TEST_USER_ID_1)},
        json={"reviewer_id": TEST_USER_ID_3} # Assign a general user
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == DocumentStatus.PENDING_REVIEW.value
    assert data["current_reviewer_id"] == TEST_USER_ID_3

    notifications = session.exec(
        select(Notification).where(Notification.recipient_id == TEST_USER_ID_3)
    ).all()
    assert len(notifications) >= 1
    assert any(n.type == NotificationType.DOCUMENT_FOR_REVIEW and n.document_id == doc.id for n in notifications)

def test_submit_for_review_by_non_creator_forbidden(client: TestClient, session: Session):
    doc = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.DRAFT)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    response = client.post(
        f"/documents/{doc.id}/submit-for-review",
        headers={"X-User-Id": str(TEST_USER_ID_2)}, # Not the creator
        json={"reviewer_id": TEST_USER_ID_3}
    )
    assert response.status_code == 403
    assert "Only the document creator can submit for review" in response.json()["detail"]


def test_submit_for_review_invalid_reviewer_id(client: TestClient, session: Session):
    doc = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.DRAFT)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    # Attempt to assign a non-existent user
    response = client.post(
        f"/documents/{doc.id}/submit-for-review",
        headers={"X-User-Id": str(TEST_USER_ID_1)},
        json={"reviewer_id": 9999} # Non-existent user
    )
    assert response.status_code == 404 # Should be 404 from auth service mocked
    print(response.json()["detail"])
    assert "Authentication service returned an error: 404 - {\"detail\":\"User not found\"}" in response.json()["detail"]


# Review document (approve/reject)
def test_approve_document(client: TestClient, session: Session):
    doc = Document(creator_id=TEST_USER_ID_1, current_reviewer_id=TEST_USER_ID_3, status=DocumentStatus.PENDING_REVIEW)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    response = client.post(
        f"/documents/{doc.id}/review",
        headers={"X-User-Id": str(TEST_USER_ID_3)}, # The assigned user
        json={"action": ReviewAction.APPROVE.value}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == DocumentStatus.PUBLISHED.value
    assert data["published_at"] is not None

    review_record = session.exec(
        select(ReviewRecord).where(ReviewRecord.document_id == doc.id)
    ).first()
    assert review_record is not None
    assert review_record.status == DocumentStatus.PUBLISHED
    assert review_record.reviewer_id == TEST_USER_ID_3

    notification = session.exec(
        select(Notification).where(
            Notification.document_id == doc.id,
            Notification.recipient_id == TEST_USER_ID_1,
            Notification.type == NotificationType.DOCUMENT_APPROVED
        )
    ).first()
    assert notification is not None
    assert f"Document ID {doc.id} has been approved and published." in notification.message

def test_reject_document(client: TestClient, session: Session):
    doc = Document(creator_id=TEST_USER_ID_1, current_reviewer_id=TEST_USER_ID_3, status=DocumentStatus.PENDING_REVIEW)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    rejection_reason = "Needs more details in section 2."
    response = client.post(
        f"/documents/{doc.id}/review",
        headers={"X-User-Id": str(TEST_USER_ID_3)}, # The assigned user
        json={"action": ReviewAction.REJECT.value, "rejection_reason": rejection_reason}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == DocumentStatus.REJECTED.value

    review_record = session.exec(
        select(ReviewRecord).where(ReviewRecord.document_id == doc.id)
    ).first()
    assert review_record is not None
    assert review_record.status == DocumentStatus.REJECTED
    assert review_record.rejection_reason == rejection_reason

    notification = session.exec(
        select(Notification).where(
            Notification.document_id == doc.id,
            Notification.recipient_id == TEST_USER_ID_1,
            Notification.type == NotificationType.DOCUMENT_REJECTED
        )
    ).first()
    assert notification is not None
    assert f"Document ID {doc.id} has been rejected. Reason: {rejection_reason}" in notification.message

def test_review_document_by_unassigned_user_forbidden(client: TestClient, session: Session):
    doc = Document(creator_id=TEST_USER_ID_1, current_reviewer_id=TEST_USER_ID_3, status=DocumentStatus.PENDING_REVIEW)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    response = client.post(
        f"/documents/{doc.id}/review",
        headers={"X-User-Id": str(TEST_USER_ID_2)}, # Not assigned reviewer
        json={"action": ReviewAction.APPROVE.value}
    )
    assert response.status_code == 403
    assert "Not authorized to review this document." in response.json()["detail"]

def test_review_document_by_admin(client: TestClient, session: Session):
    doc = Document(creator_id=TEST_USER_ID_1, current_reviewer_id=TEST_USER_ID_3, status=DocumentStatus.PENDING_REVIEW)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    response = client.post(
        f"/documents/{doc.id}/review",
        headers={"X-User-Id": str(TEST_ADMIN_ID)}, # Admin can review
        json={"action": ReviewAction.APPROVE.value}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == DocumentStatus.PUBLISHED.value
    assert data["published_at"] is not None


# Notifications
def test_get_user_notifications(client: TestClient, session: Session):
    notif1 = Notification(sender_id=TEST_USER_ID_3, recipient_id=TEST_USER_ID_1, type=NotificationType.DOCUMENT_APPROVED, message="Your document was approved.")
    notif2 = Notification(sender_id=TEST_USER_ID_3, recipient_id=TEST_USER_ID_1, type=NotificationType.DOCUMENT_FOR_REVIEW, message="Another notification.")
    notif3 = Notification(sender_id=TEST_USER_ID_1, recipient_id=TEST_USER_ID_2, type=NotificationType.DOCUMENT_STATE_CHANGE, message="Something for user 2.")
    session.add(notif1)
    session.add(notif2)
    session.add(notif3)
    session.commit()
    session.refresh(notif1)
    session.refresh(notif2)
    session.refresh(notif3)

    response = client.get(
        "/notifications/",
        headers={"X-User-Id": str(TEST_USER_ID_1)}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert any(n["message"] == "Your document was approved." for n in data)
    assert any(n["message"] == "Another notification." for n in data)
    assert not any(n["message"] == "Something for user 2." for n in data)
    assert data[0]["sender_id"] == TEST_USER_ID_3 # Assuming creation order is maintained

def test_mark_notification_as_read(client: TestClient, session: Session):
    notif = Notification(sender_id=TEST_USER_ID_3, recipient_id=TEST_USER_ID_1, type=NotificationType.DOCUMENT_APPROVED, message="Read me.")
    session.add(notif)
    session.commit()
    session.refresh(notif)

    response = client.patch(
        f"/notifications/{notif.id}/mark-as-read",
        headers={"X-User-Id": str(TEST_USER_ID_1)}
    )
    assert response.status_code == 204

    updated_notif = session.get(Notification, notif.id)
    assert updated_notif.is_read is True

def test_mark_notification_as_read_unauthorized(client: TestClient, session: Session):
    notif = Notification(sender_id=TEST_USER_ID_3, recipient_id=TEST_USER_ID_1, type=NotificationType.DOCUMENT_APPROVED, message="Read me.")
    session.add(notif)
    session.commit()
    session.refresh(notif)

    response = client.patch(
        f"/notifications/{notif.id}/mark-as-read",
        headers={"X-User-Id": str(TEST_USER_ID_2)}
    )
    assert response.status_code == 404


# Admin endpoints
def test_admin_assign_reviewer(client: TestClient, session: Session):
    doc = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.DRAFT)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    response = client.patch(
        f"/admin/documents/{doc.id}/assign-reviewer",
        headers={"X-User-Id": str(TEST_ADMIN_ID)},
        json={"reviewer_id": TEST_USER_ID_3} # Assign a general user
    )
    assert response.status_code == 200
    data = response.json()
    assert data["current_reviewer_id"] == TEST_USER_ID_3
    assert data["status"] == DocumentStatus.PENDING_REVIEW.value

    notifications = session.exec(
        select(Notification).where(Notification.recipient_id == TEST_USER_ID_3)
    ).all()
    assert len(notifications) >= 1
    assert any(n.type == NotificationType.DOCUMENT_FOR_REVIEW and n.document_id == doc.id for n in notifications)

def test_admin_assign_reviewer_unauthorized(client: TestClient, session: Session):
    doc = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.DRAFT)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    response = client.patch(
        f"/admin/documents/{doc.id}/assign-reviewer",
        headers={"X-User-Id": str(TEST_USER_ID_2)}, # Not an admin
        json={"reviewer_id": TEST_USER_ID_3}
    )
    assert response.status_code == 403

def test_admin_assign_reviewer_invalid_reviewer_id(client: TestClient, session: Session):
    doc = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.DRAFT)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    # Attempt to assign a non-existent user
    response = client.patch(
        f"/admin/documents/{doc.id}/assign-reviewer",
        headers={"X-User-Id": str(TEST_ADMIN_ID)},
        json={"reviewer_id": 9999} # Non-existent user
    )
    assert response.status_code == 404
    assert "Authentication service returned an error: 404 - {\"detail\":\"User not found\"}" in response.json()["detail"]


def test_admin_set_document_groups(client: TestClient, session: Session):
    doc = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.PUBLISHED, allowed_groups=None)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    # Set groups
    response = client.post(
        f"/admin/documents/{doc.id}/set-groups",
        headers={"X-User-Id": str(TEST_ADMIN_ID)},
        json=["group_a", "group_b"]
    )
    assert response.status_code == 200
    data = response.json()
    assert data["allowed_groups"] == "group_a,group_b"
    assert data["last_editor_id"] == TEST_ADMIN_ID

    # Clear groups
    response = client.post(
        f"/admin/documents/{doc.id}/set-groups",
        headers={"X-User-Id": str(TEST_ADMIN_ID)},
        json=[]
    )
    assert response.status_code == 200
    data = response.json()
    assert data["allowed_groups"] is None

def test_admin_set_document_groups_on_any_status_allowed(client: TestClient, session: Session):
    doc_draft = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.DRAFT)
    doc_pending = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.PENDING_REVIEW)
    doc_rejected = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.REJECTED)
    doc_published = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.PUBLISHED)
    session.add(doc_draft)
    session.add(doc_pending)
    session.add(doc_rejected)
    session.add(doc_published)
    session.commit()
    session.refresh(doc_draft)
    session.refresh(doc_pending)
    session.refresh(doc_rejected)
    session.refresh(doc_published)

    # Admin can set groups on DRAFT
    response = client.post(
        f"/admin/documents/{doc_draft.id}/set-groups",
        headers={"X-User-Id": str(TEST_ADMIN_ID)},
        json=["admin_group_draft"]
    )
    assert response.status_code == 200
    assert response.json()["allowed_groups"] == "admin_group_draft"

    # Admin can set groups on PENDING_REVIEW
    response = client.post(
        f"/admin/documents/{doc_pending.id}/set-groups",
        headers={"X-User-Id": str(TEST_ADMIN_ID)},
        json=["admin_group_pending"]
    )
    assert response.status_code == 200
    assert response.json()["allowed_groups"] == "admin_group_pending"

    # Admin can set groups on REJECTED
    response = client.post(
        f"/admin/documents/{doc_rejected.id}/set-groups",
        headers={"X-User-Id": str(TEST_ADMIN_ID)},
        json=["admin_group_rejected"]
    )
    assert response.status_code == 200
    assert response.json()["allowed_groups"] == "admin_group_rejected"

    # Admin can set groups on PUBLISHED
    response = client.post(
        f"/admin/documents/{doc_published.id}/set-groups",
        headers={"X-User-Id": str(TEST_ADMIN_ID)},
        json=["admin_group_published"]
    )
    assert response.status_code == 200
    assert response.json()["allowed_groups"] == "admin_group_published"


def test_admin_set_document_groups_unauthorized(client: TestClient, session: Session):
    doc = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.PUBLISHED)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    response = client.post(
        f"/admin/documents/{doc.id}/set-groups",
        headers={"X-User-Id": str(TEST_USER_ID_2)}, # Not an admin
        json=["group_a"]
    )
    assert response.status_code == 403


def test_admin_get_document_history(client: TestClient, session: Session):
    doc = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.DRAFT)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    review1 = ReviewRecord(document_id=doc.id, reviewer_id=TEST_USER_ID_3, action=ReviewAction.REJECT, status=DocumentStatus.REJECTED, rejection_reason="First review, needs more detail.")
    review2 = ReviewRecord(document_id=doc.id, reviewer_id=TEST_USER_ID_3, action=ReviewAction.APPROVE, status=DocumentStatus.PUBLISHED, rejection_reason=None)
    session.add(review1)
    session.add(review2)
    session.commit()

    response = client.get(
        f"/admin/documents/{doc.id}/history",
        headers={"X-User-Id": str(TEST_ADMIN_ID)}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert any(r["rejection_reason"] == "First review, needs more detail." for r in data)
    assert any(r["status"] == DocumentStatus.PUBLISHED.value for r in data)
    assert all(r["reviewer_id"] == TEST_USER_ID_3 for r in data if r["document_id"] == doc.id)

def test_admin_get_document_history_unauthorized(client: TestClient, session: Session):
    doc = Document(creator_id=TEST_USER_ID_1, status=DocumentStatus.DRAFT)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    response = client.get(
        f"/admin/documents/{doc.id}/history",
        headers={"X-User-Id": str(TEST_USER_ID_2)} # Not an admin
    )
    assert response.status_code == 403