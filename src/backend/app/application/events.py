# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

from dataclasses import dataclass

from backend.app.application.ports import Event

# ==================================== #
#               Commands               #
# ==================================== #


@dataclass(frozen=True)
class UpdateFinancialInstruments(Event):
    pass


# ======================================== #
#               Notifications              #
# ======================================== #


@dataclass(frozen=True)
class Notification(Event):
    """
    A domain event representing a notification.

    Attributes:
        - text: The text content of the notification.
    """

    text: str = "Pepega"
