# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides an asynchronous `AbstractNotification` adapter using Telegram.

This module includes:
- `TelegramNotificationAdapter`: Sends notifications to a specified Telegram chat using the Telegram Bot API
"""

from structlog import stdlib
from telegram import Bot, Message
from telegram.error import TelegramError

from backend.app.application import ports

log = stdlib.get_logger(__name__)

# ========================================= #
#               Notifications               #
# ========================================= #


class TelegramNotificationAdapter(ports.AbstractNotification):
    """
    Asynchronous notification service using Telegram.

    This class implements the `AbstractNotification` interface by sending
    notifications to a specified Telegram chat using the Telegram Bot API.

    Attributes:
        - bot: The Telegram Bot instance.
        - chat_id: The ID of the chat where notifications will be sent.

    Methods:
        - send_notification: Sends a notification through Telegram.
    """

    def __init__(self, bot_token: str, chat_id: str) -> None:
        """
        Initialize the TelegramNotificationAdapter.

        Args:
            - bot_token: The token for the Telegram bot.
            - chat_id: The ID of the chat where notifications will be sent.
        """
        self.bot_token = bot_token
        self.chat_id = chat_id

    async def send_notification(self, text: str) -> Message:
        """
        Send a notification through Telegram.

        Args:
            - text: The text content of the notification.

        Returns:
            - Message: If successful, the sent message is returned.

        Raises:
            - TelegramError: If an error occurs while sending the notification.
        """
        try:
            async with Bot(token=self.bot_token) as bot:
                message = await bot.send_message(chat_id=self.chat_id, text=text)
            await log.adebug("Telegram notification sent.")
        except TelegramError:
            await log.aexception("Failed to send Telegram notification.")
            raise
        else:
            return message
