"""
Email agent with session resume capability.

Leverages Claude SDK's built-in session management - no custom state tracking needed.

Usage:
  python email_agent_resume.py <email_id>              # Start fresh (same as email_agent.py)
  python email_agent_resume.py resume <session_id>     # Resume with fake PR approval message
"""
import asyncio
import logging
import os
from typing import Optional
from dotenv import load_dotenv
import sys

from email_agent import (
    EmailAgentConfig,
    download_email_tool,
    reply_to_sender_tool,
    send_completion_report_tool,
    log_pre_tool_use,
    log_post_tool_use,
    set_agent_config,
)

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    create_sdk_mcp_server,
    AssistantMessage,
    TextBlock,
    HookMatcher,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("email_agent_resume")


async def process_email_with_session(
    email_id: str,
    resume_session_id: Optional[str] = None,
    resume_context: Optional[str] = None,
    config: EmailAgentConfig = None,
) -> tuple[str, str]:
    """
    Process email with Claude SDK session persistence.

    Initial run: Works exactly like email_agent.py - starts fresh, SDK generates session_id
    Resume run: Continues session with injected context message

    Args:
        email_id: Email ID to process
        resume_session_id: Optional session ID to resume (SDK-generated from previous run)
        resume_context: Optional context to inject when resuming (e.g., "PR approved and deployed")
        config: Optional agent configuration

    Returns:
        Tuple of (result_text, session_id)
    """
    load_dotenv()
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise ValueError("ANTHROPIC_API_KEY not found")

    # Set up configuration
    if config:
        set_agent_config(config)

    # Create MCP server with same tools as original
    email_server = create_sdk_mcp_server(
        name="email_tools",
        version="1.0.0",
        tools=[
            download_email_tool,
            reply_to_sender_tool,
            send_completion_report_tool,
        ]
    )

    # Build prompt - SAME as original email_agent.py for initial run
    initial_prompt = f"""Download email ID {email_id} using the download_email tool, the file will be within the ./download folder.
Then analyze what the email is requesting and use the appropriate skill to process it. Common requests include: 1) Upload document to the website appropriate section

IMPORTANT GUIDELINES:
- If the request is unclear, missing attachments, or outside scope, use reply_to_sender to ask for clarification or explain why you cannot process it.
- You MUST call send_completion_report at the end of processing, regardless of success or failure. Include a summary of what was requested and what actions you took."""

    # Build options - use 'resume' parameter if resuming
    options_dict = {
        "mcp_servers": {"email_tools": email_server},
        "setting_sources": ["project"],
        "allowed_tools": [
            "mcp__email_tools__download_email",
            "mcp__email_tools__reply_to_sender",
            "mcp__email_tools__send_completion_report",
            "Skill",
            "Read", "Write", "Edit",
            "Glob", "Grep",
            "Bash",
        ],
        "hooks": {
            "PreToolUse": [
                HookMatcher(hooks=[log_pre_tool_use]),
            ],
            "PostToolUse": [
                HookMatcher(hooks=[log_post_tool_use])
            ]
        },
    }

    if resume_session_id:
        # Resuming existing session
        options_dict["resume"] = resume_session_id
        logger.info(f"Resuming session: {resume_session_id}")
    else:
        # New session - SDK will generate session_id
        logger.info("Starting new session")

    options = ClaudeAgentOptions(**options_dict)

    result_text = ""
    extracted_session_id = resume_session_id  # Will be updated from init message if new session

    async with ClaudeSDKClient(options=options) as client:
        if resume_context:
            # Resuming: SDK loads conversation history automatically
            # Just inject the new context as a follow-up message
            logger.info(f"Injecting resume context: {resume_context}")
            await client.query(resume_context)
        else:
            # Initial run: start fresh
            await client.query(initial_prompt)

        # Collect response and extract session_id from init message
        async for message in client.receive_response():
            # Extract session_id from init message (first message)
            if hasattr(message, 'subtype') and message.subtype == 'init':
                extracted_session_id = message.data.get('session_id')
                if extracted_session_id:
                    logger.info(f"Session ID from SDK: {extracted_session_id}")

            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        result_text = block.text

    return result_text, extracted_session_id


async def resume_session(session_id: str, email_id: str, context_message: str = None):
    """
    Resume a paused session.

    Args:
        session_id: The Claude SDK-generated session ID to resume
        email_id: The email ID being processed
        context_message: Custom message to inject (default: PR approved and deployed)
    """
    print(f"Resuming session: {session_id}")
    print(f"  Email ID: {email_id}")
    print()

    # Default message simulating PR approval and deployment
    if not context_message:
        context_message = "The GitHub PR has been approved and merged. The deployment was successful. All changes are now live."

    result, _ = await process_email_with_session(
        email_id,
        resume_session_id=session_id,
        resume_context=context_message,
    )

    print("\n" + "="*60 + "\nRESULT:\n" + "="*60)
    print(result)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python email_agent_resume.py <email_id>                      - Start new session (same as email_agent.py)")
        print("  python email_agent_resume.py resume <session_id> <email_id>  - Resume with default PR approval message")
        print("  python email_agent_resume.py resume <session_id> <email_id> 'msg' - Resume with custom message")
        print()
        print("Example:")
        print("  python email_agent_resume.py 32565")
        print("  python email_agent_resume.py resume a1b2c3d4e5f6 32565")
        print("  python email_agent_resume.py resume a1b2c3d4e5f6 32565 'PR merged successfully'")
        print()
        print("Note: Sessions are stored in .claude_sdk/sessions/ by the Claude SDK")
        sys.exit(1)

    command = sys.argv[1]

    if command == "resume":
        if len(sys.argv) < 4:
            print("Error: session_id and email_id required")
            print("Usage: python email_agent_resume.py resume <session_id> <email_id> ['custom message']")
            sys.exit(1)

        session_id = sys.argv[2]
        email_id = sys.argv[3]
        message = sys.argv[4] if len(sys.argv) > 4 else None
        asyncio.run(resume_session(session_id, email_id, message))

    else:
        # Treat first argument as email_id for new session
        email_id = sys.argv[1]
        print(f"Starting new session for email: {email_id}")
        result, session_id = asyncio.run(process_email_with_session(email_id))
        print("\n" + "="*60 + "\nSUMMARY:\n" + "="*60)
        print(result)
        print(f"\n📋 Session ID: {session_id}")
        print(f"📧 Email ID: {email_id}")
        print(f"\nTo resume: python email_agent_resume.py resume {session_id} {email_id}")
