import json
import re

# Load your KB file
with open('tests_kb_v2.json', 'r', encoding='utf-8') as f:
    kb = json.load(f)

# Helper: generate aliases for a test name

def generate_aliases(test_name):
    aliases = set()
    name = test_name.lower().strip()
    # Add canonical
    aliases.add(name)
    # Remove parentheticals
    name_noparen = re.sub(r'\s*\([^)]*\)', '', name).strip()
    if name_noparen and name_noparen != name:
        aliases.add(name_noparen)
    # Add common abbreviations
    abbr = re.findall(r'\(([^)]+)\)', test_name)
    for a in abbr:
        aliases.add(a.lower().strip())
    # Add space/underscore/dash variants
    aliases.update({name.replace('_', ' '), name.replace('-', ' ')})
    return sorted(a for a in aliases if a)

# Expand KB entries
for entry in kb:
    test_name = entry.get('test_name', '')
    aliases = set(entry.get('aliases', []))
    aliases.update(generate_aliases(test_name))
    entry['aliases'] = sorted(aliases)

# Save expanded KB
with open('tests_kb_v2_expanded.json', 'w', encoding='utf-8') as f:
    json.dump(kb, f, indent=2, ensure_ascii=False)

print('Expanded KB with aliases written to tests_kb_v2_expanded.json')
