import os
import subprocess
import logging
from data.paths import JoinPaths
from menus.menu import Menu
from data.settings import Settings
from data.colors import ColorFormat, Colors
from processes.process import LaunchProcess

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
    """Check if required Kconfig tools are available."""
    required_tools = ['kconfig-conf', 'kconfig-mconf']
    missing_tools = []
    
    for tool in required_tools:
        if not find_kconfig_tool(tool):
            missing_tools.append(tool)
    
    if missing_tools:
        logging.error(f"Error: Missing required tools: {', '.join(missing_tools)}")
        logging.error("Please install kconfig-frontends package.")
        return False
    return True

def RunMenuConfig():
    """Run Kconfig menuconfig interface."""
    if not EnsureKConfigTools():
        return

    mconf_tool = find_kconfig_tool('kconfig-mconf')
    project_root = Settings["paths"]["project configs"]
    # kconfig_path = os.path.join(project_root, "Kconfig")
    
    # Run menuconfig
    try:
        command = f'{mconf_tool}  {JoinPaths(project_root, "Kconfig")}'
        command = f'cd {Settings["paths"]["project configs"]}; {command}'
        logging.error(command)
        subprocess.run(command, shell=True)
        # subprocess.run([mconf_tool, kconfig_path], check=True)
        
        # Generate CMake and header files after configuration
        # build_dir = os.path.join(project_root, "build")
        # subprocess.run([
        #     "python",
        #     os.path.join(project_root, "scripts/kconfig_handler.py"),
        #     project_root,
        #     os.path.join(project_root, ".config"),
        #     build_dir
        # ], check=True)
        
        logging.error(ColorFormat(Colors.Green, "Configuration saved and processed successfully"))
    except subprocess.CalledProcessError as e:
        logging.error(ColorFormat(Colors.Red, f"Error running menuconfig: {e}"))

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