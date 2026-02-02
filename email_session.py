"""
Session management for email agent processing.

Allows pausing and resuming email processing workflows, especially useful
when waiting for external actions like PR approvals.
"""
import json
import os
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional
from pathlib import Path


@dataclass
class SessionState:
    """State of an email processing session."""
    session_id: str
    email_id: str
    status: str  # "running", "waiting_for_pr", "waiting_for_user", "completed", "failed"
    created_at: str
    updated_at: str
    email_folder_path: str
    context: dict  # Stores additional context like PR URL, waiting reason, etc.

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SessionState":
        return cls(**data)


class SessionManager:
    """Manages email processing sessions for pause/resume functionality."""

    def __init__(self, sessions_dir: str = "./.email_sessions"):
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(exist_ok=True)

    def _get_session_file(self, session_id: str) -> Path:
        """Get the path to a session file."""
        return self.sessions_dir / f"{session_id}.json"

    def create_session(
        self,
        email_id: str,
        email_folder_path: str,
        session_id: str = None,
    ) -> SessionState:
        """Create a new session or resume existing one."""
        if session_id and self.session_exists(session_id):
            return self.load_session(session_id)

        session_id = session_id or self._generate_session_id(email_id)
        now = datetime.now().isoformat()

        state = SessionState(
            session_id=session_id,
            email_id=email_id,
            status="running",
            created_at=now,
            updated_at=now,
            email_folder_path=email_folder_path,
            context={},
        )

        self.save_session(state)
        return state

    def save_session(self, state: SessionState) -> None:
        """Persist session state to disk."""
        state.updated_at = datetime.now().isoformat()
        session_file = self._get_session_file(state.session_id)

        with open(session_file, "w") as f:
            json.dump(state.to_dict(), f, indent=2)

    def load_session(self, session_id: str) -> SessionState:
        """Load session state from disk."""
        session_file = self._get_session_file(session_id)

        if not session_file.exists():
            raise ValueError(f"Session {session_id} not found")

        with open(session_file, "r") as f:
            data = json.load(f)

        return SessionState.from_dict(data)

    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        return self._get_session_file(session_id).exists()

    def list_sessions(self, status: str = None) -> list[SessionState]:
        """List all sessions, optionally filtered by status."""
        sessions = []

        for session_file in self.sessions_dir.glob("*.json"):
            with open(session_file, "r") as f:
                data = json.load(f)
                state = SessionState.from_dict(data)

                if status is None or state.status == status:
                    sessions.append(state)

        # Sort by updated_at descending
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    def update_status(
        self,
        session_id: str,
        status: str,
        context_update: dict = None,
    ) -> SessionState:
        """Update session status and context."""
        state = self.load_session(session_id)
        state.status = status

        if context_update:
            state.context.update(context_update)

        self.save_session(state)
        return state

    def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        session_file = self._get_session_file(session_id)
        if session_file.exists():
            session_file.unlink()

    def _generate_session_id(self, email_id: str) -> str:
        """Generate a unique session ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"email_{email_id}_{timestamp}"


class SessionContext:
    """Context manager for email processing sessions."""

    def __init__(self, email_id: str, session_id: str = None, manager: SessionManager = None):
        self.email_id = email_id
        self.session_id = session_id
        self.manager = manager or SessionManager()
        self.state: Optional[SessionState] = None

    def __enter__(self) -> SessionState:
        """Start or resume a session."""
        # Email folder path will be set after download
        email_folder_path = f"./downloads/{self.email_id}"
        self.state = self.manager.create_session(
            self.email_id,
            email_folder_path,
            self.session_id,
        )
        return self.state

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Save session on exit."""
        if self.state:
            if exc_type is not None:
                self.state.status = "failed"
                self.state.context["error"] = str(exc_val)
            elif self.state.status == "running":
                self.state.status = "completed"

            self.manager.save_session(self.state)


# === CLI Helper Functions ===

def list_pending_sessions() -> list[SessionState]:
    """List all sessions waiting for action."""
    manager = SessionManager()
    return manager.list_sessions(status="waiting_for_pr")


def print_sessions_table(sessions: list[SessionState]) -> None:
    """Print sessions in a formatted table."""
    if not sessions:
        print("No sessions found.")
        return

    print(f"\n{'Session ID':<30} {'Email ID':<15} {'Status':<20} {'Updated':<20}")
    print("-" * 90)

    for session in sessions:
        updated = session.updated_at[:19].replace("T", " ")  # Trim to datetime
        print(f"{session.session_id:<30} {session.email_id:<15} {session.status:<20} {updated:<20}")

        # Print context if waiting
        if session.status.startswith("waiting") and session.context:
            for key, value in session.context.items():
                print(f"  {key}: {value}")

    print()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python email_session.py list              - List all sessions")
        print("  python email_session.py list waiting_for_pr  - List sessions by status")
        sys.exit(1)

    command = sys.argv[1]
    manager = SessionManager()

    if command == "list":
        status = sys.argv[2] if len(sys.argv) > 2 else None
        sessions = manager.list_sessions(status)
        print_sessions_table(sessions)
