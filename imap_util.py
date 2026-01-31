from imapclient import IMAPClient
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Gmail IMAP settings
IMAP_SERVER = 'imap.gmail.com'
IMAP_PORT = 993
EMAIL_ACCOUNT = 'webmaster@gliding.com.au'

# Gmail SMTP settings
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587


def decode_mime_header(header_value):
    """Decode MIME encoded header value."""
    if header_value is None:
        return ''
    decoded_parts = decode_header(header_value)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or 'utf-8', errors='replace'))
        else:
            result.append(part)
    return ''.join(result)


def get_email_body(msg):
    """Extract the text body from an email message."""
    body = ''
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get('Content-Disposition', ''))

            # Skip attachments
            if 'attachment' in content_disposition:
                continue

            if content_type == 'text/plain':
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    body = payload.decode(charset, errors='replace')
                    break
            elif content_type == 'text/html' and not body:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    body = payload.decode(charset, errors='replace')
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or 'utf-8'
            body = payload.decode(charset, errors='replace')
    return body


def get_attachments(msg):
    """Extract attachment filenames from an email message."""
    attachments = []
    if msg.is_multipart():
        for part in msg.walk():
            content_disposition = str(part.get('Content-Disposition', ''))
            if 'attachment' in content_disposition:
                filename = part.get_filename()
                if filename:
                    filename = decode_mime_header(filename)
                    attachments.append(filename)
    return attachments


def _get_imap_client():
    """Create and return an authenticated IMAP client."""
    password = os.getenv('APP_PASS')
    client = IMAPClient(IMAP_SERVER, port=IMAP_PORT, ssl=True)
    client.login(EMAIL_ACCOUNT, password)
    return client


def fetch_unread_emails(from_addresses: list[str]) -> list[dict]:
    """
    Fetch unread emails from Primary category sent by specified addresses.

    Args:
        from_addresses: List of email addresses to filter by

    Returns:
        List of dicts with keys: email_id, subject, content, attachments
    """
    results = []

    try:
        client = _get_imap_client()
        client.select_folder('INBOX')

        # Build search query for unread emails from specified addresses in Primary
        for from_addr in from_addresses:
            # Use Gmail search to find unread emails from this address in Primary
            query = f'category:primary is:unread from:{from_addr}'
            message_ids = client.gmail_search(query)

            if not message_ids:
                continue

            # Fetch full message data
            response = client.fetch(message_ids, ['RFC822'])

            for msg_id, data in response.items():
                raw_email = data[b'RFC822']
                msg = email.message_from_bytes(raw_email)

                subject = decode_mime_header(msg.get('Subject', ''))
                content = get_email_body(msg)
                attachments = get_attachments(msg)

                results.append({
                    'email_id': msg_id,
                    'subject': subject,
                    'content': content,
                    'attachments': attachments
                })

        client.logout()

    except Exception as e:
        print(f"Error fetching emails: {e}")
        raise

    return results


def download_email(email_id: str, base_path: str = './downloads') -> dict:
    """
    Download an email by Gmail message ID or IMAP UID.
    Creates a folder named with the email_id containing:
    - email.txt: Subject and content
    - All attachments

    Args:
        email_id: Gmail message ID (string like 'FMfcgzQfBZlQvzFxwDsgqLTnVHVXdgCT')
                  or IMAP UID (numeric string like '12345')
        base_path: Base directory for downloads

    Returns:
        Dict with keys: email_id, folder_path, subject, content, downloaded_files
    """
    try:
        client = _get_imap_client()
        client.select_folder('INBOX')

        # Determine the IMAP UID
        # If numeric, use directly as IMAP UID (most efficient)
        if str(email_id).isdigit():
            imap_uid = int(email_id)
        else:
            # Try to find by Gmail message ID using gmail_search
            query = f'rfc822msgid:{email_id}'
            message_ids = client.gmail_search(query)

            # If not found, try direct search in All Mail with the ID
            if not message_ids:
                query = f'in:anywhere {email_id}'
                message_ids = client.gmail_search(query)

            if not message_ids:
                raise ValueError(f"Email with ID '{email_id}' not found")

            imap_uid = message_ids[0]

        # Fetch the email
        response = client.fetch([imap_uid], ['RFC822', 'X-GM-MSGID'])

        if imap_uid not in response:
            raise ValueError(f"Email with ID '{email_id}' not found in fetch")

        raw_email = response[imap_uid][b'RFC822']
        gmail_msgid = response[imap_uid].get(b'X-GM-MSGID', email_id)
        msg = email.message_from_bytes(raw_email)

        subject = decode_mime_header(msg.get('Subject', ''))
        from_addr = decode_mime_header(msg.get('From', ''))
        date = decode_mime_header(msg.get('Date', ''))
        message_id = msg.get('Message-ID', '').replace('\n', '').replace('\r', '').strip()  # RFC822 Message-ID header
        content = get_email_body(msg)

        # Create folder for this email
        folder_path = os.path.join(base_path, str(email_id))
        os.makedirs(folder_path, exist_ok=True)

        # Write email.txt with subject and content
        email_txt_path = os.path.join(folder_path, 'email.txt')
        with open(email_txt_path, 'w', encoding='utf-8') as f:
            f.write(f"Subject: {subject}\n")
            f.write(f"From: {from_addr}\n")
            f.write(f"Date: {date}\n")
            f.write(f"Message-ID: {message_id}\n")
            f.write(f"IMAP UID: {imap_uid}\n")
            f.write(f"\n{'='*60}\n\n")
            f.write(content)

        downloaded_files = [email_txt_path]

        # Download attachments into attachments/ subfolder
        if msg.is_multipart():
            attachments_folder = os.path.join(folder_path, 'attachments')
            for part in msg.walk():
                content_disposition = str(part.get('Content-Disposition', ''))
                if 'attachment' in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        filename = decode_mime_header(filename)
                        os.makedirs(attachments_folder, exist_ok=True)
                        filepath = os.path.join(attachments_folder, filename)

                        # Handle duplicate filenames
                        base, ext = os.path.splitext(filepath)
                        counter = 1
                        while os.path.exists(filepath):
                            filepath = f"{base}_{counter}{ext}"
                            counter += 1

                        payload = part.get_payload(decode=True)
                        if payload:
                            with open(filepath, 'wb') as f:
                                f.write(payload)
                            downloaded_files.append(filepath)

        client.logout()

        return {
            'email_id': email_id,
            'gmail_msgid': gmail_msgid,
            'imap_uid': imap_uid,
            'folder_path': folder_path,
            'subject': subject,
            'content': content,
            'downloaded_files': downloaded_files
        }

    except Exception as e:
        print(f"Error downloading email {email_id}: {e}")
        raise


