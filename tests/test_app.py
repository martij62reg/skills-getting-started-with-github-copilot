import pytest
from fastapi.testclient import TestClient
from src.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestActivitiesEndpoint:
    """Test the GET /activities endpoint."""

    def test_get_activities_success(self, client):
        """Test fetching all activities returns 200 and valid structure."""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        
        # Verify expected activities are present
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
        
        # Verify activity structure
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)

    def test_get_activities_contains_new_activities(self, client):
        """Test that added activities are present."""
        response = client.get("/activities")
        data = response.json()
        
        # Check for sports activities
        assert "Basketball Team" in data
        assert "Swimming Club" in data
        
        # Check for artistic activities
        assert "Art Workshop" in data
        assert "Drama Club" in data
        
        # Check for intellectual activities
        assert "Science Olympiad" in data
        assert "Debate Team" in data


class TestSignupEndpoint:
    """Test the POST /activities/{activity_name}/signup endpoint."""

    def test_signup_success(self, client):
        """Test successful signup for an activity."""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        assert "Signed up" in response.json()["message"]

    def test_signup_duplicate_prevention(self, client):
        """Test that duplicate signups are prevented."""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(
            "/activities/Programming Class/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Second signup with same email should fail
        response2 = client.post(
            "/activities/Programming Class/signup",
            params={"email": email}
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]

    def test_signup_activity_not_found(self, client):
        """Test signup for non-existent activity returns 404."""
        response = client.post(
            "/activities/Nonexistent Activity/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_signup_updates_participant_count(self, client):
        """Test that signup updates the participant list."""
        email = "counter@mergington.edu"
        activity_name = "Debate Team"
        
        # Get initial count
        response_before = client.get("/activities")
        initial_count = len(response_before.json()[activity_name]["participants"])
        
        # Signup
        client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Verify count increased
        response_after = client.get("/activities")
        final_count = len(response_after.json()[activity_name]["participants"])
        assert final_count == initial_count + 1
        assert email in response_after.json()[activity_name]["participants"]


class TestDeleteParticipantEndpoint:
    """Test the DELETE /activities/{activity_name}/participants/{email} endpoint."""

    def test_delete_participant_success(self, client):
        """Test successful deletion of a participant."""
        activity_name = "Science Olympiad"
        email = "test_delete@mergington.edu"
        
        # First, signup
        client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Then delete
        response = client.delete(
            f"/activities/{activity_name}/participants/{email}"
        )
        assert response.status_code == 200
        assert "Removed" in response.json()["message"]
        
        # Verify participant is gone
        response_check = client.get("/activities")
        assert email not in response_check.json()[activity_name]["participants"]

    def test_delete_participant_not_signed_up(self, client):
        """Test deleting a participant not signed up returns 400."""
        response = client.delete(
            "/activities/Art Workshop/participants/notexist@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]

    def test_delete_from_nonexistent_activity(self, client):
        """Test deleting from non-existent activity returns 404."""
        response = client.delete(
            "/activities/Nonexistent/participants/student@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_delete_updates_participant_count(self, client):
        """Test that delete updates the participant list."""
        activity_name = "Drama Club"
        email = "deletetest@mergington.edu"
        
        # Signup
        client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Get count before delete
        response_before = client.get("/activities")
        count_before = len(response_before.json()[activity_name]["participants"])
        
        # Delete
        client.delete(
            f"/activities/{activity_name}/participants/{email}"
        )
        
        # Get count after delete
        response_after = client.get("/activities")
        count_after = len(response_after.json()[activity_name]["participants"])
        
        assert count_after == count_before - 1


class TestActivityData:
    """Test activity data structure and content."""

    def test_all_activities_have_valid_structure(self, client):
        """Test that all activities have required fields."""
        response = client.get("/activities")
        data = response.json()
        
        required_fields = {"description", "schedule", "max_participants", "participants"}
        
        for activity_name, activity_data in data.items():
            assert all(field in activity_data for field in required_fields), \
                f"Activity '{activity_name}' missing required fields"
            
            assert isinstance(activity_data["max_participants"], int)
            assert activity_data["max_participants"] > 0
            assert isinstance(activity_data["participants"], list)

    def test_activities_have_reasonable_participant_counts(self, client):
        """Test that participant counts don't exceed max participants."""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert len(activity_data["participants"]) <= activity_data["max_participants"], \
                f"Activity '{activity_name}' has more participants than max_participants"


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_email_encoding_in_urls(self, client):
        """Test that URLs with special characters in emails are handled."""
        # Email with special characters
        email = "student+test@example.com"
        
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        
        # Verify in participants list
        response_check = client.get("/activities")
        assert email in response_check.json()["Chess Club"]["participants"]

    def test_case_sensitive_activity_names(self, client):
        """Test that activity names are case-sensitive."""
        # Correct case should work
        response1 = client.get("/activities")
        assert "Chess Club" in response1.json()
        
        # Wrong case should return 404
        response2 = client.post(
            "/activities/chess club/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response2.status_code == 404
