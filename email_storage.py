"""Email storage implementations."""
import os
from email_protocols import EmailMessage, Attachment, DownloadResult


class LocalFileStorage:
    """Store emails and attachments to local filesystem."""

    def __init__(self, base_path: str = "./downloads"):
        self.base_path = base_path

    def save(self, email: EmailMessage, attachments: list[Attachment]) -> DownloadResult:
        """Save email content and attachments to a folder."""
        folder_path = os.path.join(self.base_path, str(email.email_id))
        os.makedirs(folder_path, exist_ok=True)

        downloaded_files = []

        # Write email.txt
        email_txt_path = self._write_email_txt(email, folder_path)
        downloaded_files.append(email_txt_path)

        # Save attachments
        if attachments:
            attachment_files = self._save_attachments(attachments, folder_path)
            downloaded_files.extend(attachment_files)

        return DownloadResult(
            email_id=email.email_id,
            gmail_msgid=getattr(email, 'gmail_msgid', None),
            imap_uid=getattr(email, 'imap_uid', 0),
            folder_path=folder_path,
            subject=email.subject,
            content=email.content,
            downloaded_files=downloaded_files,
        )

    def _write_email_txt(self, email: EmailMessage, folder_path: str) -> str:
        """Write email metadata and content to email.txt."""
        email_txt_path = os.path.join(folder_path, "email.txt")
        with open(email_txt_path, "w", encoding="utf-8") as f:
            f.write(f"Subject: {email.subject}\n")
            f.write(f"From: {email.from_addr}\n")
            f.write(f"Date: {email.date}\n")
            f.write(f"Message-ID: {email.message_id}\n")
            f.write(f"IMAP UID: {getattr(email, 'imap_uid', 'N/A')}\n")
            f.write(f"\n{'='*60}\n\n")
            f.write(email.content)
        return email_txt_path

    def _save_attachments(self, attachments: list[Attachment], folder_path: str) -> list[str]:
        """Save attachments to attachments/ subfolder."""
        attachments_folder = os.path.join(folder_path, "attachments")
        saved_files = []

        for attachment in attachments:
            os.makedirs(attachments_folder, exist_ok=True)
            filepath = os.path.join(attachments_folder, attachment.filename)
            filepath = self._deduplicate_filename(filepath)

            with open(filepath, "wb") as f:
                f.write(attachment.payload)
            saved_files.append(filepath)

        return saved_files

    def _deduplicate_filename(self, filepath: str) -> str:
        """Handle duplicate filenames by appending counter."""
        if not os.path.exists(filepath):
            return filepath

        base, ext = os.path.splitext(filepath)
        counter = 1
        while os.path.exists(filepath):
            filepath = f"{base}_{counter}{ext}"
            counter += 1
        return filepath
