import subprocess
import os
import shutil
#PyInstaller is also needed

# === Configuration ===
exe_name = "QuickSilver"
entry_script = "ui.py"
icon_path = "assets/favicon.ico"
folders_to_include = ["assets", "wlan", "blue"]
separator = ';' if os.name == 'nt' else ':'

# === Cleanup old builds ===
for folder in ['build', 'dist']:
    shutil.rmtree(folder, ignore_errors=True)

spec_file = f"{exe_name}.spec"
if os.path.exists(spec_file):
    os.remove(spec_file)

# === Build PyInstaller command ===
add_data_args = []
for folder in folders_to_include:
    add_data_args += ["--add-data", f"{folder}{separator}{folder}"]

command = [
    "python", "-m", "PyInstaller",
    "--onefile",
    "--windowed",
    f"--icon={icon_path}",
    f"--name={exe_name}",
    *add_data_args,
    entry_script
]

print("Running PyInstaller...")
subprocess.run(command, check=True)

# === Move the generated .exe to the project root folder ===
dist_exe_path = os.path.join("dist", f"{exe_name}.exe")
project_root_exe_path = f"{exe_name}.exe"

if os.path.exists(project_root_exe_path):
    os.remove(project_root_exe_path)

shutil.move(dist_exe_path, project_root_exe_path)

# === Final cleanup ===
shutil.rmtree("build", ignore_errors=True)
shutil.rmtree("dist", ignore_errors=True)
if os.path.exists(spec_file):
    os.remove(spec_file)

print(f"Build complete: {project_root_exe_path} is ready in the project folder.")
