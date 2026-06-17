import glob
import re
import os

files = glob.glob('app/models/*.py') + glob.glob('app/repositories/interfaces/*.py')

for fpath in files:
    if '__init__' in fpath:
        continue
    with open(fpath, 'r') as f:
        content = f.read()

    # Find the TYPE_CHECKING block
    match = re.search(r'if TYPE_CHECKING:\n((?:\s+(?:from|import) .*?\n)+)', content)
    if match:
        imports_str = match.group(1)
        # Extract the lines and strip whitespace
        imports = [line.strip() for line in imports_str.strip().split('\n')]
        
        # Remove the TYPE_CHECKING block
        content = content.replace(match.group(0), '')
        
        # Add the imports to the top of the file, after from __future__ import annotations
        lines = content.split('\n')
        future_idx = -1
        for i, line in enumerate(lines):
            if line.startswith('from __future__ import annotations'):
                future_idx = i
                break
        
        if future_idx != -1:
            for imp in reversed(imports):
                lines.insert(future_idx + 1, imp)
            content = '\n'.join(lines)
            with open(fpath, 'w') as f:
                f.write(content)
        else:
            # Just put at top
            content = '\n'.join(imports) + '\n' + content
            with open(fpath, 'w') as f:
                f.write(content)
