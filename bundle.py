import os

# Files and folders to strictly ignore
IGNORE_DIRS = {'.venv', 'venv', '__pycache__', '.git', 'logs'}
IGNORE_FILES = {'.env', 'bundle.py'}
VALID_EXTENSIONS = {'.py', '.json', '.yaml', '.yml', '.md', '.txt', '.toml'}

output_file = "../Hari_Core_Codebase.txt"

with open(output_file, "w", encoding="utf-8") as f:
    f.write("=== PROJECT STRUCTURE ===\n")
    
    # First, write out the clean directory tree structure
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        level = root.replace('.', '').count(os.sep)
        indent = ' ' * 4 * (level)
        f.write(f"{indent}{os.path.basename(root)}/\n")
        sub_indent = ' ' * 4 * (level + 1)
        for file in files:
            if file not in IGNORE_FILES and os.path.splitext(file)[1] in VALID_EXTENSIONS:
                f.write(f"{sub_indent}{file}\n")
                
    f.write("\n=== FILE CONTENTS ===\n")
    
    # Second, dump the contents of each file safely
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for file in files:
            if file not in IGNORE_FILES and os.path.splitext(file)[1] in VALID_EXTENSIONS:
                filepath = os.path.join(root, file)
                f.write(f"\n\n--- START OF FILE: {filepath} ---\n")
                try:
                    with open(filepath, "r", encoding="utf-8") as source_f:
                        f.write(source_f.read())
                except Exception as e:
                    f.write(f"[Could not read file: {e}]\n")
                f.write(f"\n--- END OF FILE: {filepath} ---\n")

print(f"Successfully generated: {os.path.abspath(output_file)}")
