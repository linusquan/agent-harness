# Email Agent Session Resume

Session management for email processing workflows that require manual intervention (e.g., PR approval).

## Design

```
┌───────┐      ┌───────────────┐      ┌─────────────────┐
│ email │─────▶│ agent process │─────▶│ Github PR       │
└───────┘      └───────────────┘      │ approval (fake) │
                                      └────────┬────────┘
                                               │ resume
                                               ▼
                                      ┌──────────────────┐      ┌────────────────────┐
                                      │ continue session │─────▶│ send completion    │
                                      └──────────────────┘      └────────────────────┘
```

## How It Works

### Initial Run (Fresh Start)
- Uses **same prompt** as `email_agent.py`
- Agent downloads email, processes request, may invoke skills
- If skill creates a PR, agent exits naturally (no special pause mechanism)
- Session state is saved automatically via Claude SDK `session_id`

### Resume Run
- Loads the Claude SDK session (preserves full conversation history)
- Injects a **fake message**: "PR approved and deployed successfully"
- Agent continues from where it left off
- Final steps: `reply_to_sender` (if needed) + `send_completion_report`

## Usage

### Start New Session

```bash
python email_agent_resume.py <email_id>
```

Works exactly like `email_agent.py` but tracks the session ID.

**Example:**
```bash
$ python email_agent_resume.py 32565

Starting new session for email: 32565
[INFO] Created new session email_32565_20250202_143022
[INFO] Downloading email...
[INFO] Invoking skill: scgc-document-publish
[INFO] PR created: https://github.com/SCGC/scgc-data/pull/45
[Agent exits after skill completes]

SUMMARY:
============================================================
I've downloaded the document and created a PR to publish it
to the website. The PR is at:
https://github.com/SCGC/scgc-data/pull/45

Please review and merge the PR.
============================================================

📋 Session ID: email_32565_20250202_143022
To resume: python email_agent_resume.py resume email_32565_20250202_143022
```

### List Sessions

```bash
python email_agent_resume.py list
```

Shows all tracked sessions with their status.

### Resume After PR Merged

```bash
python email_agent_resume.py resume <session_id>
```

Injects default message: "The GitHub PR has been approved and merged. The deployment was successful. All changes are now live."

**With custom message:**
```bash
python email_agent_resume.py resume <session_id> "PR merged and service restarted successfully"
```

**Example:**
```bash
$ python email_agent_resume.py resume email_32565_20250202_143022

Resuming session: email_32565_20250202_143022
  Email ID: 32565
  Status: running

[INFO] Resuming session email_32565_20250202_143022
[INFO] Injecting context: PR approved and deployed...
[INFO] Sending reply to original sender...
[INFO] Sending completion report...

RESULT:
============================================================
The document has been successfully published to the website.
I've notified the sender and sent a completion report to
the webmaster.
============================================================
```

## File Structure

```
email_agent_resume.py      - Main script with resume capability
email_session.py           - Session state management
.email_sessions/           - Local session tracking (JSON files)
                            (Claude SDK sessions stored separately)
```

## Key Differences from Original Design

| Aspect | Original Design | Updated Design |
|--------|----------------|----------------|
| Initial prompt | Custom for resumable workflow | **Same as email_agent.py** |
| Pause mechanism | Special `pause_for_pr_approval` tool | **Agent exits naturally** |
| Resume method | Explicit pause/resume states | **Inject fake message** |
| Complexity | Higher (custom pause logic) | **Lower (leverage SDK sessions)** |

## Session State

Local `.email_sessions/<session_id>.json`:
```json
{
  "session_id": "email_32565_20250202_143022",
  "email_id": "32565",
  "status": "running",  // or "completed", "failed"
  "created_at": "2025-02-02T14:30:22",
  "updated_at": "2025-02-02T14:35:10",
  "email_folder_path": "./downloads/32565",
  "context": {}
}
```

Claude SDK manages the full conversation history separately.

## Benefits

1. **Simple**: No custom pause logic, agent works naturally
2. **Flexible**: Can inject any context message when resuming
3. **Compatible**: Works exactly like `email_agent.py` for initial run
4. **Persistent**: Full conversation history preserved in Claude SDK sessions
5. **Traceable**: Local session tracking for monitoring

## Example Workflow

1. **Email arrives** → secretary@gliding.com.au sends document
2. **Agent processes** → `python email_agent_resume.py 32565`
   - Downloads email
   - Invokes `scgc-document-publish` skill
   - Skill creates PR
   - Agent exits
3. **Manual review** → You review PR on GitHub
4. **PR merged** → You merge the PR
5. **Resume agent** → `python email_agent_resume.py resume email_32565_20250202_143022`
   - Fake message: "PR approved and deployed"
   - Agent sends reply to sender
   - Agent sends completion report to webmaster
   - Done!

## Future Enhancements

- Auto-detect session ID from most recent run for easier resume
- GitHub webhook to auto-resume on PR merge
- Web UI for session monitoring
- Session archival and cleanup
