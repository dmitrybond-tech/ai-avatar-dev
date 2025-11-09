"""Tests for shared Notion client factory."""
from unittest.mock import MagicMock, patch

import pytest

from app.integrations.notion_client import clear_client_cache, get_notion_client


class TestNotionClientFactory:
    """Ensure backward-compatible Notion client construction."""

    def setup_method(self):
        clear_client_cache()

    @patch("app.integrations.notion_client.Client")
    def test_timeout_kwarg_fallback(self, mock_client_cls):
        """Should retry without timeout when TypeError is raised."""

        client_instance = MagicMock()

        def side_effect(**kwargs):
            if "timeout" in kwargs:
                raise TypeError("unexpected keyword argument 'timeout'")
            return client_instance

        mock_client_cls.side_effect = side_effect

        result = get_notion_client("secret", timeout=10)

        assert result is client_instance
        assert mock_client_cls.call_count == 3
        first_call_kwargs = mock_client_cls.call_args_list[0].kwargs
        second_call_kwargs = mock_client_cls.call_args_list[1].kwargs
        third_call_kwargs = mock_client_cls.call_args_list[2].kwargs
        assert "timeout" in first_call_kwargs
        assert "timeout" in second_call_kwargs
        assert "timeout" not in third_call_kwargs

    @patch("app.integrations.notion_client.Client", side_effect=TypeError("bad arg"))
    def test_raises_when_all_attempts_fail(self, mock_client_cls):
        """Propagate the final TypeError if construction never succeeds."""
        with pytest.raises(TypeError):
            get_notion_client("secret", timeout=5)
        assert mock_client_cls.call_count >= 1

