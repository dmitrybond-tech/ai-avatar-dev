"""Tests for Notion public tasks integration."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from notion_client import APIResponseError
from app.integrations.notion_public_tasks import (
    query_public_tasks,
    create_task,
    update_task,
    add_comment,
    assert_schema,
    compute_progress,
    get_notion_client,
)


class TestComputeProgress:
    """Test progress computation logic."""

    def test_progress_zero_scope(self):
        """Test progress when scope is 0."""
        assert compute_progress(0, 0) == 0
        assert compute_progress(0, 10) == 0

    def test_progress_normal(self):
        """Test normal progress calculation."""
        assert compute_progress(100, 50) == 50
        assert compute_progress(10, 3) == 30
        assert compute_progress(3, 1) == 33  # round(100/3) = 33

    def test_progress_complete(self):
        """Test progress at 100%."""
        assert compute_progress(100, 100) == 100
        assert compute_progress(10, 10) == 100

    def test_progress_over_100(self):
        """Test progress capped at 100%."""
        assert compute_progress(100, 150) == 100
        assert compute_progress(10, 20) == 100

    def test_progress_negative(self):
        """Test progress with negative values (should normalize to 0)."""
        assert compute_progress(-10, 5) == 0
        assert compute_progress(10, -5) == 0


class TestQueryPublicTasks:
    """Test querying public tasks."""

    @patch("app.integrations.notion_public_tasks.get_notion_client")
    @patch("app.integrations.notion_public_tasks.settings")
    def test_query_public_tasks_success(self, mock_settings, mock_get_client):
        """Test successful query of public tasks."""
        mock_settings.notion_public_tasks_db_id = "test-db-id"
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        # Mock Notion API response
        mock_client.databases.query.return_value = {
            "results": [
                {
                    "id": "page-1",
                    "last_edited_time": "2024-01-01T00:00:00.000Z",
                    "properties": {
                        "Name": {
                            "type": "title",
                            "title": [{"plain_text": "Test Task"}],
                        },
                        "Status": {
                            "type": "select",
                            "select": {"name": "In Progress"},
                        },
                        "Scope": {"type": "number", "number": 10},
                        "Done": {"type": "number", "number": 5},
                        "Progress %": {"type": "number", "number": 50},
                        "Review At": {"type": "date", "date": None},
                        "Tags": {"type": "multi_select", "multi_select": []},
                    },
                }
            ],
            "has_more": False,
        }

        tasks = query_public_tasks(limit=10)

        assert len(tasks) == 1
        assert tasks[0].id == "page-1"
        assert tasks[0].title == "Test Task"
        assert tasks[0].status == "In Progress"
        assert tasks[0].progress_pct == 50

    @patch("app.integrations.notion_public_tasks.get_notion_client")
    @patch("app.integrations.notion_public_tasks.settings")
    def test_query_public_tasks_no_db_id(self, mock_settings, mock_get_client):
        """Test query fails when DB ID is not set."""
        mock_settings.notion_public_tasks_db_id = ""
        with pytest.raises(ValueError, match="NOTION_PUBLIC_TASKS_DB_ID is not set"):
            query_public_tasks()

    @patch("app.integrations.notion_public_tasks.get_notion_client")
    @patch("app.integrations.notion_public_tasks.settings")
    def test_query_public_tasks_api_error(self, mock_settings, mock_get_client):
        """Test query handles API errors."""
        mock_settings.notion_public_tasks_db_id = "test-db-id"
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        error = APIResponseError(
            code="object_not_found",
            message="Database not found",
            request_id="test-request-id",
        )
        mock_client.databases.query.side_effect = error

        with pytest.raises(ValueError, match="Notion API error"):
            query_public_tasks()


class TestCreateTask:
    """Test creating tasks."""

    @patch("app.integrations.notion_public_tasks.get_notion_client")
    @patch("app.integrations.notion_public_tasks.settings")
    def test_create_task_success(self, mock_settings, mock_get_client):
        """Test successful task creation."""
        mock_settings.notion_public_tasks_db_id = "test-db-id"
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        # Mock created page
        mock_client.pages.create.return_value = {
            "id": "new-page-id",
            "last_edited_time": "2024-01-01T00:00:00.000Z",
            "properties": {
                "Name": {
                    "type": "title",
                    "title": [{"plain_text": "New Task"}],
                },
                "Status": {
                    "type": "select",
                    "select": {"name": "Backlog"},
                },
                "Scope": {"type": "number", "number": 0},
                "Done": {"type": "number", "number": 0},
                "Progress %": {"type": "number", "number": 0},
                "Review At": {"type": "date", "date": None},
                "Tags": {"type": "multi_select", "multi_select": []},
            },
        }

        task = create_task(title="New Task", status="Backlog", source="MiniApp")

        assert task.id == "new-page-id"
        assert task.title == "New Task"
        assert task.status == "Backlog"
        # Verify create was called with correct properties
        mock_client.pages.create.assert_called_once()
        call_args = mock_client.pages.create.call_args
        assert call_args[1]["parent"]["database_id"] == "test-db-id"
        props = call_args[1]["properties"]
        assert props["Name"]["title"][0]["text"]["content"] == "New Task"
        assert props["Status"]["status"]["name"] == "Backlog"
        assert props["Public?"]["checkbox"] is True

    @patch("app.integrations.notion_public_tasks.get_notion_client")
    @patch("app.integrations.notion_public_tasks.settings")
    def test_create_task_with_progress(self, mock_settings, mock_get_client):
        """Test task creation with scope and done values."""
        mock_settings.notion_public_tasks_db_id = "test-db-id"
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_client.pages.create.return_value = {
            "id": "new-page-id",
            "last_edited_time": "2024-01-01T00:00:00.000Z",
            "properties": {
                "Name": {
                    "type": "title",
                    "title": [{"plain_text": "Task with Progress"}],
                },
                "Status": {
                    "type": "select",
                    "select": {"name": "In Progress"},
                },
                "Scope": {"type": "number", "number": 100},
                "Done": {"type": "number", "number": 50},
                "Progress %": {"type": "number", "number": 50},
                "Review At": {"type": "date", "date": None},
                "Tags": {"type": "multi_select", "multi_select": []},
            },
        }

        task = create_task(title="Task with Progress", scope=100, done=50)

        # Verify progress was computed correctly
        call_args = mock_client.pages.create.call_args
        props = call_args[1]["properties"]
        assert props["Scope"]["number"] == 100
        assert props["Done"]["number"] == 50
        assert props["Progress %"]["number"] == 50


class TestUpdateTask:
    """Test updating tasks."""

    @patch("app.integrations.notion_public_tasks.get_notion_client")
    def test_update_task_status(self, mock_get_client):
        """Test updating task status."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        # Mock updated page
        mock_client.pages.update.return_value = {
            "id": "page-id",
            "last_edited_time": "2024-01-02T00:00:00.000Z",
            "properties": {
                "Name": {
                    "type": "title",
                    "title": [{"plain_text": "Updated Task"}],
                },
                "Status": {
                    "type": "select",
                    "select": {"name": "Done"},
                },
                "Scope": {"type": "number", "number": 10},
                "Done": {"type": "number", "number": 10},
                "Progress %": {"type": "number", "number": 100},
                "Review At": {"type": "date", "date": None},
                "Tags": {"type": "multi_select", "multi_select": []},
            },
        }

        task = update_task("page-id", status="Done")

        assert task.status == "Done"
        mock_client.pages.update.assert_called_once()
        call_args = mock_client.pages.update.call_args
        assert call_args[0][0] == "page-id"
        assert call_args[1]["properties"]["Status"]["status"]["name"] == "Done"

    @patch("app.integrations.notion_public_tasks.get_notion_client")
    def test_update_task_progress(self, mock_get_client):
        """Test updating task progress (scope/done)."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        # Mock current page state
        mock_client.pages.retrieve.return_value = {
            "id": "page-id",
            "properties": {
                "Scope": {"type": "number", "number": 10},
                "Done": {"type": "number", "number": 5},
            },
        }

        # Mock updated page
        mock_client.pages.update.return_value = {
            "id": "page-id",
            "last_edited_time": "2024-01-02T00:00:00.000Z",
            "properties": {
                "Name": {
                    "type": "title",
                    "title": [{"plain_text": "Task"}],
                },
                "Status": {
                    "type": "select",
                    "select": {"name": "In Progress"},
                },
                "Scope": {"type": "number", "number": 20},
                "Done": {"type": "number", "number": 10},
                "Progress %": {"type": "number", "number": 50},
                "Review At": {"type": "date", "date": None},
                "Tags": {"type": "multi_select", "multi_select": []},
            },
        }

        task = update_task("page-id", scope=20, done=10)

        # Verify progress was recomputed
        call_args = mock_client.pages.update.call_args
        props = call_args[1]["properties"]
        assert props["Scope"]["number"] == 20
        assert props["Done"]["number"] == 10
        assert props["Progress %"]["number"] == 50


class TestAddComment:
    """Test adding comments."""

    @patch("app.integrations.notion_public_tasks.get_notion_client")
    def test_add_comment_success(self, mock_get_client):
        """Test successful comment addition."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        add_comment("page-id", "This is a test comment")

        mock_client.comments.create.assert_called_once()
        call_args = mock_client.comments.create.call_args
        assert call_args[1]["parent"]["page_id"] == "page-id"
        assert call_args[1]["rich_text"][0]["text"]["content"] == "This is a test comment"

    @patch("app.integrations.notion_public_tasks.get_notion_client")
    def test_add_comment_truncated(self, mock_get_client):
        """Test comment text is truncated if too long."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        long_text = "a" * 2000
        add_comment("page-id", long_text)

        call_args = mock_client.comments.create.call_args
        assert len(call_args[1]["rich_text"][0]["text"]["content"]) == 1000


class TestAssertSchema:
    """Test schema assertion."""

    @patch("app.integrations.notion_public_tasks.get_notion_client")
    @patch("app.integrations.notion_public_tasks.settings")
    def test_assert_schema_success(self, mock_settings, mock_get_client):
        """Test successful schema validation."""
        mock_settings.notion_public_tasks_db_id = "test-db-id"
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_client.databases.retrieve.return_value = {
            "properties": {
                "Name": {"type": "title"},
                "Status": {
                    "type": "select",
                    "select": {
                        "options": [
                            {"name": "Backlog"},
                            {"name": "In Progress"},
                            {"name": "Review"},
                            {"name": "Blocked"},
                            {"name": "Done"},
                        ]
                    },
                },
                "Public?": {"type": "checkbox"},
                "Scope": {"type": "number"},
                "Done": {"type": "number"},
                "Progress %": {"type": "number"},
                "Review At": {"type": "date"},
                "Last Updated": {"type": "last_edited_time"},
            },
        }

        # Should not raise
        assert_schema()

    @patch("app.integrations.notion_public_tasks.get_notion_client")
    @patch("app.integrations.notion_public_tasks.settings")
    def test_assert_schema_missing_property(self, mock_settings, mock_get_client):
        """Test schema validation fails when property is missing."""
        mock_settings.notion_public_tasks_db_id = "test-db-id"
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_client.databases.retrieve.return_value = {
            "properties": {
                "Name": {"type": "title"},
                # Missing Status property
            },
        }

        with pytest.raises(ValueError, match="schema mismatch"):
            assert_schema()

    @patch("app.integrations.notion_public_tasks.get_notion_client")
    @patch("app.integrations.notion_public_tasks.settings")
    def test_assert_schema_wrong_type(self, mock_settings, mock_get_client):
        """Test schema validation fails when property type is wrong."""
        mock_settings.notion_public_tasks_db_id = "test-db-id"
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_client.databases.retrieve.return_value = {
            "properties": {
                "Name": {"type": "title"},
                "Status": {"type": "text"},  # Wrong type, should be select
                "Public?": {"type": "checkbox"},
                "Scope": {"type": "number"},
                "Done": {"type": "number"},
                "Progress %": {"type": "number"},
                "Review At": {"type": "date"},
                "Last Updated": {"type": "last_edited_time"},
            },
        }

        with pytest.raises(ValueError, match="schema mismatch"):
            assert_schema()

