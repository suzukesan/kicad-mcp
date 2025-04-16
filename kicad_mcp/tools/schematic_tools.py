"""
Tools for creating and manipulating KiCad schematic files via IPC API.
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

def register_schematic_tools(app: FastMCP) -> None:
    """Register all schematic creation and manipulation tools."""
    # Check if we're using the new API (add_tool instead of register_tools)
    if hasattr(app, 'add_tool'):
        # New MCP SDK API
        app.add_tool(create_schematic)
        app.add_tool(add_schematic_component)
        app.add_tool(add_schematic_wire)
        app.add_tool(create_schematic_sheet)
        app.add_tool(create_schematic_label)
        app.add_tool(create_schematic_bus)
        app.add_tool(save_schematic)
        # Add edit tools
        app.add_tool(move_schematic_component)
        app.add_tool(delete_schematic_component)
        app.add_tool(edit_schematic_component)
        app.add_tool(delete_schematic_wire)
        app.add_tool(edit_schematic_label)
    else:
        # Legacy API
        app.register_tools(
            create_schematic,
            add_schematic_component,
            add_schematic_wire,
            create_schematic_sheet,
            create_schematic_label,
            create_schematic_bus,
            save_schematic,
            # Add edit tools
            move_schematic_component,
            delete_schematic_component,
            edit_schematic_component,
            delete_schematic_wire,
            edit_schematic_label
        )


@tool(
    name="create_schematic",
    description="Create a new KiCad schematic file",
    parameters={
        "project_path": {
            "type": "string",
            "description": "Path to the KiCad project where the schematic should be created"
        },
        "schematic_name": {
            "type": "string",
            "description": "Name of the schematic file to create (without extension)"
        },
        "title": {
            "type": "string",
            "description": "Title for the schematic sheet",
            "required": False
        },
        "company": {
            "type": "string",
            "description": "Company name for the schematic sheet",
            "required": False
        },
        "rev": {
            "type": "string",
            "description": "Revision for the schematic sheet",
            "required": False
        }
    }
)
async def create_schematic(
    project_path: str,
    schematic_name: str,
    title: Optional[str] = None,
    company: Optional[str] = None,
    rev: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new KiCad schematic file using the IPC API.
    
    Args:
        project_path: Path to the KiCad project
        schematic_name: Name of the schematic file to create
        title: Title for the schematic sheet
        company: Company name for the schematic sheet
        rev: Revision for the schematic sheet
        
    Returns:
        Dict with information about the created schematic
    """
    # Ensure project directory exists
    os.makedirs(project_path, exist_ok=True)
    
    # Full schematic path
    if not schematic_name.endswith(".kicad_sch"):
        schematic_name += ".kicad_sch"
    
    schematic_path = os.path.join(project_path, schematic_name)
    
    # Create project file if it doesn't exist
    project_file = os.path.join(project_path, f"{os.path.basename(project_path)}.kicad_pro")
    if not os.path.exists(project_file):
        # Create minimal project file
        with open(project_file, "w") as f:
            f.write("""
{
  "schematic": {
    "drawing": {
      "default_bus_thickness": 12.0,
      "default_junction_size": 40.0,
      "default_line_thickness": 6.0,
      "default_text_size": 50.0,
      "default_wire_thickness": 6.0
    },
    "version": 20211123
  },
  "version": 1
}
""")
    
    # Check if schematic already exists
    if os.path.exists(schematic_path):
        raise McpError(f"Schematic file already exists: {schematic_path}")
    
    # Create basic schematic content
    schematic_content = {
        "version": 20211123,
        "generator": "Kicad Schematic via MCP",
        "uuid": "your-uuid-here",  # In real implementation, generate a UUID
        "paper": "A4",
        "title_block": {
            "title": title or "",
            "company": company or "",
            "rev": rev or "",
            "date": "",
            "comment": []
        }
    }
    
    # Write schematic file
    try:
        with open(schematic_path, "w") as f:
            json.dump(schematic_content, f, indent=2)
        
        return {
            "status": "success",
            "message": f"Created new schematic file: {schematic_path}",
            "schematic_path": schematic_path
        }
    except Exception as e:
        raise McpError(f"Failed to create schematic file: {str(e)}")


