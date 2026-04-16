#!/usr/bin/env python3
"""Generate skill_index.yaml from ~/.claude/commands/ skill files."""
import os, re, yaml

def strip_frontmatter(content):
    if content.startswith('---'):
        end = content.find('\n---\n', 3)
        if end != -1:
            return content[end+4:]
    return content

skill_index = {}
cmd_dir = os.path.expanduser('~/.claude/commands')

for fname in sorted(os.listdir(cmd_dir)):
    fpath = os.path.join(cmd_dir, fname)
    if fname.startswith('.') or fname.endswith('.js') or fname.endswith('.json'):
        continue

    if os.path.isdir(fpath):
        skill_md = os.path.join(fpath, 'SKILL.md')
        content = open(skill_md).read() if os.path.isfile(skill_md) else ''
    elif fname.endswith('.md'):
        content = open(fpath).read()
    else:
        continue

    content = strip_frontmatter(content)
    h1 = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = h1.group(1).strip() if h1 else fname
    lines = content.split('\n')
    desc_lines = []
    for line in lines[1:30]:
        s = line.strip()
        if not s or s.startswith('#') or s.startswith('`') or s.startswith('!'):
            if desc_lines:
                break
            continue
        if len(s) > 20:
            desc_lines.append(s)
            if len(desc_lines) >= 2:
                break
    description = ' '.join(desc_lines)[:150]
    skill_id = fname.replace('.md','').replace('-','_')
    skill_index[skill_id] = {
        'name': title,
        'description': description,
        'type': 'harness' if os.path.isdir(fpath) else 'prompt',
        'source_path': f'~/.claude/commands/{fname}'
    }

by_category = {
    'model_routing': {'description': 'Model selection and delegation rules', 'skills': {}},
    'cfd_harness': {'description': 'CFD simulation harness and automation', 'skills': {}},
    'ui_systems': {'description': 'UI and panel systems', 'skills': {}},
    'architecture': {'Description': 'System architecture and patterns', 'skills': {}},
    'uncategorized': {'description': 'Other skills', 'skills': {}}
}

for k, v in skill_index.items():
    if any(x in k for x in ['codex', 'glm', 'gemini', 'minimax', 'm27']):
        by_category['model_routing']['skills'][k] = v
    elif any(x in k for x in ['openfoam', 'dakota', 'su2', 'freecad', 'gmsh', 'paraview', 'cfd']):
        by_category['cfd_harness']['skills'][k] = v
    elif any(x in k for x in ['panel', 'ui']):
        by_category['ui_systems']['skills'][k] = v
    elif any(x in k for x in ['architecture', 'seed', 'gateway', 'multi']):
        by_category['architecture']['skills'][k] = v
    else:
        by_category['uncategorized']['skills'][k] = v

result = yaml.dump(by_category, allow_unicode=True, sort_keys=False, default_flow_style=False)
print(result)
