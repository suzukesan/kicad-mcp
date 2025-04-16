"""
KiCad-specific utility functions.
"""
import os
import subprocess
from typing import Dict, List, Any, Optional

from kicad_mcp.config import KICAD_USER_DIR, KICAD_APP_PATH, KICAD_EXTENSIONS, ADDITIONAL_SEARCH_PATHS

def find_kicad_projects() -> List[Dict[str, Any]]:
    """Find KiCad projects in the user's directory.
    
    Returns:
        List of dictionaries with project information
    """
    projects = []

    # Search directories to look for KiCad projects
    search_dirs = [KICAD_USER_DIR] + ADDITIONAL_SEARCH_PATHS

    for search_dir in search_dirs:
        if not os.path.exists(search_dir):
            print(f"Search directory does not exist: {search_dir}")
            continue
        
        print(f"Scanning directory: {search_dir}")
        for root, _, files in os.walk(search_dir):
            for file in files:
                if file.endswith(KICAD_EXTENSIONS["project"]):
                    project_path = os.path.join(root, file)
                    rel_path = os.path.relpath(project_path, search_dir)
                    project_name = get_project_name_from_path(project_path)

                    print(f"Found KiCad project: {project_path}")
                    projects.append({
                        "name": project_name,
                        "path": project_path,
                        "relative_path": rel_path,
                        "modified": os.path.getmtime(project_path)
                    })
    
    print(f"Found {len(projects)} KiCad projects")
    return projects


def get_project_name_from_path(project_path: str) -> str:
    """Extract project name from a KiCad project file path.
    
    Args:
        project_path: Path to the .kicad_pro file
        
    Returns:
        Project name without extension
    """
    basename = os.path.basename(project_path)
    if basename.endswith(KICAD_EXTENSIONS["project"]):
        # Remove extension
        return basename[:-len(KICAD_EXTENSIONS["project"])]
    return basename


def open_kicad_project(project_path: str) -> Dict[str, Any]:
    """Open a KiCad project using the KiCad application.
    
    Args:
        project_path: Path to the .kicad_pro file
        
    Returns:
        Dictionary with result information
    """
    if not os.path.exists(project_path):
        return {"success": False, "error": f"Project not found: {project_path}"}
    
    try:
        # On MacOS, use the 'open' command to open the project in KiCad
        cmd = ["open", "-a", KICAD_APP_PATH, project_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "command": " ".join(cmd),
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}


def find_kicad_executable() -> Optional[str]:
    """Find the KiCad executable in the system.
    
    Returns:
        Path to KiCad executable if found, None otherwise
    """
    # Use the configured KiCad application path
    import platform
    system = platform.system()
    
    if system == "Windows":
        # Check for KiCad executable in the application path
        kicad_exe = os.path.join(KICAD_APP_PATH, "bin", "kicad.exe")
        if os.path.exists(kicad_exe):
            return kicad_exe
        
        # Try other common Windows locations
        potential_paths = [
            r"C:\Program Files\KiCad\bin\kicad.exe",
            r"C:\Program Files (x86)\KiCad\bin\kicad.exe",
            os.path.join(KICAD_APP_PATH, "kicad.exe")
        ]
        
        for path in potential_paths:
            if os.path.exists(path):
                return path
                
    elif system == "Darwin":  # macOS
        # Check for KiCad executable in the application path
        kicad_exe = os.path.join(KICAD_APP_PATH, "Contents", "MacOS", "kicad")
        if os.path.exists(kicad_exe):
            return kicad_exe
            
    else:  # Linux and other systems
        # Check if kicad is in PATH
        try:
            result = subprocess.run(["which", "kicad"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
            
        # Try common Linux locations
        potential_paths = [
            "/usr/bin/kicad",
            "/usr/local/bin/kicad"
        ]
        
        for path in potential_paths:
            if os.path.exists(path):
                return path
                
    # If we get here, KiCad executable was not found
    return None


def get_kicad_command() -> Optional[str]:
    """Get the KiCad executable command.
    
    Returns:
        Path to KiCad executable if found, None otherwise
    """
    # Check configured application path first
    import platform
    system = platform.system()
    
    if system == "Windows":
        # For Windows, look for python.exe in KiCad's bin directory
        python_exe = os.path.join(KICAD_APP_PATH, "bin", "python.exe")
        if os.path.exists(python_exe):
            return python_exe
            
        # Check for standard KiCad 9.0 location
        python_exe = os.path.join(KICAD_APP_PATH, "bin", "python.exe")
        if os.path.exists(python_exe):
            return python_exe
            
    elif system == "Darwin":  # macOS
        # For macOS, look for Python in the app bundle
        python_exe = os.path.join(KICAD_APP_PATH, "Contents", "Frameworks", "Python.framework", 
                                 "Versions", "Current", "bin", "python3")
        if os.path.exists(python_exe):
            return python_exe
            
    else:  # Linux and other systems
        # Check for python3 in PATH
        try:
            result = subprocess.run(["which", "python3"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
    
    # If KiCad's Python not found, use system Python as fallback
    return find_kicad_executable()
