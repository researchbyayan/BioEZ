"""Copy each diagram's part ids and labels into shared/diagrams.json.

The backend uses them to tell the model which parts it can focus on (for example the femur in
the skeleton) and to validate that focus; the frontend uses them to zoom to the part.
Run after adding or redrawing a diagram: .venv/bin/python scripts/sync-diagram-parts.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'shared' / 'diagrams.json'
ASSETS = ROOT / 'frontend' / 'src' / 'diagrams'


def section_parts(svg):
    parts = []
    for tag in re.finditer(r'<g\b[^>]*>', svg):
        text = tag.group(0)
        if not re.search(r'class="[^"]*\bpart\b', text):
            continue
        part_id = re.search(r'\bid="([^"]+)"', text)
        label = re.search(r'\bdata-label="([^"]+)"', text)
        if part_id:
            parts.append({'id': part_id.group(1), 'label': (label.group(1) if label else part_id.group(1)).replace('&amp;', '&').replace('&#39;', "'")})
    return parts


def main():
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    for entry in catalog:
        if entry['kind'] == 'model':
            meta = json.loads((ASSETS / 'models' / f"{entry['id']}.json").read_text(encoding='utf-8'))
            entry['parts'] = [{'id': p['id'], 'label': p['label']} for p in meta['parts']]
        else:
            entry['parts'] = section_parts((ASSETS / 'sections' / f"{entry['id']}.svg").read_text(encoding='utf-8'))
    CATALOG.write_text('[\n' + ',\n'.join(' ' + json.dumps(e, ensure_ascii=False) for e in catalog) + '\n]\n', encoding='utf-8')
    print(sum(len(e['parts']) for e in catalog), 'parts across', len(catalog), 'diagrams')


if __name__ == '__main__':
    main()
