"""Email configuration module with provider support."""
from dataclasses import dataclass
import os
from dotenv import load_dotenv


@dataclass
class EmailConfig:
    """Configuration for email client connections."""
    imap_server: str
    imap_port: int
    smtp_server: str
    smtp_port: int
    email_account: str
    password: str

    @classmethod
    def gmail(cls, email_account: str = None, password: str = None) -> "EmailConfig":
        """Create Gmail configuration."""
        load_dotenv()
        return cls(
            imap_server="imap.gmail.com",
            imap_port=993,
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            email_account=email_account or "webmaster@gliding.com.au",
            password=password or os.getenv("APP_PASS"),
        )

    @classmethod
    def outlook(cls, email_account: str, password: str = None) -> "EmailConfig":
        """Create Outlook configuration."""
        load_dotenv()
        return cls(
            imap_server="outlook.office365.com",
            imap_port=993,
            smtp_server="smtp.office365.com",
            smtp_port=587,
            email_account=email_account,
            password=password or os.getenv("OUTLOOK_PASS"),
        )

    @classmethod
    def from_env(cls, provider: str = "gmail") -> "EmailConfig":
        """Factory method to create config from environment variables."""
        load_dotenv()
        if provider == "gmail":
            return cls.gmail()
        elif provider == "outlook":
            return cls.outlook(os.getenv("OUTLOOK_EMAIL"))
        else:
            raise ValueError(f"Unknown provider: {provider}")
