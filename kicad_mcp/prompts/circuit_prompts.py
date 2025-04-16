"""
Prompt templates for circuit creation tasks.
"""
from mcp.server.fastmcp import FastMCP

# Creating custom prompt classes compatible with new MCP SDK
class PromptTemplate:
    def __init__(self, name, description, prompt_template):
        self.name = name
        self.description = description
        self.prompt_template = prompt_template
        self.template = prompt_template  # Some versions use .template instead of .prompt_template

# Custom prompt implementation
def create_schematic_prompt_impl():
    return ""

def create_pcb_prompt_impl():
    return ""

def create_simple_circuit_prompt_impl():
    return ""

def edit_schematic_prompt_impl():
    return ""

def edit_pcb_prompt_impl():
    return ""

# Create prompt objects for new SDK
create_schematic_prompt = PromptTemplate(
    name="create_schematic_prompt",
    description="Creating a new schematic from scratch",
    prompt_template="""
You are helping to create a new KiCad schematic file.

# Available Tools

You have access to the following schematic creation tools:
- `create_schematic`: Create a new blank schematic file
- `add_schematic_component`: Add a component to a schematic
- `add_schematic_wire`: Add a wire connection between points
- `create_schematic_sheet`: Create a hierarchical sheet
- `create_schematic_label`: Add a label to a schematic
- `create_schematic_bus`: Add a bus to a schematic
- `save_schematic`: Save changes to a schematic file

# Instructions

Please help me create a new schematic by:
1. First asking about the project name, location, and the type of circuit I want to create
2. Create a new schematic file using the information provided
3. Guide me through adding components, wires, and other elements to the schematic
4. Provide clear explanations of the circuit design principles as we build the schematic

I may have specific requirements for the circuit, or I might ask you to suggest common circuit patterns (like power supplies, amplifiers, etc.) that I can use as a starting point.
"""
)

create_pcb_prompt = PromptTemplate(
    name="create_pcb_prompt",
    description="Creating a new PCB from scratch",
    prompt_template="""
You are helping to create a new KiCad PCB file.

# Available Tools

You have access to the following PCB creation tools:
- `create_pcb`: Create a new blank PCB file
- `add_pcb_footprint`: Add a footprint to a PCB
- `add_pcb_track`: Add a track connection between points
- `add_pcb_via`: Add a via to a PCB
- `add_pcb_zone`: Add a copper zone/pour to a PCB
- `save_pcb`: Save changes to a PCB file

# Instructions

Please help me create a new PCB by:
1. First asking about the project name, location, and PCB dimensions
2. Create a new PCB file using the information provided
3. Guide me through adding footprints, tracks, vias, and zones to the PCB
4. Provide clear explanations of PCB design principles and best practices as we build the board

I may have specific requirements for the PCB layout, or I might ask you to suggest common layout patterns and techniques.
"""
)

create_simple_circuit_prompt = PromptTemplate(
    name="create_simple_circuit_prompt",
    description="Creating a complete simple circuit with schematic and PCB",
    prompt_template="""
You are helping to create a complete circuit project with both a schematic and PCB layout.

# Available Tools

You have access to tools for both schematic and PCB creation:

Schematic Tools:
- `create_schematic`: Create a new blank schematic file
- `add_schematic_component`: Add a component to a schematic
- `add_schematic_wire`: Add a wire connection between points
- `create_schematic_sheet`: Create a hierarchical sheet
- `create_schematic_label`: Add a label to a schematic
- `create_schematic_bus`: Add a bus to a schematic
- `save_schematic`: Save changes to a schematic file

PCB Tools:
- `create_pcb`: Create a new blank PCB file
- `add_pcb_footprint`: Add a footprint to a PCB
- `add_pcb_track`: Add a track connection between points
- `add_pcb_via`: Add a via to a PCB
- `add_pcb_zone`: Add a copper zone/pour to a PCB
- `save_pcb`: Save changes to a PCB file

# Instructions

Please help me create a complete circuit project by:
1. First asking about the project name, location, and the type of circuit I want to create
2. Creating both a schematic and PCB file using the information provided
3. Guiding me through the schematic design process first
4. Then helping me design the corresponding PCB layout
5. Providing clear explanations of both circuit and PCB design principles as we go

I may ask for a specific type of circuit, such as:
- LED blinker with 555 timer
- Arduino shield
- Simple power supply
- Sensor interface circuit
- Audio amplifier

For each type, you should guide me through the appropriate components, connections, and layout considerations.
"""
)

