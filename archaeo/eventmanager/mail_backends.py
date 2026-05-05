import base64
import json
import os

from django.core.mail.backends.base import BaseEmailBackend

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build


class GmailAPIMailBackend(BaseEmailBackend):
    scope = "https://www.googleapis.com/auth/gmail.send"

    def _load_service_account_info(self):
        encoded_json = os.environ.get("GMAIL_SERVICE_ACCOUNT_JSON_B64", "")
        raw_json = os.environ.get("GMAIL_SERVICE_ACCOUNT_JSON", "")

        if encoded_json:
            return json.loads(base64.b64decode(encoded_json).decode("utf-8"))

        if raw_json:
            return json.loads(raw_json)

        return None

    def open(self):
        if self.connection is not None:
            return False

        service_account_info = self._load_service_account_info()
        delegated_user_email = os.environ.get("GMAIL_DELEGATED_USER_EMAIL", "mit.rex.events@gmail.com")

        if not service_account_info:
            if self.fail_silently:
                return False
            raise ValueError("Gmail API credentials are not configured")

        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=[self.scope],
        ).with_subject(delegated_user_email)

        credentials.refresh(Request())

        self.connection = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        self.user_email = delegated_user_email
        return True

    def close(self):
        self.connection = None

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        if self.connection is None:
            self.open()

        if self.connection is None:
            return 0

        sent_count = 0
        for email_message in email_messages:
            message = email_message.message()
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            payload = {"raw": raw_message}

            try:
                self.connection.users().messages().send(userId="me", body=payload).execute()
            except Exception:
                if not self.fail_silently:
                    raise
            else:
                sent_count += 1

        return sent_count