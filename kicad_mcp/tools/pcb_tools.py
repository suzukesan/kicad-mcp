"""
Tools for creating and manipulating KiCad PCB files via IPC API.
"""
import os
import subprocess
import json
import tempfile
import platform
from typing import Dict, Any, List, Optional, Union

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import FastMCPError

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
from kicad_mcp.utils.temp_dir_manager import register_temp_dir
from kicad_mcp.config import KICAD_VERSION


def register_pcb_tools(app: FastMCP) -> None:
    """Register all PCB creation and manipulation tools."""
    # Check if we're using the new API (add_tool instead of register_tools)
    if hasattr(app, 'add_tool'):
        # New MCP SDK API
        app.add_tool(create_pcb)
        app.add_tool(add_pcb_footprint)
        app.add_tool(add_pcb_track)
        app.add_tool(add_pcb_via)
        app.add_tool(add_pcb_zone)
        app.add_tool(save_pcb)
        # Add edit tools
        app.add_tool(move_pcb_footprint)
        app.add_tool(delete_pcb_footprint)
        app.add_tool(edit_pcb_footprint)
        app.add_tool(delete_pcb_track)
        app.add_tool(move_pcb_via)
        app.add_tool(delete_pcb_via)
        app.add_tool(delete_pcb_zone)
    else:
        # Legacy API
        app.register_tools(
            create_pcb,
            add_pcb_footprint,
            add_pcb_track,
            add_pcb_via,
            add_pcb_zone,
            save_pcb,
            # Add edit tools
            move_pcb_footprint,
            delete_pcb_footprint,
            edit_pcb_footprint,
            delete_pcb_track,
            move_pcb_via,
            delete_pcb_via,
            delete_pcb_zone
        )


