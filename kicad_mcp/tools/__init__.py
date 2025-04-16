"""
Tool registration for the KiCad MCP server.

This package includes:
- Project management tools
- Analysis tools
- Export tools (BOM extraction, PCB thumbnail generation)
- DRC tools
"""

# Import tool registration functions
from kicad_mcp.tools.project_tools import register_project_tools
from kicad_mcp.tools.analysis_tools import register_analysis_tools
from kicad_mcp.tools.export_tools import register_export_tools
from kicad_mcp.tools.drc_tools import register_drc_tools
from kicad_mcp.tools.bom_tools import register_bom_tools
from kicad_mcp.tools.netlist_tools import register_netlist_tools
from kicad_mcp.tools.pattern_tools import register_pattern_tools
from kicad_mcp.tools.schematic_tools import register_schematic_tools
from kicad_mcp.tools.pcb_tools import register_pcb_tools
