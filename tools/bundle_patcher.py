import os
import json
import subprocess

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
metadata_path = os.path.join(BASE_PATH, 'assets', 'metadata.oldjson')

try:
    with open(metadata_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    last_item = data[-1]
    current_version = last_item['versionNumber']
    version_parts = list(map(int, current_version.split('.')))
    version_parts[-1] += 1
    new_version = '.'.join(map(str, version_parts))
    command = ['python', 'main.py', 'b', '-i', 'assets', '-o', new_version]
    result = subprocess.run(command, cwd=BASE_PATH, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    input("Press Enter to continue...")
    
except Exception as e:
    print(f"Error: {str(e)}")