@tool(
    name="create_pcb",
    description="Create a new KiCad PCB file",
    parameters={
        "project_path": {
            "type": "string",
            "description": "Path to the KiCad project where the PCB should be created"
        },
        "pcb_name": {
            "type": "string",
            "description": "Name of the PCB file to create (without extension)"
        },
        "title": {
            "type": "string",
            "description": "Title for the PCB",
            "required": False
        },
        "width_mm": {
            "type": "number",
            "description": "Width of the PCB in mm",
            "required": False
        },
        "height_mm": {
            "type": "number",
            "description": "Height of the PCB in mm",
            "required": False
        }
    }
)
async def create_pcb(
    project_path: str,
    pcb_name: str,
    title: Optional[str] = None,
    width_mm: Optional[float] = 100.0,
    height_mm: Optional[float] = 80.0
) -> Dict[str, Any]:
    """
    Create a new KiCad PCB file using the IPC API.
    
    Args:
        project_path: Path to the KiCad project
        pcb_name: Name of the PCB file to create
        title: Title for the PCB
        width_mm: Width of the PCB in mm
        height_mm: Height of the PCB in mm
        
    Returns:
        Dict with information about the created PCB
    """
    # Ensure project directory exists
    os.makedirs(project_path, exist_ok=True)
    
    # Full PCB path
    if not pcb_name.endswith(".kicad_pcb"):
        pcb_name += ".kicad_pcb"
    
    pcb_path = os.path.join(project_path, pcb_name)
    
    # Create project file if it doesn't exist
    project_file = os.path.join(project_path, f"{os.path.basename(project_path)}.kicad_pro")
    if not os.path.exists(project_file):
        # Create minimal project file
        with open(project_file, "w") as f:
            f.write("""
{
  "board": {
    "design_settings": {
      "defaults": {
        "board_outline_line_width": 0.09999999999999999,
        "copper_line_width": 0.19999999999999998,
        "copper_text_italic": false,
        "copper_text_size_h": 1.5,
        "copper_text_size_v": 1.5,
        "copper_text_thickness": 0.3,
        "copper_text_upright": false,
        "courtyard_line_width": 0.049999999999999996,
        "dimension_precision": 4,
        "dimension_units": 3,
        "dimensions": {
          "arrow_length": 1270000,
          "extension_offset": 500000,
          "keep_text_aligned": true,
          "suppress_zeroes": false,
          "text_position": 0,
          "units_format": 1
        },
        "fab_line_width": 0.09999999999999999,
        "fab_text_italic": false,
        "fab_text_size_h": 1.0,
        "fab_text_size_v": 1.0,
        "fab_text_thickness": 0.15,
        "fab_text_upright": false,
        "other_line_width": 0.15,
        "other_text_italic": false,
        "other_text_size_h": 1.0,
        "other_text_size_v": 1.0,
        "other_text_thickness": 0.15,
        "other_text_upright": false,
        "pads": {
          "drill": 0.762,
          "height": 1.524,
          "width": 1.524
        },
        "silk_line_width": 0.15,
        "silk_text_italic": false,
        "silk_text_size_h": 1.0,
        "silk_text_size_v": 1.0,
        "silk_text_thickness": 0.15,
        "silk_text_upright": false,
        "zones": {
          "45_degree_only": false,
          "min_clearance": 0.508
        }
      },
      "diff_pair_dimensions": [],
      "drc_exclusions": [],
      "meta": {
        "version": 2
      },
      "rule_severities": {
        "annular_width": "error",
        "clearance": "error",
        "copper_edge_clearance": "error",
        "courtyards_overlap": "error",
        "diff_pair_gap_out_of_range": "error",
        "diff_pair_uncoupled_length_too_long": "error",
        "drill_out_of_range": "error",
        "duplicate_footprints": "warning",
        "extra_footprint": "warning",
        "footprint_type_mismatch": "error",
        "hole_clearance": "error",
        "hole_near_hole": "error",
        "invalid_outline": "error",
        "item_on_disabled_layer": "error",
        "items_not_allowed": "error",
        "length_out_of_range": "error",
        "malformed_courtyard": "error",
        "microvia_drill_out_of_range": "error",
        "missing_courtyard": "ignore",
        "missing_footprint": "warning",
        "net_conflict": "warning",
        "npth_inside_courtyard": "ignore",
        "padstack": "error",
        "pth_inside_courtyard": "ignore",
        "shorting_items": "error",
        "silk_over_copper": "warning",
        "silk_overlap": "warning",
        "skew_out_of_range": "error",
        "through_hole_pad_without_hole": "error",
        "too_many_vias": "error",
        "track_dangling": "warning",
        "track_width": "error",
        "tracks_crossing": "error",
        "unconnected_items": "error",
        "unresolved_variable": "error",
        "via_dangling": "warning",
        "zone_has_empty_net": "error",
        "zones_intersect": "error"
      },
      "rule_severitieslegacy_courtyards_overlap": true,
      "rule_severitieslegacy_no_courtyard_defined": false,
      "rules": {
        "allow_blind_buried_vias": false,
        "allow_microvias": false,
        "max_error": 0.005,
        "min_clearance": 0.0,
        "min_copper_edge_clearance": 0.0,
        "min_hole_clearance": 0.25,
        "min_hole_to_hole": 0.25,
        "min_microvia_diameter": 0.19999999999999998,
        "min_microvia_drill": 0.09999999999999999,
        "min_silk_clearance": 0.0,
        "min_through_hole_diameter": 0.3,
        "min_track_width": 0.19999999999999998,
        "min_via_annular_width": 0.049999999999999996,
        "min_via_diameter": 0.39999999999999997,
        "solder_mask_clearance": 0.0,
        "solder_mask_min_width": 0.0,
        "use_height_for_length_calcs": true
      },
      "track_widths": [],
      "via_dimensions": [],
      "zones_allow_external_fillets": false,
      "zones_use_no_outline": true
    },
    "layer_presets": []
  },
  "boards": [],
  "cvpcb": {
    "equivalence_files": []
  },
  "libraries": {
    "pinned_footprint_libs": [],
    "pinned_symbol_libs": []
  },
  "pcbnew": {
    "last_paths": {
      "gencad": "",
      "idf": "",
      "netlist": "",
      "specctra_dsn": "",
      "step": "",
      "vrml": ""
    },
    "page_layout_descr_file": ""
  },
  "schematic": {
    "drawing": {
      "default_text_size": 50,
      "default_line_thickness": 6,
      "default_bus_thickness": 12,
      "default_junction_size": 36,
      "default_netname_size": 50,
      "default_wire_thickness": 6
    },
    "net_format_name": "",
    "page_layout_descr_file": "",
    "plot_directory": "",
    "spice_adjust_passive_values": false,
    "subpart_first_id": 65,
    "subpart_id_separator": 0
  },
  "sheets": [],
  "text_variables": {}
}
""")
    
    # Check if PCB already exists
    if os.path.exists(pcb_path):
        raise McpError(f"PCB file already exists: {pcb_path}")
    
    # Create a temporary script to generate the PCB
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="kicad_script_")
    os.close(fd)
    register_temp_dir(os.path.dirname(script_path))
    
    with open(script_path, "w") as f:
        f.write(f"""
import pcbnew
from pcbnew import *
import os

# Create a new board
board = pcbnew.BOARD()

# Set the board title
title_block = board.GetTitleBlock()
title_block.SetTitle({"" if title is None else f'"{title}"'})

# Set board size (create an outline)
width_iu = pcbnew.FromMM({width_mm})  # Internal units
height_iu = pcbnew.FromMM({height_mm})  # Internal units

# Create board outline on Edge.Cuts layer
edge_layer = board.GetLayerID("Edge.Cuts")
outline = pcbnew.PCB_SHAPE(board)
outline.SetShape(pcbnew.SHAPE_T_RECT)
outline.SetLayer(edge_layer)
outline.SetStart(pcbnew.VECTOR2I(0, 0))
outline.SetEnd(pcbnew.VECTOR2I(width_iu, height_iu))
board.Add(outline)

# Save the board
pcbnew.SaveBoard("{pcb_path}", board)

print(f"Created PCB file: {pcb_path}")
""")
    
    # Get KiCad command
    kicad_cmd = get_kicad_command()
    if not kicad_cmd:
        raise McpError("KiCad executable not found")
    
    # Execute the script with KiCad's Python interpreter
    try:
        cmd = [kicad_cmd, "--run", script_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": f"Created new PCB file: {pcb_path}",
            "pcb_path": pcb_path,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise McpError(f"Failed to create PCB file: {e.stderr}")
    finally:
        # Clean up temporary script
        try:
            os.remove(script_path)
        except:
            pass


@tool(
    name="add_pcb_footprint",
    description="Add a footprint to a KiCad PCB",
    parameters={
        "pcb_path": {
            "type": "string",
            "description": "Path to the KiCad PCB file"
        },
        "library": {
            "type": "string",
            "description": "Footprint library name"
        },
        "footprint": {
            "type": "string",
            "description": "Footprint name within the library"
        },
        "x": {
            "type": "number",
            "description": "X coordinate for footprint placement (in mm)"
        },
        "y": {
            "type": "number",
            "description": "Y coordinate for footprint placement (in mm)"
        },
        "rotation": {
            "type": "number",
            "description": "Rotation angle in degrees",
            "required": False
        },
        "reference": {
            "type": "string",
            "description": "Reference designator for the footprint",
            "required": False
        },
        "value": {
            "type": "string",
            "description": "Value for the footprint",
            "required": False
        }
    }
)
async def add_pcb_footprint(
    pcb_path: str,
    library: str,
    footprint: str,
    x: float,
    y: float,
    rotation: Optional[float] = 0.0,
    reference: Optional[str] = None,
    value: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add a footprint to a KiCad PCB using the IPC API.
    
    Args:
        pcb_path: Path to the PCB file
        library: Footprint library name
        footprint: Footprint name within the library
        x: X coordinate for placement
        y: Y coordinate for placement
        rotation: Rotation angle in degrees
        reference: Reference designator
        value: Component value
        
    Returns:
        Dict with information about the added footprint
    """
    # Check if PCB exists
    if not os.path.exists(pcb_path):
        raise McpError(f"PCB file does not exist: {pcb_path}")
    
    # Create a temporary script
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="kicad_script_")
    os.close(fd)
    register_temp_dir(os.path.dirname(script_path))
    
    with open(script_path, "w") as f:
        f.write(f"""
import pcbnew
from pcbnew import *
import os

# Load the board
board = pcbnew.LoadBoard("{pcb_path}")

# Add a footprint
footprint_id = "{library}:{footprint}"
try:
    # Use the footprint loader to get a new footprint
    io = pcbnew.PCB_IO()
    footprint = io.FootprintLoad(pcbnew.FPID(footprint_id))
    
    if footprint is None:
        print(f"Error: Could not load footprint: {footprint_id}")
        exit(1)
    
    # Set position
    position = pcbnew.VECTOR2I(
        pcbnew.FromMM({x}),
        pcbnew.FromMM({y})
    )
    footprint.SetPosition(position)
    
    # Set rotation
    footprint.SetOrientationDegrees({rotation})
    
    # Set reference if provided
    if {reference is not None}:
        footprint.SetReference("{reference}")
    
    # Set value if provided
    if {value is not None}:
        footprint.SetValue("{value}")
    
    # Add to board
    board.Add(footprint)
    
    # Save the board
    pcbnew.SaveBoard("{pcb_path}", board)
    
    print(f"Added footprint '{footprint_id}' to PCB")
except Exception as e:
    print(f"Error: {str(e)}")
    exit(1)
""")
    
    # Get KiCad command
    kicad_cmd = get_kicad_command()
    if not kicad_cmd:
        raise McpError("KiCad executable not found")
    
    # Execute the script with KiCad's Python interpreter
    try:
        cmd = [kicad_cmd, "--run", script_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": f"Added footprint to PCB: {library}:{footprint}",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise McpError(f"Failed to add footprint: {e.stderr}")
    finally:
        # Clean up temporary script
        try:
            os.remove(script_path)
        except:
            pass


@tool(
    name="add_pcb_track",
    description="Add a track to a KiCad PCB",
    parameters={
        "pcb_path": {
            "type": "string",
            "description": "Path to the KiCad PCB file"
        },
        "start_x": {
            "type": "number",
            "description": "X coordinate for track start point (in mm)"
        },
        "start_y": {
            "type": "number",
            "description": "Y coordinate for track start point (in mm)"
        },
        "end_x": {
            "type": "number",
            "description": "X coordinate for track end point (in mm)"
        },
        "end_y": {
            "type": "number",
            "description": "Y coordinate for track end point (in mm)"
        },
        "width": {
            "type": "number",
            "description": "Track width (in mm)",
            "required": False
        },
        "layer": {
            "type": "string",
            "description": "Layer name (e.g., F.Cu, B.Cu)",
            "required": False
        },
        "net_name": {
            "type": "string",
            "description": "Net name for the track",
            "required": False
        }
    }
)
async def add_pcb_track(
    pcb_path: str,
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    width: Optional[float] = 0.25,
    layer: Optional[str] = "F.Cu",
    net_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add a track to a KiCad PCB using the IPC API.
    
    Args:
        pcb_path: Path to the PCB file
        start_x: X coordinate for track start point
        start_y: Y coordinate for track start point
        end_x: X coordinate for track end point
        end_y: Y coordinate for track end point
        width: Track width in mm
        layer: Layer name
        net_name: Net name for the track
        
    Returns:
        Dict with information about the added track
    """
    # Check if PCB exists
    if not os.path.exists(pcb_path):
        raise McpError(f"PCB file does not exist: {pcb_path}")
    
    # Create a temporary script
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="kicad_script_")
    os.close(fd)
    register_temp_dir(os.path.dirname(script_path))
    
    with open(script_path, "w") as f:
        f.write(f"""
import pcbnew
from pcbnew import *
import os

# Load the board
board = pcbnew.LoadBoard("{pcb_path}")

# Create a new track
track = pcbnew.PCB_TRACK(board)

# Set track width
track.SetWidth(pcbnew.FromMM({width}))

# Set layer
layer_id = board.GetLayerID("{layer}")
track.SetLayer(layer_id)

# Set start and end points
start_point = pcbnew.VECTOR2I(
    pcbnew.FromMM({start_x}),
    pcbnew.FromMM({start_y})
)
end_point = pcbnew.VECTOR2I(
    pcbnew.FromMM({end_x}),
    pcbnew.FromMM({end_y})
)
track.SetStart(start_point)
track.SetEnd(end_point)

# Set net if provided
if "{net_name}" != "None":
    net_code = board.GetNetcodeFromNetname("{net_name}")
    if net_code == pcbnew.NETINFO_LIST.UNCONNECTED:
        # Create a new net if it doesn't exist
        new_net = pcbnew.NETINFO_ITEM(board, "{net_name}")
        board.Add(new_net)
        net_code = new_net.GetNetCode()
    track.SetNetCode(net_code)

# Add the track to the board
board.Add(track)

# Save the board
pcbnew.SaveBoard("{pcb_path}", board)

print(f"Added track to PCB on layer {layer}")
""")
    
    # Get KiCad command
    kicad_cmd = get_kicad_command()
    if not kicad_cmd:
        raise McpError("KiCad executable not found")
    
    # Execute the script with KiCad's Python interpreter
    try:
        cmd = [kicad_cmd, "--run", script_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": f"Added track to PCB on layer {layer}",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise McpError(f"Failed to add track: {e.stderr}")
    finally:
        # Clean up temporary script
        try:
            os.remove(script_path)
        except:
            pass 


@tool(
    name="add_pcb_via",
    description="Add a via to a KiCad PCB",
    parameters={
        "pcb_path": {
            "type": "string",
            "description": "Path to the KiCad PCB file"
        },
        "x": {
            "type": "number",
            "description": "X coordinate for via placement (in mm)"
        },
        "y": {
            "type": "number",
            "description": "Y coordinate for via placement (in mm)"
        },
        "drill": {
            "type": "number",
            "description": "Via drill diameter (in mm)",
            "required": False
        },
        "diameter": {
            "type": "number",
            "description": "Via diameter (in mm)",
            "required": False
        },
        "net_name": {
            "type": "string",
            "description": "Net name for the via",
            "required": False
        }
    }
)
async def add_pcb_via(
    pcb_path: str,
    x: float,
    y: float,
    drill: Optional[float] = 0.4,
    diameter: Optional[float] = 0.8,
    net_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add a via to a KiCad PCB using the IPC API.
    
    Args:
        pcb_path: Path to the PCB file
        x: X coordinate for via placement
        y: Y coordinate for via placement
        drill: Via drill diameter in mm
        diameter: Via diameter in mm
        net_name: Net name for the via
        
    Returns:
        Dict with information about the added via
    """
    # Check if PCB exists
    if not os.path.exists(pcb_path):
        raise McpError(f"PCB file does not exist: {pcb_path}")
    
    # Create a temporary script
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="kicad_script_")
    os.close(fd)
    register_temp_dir(os.path.dirname(script_path))
    
    with open(script_path, "w") as f:
        f.write(f"""
import pcbnew
from pcbnew import *
import os

# Load the board
board = pcbnew.LoadBoard("{pcb_path}")

# Create a new via
via = pcbnew.PCB_VIA(board)

# Set via type (through-hole)
via.SetViaType(pcbnew.VIATYPE_THROUGH)

# Set via position
position = pcbnew.VECTOR2I(
    pcbnew.FromMM({x}),
    pcbnew.FromMM({y})
)
via.SetPosition(position)

# Set via size and drill
via.SetWidth(pcbnew.FromMM({diameter}))
via.SetDrill(pcbnew.FromMM({drill}))

# Set layers (through all layers)
via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)

# Set net if provided
if "{net_name}" != "None":
    net_code = board.GetNetcodeFromNetname("{net_name}")
    if net_code == pcbnew.NETINFO_LIST.UNCONNECTED:
        # Create a new net if it doesn't exist
        new_net = pcbnew.NETINFO_ITEM(board, "{net_name}")
        board.Add(new_net)
        net_code = new_net.GetNetCode()
    via.SetNetCode(net_code)

# Add the via to the board
board.Add(via)

# Save the board
pcbnew.SaveBoard("{pcb_path}", board)

print(f"Added via to PCB at ({x}mm, {y}mm)")
""")
    
    # Get KiCad command
    kicad_cmd = get_kicad_command()
    if not kicad_cmd:
        raise McpError("KiCad executable not found")
    
    # Execute the script with KiCad's Python interpreter
    try:
        cmd = [kicad_cmd, "--run", script_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": f"Added via to PCB at ({x}mm, {y}mm)",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise McpError(f"Failed to add via: {e.stderr}")
    finally:
        # Clean up temporary script
        try:
            os.remove(script_path)
        except:
            pass


@tool(
    name="add_pcb_zone",
    description="Add a copper zone/pour to a KiCad PCB",
    parameters={
        "pcb_path": {
            "type": "string",
            "description": "Path to the KiCad PCB file"
        },
        "layer": {
            "type": "string",
            "description": "Layer name (e.g., F.Cu, B.Cu)"
        },
        "net_name": {
            "type": "string",
            "description": "Net name for the zone (e.g., GND, VCC)"
        },
        "points": {
            "type": "array",
            "description": "Array of points defining the zone outline [x,y] in mm",
            "items": {
                "type": "array",
                "items": {
                    "type": "number"
                }
            }
        },
        "clearance": {
            "type": "number",
            "description": "Zone clearance (in mm)",
            "required": False
        }
    }
)
async def add_pcb_zone(
    pcb_path: str,
    layer: str,
    net_name: str,
    points: List[List[float]],
    clearance: Optional[float] = 0.2
) -> Dict[str, Any]:
    """
    Add a copper zone/pour to a KiCad PCB using the IPC API.
    
    Args:
        pcb_path: Path to the PCB file
        layer: Layer name
        net_name: Net name for the zone
        points: Array of points defining the zone outline
        clearance: Zone clearance in mm
        
    Returns:
        Dict with information about the added zone
    """
    # Check if PCB exists
    if not os.path.exists(pcb_path):
        raise McpError(f"PCB file does not exist: {pcb_path}")
    
    # Make sure we have at least 3 points for a zone
    if len(points) < 3:
        raise McpError("Zone requires at least 3 points")
    
    # Format points for the script
    points_str = ""
    for i, (x, y) in enumerate(points):
        points_str += f"    outline.Append(pcbnew.VECTOR2I(pcbnew.FromMM({x}), pcbnew.FromMM({y})))\n"
    
    # Create a temporary script
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="kicad_script_")
    os.close(fd)
    register_temp_dir(os.path.dirname(script_path))
    
    with open(script_path, "w") as f:
        f.write(f"""
import pcbnew
from pcbnew import *
import os

# Load the board
board = pcbnew.LoadBoard("{pcb_path}")

# Get the layer ID
layer_id = board.GetLayerID("{layer}")

# Create a new zone
zone = pcbnew.ZONE(board)
zone.SetLayer(layer_id)

# Set the net
net_code = board.GetNetcodeFromNetname("{net_name}")
if net_code == pcbnew.NETINFO_LIST.UNCONNECTED:
    # Create a new net if it doesn't exist
    new_net = pcbnew.NETINFO_ITEM(board, "{net_name}")
    board.Add(new_net)
    net_code = new_net.GetNetCode()
zone.SetNetCode(net_code)

# Set the zone clearance
zone.SetLocalClearance(pcbnew.FromMM({clearance}))

# Create the zone outline
outline = zone.Outline()
{points_str}

# Add the zone to the board
board.Add(zone)

# Fill the zone
filler = pcbnew.ZONE_FILLER(board)
filler.Fill(board.Zones())

# Save the board
pcbnew.SaveBoard("{pcb_path}", board)

print(f"Added zone to PCB on layer {layer} with net {net_name}")
""")
    
    # Get KiCad command
    kicad_cmd = get_kicad_command()
    if not kicad_cmd:
        raise McpError("KiCad executable not found")
    
    # Execute the script with KiCad's Python interpreter
    try:
        cmd = [kicad_cmd, "--run", script_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": f"Added zone to PCB on layer {layer} with net {net_name}",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise McpError(f"Failed to add zone: {e.stderr}")
    finally:
        # Clean up temporary script
        try:
            os.remove(script_path)
        except:
            pass


@tool(
    name="save_pcb",
    description="Save changes to a KiCad PCB",
    parameters={
        "pcb_path": {
            "type": "string",
            "description": "Path to the KiCad PCB file to save"
        }
    }
)
async def save_pcb(pcb_path: str) -> Dict[str, Any]:
    """
    Save changes to a KiCad PCB using the IPC API.
    
    Args:
        pcb_path: Path to the PCB file to save
        
    Returns:
        Dict with information about the save operation
    """
    # Check if PCB exists
    if not os.path.exists(pcb_path):
        raise McpError(f"PCB file does not exist: {pcb_path}")
    
    # Create a temporary script
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="kicad_script_")
    os.close(fd)
    register_temp_dir(os.path.dirname(script_path))
    
    with open(script_path, "w") as f:
        f.write(f"""
import pcbnew
from pcbnew import *
import os

# Load the board
board = pcbnew.LoadBoard("{pcb_path}")

# Save the board
pcbnew.SaveBoard("{pcb_path}", board)

print(f"PCB saved successfully: {pcb_path}")
""")
    
    # Get KiCad command
    kicad_cmd = get_kicad_command()
    if not kicad_cmd:
        raise McpError("KiCad executable not found")
    
    # Execute the script with KiCad's Python interpreter
    try:
        cmd = [kicad_cmd, "--run", script_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": "PCB saved successfully",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise McpError(f"Failed to save PCB: {e.stderr}")
    finally:
        # Clean up temporary script
        try:
            os.remove(script_path)
        except:
            pass 


@tool(
    name="move_pcb_footprint",
    description="Move a footprint on a KiCad PCB",
    parameters={
        "pcb_path": {
            "type": "string",
            "description": "Path to the KiCad PCB file"
        },
        "reference": {
            "type": "string",
            "description": "Reference designator of the footprint to move (e.g., R1, C3)"
        },
        "x": {
            "type": "number",
            "description": "New X coordinate for footprint placement (in mm)"
        },
        "y": {
            "type": "number",
            "description": "New Y coordinate for footprint placement (in mm)"
        },
        "rotation": {
            "type": "number",
            "description": "New rotation angle in degrees",
            "required": False
        }
    }
)
async def move_pcb_footprint(
    pcb_path: str,
    reference: str,
    x: float,
    y: float,
    rotation: Optional[float] = None
) -> Dict[str, Any]:
    """
    Move a footprint on a KiCad PCB using the IPC API.
    
    Args:
        pcb_path: Path to the PCB file
        reference: Reference designator of the footprint to move
        x: New X coordinate for placement
        y: New Y coordinate for placement
        rotation: New rotation angle in degrees (if None, keep current rotation)
        
    Returns:
        Dict with information about the moved footprint
    """
    # Check if PCB exists
    if not os.path.exists(pcb_path):
        raise McpError(f"PCB file does not exist: {pcb_path}")
    
    # Create a temporary script
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="kicad_script_")
    os.close(fd)
    register_temp_dir(os.path.dirname(script_path))
    
    rotation_code = ""
    if rotation is not None:
        rotation_code = f"    footprint.SetOrientationDegrees({rotation})"
    
    with open(script_path, "w") as f:
        f.write(f"""
import pcbnew
from pcbnew import *
import os

# Load the board
board = pcbnew.LoadBoard("{pcb_path}")

# Find the footprint by reference
footprint = None
for fp in board.GetFootprints():
    if fp.GetReference() == "{reference}":
        footprint = fp
        break

if footprint is None:
    print(f"Error: Footprint with reference '{reference}' not found")
    exit(1)

# Set the new position
position = pcbnew.VECTOR2I(
    pcbnew.FromMM({x}),
    pcbnew.FromMM({y})
)
footprint.SetPosition(position)

# Set new rotation if specified
{rotation_code}

# Save the board
pcbnew.SaveBoard("{pcb_path}", board)

print(f"Footprint {reference} moved successfully")
""")
    
    # Get KiCad command
    kicad_cmd = get_kicad_command()
    if not kicad_cmd:
        raise McpError("KiCad executable not found")
    
    # Execute the script with KiCad's Python interpreter
    try:
        cmd = [kicad_cmd, "--run", script_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": f"Footprint {reference} moved successfully",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise McpError(f"Failed to move footprint: {e.stderr}")
    finally:
        # Clean up temporary script
        try:
            os.remove(script_path)
        except:
            pass


@tool(
    name="delete_pcb_footprint",
    description="Delete a footprint from a KiCad PCB",
    parameters={
        "pcb_path": {
            "type": "string",
            "description": "Path to the KiCad PCB file"
        },
        "reference": {
            "type": "string",
            "description": "Reference designator of the footprint to delete (e.g., R1, C3)"
        }
    }
)
async def delete_pcb_footprint(
    pcb_path: str,
    reference: str
) -> Dict[str, Any]:
    """
    Delete a footprint from a KiCad PCB using the IPC API.
    
    Args:
        pcb_path: Path to the PCB file
        reference: Reference designator of the footprint to delete
        
    Returns:
        Dict with information about the delete operation
    """
    # Check if PCB exists
    if not os.path.exists(pcb_path):
        raise McpError(f"PCB file does not exist: {pcb_path}")
    
    # Create a temporary script
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="kicad_script_")
    os.close(fd)
    register_temp_dir(os.path.dirname(script_path))
    
    with open(script_path, "w") as f:
        f.write(f"""
import pcbnew
from pcbnew import *
import os

# Load the board
board = pcbnew.LoadBoard("{pcb_path}")

# Find the footprint by reference
footprint = None
for fp in board.GetFootprints():
    if fp.GetReference() == "{reference}":
        footprint = fp
        break

if footprint is None:
    print(f"Error: Footprint with reference '{reference}' not found")
    exit(1)

# Remove the footprint
board.Remove(footprint)

# Save the board
pcbnew.SaveBoard("{pcb_path}", board)

print(f"Footprint {reference} deleted successfully")
""")
    
    # Get KiCad command
    kicad_cmd = get_kicad_command()
    if not kicad_cmd:
        raise McpError("KiCad executable not found")
    
    # Execute the script with KiCad's Python interpreter
    try:
        cmd = [kicad_cmd, "--run", script_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": f"Footprint {reference} deleted successfully",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise McpError(f"Failed to delete footprint: {e.stderr}")
    finally:
        # Clean up temporary script
        try:
            os.remove(script_path)
        except:
            pass


@tool(
    name="edit_pcb_footprint",
    description="Edit properties of a footprint on a KiCad PCB",
    parameters={
        "pcb_path": {
            "type": "string",
            "description": "Path to the KiCad PCB file"
        },
        "reference": {
            "type": "string",
            "description": "Current reference designator of the footprint (e.g., R1, C3)"
        },
        "new_reference": {
            "type": "string",
            "description": "New reference designator for the footprint",
            "required": False
        },
        "value": {
            "type": "string",
            "description": "New value for the footprint",
            "required": False
        },
        "layer": {
            "type": "string",
            "description": "New layer for the footprint (e.g., F.Cu, B.Cu)",
            "required": False
        }
    }
)
async def edit_pcb_footprint(
    pcb_path: str,
    reference: str,
    new_reference: Optional[str] = None,
    value: Optional[str] = None,
    layer: Optional[str] = None
) -> Dict[str, Any]:
    """
    Edit properties of a footprint on a KiCad PCB using the IPC API.
    
    Args:
        pcb_path: Path to the PCB file
        reference: Current reference designator of the footprint
        new_reference: New reference designator for the footprint
        value: New value for the footprint
        layer: New layer for the footprint
        
    Returns:
        Dict with information about the edit operation
    """
    # Check if PCB exists
    if not os.path.exists(pcb_path):
        raise McpError(f"PCB file does not exist: {pcb_path}")
    
    # At least one of new_reference, value, or layer must be provided
    if new_reference is None and value is None and layer is None:
        raise McpError("At least one of new_reference, value, or layer must be provided")
    
    # Create a temporary script
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="kicad_script_")
    os.close(fd)
    register_temp_dir(os.path.dirname(script_path))
    
    # Prepare the edit commands
    edit_commands = []
    if new_reference is not None:
        edit_commands.append(f'    footprint.SetReference("{new_reference}")')
    
    if value is not None:
        edit_commands.append(f'    footprint.SetValue("{value}")')
    
    layer_code = ""
    if layer is not None:
        layer_code = f"""
    layer_id = board.GetLayerID("{layer}")
    footprint.SetLayer(layer_id)
"""
        edit_commands.append(layer_code)
    
    edit_code = "\n".join(edit_commands)
    
    with open(script_path, "w") as f:
        f.write(f"""
import pcbnew
from pcbnew import *
import os

# Load the board
board = pcbnew.LoadBoard("{pcb_path}")

# Find the footprint by reference
footprint = None
for fp in board.GetFootprints():
    if fp.GetReference() == "{reference}":
        footprint = fp
        break

if footprint is None:
    print(f"Error: Footprint with reference '{reference}' not found")
    exit(1)

# Edit the footprint
{edit_code}

# Save the board
pcbnew.SaveBoard("{pcb_path}", board)

print(f"Footprint {reference} edited successfully")
""")
    
    # Get KiCad command
    kicad_cmd = get_kicad_command()
    if not kicad_cmd:
        raise McpError("KiCad executable not found")
    
    # Execute the script with KiCad's Python interpreter
    try:
        cmd = [kicad_cmd, "--run", script_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": f"Footprint {reference} edited successfully",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise McpError(f"Failed to edit footprint: {e.stderr}")
    finally:
        # Clean up temporary script
        try:
            os.remove(script_path)
        except:
            pass


@tool(
    name="delete_pcb_track",
    description="Delete a track from a KiCad PCB",
    parameters={
        "pcb_path": {
            "type": "string",
            "description": "Path to the KiCad PCB file"
        },
        "start_x": {
            "type": "number",
            "description": "X coordinate for track start point (in mm)"
        },
        "start_y": {
            "type": "number",
            "description": "Y coordinate for track start point (in mm)"
        },
        "end_x": {
            "type": "number",
            "description": "X coordinate for track end point (in mm)"
        },
        "end_y": {
            "type": "number",
            "description": "Y coordinate for track end point (in mm)"
        },
        "layer": {
            "type": "string",
            "description": "Layer name (e.g., F.Cu, B.Cu)",
            "required": False
        },
        "tolerance_mm": {
            "type": "number",
            "description": "Tolerance for track endpoint matching (in mm)",
            "required": False
        }
    }
)
async def delete_pcb_track(
    pcb_path: str,
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    layer: Optional[str] = None,
    tolerance_mm: Optional[float] = 1.0
) -> Dict[str, Any]:
    """
    Delete a track from a KiCad PCB using the IPC API.
    
    Args:
        pcb_path: Path to the PCB file
        start_x: X coordinate for track start point
        start_y: Y coordinate for track start point
        end_x: X coordinate for track end point
        end_y: Y coordinate for track end point
        layer: Layer name to limit search (if None, search all layers)
        tolerance_mm: Tolerance for track endpoint matching
        
    Returns:
        Dict with information about the delete operation
    """
    # Check if PCB exists
    if not os.path.exists(pcb_path):
        raise McpError(f"PCB file does not exist: {pcb_path}")
    
    # Create a temporary script
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="kicad_script_")
    os.close(fd)
    register_temp_dir(os.path.dirname(script_path))
    
    layer_filter = ""
    if layer is not None:
        layer_filter = f"""
    # Get layer ID
    layer_id = board.GetLayerID("{layer}")
    # Only consider tracks on the specified layer
    if track.GetLayer() != layer_id:
        continue
"""
    
    with open(script_path, "w") as f:
        f.write(f"""
import pcbnew
from pcbnew import *
import os
import math

# Load the board
board = pcbnew.LoadBoard("{pcb_path}")

# Convert mm to internal units
start_point_x = FromMM({start_x})
start_point_y = FromMM({start_y})
end_point_x = FromMM({end_x})
end_point_y = FromMM({end_y})
tolerance = FromMM({tolerance_mm})

# Function to check if two points are close enough
def points_match(p1, p2, tol):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2) <= tol

# Find matching tracks
tracks_to_delete = []
for track in board.GetTracks():
    # Skip vias
    if not isinstance(track, pcbnew.PCB_TRACK):
        continue
{layer_filter}
    track_start = track.GetStart()
    track_end = track.GetEnd()
    
    # Check both orientations of the track
    if (points_match(track_start, VECTOR2I(start_point_x, start_point_y), tolerance) and 
        points_match(track_end, VECTOR2I(end_point_x, end_point_y), tolerance)) or \
       (points_match(track_start, VECTOR2I(end_point_x, end_point_y), tolerance) and 
        points_match(track_end, VECTOR2I(start_point_x, start_point_y), tolerance)):
        tracks_to_delete.append(track)

if not tracks_to_delete:
    print("Error: No matching track found at the specified coordinates")
    exit(1)

# Remove the tracks
for track in tracks_to_delete:
    board.Remove(track)

# Save the board
pcbnew.SaveBoard("{pcb_path}", board)

print(f"Deleted {len(tracks_to_delete)} track(s) successfully")
""")
    
    # Get KiCad command
    kicad_cmd = get_kicad_command()
    if not kicad_cmd:
        raise McpError("KiCad executable not found")
    
    # Execute the script with KiCad's Python interpreter
    try:
        cmd = [kicad_cmd, "--run", script_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": "Track(s) deleted successfully",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise McpError(f"Failed to delete track: {e.stderr}")
    finally:
        # Clean up temporary script
        try:
            os.remove(script_path)
        except:
            pass


@tool(
    name="move_pcb_via",
    description="Move a via on a KiCad PCB",
    parameters={
        "pcb_path": {
            "type": "string",
            "description": "Path to the KiCad PCB file"
        },
        "x": {
            "type": "number",
            "description": "Current X coordinate of the via (in mm)"
        },
        "y": {
            "type": "number",
            "description": "Current Y coordinate of the via (in mm)"
        },
        "new_x": {
            "type": "number",
            "description": "New X coordinate for the via (in mm)"
        },
        "new_y": {
            "type": "number",
            "description": "New Y coordinate for the via (in mm)"
        },
        "tolerance_mm": {
            "type": "number",
            "description": "Tolerance for via position matching (in mm)",
            "required": False
        }
    }
)
async def move_pcb_via(
    pcb_path: str,
    x: float,
    y: float,
    new_x: float,
    new_y: float,
    tolerance_mm: Optional[float] = 1.0
) -> Dict[str, Any]:
    """
    Move a via on a KiCad PCB using the IPC API.
    
    Args:
        pcb_path: Path to the PCB file
        x: Current X coordinate of the via
        y: Current Y coordinate of the via
        new_x: New X coordinate for the via
        new_y: New Y coordinate for the via
        tolerance_mm: Tolerance for via position matching
        
    Returns:
        Dict with information about the moved via
    """
    # Check if PCB exists
    if not os.path.exists(pcb_path):
        raise McpError(f"PCB file does not exist: {pcb_path}")
    
    # Create a temporary script
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="kicad_script_")
    os.close(fd)
    register_temp_dir(os.path.dirname(script_path))
    
    with open(script_path, "w") as f:
        f.write(f"""
import pcbnew
from pcbnew import *
import os
import math

# Load the board
board = pcbnew.LoadBoard("{pcb_path}")

# Convert mm to internal units
current_x = FromMM({x})
current_y = FromMM({y})
target_x = FromMM({new_x})
target_y = FromMM({new_y})
tolerance = FromMM({tolerance_mm})

# Function to check if a point matches the target position
def point_matches(p, target_x, target_y, tol):
    return math.sqrt((p.x - target_x)**2 + (p.y - target_y)**2) <= tol

# Find the via at the specified position
via = None
for v in board.GetTracks():
    if not isinstance(v, pcbnew.PCB_VIA):
        continue
        
    if point_matches(v.GetPosition(), current_x, current_y, tolerance):
        via = v
        break

if via is None:
    print(f"Error: No via found at position ({x}mm, {y}mm)")
    exit(1)

# Set the new position
new_position = pcbnew.VECTOR2I(target_x, target_y)
via.SetPosition(new_position)

# Save the board
pcbnew.SaveBoard("{pcb_path}", board)

print(f"Via moved from ({x}mm, {y}mm) to ({new_x}mm, {new_y}mm) successfully")
""")
    
    # Get KiCad command
    kicad_cmd = get_kicad_command()
    if not kicad_cmd:
        raise McpError("KiCad executable not found")
    
    # Execute the script with KiCad's Python interpreter
    try:
        cmd = [kicad_cmd, "--run", script_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": f"Via moved successfully",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise McpError(f"Failed to move via: {e.stderr}")
    finally:
        # Clean up temporary script
        try:
            os.remove(script_path)
        except:
            pass


@tool(
    name="delete_pcb_via",
    description="Delete a via from a KiCad PCB",
    parameters={
        "pcb_path": {
            "type": "string",
            "description": "Path to the KiCad PCB file"
        },
        "x": {
            "type": "number",
            "description": "X coordinate of the via to delete (in mm)"
        },
        "y": {
            "type": "number",
            "description": "Y coordinate of the via to delete (in mm)"
        },
        "tolerance_mm": {
            "type": "number",
            "description": "Tolerance for via position matching (in mm)",
            "required": False
        }
    }
)
async def delete_pcb_via(
    pcb_path: str,
    x: float,
    y: float,
    tolerance_mm: Optional[float] = 1.0
) -> Dict[str, Any]:
    """
    Delete a via from a KiCad PCB using the IPC API.
    
    Args:
        pcb_path: Path to the PCB file
        x: X coordinate of the via to delete
        y: Y coordinate of the via to delete
        tolerance_mm: Tolerance for via position matching
        
    Returns:
        Dict with information about the delete operation
    """
    # Check if PCB exists
    if not os.path.exists(pcb_path):
        raise McpError(f"PCB file does not exist: {pcb_path}")
    
    # Create a temporary script
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="kicad_script_")
    os.close(fd)
    register_temp_dir(os.path.dirname(script_path))
    
    with open(script_path, "w") as f:
        f.write(f"""
import pcbnew
from pcbnew import *
import os
import math

# Load the board
board = pcbnew.LoadBoard("{pcb_path}")

# Convert mm to internal units
target_x = FromMM({x})
target_y = FromMM({y})
tolerance = FromMM({tolerance_mm})

# Function to check if a point matches the target position
def point_matches(p, target_x, target_y, tol):
    return math.sqrt((p.x - target_x)**2 + (p.y - target_y)**2) <= tol

# Find the via at the specified position
via = None
for v in board.GetTracks():
    if not isinstance(v, pcbnew.PCB_VIA):
        continue
        
    if point_matches(v.GetPosition(), target_x, target_y, tolerance):
        via = v
        break

if via is None:
    print(f"Error: No via found at position ({x}mm, {y}mm)")
    exit(1)

# Remove the via
board.Remove(via)

# Save the board
pcbnew.SaveBoard("{pcb_path}", board)

print(f"Via at ({x}mm, {y}mm) deleted successfully")
""")
    
    # Get KiCad command
    kicad_cmd = get_kicad_command()
    if not kicad_cmd:
        raise McpError("KiCad executable not found")
    
    # Execute the script with KiCad's Python interpreter
    try:
        cmd = [kicad_cmd, "--run", script_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": f"Via deleted successfully",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise McpError(f"Failed to delete via: {e.stderr}")
    finally:
        # Clean up temporary script
        try:
            os.remove(script_path)
        except:
            pass


@tool(
    name="delete_pcb_zone",
    description="Delete a copper zone/pour from a KiCad PCB",
    parameters={
        "pcb_path": {
            "type": "string",
            "description": "Path to the KiCad PCB file"
        },
        "x": {
            "type": "number",
            "description": "X coordinate of a point inside the zone (in mm)"
        },
        "y": {
            "type": "number",
            "description": "Y coordinate of a point inside the zone (in mm)"
        },
        "layer": {
            "type": "string",
            "description": "Layer name (e.g., F.Cu, B.Cu)",
            "required": False
        },
        "net_name": {
            "type": "string",
            "description": "Net name of the zone (e.g., GND, VCC)",
            "required": False
        }
    }
)
async def delete_pcb_zone(
    pcb_path: str,
    x: float,
    y: float,
    layer: Optional[str] = None,
    net_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Delete a copper zone/pour from a KiCad PCB using the IPC API.
    
    Args:
        pcb_path: Path to the PCB file
        x: X coordinate of a point inside the zone
        y: Y coordinate of a point inside the zone
        layer: Layer name to limit search (if None, search all layers)
        net_name: Net name to limit search (if None, no net filtering)
        
    Returns:
        Dict with information about the delete operation
    """
    # Check if PCB exists
    if not os.path.exists(pcb_path):
        raise McpError(f"PCB file does not exist: {pcb_path}")
    
    # Create a temporary script
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="kicad_script_")
    os.close(fd)
    register_temp_dir(os.path.dirname(script_path))
    
    layer_filter = ""
    if layer is not None:
        layer_filter = f"""
    # Get layer ID
    layer_id = board.GetLayerID("{layer}")
    # Only consider zones on the specified layer
    if zone.GetLayer() != layer_id:
        continue
"""
    
    net_filter = ""
    if net_name is not None:
        net_filter = f"""
    # Get netcode for the specified net name
    net_code = board.GetNetcodeFromNetname("{net_name}")
    # Only consider zones with the specified net
    if zone.GetNetCode() != net_code:
        continue
"""
    
    with open(script_path, "w") as f:
        f.write(f"""
import pcbnew
from pcbnew import *
import os

# Load the board
board = pcbnew.LoadBoard("{pcb_path}")

# Convert mm to internal units
point_x = FromMM({x})
point_y = FromMM({y})
test_point = VECTOR2I(point_x, point_y)

# Find zones containing the specified point
zones_to_delete = []
for zone in board.Zones():
{layer_filter}
{net_filter}
    # Check if the point is inside the zone
    if zone.HitTest(test_point):
        zones_to_delete.append(zone)

if not zones_to_delete:
    print(f"Error: No matching zone found at the specified position ({x}mm, {y}mm)")
    exit(1)

# Remove the zones
for zone in zones_to_delete:
    board.Remove(zone)

# Save the board
pcbnew.SaveBoard("{pcb_path}", board)

print(f"Deleted {len(zones_to_delete)} zone(s) successfully")
""")
    
    # Get KiCad command
    kicad_cmd = get_kicad_command()
    if not kicad_cmd:
        raise McpError("KiCad executable not found")
    
    # Execute the script with KiCad's Python interpreter
    try:
        cmd = [kicad_cmd, "--run", script_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": "Zone(s) deleted successfully",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise McpError(f"Failed to delete zone: {e.stderr}")
    finally:
        # Clean up temporary script
        try:
            os.remove(script_path)
        except:
            pass 