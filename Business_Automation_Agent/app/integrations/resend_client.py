import logging
from typing import Any

import resend

from app.core.config import settings

logger = logging.getLogger(__name__)


class ResendClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        from_email: str | None = None,
    ) -> None:
        self.api_key = api_key or settings.RESEND_API_KEY
        self.from_email = from_email or settings.RESEND_FROM_EMAIL
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        if not self.api_key:
            raise ValueError("RESEND_API_KEY is not configured")
        if not self.from_email:
            raise ValueError("RESEND_FROM_EMAIL is not configured")

        resend.api_key = self.api_key

    def send_email(
        self,
        *,
        to: str,
        subject: str,
        html: str,
    ) -> dict[str, Any]:
        self._validate_configuration()

        response = resend.Emails.send(
            {
                "from": self.from_email,
                "to": [to],
                "subject": subject,
                "html": html,
            }
        )

        if not isinstance(response, dict) or not response.get("id"):
            raise RuntimeError(f"Unexpected Resend response: {response}")

        logger.info("Email sent via Resend with id %s", response["id"])
        return response


def get_resend_client() -> ResendClient:
    return ResendClient()
