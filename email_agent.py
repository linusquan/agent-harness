"""
Email Processing Agent - Downloads and summarizes emails using Claude Agent SDK.

Usage: python email_agent.py <email_id>
"""
import asyncio
import logging
import os
from typing import Any
from dotenv import load_dotenv
import sys


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("agent.hooks")
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    tool,
    create_sdk_mcp_server,
    AssistantMessage,
    TextBlock,
    HookMatcher,
)
from imap_util import download_email as imap_download_email, send_email

DOWNLOADS_DIR = os.path.abspath("./downloads")


async def log_pre_tool_use(input_data, tool_use_id, context):
    """Log all PreToolUse events."""
    tool_name = input_data.get("tool_name", "unknown")
    tool_input = input_data.get("tool_input", {})
    logger.info(f"[PRE]  {tool_name} | id={tool_use_id} | input={tool_input}")
    return {}


async def log_post_tool_use(input_data, tool_use_id, context):
    """Log all PostToolUse events."""
    tool_name = input_data.get("tool_name", "unknown")
    response = input_data.get("tool_response", "")
    response_str = str(response)[:200] + "..." if len(str(response)) > 200 else str(response)
    logger.info(f"[POST] {tool_name} | id={tool_use_id} | response={response_str}")
    return {}


async def restrict_read_to_downloads(input_data, tool_use_id, context):
    """PreToolUse hook: deny Read if file_path is outside downloads folder."""
    file_path = os.path.abspath(input_data["tool_input"].get("file_path", ""))
    if not file_path.startswith(DOWNLOADS_DIR):
        logger.warning(f"[DENY] Read blocked: {file_path} outside {DOWNLOADS_DIR}")
        return {
            "hookSpecificOutput": {
                "hookEventName": input_data["hook_event_name"],
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Read restricted to {DOWNLOADS_DIR}"
            }
        }
    logger.info(f"[ALLOW] Read permitted: {file_path}")
    return {}


@tool(
    "download_email",
    "Download an email by IMAP UID. Creates folder with email.txt (containing subject/content) and attachments/ subfolder. Returns the folder path - use Read tool to view the content.",
    {"email_id": str}
)
async def download_email_tool(args: dict[str, Any]) -> dict[str, Any]:
    """Wrapper for imap_util.download_email as an MCP tool."""
    try:
        result = imap_download_email(args["email_id"], "./downloads")
        return {
            "content": [{
                "type": "text",
                "text": f"""Downloaded email to: {result['folder_path']}
Files: {', '.join(result['downloaded_files'])}

Use Read tool to view {result['folder_path']}/email.txt for the email content."""
            }]
        }
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {e}"}], "is_error": True}


