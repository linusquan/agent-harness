"""Email parsing utilities."""
import email
from email.message import Message
from email.header import decode_header
from email_protocols import EmailMessage, Attachment


def decode_mime_header(header_value: str | None) -> str:
    """Decode MIME encoded header value."""
    if header_value is None:
        return ""
    decoded_parts = decode_header(header_value)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)


def get_email_body(msg: Message) -> str:
    """Extract the text body from an email message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            if "attachment" in content_disposition:
                continue

            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
                    break
            elif content_type == "text/html" and not body:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            body = payload.decode(charset, errors="replace")
    return body


def extract_attachments(msg: Message) -> list[Attachment]:
    """Extract attachments from an email message."""
    attachments = []
    if msg.is_multipart():
        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in content_disposition:
                filename = part.get_filename()
                if filename:
                    filename = decode_mime_header(filename)
                    payload = part.get_payload(decode=True)
                    if payload:
                        attachments.append(Attachment(
                            filename=filename,
                            content_type=part.get_content_type(),
                            payload=payload,
                        ))
    return attachments


def parse_email(raw_bytes: bytes, email_id: str, imap_uid: int = None, gmail_msgid: str = None) -> EmailMessage:
    """Parse raw email bytes into EmailMessage."""
    msg = email.message_from_bytes(raw_bytes)

    subject = decode_mime_header(msg.get("Subject", ""))
    from_addr = decode_mime_header(msg.get("From", ""))
    date = decode_mime_header(msg.get("Date", ""))
    message_id = msg.get("Message-ID", "").replace("\n", "").replace("\r", "").strip()
    content = get_email_body(msg)
    attachment_names = [a.filename for a in extract_attachments(msg)]

    email_msg = EmailMessage(
        email_id=email_id,
        subject=subject,
        content=content,
        from_addr=from_addr,
        date=date,
        message_id=message_id,
        attachments=attachment_names,
        raw_msg=msg,
    )
    # Store additional metadata as attributes
    email_msg.imap_uid = imap_uid
    email_msg.gmail_msgid = gmail_msgid

    return email_msg
