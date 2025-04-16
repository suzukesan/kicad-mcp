"""
Prompt registration for the KiCad MCP server.
"""

# Import prompt registration functions
from kicad_mcp.prompts.templates import register_prompts
from kicad_mcp.prompts.drc_prompt import register_drc_prompts
from kicad_mcp.prompts.bom_prompts import register_bom_prompts
from kicad_mcp.prompts.pattern_prompts import register_pattern_prompts
from kicad_mcp.prompts.circuit_prompts import register_circuit_prompts
