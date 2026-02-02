"""
IMAP/SMTP email utilities with SOLID principles.

This module provides:
- GmailClient: EmailFetcher implementation for Gmail
- SmtpSender: EmailSender implementation
- Convenience functions for backwards compatibility
"""
from contextlib import contextmanager
from imapclient import IMAPClient
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from email_config import EmailConfig
from email_protocols import EmailFetcher, EmailSender, EmailMessage, DownloadResult
from email_parser import decode_mime_header, get_email_body, extract_attachments, parse_email
from email_storage import LocalFileStorage


class GmailClient(EmailFetcher):
    """Gmail-specific IMAP client implementation."""

    def __init__(self, config: EmailConfig = None):
        self.config = config or EmailConfig.gmail()
        self._client: IMAPClient | None = None

    @contextmanager
    def connection(self):
        """Context manager for IMAP connection."""
        client = IMAPClient(self.config.imap_server, port=self.config.imap_port, ssl=True)
        client.login(self.config.email_account, self.config.password)
        try:
            yield client
        finally:
            client.logout()

    def fetch_unread(self, from_addresses: list[str]) -> list[dict]:
        """Fetch unread emails from Primary category sent by specified addresses."""
        results = []

        with self.connection() as client:
            client.select_folder("INBOX")

            for from_addr in from_addresses:
                query = f"category:primary is:unread from:{from_addr}"
                message_ids = client.gmail_search(query)

                if not message_ids:
                    continue

                response = client.fetch(message_ids, ["RFC822"])

                for msg_id, data in response.items():
                    email_msg = parse_email(data[b"RFC822"], str(msg_id), imap_uid=msg_id)
                    results.append({
                        "email_id": msg_id,
                        "subject": email_msg.subject,
                        "content": email_msg.content,
                        "attachments": email_msg.attachments,
                    })

        return results

    def fetch_raw(self, email_id: str) -> tuple[bytes, dict]:
        """Fetch raw email bytes and metadata by ID."""
        with self.connection() as client:
            client.select_folder("INBOX")
            imap_uid = self._resolve_email_id(client, email_id)

            response = client.fetch([imap_uid], ["RFC822", "X-GM-MSGID"])
            if imap_uid not in response:
                raise ValueError(f"Email with ID '{email_id}' not found in fetch")

            raw_bytes = response[imap_uid][b"RFC822"]
            gmail_msgid = response[imap_uid].get(b"X-GM-MSGID", email_id)

            return raw_bytes, {"imap_uid": imap_uid, "gmail_msgid": gmail_msgid}

    def _resolve_email_id(self, client: IMAPClient, email_id: str) -> int:
        """Resolve email_id to IMAP UID."""
        if str(email_id).isdigit():
            return int(email_id)

        # Try Gmail message ID search
        query = f"rfc822msgid:{email_id}"
        message_ids = client.gmail_search(query)

        if not message_ids:
            query = f"in:anywhere {email_id}"
            message_ids = client.gmail_search(query)

        if not message_ids:
            raise ValueError(f"Email with ID '{email_id}' not found")

        return message_ids[0]


class SmtpSender(EmailSender):
    """SMTP email sender implementation."""

    def __init__(self, config: EmailConfig = None):
        self.config = config or EmailConfig.gmail()

    def send(self, to: str, subject: str, body: str, reply_to_msgid: str = None, html: str = None) -> dict:
        """Send email via SMTP."""
        try:
            if not self.config.password:
                raise ValueError("Password not found in configuration")

            msg = MIMEMultipart("alternative")
            msg["From"] = self.config.email_account
            msg["To"] = to
            msg["Subject"] = subject

            if reply_to_msgid:
                msg["In-Reply-To"] = reply_to_msgid
                msg["References"] = reply_to_msgid

            msg.attach(MIMEText(body, "plain"))
            if html:
                msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.email_account, self.config.password)
                server.send_message(msg)

            return {
                "success": True,
                "message_id": msg["Message-ID"],
                "to": to,
                "subject": subject,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "to": to,
                "subject": subject,
            }