def _parse_email_txt(email_folder_path: str) -> dict:
    """Parse email.txt to extract sender address, message ID, and body."""
    email_txt_path = os.path.join(email_folder_path, "email.txt")
    result = {"from": None, "from_full": None, "subject": None, "message_id": None, "date": None, "body": None}

    with open(email_txt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    in_body = False
    body_lines = []

    for line in lines:
        if in_body:
            body_lines.append(line.rstrip())
        elif line.startswith("From: "):
            from_value = line[6:].strip()
            result["from_full"] = from_value
            # Extract email address from "Name <email>" format
            if '<' in from_value and '>' in from_value:
                result["from"] = from_value.split('<')[1].split('>')[0]
            else:
                result["from"] = from_value
        elif line.startswith("Subject: "):
            result["subject"] = line[9:].strip()
        elif line.startswith("Date: "):
            result["date"] = line[6:].strip()
        elif line.startswith("Message-ID: "):
            result["message_id"] = line[12:].strip()
        elif line.startswith("="*10):
            in_body = True

    result["body"] = "\n".join(body_lines).strip()
    return result


def _format_reply_body_html(new_text: str, email_info: dict) -> str:
    """Format reply body as HTML with blockquote for original message."""
    import html
    original_body = email_info.get("body", "")
    # Escape HTML and convert newlines to <br>
    escaped_body = html.escape(original_body).replace("\n", "<br>\n")
    escaped_new_text = html.escape(new_text).replace("\n", "<br>\n")

    date = email_info.get("date", "")
    from_full = html.escape(email_info.get("from_full", email_info.get("from", "")))

    return f"""<div>{escaped_new_text}</div>
<br>
<div>On {date}, {from_full} wrote:</div>
<blockquote style="margin:0px 0px 0px 0.8ex; border-left:1px solid rgb(204,204,204); padding-left:1ex">
{escaped_body}
</blockquote>
"""


@tool(
    "reply_to_sender",
    "Reply to the original email sender when a request needs clarification or cannot be processed. Use when: unclear instructions, missing attachments, request outside scope.",
    {"email_folder_path": str, "subject": str, "body": str}
)
async def reply_to_sender_tool(args: dict[str, Any]) -> dict[str, Any]:
    """Send a reply to the original email sender."""
    try:
        email_info = _parse_email_txt(args["email_folder_path"])

        if not email_info["from"]:
            return {"content": [{"type": "text", "text": "Error: Could not extract sender address from email.txt"}], "is_error": True}

        subject = args["subject"]
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        # Format reply with quoted original as HTML
        html_body = _format_reply_body_html(args["body"], email_info)

        result = send_email(
            to=email_info["from"],
            subject=subject,
            body=args["body"],  # Plain text fallback
            reply_to_msgid=email_info.get("message_id"),
            html=html_body
        )

        if result["success"]:
            return {"content": [{"type": "text", "text": f"Reply sent to {result['to']}: {result['subject']}"}]}
        else:
            return {"content": [{"type": "text", "text": f"Failed to send reply: {result['error']}"}], "is_error": True}

    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {e}"}], "is_error": True}


@tool(
    "send_completion_report",
    "Send job completion report to webmaster. MUST be called at the end of every email processing task.",
    {"email_folder_path": str, "summary": str, "actions_taken": str, "success": bool}
)
async def send_completion_report_tool(args: dict[str, Any]) -> dict[str, Any]:
    """Send a completion report to the webmaster."""
    try:
        email_info = _parse_email_txt(args["email_folder_path"])
        original_subject = email_info.get("subject", "Unknown")
        original_sender = email_info.get("from", "Unknown")

        status = "SUCCESS" if args["success"] else "FAILED"
        subject = f"[Email Agent Report] {status}: {original_subject}"

        body = f"""Email Processing Report
{'='*50}

Original Email:
  From: {original_sender}
  Subject: {original_subject}

Status: {status}

Summary:
{args['summary']}

Actions Taken:
{args['actions_taken']}

{'='*50}
This is an automated report from the Email Processing Agent.
"""

        result = send_email(
            to="webmaster@gliding.com.au",
            subject=subject,
            body=body,
            reply_to_msgid=email_info.get("message_id")
        )

        if result["success"]:
            return {"content": [{"type": "text", "text": f"Completion report sent to webmaster@gliding.com.au"}]}
        else:
            return {"content": [{"type": "text", "text": f"Failed to send completion report: {result['error']}"}], "is_error": True}

    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {e}"}], "is_error": True}


async def process_email(email_id: str) -> str:
    """Download email and return agent's summary."""
    load_dotenv()
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise ValueError("ANTHROPIC_API_KEY not found")

    email_server = create_sdk_mcp_server(
        name="email_tools",
        version="1.0.0",
        tools=[download_email_tool, reply_to_sender_tool, send_completion_report_tool]
    )

    options = ClaudeAgentOptions(
        mcp_servers={"email_tools": email_server},
        setting_sources=["project"],  # Load skills from .claude/skills/
        allowed_tools=[
            "mcp__email_tools__download_email",
            "mcp__email_tools__reply_to_sender",
            "mcp__email_tools__send_completion_report",
            "Skill",  # Enable skills (add_documents, database_analysis, service_update)
            "Read", "Write", "Edit",  # File operations for skills
            "Glob", "Grep",  # Search tools
            "Bash",  # Shell commands
        ],
        hooks={
            "PreToolUse": [
                HookMatcher(hooks=[log_pre_tool_use]),  # Log all tools
            ],
            "PostToolUse": [
                HookMatcher(hooks=[log_post_tool_use])  # Log all results
            ]
        }
    )

    prompt = f"""Download email ID {email_id} using the download_email tool, the file will be within the ./download folder.
Then analyze what the email is requesting and use the appropriate skill to process it. Common requests include: 1) Upload document to the website appropriate section

IMPORTANT GUIDELINES:
- If the request is unclear, missing attachments, or outside scope, use reply_to_sender to ask for clarification or explain why you cannot process it.
- You MUST call send_completion_report at the end of processing, regardless of success or failure. Include a summary of what was requested and what actions you took."""

    result_text = ""
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        result_text = block.text  # Keep the last text block as final result

    return result_text


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python email_agent.py <email_id>")
        sys.exit(1)

    print(f"Processing email: ")
    result = asyncio.run(process_email(sys.argv[1]))
    # result = asyncio.run(process_email(32565))
    print("\n" + "="*60 + "\nSUMMARY:\n" + "="*60)
    print(result)
