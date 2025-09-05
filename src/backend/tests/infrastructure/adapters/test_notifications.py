# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides tests for the `TelegramNotificationAdapter` class.

This module includes:
- `TestTelegramNotificationAdapter`: Tests for the `TelegramNotificationAdapter` class.
"""

import pytest

from telegram import Message


class TestTelegramNotificationAdapter:
    """
    Tests for the `TelegramNotificationAdapter` class.

    Methods:
        - test_telegram_notification: Tests that the `send_notification` method sends a message to the specified chat.
    """

    # ============================================= #
    #               Integration Tests               #
    # ============================================= #

    @pytest.mark.integration
    async def test_telegram_notification(self, real_dependencies):
        """
        Test that the `send_notification` method sends a message to the specified chat.

        Args:
            - real_dependencies: Fixture providing real dependencies.

        Assertions:
            - The result of `send_notification` is an instance of `Message`.
            - The chat ID of the sent message matches the specified chat ID.

        Raises:
            - AssertionError: If the message is not sent correctly.
        """
        config = real_dependencies.config()
        adapter = real_dependencies.notification()
        chat_id = config.telegram_chat_id
        test_message = "This is a test message."

        result = await adapter.send_notification(test_message)

        assert isinstance(result, Message)
        assert result.chat.id == int(chat_id)