class EmailService:
    """High-level email service composing fetcher, sender, and storage."""

    def __init__(
        self,
        fetcher: EmailFetcher = None,
        sender: EmailSender = None,
        storage: LocalFileStorage = None,
        config: EmailConfig = None,
    ):
        config = config or EmailConfig.gmail()
        self.fetcher = fetcher or GmailClient(config)
        self.sender = sender or SmtpSender(config)
        self.storage = storage or LocalFileStorage()

    def fetch_unread_emails(self, from_addresses: list[str]) -> list[dict]:
        """Fetch unread emails from specified addresses."""
        return self.fetcher.fetch_unread(from_addresses)

    def download_email(self, email_id: str, base_path: str = "./downloads") -> dict:
        """Download email and save to storage."""
        # Update storage path if different
        if base_path != self.storage.base_path:
            self.storage = LocalFileStorage(base_path)

        raw_bytes, metadata = self.fetcher.fetch_raw(email_id)
        email_msg = parse_email(
            raw_bytes,
            email_id,
            imap_uid=metadata["imap_uid"],
            gmail_msgid=metadata["gmail_msgid"],
        )
        attachments = extract_attachments(email_msg.raw_msg)

        result = self.storage.save(email_msg, attachments)

        return {
            "email_id": result.email_id,
            "gmail_msgid": result.gmail_msgid,
            "imap_uid": result.imap_uid,
            "folder_path": result.folder_path,
            "subject": result.subject,
            "content": result.content,
            "downloaded_files": result.downloaded_files,
        }

    def send_email(self, to: str, subject: str, body: str, reply_to_msgid: str = None, html: str = None) -> dict:
        """Send an email."""
        return self.sender.send(to, subject, body, reply_to_msgid, html)


# === Backwards-compatible module-level functions ===

_default_service: EmailService | None = None


def _get_service() -> EmailService:
    """Get or create default email service."""
    global _default_service
    if _default_service is None:
        _default_service = EmailService()
    return _default_service


def fetch_unread_emails(from_addresses: list[str]) -> list[dict]:
    """Fetch unread emails from Primary category sent by specified addresses."""
    return _get_service().fetch_unread_emails(from_addresses)


def download_email(email_id: str, base_path: str = "./downloads") -> dict:
    """Download an email by Gmail message ID or IMAP UID."""
    return _get_service().download_email(email_id, base_path)


def send_email(to: str, subject: str, body: str, reply_to_msgid: str = None, html: str = None) -> dict:
    """Send email via Gmail SMTP."""
    return _get_service().send_email(to, subject, body, reply_to_msgid, html)


def fetch_email_with_attachments(email_id: int, download_path: str = None) -> dict:
    """Fetch a specific email by ID and optionally download all attachments."""
    service = _get_service()
    raw_bytes, metadata = service.fetcher.fetch_raw(str(email_id))
    email_msg = parse_email(raw_bytes, str(email_id), imap_uid=metadata["imap_uid"])
    attachments = extract_attachments(email_msg.raw_msg)

    downloaded_files = []
    if download_path:
        storage = LocalFileStorage(download_path)
        result = storage.save(email_msg, attachments)
        downloaded_files = result.downloaded_files

    return {
        "email_id": email_id,
        "subject": email_msg.subject,
        "content": email_msg.content,
        "attachments": email_msg.attachments,
        "downloaded_files": downloaded_files,
    }


if __name__ == "__main__":
    # Test use case: fetch_unread_emails -> download_email chain
    test_addresses = ["secretary@gliding.com.au", "liquan1992@outlook.com"]

    print("Step 1: Fetching unread emails...")
    print("=" * 60)

    emails = fetch_unread_emails(test_addresses)
    print(f"Found {len(emails)} unread email(s)\n")

    for i, email_data in enumerate(emails, 1):
        print(f"  [{i}] IMAP UID: {email_data['email_id']}")
        print(f"      Subject: {email_data['subject']}")
        print(f"      Attachments: {email_data['attachments'] or 'None'}")
        print()

    if emails:
        print("=" * 60)
        print("Step 2: Downloading first email using IMAP UID...")
        print("=" * 60)

        imap_uid = emails[0]["email_id"]
        print(f"\nDownloading email with IMAP UID: {imap_uid}")

        try:
            result = download_email(str(imap_uid), base_path="./downloads")
            print(f"  Subject: {result['subject']}")
            print(f"  Folder: {result['folder_path']}")
            print(f"  Gmail MSG ID: {result['gmail_msgid']}")
            print(f"  IMAP UID: {result['imap_uid']}")
            print(f"  Downloaded files:")
            for f in result["downloaded_files"]:
                print(f"    - {f}")
        except Exception as e:
            print(f"  ERROR: {e}")
    else:
        print("No unread emails found to download.")

    print("\n" + "=" * 60)
    print("Done!")