@tool(
    name="add_schematic_component",
    description="Add a component to a KiCad schematic",
    parameters={
        "schematic_path": {
            "type": "string",
            "description": "Path to the KiCad schematic file"
        },
        "library": {
            "type": "string",
            "description": "Symbol library name"
        },
        "symbol": {
            "type": "string",
            "description": "Symbol name within the library"
        },
        "x": {
            "type": "number",
            "description": "X coordinate for component placement (in mm)"
        },
        "y": {
            "type": "number",
            "description": "Y coordinate for component placement (in mm)"
        },
        "reference": {
            "type": "string",
            "description": "Reference designator for the component (e.g., R1, C3)",
            "required": False
        },
        "value": {
            "type": "string",
            "description": "Value for the component (e.g., 10K, 0.1uF)",
            "required": False
        },
        "rotation": {
            "type": "number",
            "description": "Rotation angle in degrees",
            "required": False
        }
    }
)
async def add_schematic_component(
    schematic_path: str,
    library: str,
    symbol: str,
    x: float,
    y: float,
    reference: Optional[str] = None,
    value: Optional[str] = None,
    rotation: Optional[float] = 0
) -> Dict[str, Any]:
    """
    Add a component to a KiCad schematic using the IPC API.
    
    Args:
        schematic_path: Path to the schematic file
        library: Symbol library name
        symbol: Symbol name within the library
        x: X coordinate for placement
        y: Y coordinate for placement
        reference: Reference designator
        value: Component value
        rotation: Rotation angle in degrees
        
    Returns:
        Dict with information about the added component
    """
    # Check if schematic exists
    if not os.path.exists(schematic_path):
        raise McpError(f"Schematic file does not exist: {schematic_path}")
    
    # In a real implementation, we would use the IPC API to add the component
    # For now, we'll create a Python script to run with KiCad's Python console
    
    # Create a temporary script
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="kicad_script_")
    os.close(fd)
    register_temp_dir(os.path.dirname(script_path))
    
    with open(script_path, "w") as f:
        f.write(f"""
import pcbnew
import os
from pcbnew import *
import eeschema

# Load the schematic
sch = eeschema.LoadSchematic("{schematic_path}")

# Create a new component
lib_id = "{library}:{symbol}"
component = sch.AddSymbol(lib_id)

# Set the component position
component.SetPosition(VECTOR2I(FromMM({x}), FromMM({y})))

# Set rotation if specified
component.SetOrientation({rotation})

# Set reference if specified
if "{reference}":
    component.SetReference("{reference}")

# Set value if specified
if "{value}":
    component.SetValue("{value}")

# Save the schematic
sch.Save()

print("Component added successfully")
""")
    
    # Get KiCad command
    kicad_cmd = get_kicad_command()
    if not kicad_cmd:
        raise McpError("KiCad executable not found")
    
    # Execute the script with KiCad's Python interpreter
    try:
        cmd = [kicad_cmd, "--run", script_path, schematic_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": "Component added successfully",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise McpError(f"Failed to add component: {e.stderr}")
    finally:
        # Clean up temporary script
        try:
            os.remove(script_path)
        except:
            pass


@tool(
    name="add_schematic_wire",
    description="Add a wire between points in a KiCad schematic",
    parameters={
        "schematic_path": {
            "type": "string", 
            "description": "Path to the KiCad schematic file"
        },
        "start_x": {
            "type": "number",
            "description": "X coordinate for wire start point (in mm)"
        },
        "start_y": {
            "type": "number",
            "description": "Y coordinate for wire start point (in mm)"
        },
        "end_x": {
            "type": "number", 
            "description": "X coordinate for wire end point (in mm)"
        },
        "end_y": {
            "type": "number",
            "description": "Y coordinate for wire end point (in mm)"
        }
    }
)
async def add_schematic_wire(
    schematic_path: str,
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float
) -> Dict[str, Any]:
    """
    Add a wire between points in a KiCad schematic using the IPC API.
    
    Args:
        schematic_path: Path to the schematic file
        start_x: X coordinate for wire start point
        start_y: Y coordinate for wire start point
        end_x: X coordinate for wire end point
        end_y: Y coordinate for wire end point
        
    Returns:
        Dict with information about the added wire
    """
    # Check if schematic exists
    if not os.path.exists(schematic_path):
        raise McpError(f"Schematic file does not exist: {schematic_path}")
    
    # Create a temporary script
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="kicad_script_")
    os.close(fd)
    register_temp_dir(os.path.dirname(script_path))
    
    with open(script_path, "w") as f:
        f.write(f"""
import pcbnew
import os
from pcbnew import *
import eeschema

# Load the schematic
sch = eeschema.LoadSchematic("{schematic_path}")

# Create a new wire
start_point = VECTOR2I(FromMM({start_x}), FromMM({start_y}))
end_point = VECTOR2I(FromMM({end_x}), FromMM({end_y}))
wire = sch.AddWire(start_point, end_point)

# Save the schematic
sch.Save()

print("Wire added successfully")
""")
    
    # Get KiCad command
    kicad_cmd = get_kicad_command()
    if not kicad_cmd:
        raise McpError("KiCad executable not found")
    
    # Execute the script with KiCad's Python interpreter
    try:
        cmd = [kicad_cmd, "--run", script_path, schematic_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": "Wire added successfully",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise McpError(f"Failed to add wire: {e.stderr}")
    finally:
        # Clean up temporary script
        try:
            os.remove(script_path)
        except:
            pass


@tool(
    name="create_schematic_sheet",
    description="Create a hierarchical sheet in a KiCad schematic",
    parameters={
        "schematic_path": {
            "type": "string",
            "description": "Path to the KiCad schematic file"
        },
        "sheet_name": {
            "type": "string",
            "description": "Name of the hierarchical sheet"
        },
        "x": {
            "type": "number", 
            "description": "X coordinate for sheet placement (in mm)"
        },
        "y": {
            "type": "number",
            "description": "Y coordinate for sheet placement (in mm)"
        },
        "width": {
            "type": "number",
            "description": "Sheet width (in mm)",
            "required": False
        },
        "height": {
            "type": "number",
            "description": "Sheet height (in mm)",
            "required": False
        }
    }
)
async def create_schematic_sheet(
    schematic_path: str,
    sheet_name: str,
    x: float,
    y: float,
    width: Optional[float] = 100.0,
    height: Optional[float] = 70.0
) -> Dict[str, Any]:
    """
    Create a hierarchical sheet in a KiCad schematic using the IPC API.
    
    Args:
        schematic_path: Path to the schematic file
        sheet_name: Name of the hierarchical sheet
        x: X coordinate for sheet placement
        y: Y coordinate for sheet placement
        width: Sheet width in mm
        height: Sheet height in mm
        
    Returns:
        Dict with information about the created sheet
    """
    # Check if schematic exists
    if not os.path.exists(schematic_path):
        raise McpError(f"Schematic file does not exist: {schematic_path}")
    
    # Create a temporary script
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="kicad_script_")
    os.close(fd)
    register_temp_dir(os.path.dirname(script_path))
    
    with open(script_path, "w") as f:
        f.write(f"""
import pcbnew
import os
from pcbnew import *
import eeschema

# Load the schematic
sch = eeschema.LoadSchematic("{schematic_path}")

# Create a new hierarchical sheet
sheet = sch.AddSheet()
sheet.SetName("{sheet_name}")
sheet.SetPosition(VECTOR2I(FromMM({x}), FromMM({y})))
sheet.SetSize(VECTOR2I(FromMM({width}), FromMM({height})))

# Save the schematic
sch.Save()

print("Hierarchical sheet created successfully")
""")
    
    # Get KiCad command
    kicad_cmd = get_kicad_command()
    if not kicad_cmd:
        raise McpError("KiCad executable not found")
    
    # Execute the script with KiCad's Python interpreter
    try:
        cmd = [kicad_cmd, "--run", script_path, schematic_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": "Hierarchical sheet created successfully",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise McpError(f"Failed to create hierarchical sheet: {e.stderr}")
    finally:
        # Clean up temporary script
        try:
            os.remove(script_path)
        except:
            pass


@tool(
    name="create_schematic_label",
    description="Add a label to a KiCad schematic",
    parameters={
        "schematic_path": {
            "type": "string",
            "description": "Path to the KiCad schematic file"
        },
        "text": {
            "type": "string",
            "description": "Text content of the label"
        },
        "x": {
            "type": "number",
            "description": "X coordinate for label placement (in mm)"
        },
        "y": {
            "type": "number",
            "description": "Y coordinate for label placement (in mm)"
        },
        "size": {
            "type": "number",
            "description": "Text size (in mm)",
            "required": False
        },
        "rotation": {
            "type": "number",
            "description": "Rotation angle in degrees",
            "required": False
        }
    }
)
async def create_schematic_label(
    schematic_path: str,
    text: str,
    x: float,
    y: float,
    size: Optional[float] = 1.27,
    rotation: Optional[float] = 0
) -> Dict[str, Any]:
    """
    Add a label to a KiCad schematic using the IPC API.
    
    Args:
        schematic_path: Path to the schematic file
        text: Text content of the label
        x: X coordinate for label placement
        y: Y coordinate for label placement
        size: Text size in mm
        rotation: Rotation angle in degrees
        
    Returns:
        Dict with information about the created label
    """
    # Check if schematic exists
    if not os.path.exists(schematic_path):
        raise McpError(f"Schematic file does not exist: {schematic_path}")
    
    # Create a temporary script
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="kicad_script_")
    os.close(fd)
    register_temp_dir(os.path.dirname(script_path))
    
    with open(script_path, "w") as f:
        f.write(f"""
import pcbnew
import os
from pcbnew import *
import eeschema

# Load the schematic
sch = eeschema.LoadSchematic("{schematic_path}")

# Create a new label
label = sch.AddLabel()
label.SetText("{text}")
label.SetPosition(VECTOR2I(FromMM({x}), FromMM({y})))
label.SetTextSize(FromMM({size}))
label.SetOrientation({rotation})

# Save the schematic
sch.Save()

print("Label created successfully")
""")
    
    # Get KiCad command
    kicad_cmd = get_kicad_command()
    if not kicad_cmd:
        raise McpError("KiCad executable not found")
    
    # Execute the script with KiCad's Python interpreter
    try:
        cmd = [kicad_cmd, "--run", script_path, schematic_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": "Label created successfully",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise McpError(f"Failed to create label: {e.stderr}")
    finally:
        # Clean up temporary script
        try:
            os.remove(script_path)
        except:
            pass


@tool(
    name="create_schematic_bus",
    description="Add a bus to a KiCad schematic",
    parameters={
        "schematic_path": {
            "type": "string",
            "description": "Path to the KiCad schematic file"
        },
        "name": {
            "type": "string",
            "description": "Name of the bus (e.g., DATA[0..7])"
        },
        "start_x": {
            "type": "number",
            "description": "X coordinate for bus start point (in mm)"
        },
        "start_y": {
            "type": "number",
            "description": "Y coordinate for bus start point (in mm)"
        },
        "end_x": {
            "type": "number",
            "description": "X coordinate for bus end point (in mm)"
        },
        "end_y": {
            "type": "number",
            "description": "Y coordinate for bus end point (in mm)"
        }
    }
)
async def create_schematic_bus(
    schematic_path: str,
    name: str,
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float
) -> Dict[str, Any]:
    """
    Add a bus to a KiCad schematic using the IPC API.
    
    Args:
        schematic_path: Path to the schematic file
        name: Name of the bus
        start_x: X coordinate for bus start point
        start_y: Y coordinate for bus start point
        end_x: X coordinate for bus end point
        end_y: Y coordinate for bus end point
        
    Returns:
        Dict with information about the created bus
    """
    # Check if schematic exists
    if not os.path.exists(schematic_path):
        raise McpError(f"Schematic file does not exist: {schematic_path}")
    
    # Create a temporary script
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="kicad_script_")
    os.close(fd)
    register_temp_dir(os.path.dirname(script_path))
    
    with open(script_path, "w") as f:
        f.write(f"""
import pcbnew
import os
from pcbnew import *
import eeschema

# Load the schematic
sch = eeschema.LoadSchematic("{schematic_path}")

# Create a new bus
start_point = VECTOR2I(FromMM({start_x}), FromMM({start_y}))
end_point = VECTOR2I(FromMM({end_x}), FromMM({end_y}))
bus = sch.AddBus(start_point, end_point)
bus.SetName("{name}")

# Save the schematic
sch.Save()

print("Bus created successfully")
""")
    
    # Get KiCad command
    kicad_cmd = get_kicad_command()
    if not kicad_cmd:
        raise McpError("KiCad executable not found")
    
    # Execute the script with KiCad's Python interpreter
    try:
        cmd = [kicad_cmd, "--run", script_path, schematic_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": "Bus created successfully",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise McpError(f"Failed to create bus: {e.stderr}")
    finally:
        # Clean up temporary script
        try:
            os.remove(script_path)
        except:
            pass


@tool(
    name="save_schematic",
    description="Save changes to a KiCad schematic",
    parameters={
        "schematic_path": {
            "type": "string",
            "description": "Path to the KiCad schematic file to save"
        }
    }
)
async def save_schematic(schematic_path: str) -> Dict[str, Any]:
    """
    Save changes to a KiCad schematic using the IPC API.
    
    Args:
        schematic_path: Path to the schematic file to save
        
    Returns:
        Dict with information about the save operation
    """
    # Check if schematic exists
    if not os.path.exists(schematic_path):
        raise McpError(f"Schematic file does not exist: {schematic_path}")
    
    # Create a temporary script
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="kicad_script_")
    os.close(fd)
    register_temp_dir(os.path.dirname(script_path))
    
    with open(script_path, "w") as f:
        f.write(f"""
import pcbnew
import os
from pcbnew import *
import eeschema

# Load the schematic
sch = eeschema.LoadSchematic("{schematic_path}")

# Save the schematic
sch.Save()

print("Schematic saved successfully")
""")
    
    # Get KiCad command
    kicad_cmd = get_kicad_command()
    if not kicad_cmd:
        raise McpError("KiCad executable not found")
    
    # Execute the script with KiCad's Python interpreter
    try:
        cmd = [kicad_cmd, "--run", script_path, schematic_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": "Schematic saved successfully",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise McpError(f"Failed to save schematic: {e.stderr}")
    finally:
        # Clean up temporary script
        try:
            os.remove(script_path)
        except:
            pass


@tool(
    name="move_schematic_component",
    description="Move a component in a KiCad schematic",
    parameters={
        "schematic_path": {
            "type": "string",
            "description": "Path to the KiCad schematic file"
        },
        "reference": {
            "type": "string",
            "description": "Reference designator of the component to move (e.g., R1, C3)"
        },
        "x": {
            "type": "number",
            "description": "New X coordinate for component placement (in mm)"
        },
        "y": {
            "type": "number",
            "description": "New Y coordinate for component placement (in mm)"
        },
        "rotation": {
            "type": "number",
            "description": "New rotation angle in degrees",
            "required": False
        }
    }
)
async def move_schematic_component(
    schematic_path: str,
    reference: str,
    x: float,
    y: float,
    rotation: Optional[float] = None
) -> Dict[str, Any]:
    """
    Move a component in a KiCad schematic using the IPC API.
    
    Args:
        schematic_path: Path to the schematic file
        reference: Reference designator of the component to move
        x: New X coordinate for placement
        y: New Y coordinate for placement
        rotation: New rotation angle in degrees (if None, keep current rotation)
        
    Returns:
        Dict with information about the moved component
    """
    # Check if schematic exists
    if not os.path.exists(schematic_path):
        raise McpError(f"Schematic file does not exist: {schematic_path}")
    
    # Create a temporary script
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="kicad_script_")
    os.close(fd)
    register_temp_dir(os.path.dirname(script_path))
    
    rotation_code = ""
    if rotation is not None:
        rotation_code = f"    component.SetOrientation({rotation})"
    
    with open(script_path, "w") as f:
        f.write(f"""
import pcbnew
import os
from pcbnew import *
import eeschema

# Load the schematic
sch = eeschema.LoadSchematic("{schematic_path}")

# Find the component by reference
component = None
for c in sch.GetComponents():
    if c.GetReference() == "{reference}":
        component = c
        break

if component is None:
    print(f"Error: Component with reference '{reference}' not found")
    exit(1)

# Set the new position
component.SetPosition(VECTOR2I(FromMM({x}), FromMM({y})))

# Set new rotation if specified
{rotation_code}

# Save the schematic
sch.Save()

print(f"Component {reference} moved successfully")
""")
    
    # Get KiCad command
    kicad_cmd = get_kicad_command()
    if not kicad_cmd:
        raise McpError("KiCad executable not found")
    
    # Execute the script with KiCad's Python interpreter
    try:
        cmd = [kicad_cmd, "--run", script_path, schematic_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": f"Component {reference} moved successfully",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise McpError(f"Failed to move component: {e.stderr}")
    finally:
        # Clean up temporary script
        try:
            os.remove(script_path)
        except:
            pass


@tool(
    name="delete_schematic_component",
    description="Delete a component from a KiCad schematic",
    parameters={
        "schematic_path": {
            "type": "string",
            "description": "Path to the KiCad schematic file"
        },
        "reference": {
            "type": "string",
            "description": "Reference designator of the component to delete (e.g., R1, C3)"
        }
    }
)
async def delete_schematic_component(
    schematic_path: str,
    reference: str
) -> Dict[str, Any]:
    """
    Delete a component from a KiCad schematic using the IPC API.
    
    Args:
        schematic_path: Path to the schematic file
        reference: Reference designator of the component to delete
        
    Returns:
        Dict with information about the delete operation
    """
    # Check if schematic exists
    if not os.path.exists(schematic_path):
        raise McpError(f"Schematic file does not exist: {schematic_path}")
    
    # Create a temporary script
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="kicad_script_")
    os.close(fd)
    register_temp_dir(os.path.dirname(script_path))
    
    with open(script_path, "w") as f:
        f.write(f"""
import pcbnew
import os
from pcbnew import *
import eeschema

# Load the schematic
sch = eeschema.LoadSchematic("{schematic_path}")

# Find the component by reference
component = None
for c in sch.GetComponents():
    if c.GetReference() == "{reference}":
        component = c
        break

if component is None:
    print(f"Error: Component with reference '{reference}' not found")
    exit(1)

# Remove the component
sch.Remove(component)

# Save the schematic
sch.Save()

print(f"Component {reference} deleted successfully")
""")
    
    # Get KiCad command
    kicad_cmd = get_kicad_command()
    if not kicad_cmd:
        raise McpError("KiCad executable not found")
    
    # Execute the script with KiCad's Python interpreter
    try:
        cmd = [kicad_cmd, "--run", script_path, schematic_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": f"Component {reference} deleted successfully",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise McpError(f"Failed to delete component: {e.stderr}")
    finally:
        # Clean up temporary script
        try:
            os.remove(script_path)
        except:
            pass


@tool(
    name="edit_schematic_component",
    description="Edit properties of a component in a KiCad schematic",
    parameters={
        "schematic_path": {
            "type": "string",
            "description": "Path to the KiCad schematic file"
        },
        "reference": {
            "type": "string",
            "description": "Current reference designator of the component (e.g., R1, C3)"
        },
        "new_reference": {
            "type": "string",
            "description": "New reference designator for the component",
            "required": False
        },
        "value": {
            "type": "string",
            "description": "New value for the component (e.g., 10K, 0.1uF)",
            "required": False
        }
    }
)
async def edit_schematic_component(
    schematic_path: str,
    reference: str,
    new_reference: Optional[str] = None,
    value: Optional[str] = None
) -> Dict[str, Any]:
    """
    Edit properties of a component in a KiCad schematic using the IPC API.
    
    Args:
        schematic_path: Path to the schematic file
        reference: Current reference designator of the component
        new_reference: New reference designator for the component
        value: New value for the component
        
    Returns:
        Dict with information about the edit operation
    """
    # Check if schematic exists
    if not os.path.exists(schematic_path):
        raise McpError(f"Schematic file does not exist: {schematic_path}")
    
    # At least one of new_reference or value must be provided
    if new_reference is None and value is None:
        raise McpError("At least one of new_reference or value must be provided")
    
    # Create a temporary script
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="kicad_script_")
    os.close(fd)
    register_temp_dir(os.path.dirname(script_path))
    
    new_ref_code = ""
    if new_reference is not None:
        new_ref_code = f"    component.SetReference(\"{new_reference}\")"
    
    value_code = ""
    if value is not None:
        value_code = f"    component.SetValue(\"{value}\")"
    
    with open(script_path, "w") as f:
        f.write(f"""
import pcbnew
import os
from pcbnew import *
import eeschema

# Load the schematic
sch = eeschema.LoadSchematic("{schematic_path}")

# Find the component by reference
component = None
for c in sch.GetComponents():
    if c.GetReference() == "{reference}":
        component = c
        break

if component is None:
    print(f"Error: Component with reference '{reference}' not found")
    exit(1)

# Set new reference if specified
{new_ref_code}

# Set new value if specified
{value_code}

# Save the schematic
sch.Save()

print(f"Component {reference} edited successfully")
""")
    
    # Get KiCad command
    kicad_cmd = get_kicad_command()
    if not kicad_cmd:
        raise McpError("KiCad executable not found")
    
    # Execute the script with KiCad's Python interpreter
    try:
        cmd = [kicad_cmd, "--run", script_path, schematic_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": f"Component {reference} edited successfully",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise McpError(f"Failed to edit component: {e.stderr}")
    finally:
        # Clean up temporary script
        try:
            os.remove(script_path)
        except:
            pass


@tool(
    name="delete_schematic_wire",
    description="Delete a wire from a KiCad schematic",
    parameters={
        "schematic_path": {
            "type": "string",
            "description": "Path to the KiCad schematic file"
        },
        "start_x": {
            "type": "number",
            "description": "X coordinate for wire start point (in mm)"
        },
        "start_y": {
            "type": "number",
            "description": "Y coordinate for wire start point (in mm)"
        },
        "end_x": {
            "type": "number",
            "description": "X coordinate for wire end point (in mm)"
        },
        "end_y": {
            "type": "number",
            "description": "Y coordinate for wire end point (in mm)"
        },
        "tolerance_mm": {
            "type": "number",
            "description": "Tolerance for wire endpoint matching (in mm)",
            "required": False
        }
    }
)
async def delete_schematic_wire(
    schematic_path: str,
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    tolerance_mm: Optional[float] = 1.0
) -> Dict[str, Any]:
    """
    Delete a wire from a KiCad schematic using the IPC API.
    
    Args:
        schematic_path: Path to the schematic file
        start_x: X coordinate for wire start point
        start_y: Y coordinate for wire start point
        end_x: X coordinate for wire end point
        end_y: Y coordinate for wire end point
        tolerance_mm: Tolerance for wire endpoint matching
        
    Returns:
        Dict with information about the delete operation
    """
    # Check if schematic exists
    if not os.path.exists(schematic_path):
        raise McpError(f"Schematic file does not exist: {schematic_path}")
    
    # Create a temporary script
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="kicad_script_")
    os.close(fd)
    register_temp_dir(os.path.dirname(script_path))
    
    with open(script_path, "w") as f:
        f.write(f"""
import pcbnew
import os
import math
from pcbnew import *
import eeschema

# Load the schematic
sch = eeschema.LoadSchematic("{schematic_path}")

# Convert mm to internal units
start_point_x = FromMM({start_x})
start_point_y = FromMM({start_y})
end_point_x = FromMM({end_x})
end_point_y = FromMM({end_y})
tolerance = FromMM({tolerance_mm})

# Function to check if two points are close enough
def points_match(p1, p2, tol):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2) <= tol

# Find matching wires
wires_to_delete = []
for wire in sch.GetWires():
    wire_start = wire.GetStart()
    wire_end = wire.GetEnd()
    
    # Check both orientations of the wire
    if (points_match(wire_start, VECTOR2I(start_point_x, start_point_y), tolerance) and 
        points_match(wire_end, VECTOR2I(end_point_x, end_point_y), tolerance)) or \
       (points_match(wire_start, VECTOR2I(end_point_x, end_point_y), tolerance) and 
        points_match(wire_end, VECTOR2I(start_point_x, start_point_y), tolerance)):
        wires_to_delete.append(wire)

if not wires_to_delete:
    print("Error: No matching wire found at the specified coordinates")
    exit(1)

# Remove the wires
for wire in wires_to_delete:
    sch.Remove(wire)

# Save the schematic
sch.Save()

print(f"Deleted {len(wires_to_delete)} wire(s) successfully")
""")
    
    # Get KiCad command
    kicad_cmd = get_kicad_command()
    if not kicad_cmd:
        raise McpError("KiCad executable not found")
    
    # Execute the script with KiCad's Python interpreter
    try:
        cmd = [kicad_cmd, "--run", script_path, schematic_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": "Wire deleted successfully",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise McpError(f"Failed to delete wire: {e.stderr}")
    finally:
        # Clean up temporary script
        try:
            os.remove(script_path)
        except:
            pass


@tool(
    name="edit_schematic_label",
    description="Edit a label in a KiCad schematic",
    parameters={
        "schematic_path": {
            "type": "string",
            "description": "Path to the KiCad schematic file"
        },
        "x": {
            "type": "number",
            "description": "X coordinate of the label to edit (in mm)"
        },
        "y": {
            "type": "number",
            "description": "Y coordinate of the label to edit (in mm)"
        },
        "new_text": {
            "type": "string",
            "description": "New text content for the label",
            "required": False
        },
        "new_x": {
            "type": "number",
            "description": "New X coordinate for label placement (in mm)",
            "required": False
        },
        "new_y": {
            "type": "number",
            "description": "New Y coordinate for label placement (in mm)",
            "required": False
        },
        "new_size": {
            "type": "number",
            "description": "New text size (in mm)",
            "required": False
        },
        "tolerance_mm": {
            "type": "number",
            "description": "Tolerance for label position matching (in mm)",
            "required": False
        }
    }
)
async def edit_schematic_label(
    schematic_path: str,
    x: float,
    y: float,
    new_text: Optional[str] = None,
    new_x: Optional[float] = None,
    new_y: Optional[float] = None,
    new_size: Optional[float] = None,
    tolerance_mm: Optional[float] = 1.0
) -> Dict[str, Any]:
    """
    Edit a label in a KiCad schematic using the IPC API.
    
    Args:
        schematic_path: Path to the schematic file
        x: X coordinate of the label to edit
        y: Y coordinate of the label to edit
        new_text: New text content for the label
        new_x: New X coordinate for label placement
        new_y: New Y coordinate for label placement
        new_size: New text size in mm
        tolerance_mm: Tolerance for label position matching
        
    Returns:
        Dict with information about the edit operation
    """
    # Check if schematic exists
    if not os.path.exists(schematic_path):
        raise McpError(f"Schematic file does not exist: {schematic_path}")
    
    # At least one edit parameter must be provided
    if new_text is None and new_x is None and new_y is None and new_size is None:
        raise McpError("At least one of new_text, new_x, new_y, or new_size must be provided")
    
    # Create a temporary script
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="kicad_script_")
    os.close(fd)
    register_temp_dir(os.path.dirname(script_path))
    
    # Prepare the edit commands
    edit_commands = []
    if new_text is not None:
        edit_commands.append(f'    label.SetText("{new_text}")')
    
    position_code = ""
    if new_x is not None or new_y is not None:
        # Use current coordinates for any not specified
        pos_x = f"FromMM({new_x})" if new_x is not None else "label.GetPosition().x"
        pos_y = f"FromMM({new_y})" if new_y is not None else "label.GetPosition().y"
        position_code = f"    label.SetPosition(VECTOR2I({pos_x}, {pos_y}))"
        edit_commands.append(position_code)
    
    if new_size is not None:
        edit_commands.append(f"    label.SetTextSize(FromMM({new_size}))")
    
    edit_code = "\n".join(edit_commands)
    
    with open(script_path, "w") as f:
        f.write(f"""
import pcbnew
import os
import math
from pcbnew import *
import eeschema

# Load the schematic
sch = eeschema.LoadSchematic("{schematic_path}")

# Convert mm to internal units
target_x = FromMM({x})
target_y = FromMM({y})
tolerance = FromMM({tolerance_mm})

# Function to check if two points are close enough
def points_match(p1, p2, tol):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2) <= tol

# Find matching label
label = None
for l in sch.GetLabels():
    pos = l.GetPosition()
    if points_match(pos, VECTOR2I(target_x, target_y), tolerance):
        label = l
        break

if label is None:
    print("Error: No label found at the specified coordinates")
    exit(1)

# Edit the label
{edit_code}

# Save the schematic
sch.Save()

print("Label edited successfully")
""")
    
    # Get KiCad command
    kicad_cmd = get_kicad_command()
    if not kicad_cmd:
        raise McpError("KiCad executable not found")
    
    # Execute the script with KiCad's Python interpreter
    try:
        cmd = [kicad_cmd, "--run", script_path, schematic_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": "Label edited successfully",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise McpError(f"Failed to edit label: {e.stderr}")
    finally:
        # Clean up temporary script
        try:
            os.remove(script_path)
        except:
            pass 