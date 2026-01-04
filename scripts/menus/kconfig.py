import os
import subprocess
import logging
from data.paths import JoinPaths
from menus.menu import Menu
from data.settings import Settings
from data.colors import ColorFormat, Colors
from processes.repository import ConvertKconfigToHeader
import sys
import kconfiglib


def find_kconfig_tool(tool_name):
    """Find a kconfig tool in common locations."""
    common_paths = [
        f"/usr/bin/{tool_name}",
        f"/usr/local/bin/{tool_name}",
        f"/bin/{tool_name}"
    ]
    for path in common_paths:
        if os.path.exists(path):
            return path
    return None

def EnsureKConfigTools():
    return True



def RunMenuConfig():
    """Run Kconfig interactive menu."""
    project_configs = Settings["paths"]["project configs"]
    root_kconfig = JoinPaths(project_configs, "Kconfig")
    config_file  = JoinPaths(project_configs, ".config")
    
    # Ensure the root file exists before running
    if not os.path.isfile(root_kconfig):
        logging.error(f"Root Kconfig not found at {root_kconfig}")
        return

    # Setup Environment
    env = os.environ.copy()
    env["KCONFIG_CONFIG"] = config_file
    
    # Setting srctree to the project configs folder makes the UI 
    # show simpler paths, but ensure your 'source' paths are absolute 
    # or correctly relative to this root.
    env["srctree"] = project_configs 

    # Command: python -m menuconfig path/to/Kconfig
    # This is the standard way to invoke kconfiglib's menuconfig
    cmd = [sys.executable, "-m", "menuconfig", root_kconfig]
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        subprocess.run(
            cmd,
            cwd=project_configs,
            check=True,
            env=env,
        )
        # After menuconfig closes, we should regenerate headers
        ConvertKconfigToHeader() 
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Menuconfig exited with error: {e}")
    except Exception as e:
        logging.error(f"Failed to launch menuconfig: {e}")


# def save_config():
#     """Save current configuration as default."""
#     if not EnsureKConfigTools():
#         return

#     conf_tool = find_kconfig_tool('kconfig-conf')
#     project_root = Settings["paths"]["project configs"]
    
#     try:
#         command = f'{conf_tool} --save-defconfig=defconfig {JoinPaths(project_root, "Kconfig")}'
#         LaunchProcess(command, Settings["paths"]["project configs"])
#         logging.error(ColorFormat(Colors.Green, "Default configuration saved successfully"))
#     except subprocess.CalledProcessError as e:
#         logging.error(ColorFormat(Colors.Red, f"Error saving configuration: {e}"))

# def load_default_config():
#     """Load default configuration."""
#     if not EnsureKConfigTools():
#         return

#     conf_tool = find_kconfig_tool('kconfig-conf')
#     project_root = Settings["paths"]["project configs"]
    
#     try:
#         subprocess.run([
#             conf_tool,
#             "--defconfig=defconfig",
#             os.path.join(project_root, "Kconfig")
#         ], check=True)
        
#         # Generate CMake and header files after loading defaults
#         build_dir = os.path.join(project_root, "build")
#         subprocess.run([
#             "python",
#             os.path.join(project_root, "scripts/kconfig_handler.py"),
#             project_root,
#             os.path.join(project_root, ".config"),
#             build_dir
#         ], check=True)
        
#         logging.error(ColorFormat(Colors.Green, "Default configuration loaded and processed successfully"))
#     except subprocess.CalledProcessError as e:
#         logging.error(ColorFormat(Colors.Red, f"Error loading configuration: {e}"))

# Create Kconfig submenu
KconfigMenu = Menu("Kconfig Menu", stay_in_menu=True)
KconfigMenu.AddCallbackEntry("Configure build options (menuconfig)", RunMenuConfig)
# KconfigMenu.AddCallbackEntry("Save current configuration as default", save_config)
# KconfigMenu.AddCallbackEntry("Load default configuration", load_default_config) 