edit_schematic_prompt = PromptTemplate(
    name="edit_schematic_prompt",
    description="Editing an existing schematic",
    prompt_template="""
You are helping to edit an existing KiCad schematic file.

# Available Tools

You have access to the following schematic editing tools:

Creation Tools:
- `add_schematic_component`: Add a component to a schematic
- `add_schematic_wire`: Add a wire connection between points
- `create_schematic_sheet`: Create a hierarchical sheet
- `create_schematic_label`: Add a label to a schematic
- `create_schematic_bus`: Add a bus to a schematic

Edit Tools:
- `move_schematic_component`: Move a component in the schematic
- `delete_schematic_component`: Delete a component from the schematic
- `edit_schematic_component`: Edit properties of a component (reference, value)
- `delete_schematic_wire`: Delete a wire from the schematic
- `edit_schematic_label`: Edit a label in the schematic
- `save_schematic`: Save changes to a schematic file

# Instructions

Please help me edit an existing schematic by:
1. First asking about the path to the schematic file I want to edit
2. Asking what changes I want to make to the schematic
3. Using the appropriate tools to make the requested changes
4. Providing clear explanations of what each change does and how it affects the overall circuit
5. Saving the changes when done

I may need help with various editing tasks such as:
- Moving components to improve the layout
- Deleting unwanted components or wires
- Editing component properties
- Adding new components or connections to extend functionality
- Reorganizing sections of the circuit
"""
)

edit_pcb_prompt = PromptTemplate(
    name="edit_pcb_prompt",
    description="Editing an existing PCB layout",
    prompt_template="""
You are helping to edit an existing KiCad PCB file.

# Available Tools

You have access to the following PCB editing tools:

Creation Tools:
- `add_pcb_footprint`: Add a footprint to a PCB
- `add_pcb_track`: Add a track connection between points
- `add_pcb_via`: Add a via to a PCB
- `add_pcb_zone`: Add a copper zone/pour to a PCB

Edit Tools:
- `move_pcb_footprint`: Move a footprint on the PCB
- `delete_pcb_footprint`: Delete a footprint from the PCB
- `edit_pcb_footprint`: Edit properties of a footprint (reference, value, layer)
- `delete_pcb_track`: Delete a track from the PCB
- `move_pcb_via`: Move a via on the PCB
- `delete_pcb_via`: Delete a via from the PCB
- `delete_pcb_zone`: Delete a copper zone/pour from the PCB
- `save_pcb`: Save changes to a PCB file

# Instructions

Please help me edit an existing PCB by:
1. First asking about the path to the PCB file I want to edit
2. Asking what changes I want to make to the PCB layout
3. Using the appropriate tools to make the requested changes
4. Providing clear explanations of what each change does and how it affects the overall layout
5. Saving the changes when done

I may need help with various editing tasks such as:
- Moving footprints to improve the layout
- Deleting unwanted footprints, tracks, or vias
- Editing footprint properties
- Adding new footprints, tracks, or vias to extend functionality
- Reorganizing sections of the PCB
- Adjusting the copper zones
"""
)

def register_circuit_prompts(app: FastMCP) -> None:
    """Register all circuit creation related prompts."""
    # Always use add_prompt for the new SDK as we've created compatible prompt objects
    try:
        app.add_prompt(create_schematic_prompt)
        app.add_prompt(create_pcb_prompt)
        app.add_prompt(create_simple_circuit_prompt)
        app.add_prompt(edit_schematic_prompt)
        app.add_prompt(edit_pcb_prompt)
    except Exception as e:
        print(f"Failed to register circuit prompts: {str(e)}")
        # Fallback to legacy API if needed
        try:
            app.register_prompts(
                create_schematic_prompt,
                create_pcb_prompt,
                create_simple_circuit_prompt,
                edit_schematic_prompt,
                edit_pcb_prompt
            )
        except Exception as e2:
            print(f"Failed to register circuit prompts with legacy API: {str(e2)}") 