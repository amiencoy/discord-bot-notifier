#!/usr/bin/env python3
"""MCP Server for Discord Bot Notifier - connects to n8n webhook for agent notifications."""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolRequestParams, Tool

# Configuration
N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "https://draxisdigital.app.n8n.cloud/webhook/agent-notifier")
AGENT_NAME = os.environ.get("AGENT_NAME", "Mistral Vibe")
AGENT_VARIANT = os.environ.get("AGENT_VARIANT", "devstral")


async def send_to_n8n(payload: Dict[str, Any]) -> bool:
    """Send notification payload to n8n webhook."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                N8N_WEBHOOK_URL,
                json=payload,
                headers={"Content-Type": "application/json", "User-Agent": "MCP-Discord-Notifier/1.0"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    return True
                else:
                    print(f"n8n webhook returned status {response.status}", file=sys.stderr, flush=True)
                    return False
    except Exception as e:
        print(f"Error sending to n8n: {e}", file=sys.stderr, flush=True)
        return False


async def handle_tools_call(params: CallToolRequestParams) -> Dict[str, Any]:
    """Handle MCP tool calls."""
    name = params.name
    arguments = params.arguments or {}
    
    if name == "send_notification":
        event_type = arguments.get("event_type", "completed")
        status = arguments.get("status", "success")
        prompt = arguments.get("prompt", "")
        summary = arguments.get("summary", "")
        details = arguments.get("details", {})
        
        run_id = f"vibe-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}"
        
        payload = {
            "run_id": run_id,
            "agent_name": AGENT_NAME,
            "agent_variant": AGENT_VARIANT,
            "event_type": event_type,
            "status": status,
            "prompt": prompt,
            "summary": summary,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        success = await send_to_n8n(payload)
        
        return {
            "status": "sent" if success else "failed",
            "run_id": run_id,
            "webhook_url": N8N_WEBHOOK_URL,
            "timestamp": payload["timestamp"]
        }
    
    return {"error": f"Unknown tool: {name}"}


async def get_tools() -> List[Tool]:
    """Get list of available tools."""
    return [
        Tool(
            name="send_notification",
            description="Send a notification to Discord via n8n webhook",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_type": {
                        "type": "string",
                        "enum": ["started", "progress", "completed", "failed"],
                        "default": "completed",
                        "description": "Event type"
                    },
                    "status": {
                        "type": "string",
                        "default": "success",
                        "description": "Status of the operation"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "The user's original prompt"
                    },
                    "summary": {
                        "type": "string",
                        "default": "",
                        "description": "Summary of the agent's work"
                    },
                    "details": {
                        "type": "object",
                        "additionalProperties": True,
                        "default": {},
                        "description": "Additional details"
                    }
                },
                "required": ["prompt"]
            }
        )
    ]


async def main() -> None:
    """Start MCP server."""
    print(f"Starting MCP server for Discord Bot Notifier", flush=True)
    print(f"n8n Webhook URL: {N8N_WEBHOOK_URL}", flush=True)
    print(f"Agent: {AGENT_NAME}/{AGENT_VARIANT}", flush=True)
    
    server = Server("discord-notifier-mcp")
    
    # Register tool handler
    server.add_request_handler(
        method="tools/call",
        params_type=CallToolRequestParams,
        handler=handle_tools_call
    )
    
    # Update capabilities with tools
    tools = await get_tools()
    caps = server.get_capabilities()
    caps.tools = tools
    
    # Run over stdio
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream=read_stream,
            write_stream=write_stream,
            initialization_options=server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
