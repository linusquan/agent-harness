"""Protocol definitions for email operations (Dependency Inversion)."""
from typing import Protocol, runtime_checkable
from dataclasses import dataclass


@dataclass
class EmailMessage:
    """Parsed email message."""
    email_id: str
    subject: str
    content: str
    from_addr: str
    date: str
    message_id: str
    attachments: list[str]
    raw_msg: object = None  # Original email.message.Message


@dataclass
class Attachment:
    """Email attachment."""
    filename: str
    content_type: str
    payload: bytes


@dataclass
class DownloadResult:
    """Result of downloading an email."""
    email_id: str
    gmail_msgid: str | None
    imap_uid: int
    folder_path: str
    subject: str
    content: str
    downloaded_files: list[str]


@runtime_checkable
class EmailFetcher(Protocol):
    """Protocol for fetching emails from a server."""

    def fetch_unread(self, from_addresses: list[str]) -> list[dict]:
        """Fetch unread emails from specified addresses."""
        ...

    def fetch_raw(self, email_id: str) -> tuple[bytes, dict]:
        """Fetch raw email bytes and metadata by ID. Returns (raw_bytes, metadata)."""
        ...


@runtime_checkable
class EmailSender(Protocol):
    """Protocol for sending emails."""

    def send(self, to: str, subject: str, body: str, reply_to_msgid: str = None, html: str = None) -> dict:
        """Send an email."""
        ...


@runtime_checkable
class EmailStorage(Protocol):
    """Protocol for storing downloaded emails."""

    def save(self, email: EmailMessage, attachments: list[Attachment]) -> DownloadResult:
        """Save email and attachments to storage. Returns download result."""
        ...