def fetch_email_with_attachments(email_id: int, download_path: str = None) -> dict:
    """
    Fetch a specific email by ID and optionally download all attachments.

    Args:
        email_id: The IMAP message ID
        download_path: Directory to save attachments. If None, attachments are not downloaded.

    Returns:
        Dict with keys: email_id, subject, content, attachments, downloaded_files
        - attachments: list of attachment filenames
        - downloaded_files: list of full paths to downloaded files (empty if download_path is None)
    """
    try:
        client = _get_imap_client()
        client.select_folder('INBOX')

        # Fetch the email
        response = client.fetch([email_id], ['RFC822'])

        if email_id not in response:
            raise ValueError(f"Email with ID {email_id} not found")

        raw_email = response[email_id][b'RFC822']
        msg = email.message_from_bytes(raw_email)

        subject = decode_mime_header(msg.get('Subject', ''))
        content = get_email_body(msg)
        attachments = []
        downloaded_files = []

        # Process attachments
        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = str(part.get('Content-Disposition', ''))
                if 'attachment' in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        filename = decode_mime_header(filename)
                        attachments.append(filename)

                        # Download if path is provided
                        if download_path:
                            os.makedirs(download_path, exist_ok=True)
                            filepath = os.path.join(download_path, filename)

                            # Handle duplicate filenames
                            base, ext = os.path.splitext(filepath)
                            counter = 1
                            while os.path.exists(filepath):
                                filepath = f"{base}_{counter}{ext}"
                                counter += 1

                            payload = part.get_payload(decode=True)
                            if payload:
                                with open(filepath, 'wb') as f:
                                    f.write(payload)
                                downloaded_files.append(filepath)

        client.logout()

        return {
            'email_id': email_id,
            'subject': subject,
            'content': content,
            'attachments': attachments,
            'downloaded_files': downloaded_files
        }

    except Exception as e:
        print(f"Error fetching email {email_id}: {e}")
        raise


def send_email(to: str, subject: str, body: str, reply_to_msgid: str = None, html: str = None) -> dict:
    """
    Send email via Gmail SMTP.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Plain text email body (fallback if html not provided)
        reply_to_msgid: Optional Message-ID to reply to (for threading)
        html: Optional HTML body content

    Returns:
        Dict with keys: success, message_id, error (if failed)
    """
    try:
        password = os.getenv('APP_PASS')
        if not password:
            raise ValueError("APP_PASS not found in environment")

        msg = MIMEMultipart('alternative')
        msg['From'] = EMAIL_ACCOUNT
        msg['To'] = to
        msg['Subject'] = subject

        if reply_to_msgid:
            msg['In-Reply-To'] = reply_to_msgid
            msg['References'] = reply_to_msgid

        # Attach plain text first, then HTML (email clients prefer last)
        msg.attach(MIMEText(body, 'plain'))
        if html:
            msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ACCOUNT, password)
            server.send_message(msg)

        return {
            'success': True,
            'message_id': msg['Message-ID'],
            'to': to,
            'subject': subject
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'to': to,
            'subject': subject
        }


if __name__ == '__main__':
    # Test use case: fetch_unread_emails -> download_email chain
    test_addresses = ['secretary@gliding.com.au', 'liquan1992@outlook.com']

    print("Step 1: Fetching unread emails...")
    print("="*60)

    emails = fetch_unread_emails(test_addresses)
    print(f"Found {len(emails)} unread email(s)\n")

    for i, email_data in enumerate(emails, 1):
        print(f"  [{i}] IMAP UID: {email_data['email_id']}")
        print(f"      Subject: {email_data['subject']}")
        print(f"      Attachments: {email_data['attachments'] or 'None'}")
        print()

    if emails:
        print("="*60)
        print("Step 2: Downloading first email using IMAP UID...")
        print("="*60)

        # Get the IMAP UID from the first email
        imap_uid = emails[0]['email_id']
        print(f"\nDownloading email with IMAP UID: {imap_uid}")

        try:
            result = download_email(str(imap_uid), base_path='./downloads')
            print(f"  Subject: {result['subject']}")
            print(f"  Folder: {result['folder_path']}")
            print(f"  Gmail MSG ID: {result['gmail_msgid']}")
            print(f"  IMAP UID: {result['imap_uid']}")
            print(f"  Downloaded files:")
            for f in result['downloaded_files']:
                print(f"    - {f}")
        except Exception as e:
            print(f"  ERROR: {e}")
    else:
        print("No unread emails found to download.")

    print("\n" + "="*60)
    print("Done!")
