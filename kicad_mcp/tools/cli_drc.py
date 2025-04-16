import os
import json
import subprocess
import re
import platform
from typing import Dict, List, Any, Union, Optional

# MCP tool decorator setup for compatibility across versions
try:
    from mcp.server.tools import tool
except ImportError:
    try:
        from mcp.server.fastmcp.tools.base import tool
    except ImportError:
        # Fallback to a basic decorator if all imports fail
        def tool(*args, **kwargs):
            def decorator(func):
                return func
            if args and callable(args[0]):
                return decorator(args[0])
            return decorator

try:
    from mcp.server.fastmcp.exceptions import FastMCPError
    # Define McpError locally as FastMCPError
    McpError = FastMCPError
except ImportError:
    # Fallback for backwards compatibility
    class McpError(Exception):
        """Exception raised for errors in the MCP API."""
        pass

from kicad_mcp.utils.kicad_utils import find_kicad_executable, get_kicad_command 