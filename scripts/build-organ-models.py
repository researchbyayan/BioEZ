"""Build BioEZ's explorable organ models from the HuBMAP Human Reference Atlas (HRA) v1.2.

Data: HuBMAP CCF 3D Reference Object Library, v1.2, CC BY 4.0
(https://hubmapconsortium.github.io/ccf/pages/ccf-3d-reference-library.html,
GLB files from https://github.com/hubmapconsortium/ccf-releases/tree/main/v1.2/models).

Each named structure in the source becomes one named part (left/right copies and lettered
sub-pieces such as renal pyramids a-i are merged), heavy meshes are simplified, and parts are
coloured by tissue type. Usage:
  .venv/bin/python scripts/build-organ-models.py <folder with the HRA .glb files>
Needs trimesh and fast-simplification (development only).
"""
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

import fast_simplification
import numpy as np
import trimesh

OUT = Path(__file__).resolve().parents[1] / 'frontend' / 'src' / 'diagrams' / 'models'
CREDIT = 'HuBMAP Human Reference Atlas (CCF 3D Reference Object Library v1.2), CC BY 4.0. Simplified for BioEZ.'

# file, BioEZ id, title, face budget
ORGANS = [
    ('VH_M_Heart', 'organ-heart', 'Human heart', 90000),
    ('VH_M_Kidney_L', 'organ-kidney', 'Human kidney', 60000),
    ('VH_F_Eye_L', 'organ-eye', 'Human eye', 90000),
    ('Allen_M_Brain', 'organ-brain', 'Human brain', 170000),
    ('VH_M_Lung', 'organ-lungs', 'Human lungs and airways', 130000),
    ('VH_M_Liver', 'organ-liver', 'Human liver', 60000),
    ('VH_M_Small_Intestine', 'organ-small-intestine', 'Human small intestine', 40000),
    ('SBU_M_Intestine_Large', 'organ-large-intestine', 'Human large intestine', 40000),
    ('VH_M_Pancreas', 'organ-pancreas', 'Human pancreas', 20000),
    ('VH_M_Spleen', 'organ-spleen', 'Human spleen', 20000),
    ('VH_M_Urinary_Bladder', 'organ-bladder', 'Human urinary bladder', 15000),
    ('VH_M_Ureter_L', 'organ-renal-pelvis-ureter', 'Renal pelvis, calyces and ureter', 30000),
    ('VH_M_Spinal_Cord', 'organ-spinal-cord', 'Human spinal cord (segments)', 20000),
    ('VH_M_Knee_L', 'organ-knee', 'Human knee joint', 30000),
    ('VH_M_Pelvis', 'organ-pelvis', 'Human pelvis (bony)', 60000),
    ('VH_M_Blood_Vasculature', 'organ-blood-vessels', 'Major blood vessels', 120000),
    ('NIH_M_Lymph_Node', 'organ-lymph-node', 'Human lymph node', 50000),
    ('VH_M_Thymus', 'organ-thymus', 'Human thymus', 5000),
    ('VH_M_Prostate', 'organ-prostate', 'Human prostate', 60000),
    ('VH_F_Uterus', 'organ-uterus', 'Human uterus', 40000),
    ('VH_F_Fallopian_Tube_L', 'organ-fallopian-tube', 'Human fallopian tube', 20000),
    ('VH_F_Ovary_L', 'organ-ovary', 'Human ovary', 2000),
    ('VH_F_Placenta', 'organ-placenta', 'Human placenta and umbilical cord', 60000),
]

TISSUE = [  # first match wins: (pattern, colour, opacity)
    (r'capsule|sclera|amnion|conjunctiva|skin|chorionic|basal_plate|outer_cortex', '#d8b4fe', 0.32),
    (r'cornea|lens|humou?r|vitreous|aqueous', '#a5f3fc', 0.45),
    (r'valve', '#fde68a', 1), (r'papillary', '#fb7185', 1),
    (r'arter|aorta|coronary|trunk|umbilical_artery', '#ef4444', 1),
    (r'vein|vena|sinus|umbilical_vein|venous', '#3b82f6', 1),
    (r'ventricle|atrium|septum|myocard|muscle', '#e05a6d', 1),
    (r'nerve|optic|retina|fovea|macula|chiasm|radiation', '#fbbf24', 1),
    (r'cartilage|meniscus|articular', '#99f6e4', 1),
    (r'bone|femur|tibia|fibula|patella|ilium|ischium|pubis|sacrum|coccyx|condyle|epicondyl|perichond|enthesis|fossa|surface', '#efe7da', 1),
    (r'bronch|trachea|carina|lar[iy]n|epiglott|thyroid|cricoid|arytenoid|corniculate', '#f9a8d4', 1),
    (r'duct|ureter|calyx|pelvis|tube|utricle|vas_deferens|vesicle|ostium', '#fcd34d', 1),
    (r'pyramid|medulla|papilla', '#be123c', 1), (r'cortex|column', '#fb923c', 1),
    (r'lymph|follicle|paracortex', '#86efac', 1),
]
PALETTE = ['#c084fc', '#f472b6', '#fb923c', '#facc15', '#38bdf8', '#a3e635', '#f87171', '#2dd4bf', '#e879f9', '#fdba74', '#93c5fd', '#fda4af']


def part_key(node):
    key = re.sub(r'^(VH|SBU|NIH|Allen)_[MF]_', '', node)
    key = re.sub(r'^(Allen|Yao)_', '', key)
    key = re.sub(r'_\d+$', '', key)
    key = re.sub(r'(_[LR])?(_(?:[a-z]|sup|inf|frontal|base\d?|dome))?$', '', key)
    key = key.replace('transition_zone__', 'transition_zone_').replace('fibria', 'fimbria').replace('hepataduodenal', 'hepatoduodenal').replace('horizonal', 'horizontal').replace('superiomedial', 'superomedial').replace('perichondular', 'perichondral')
    return key.strip('_').lower()


def label(key):
    text = key.replace('_', ' ').replace(' of left ', ' of ').strip()
    text = re.sub(r'^heart (left|right) ventricle$', r'\1 ventricle', text)
    text = re.sub(r'^(left|right) cardiac atrium$', r'\1 atrium', text)
    text = re.sub(r'\bhth\b', 'hypothalamus', text)
    text = re.sub(r'\bfugt\b', '(temporal fusiform gyrus)', text)
    text = re.sub(r'\b(c\d+)\b', lambda m: m.group(1).upper(), text)
    return text[:1].upper() + text[1:]


def colour(key, index):
    for pattern, hex_colour, alpha in TISSUE:
        if re.search(pattern, key):
            return hex_colour, alpha
    return PALETTE[index % len(PALETTE)], 1


def material(hex_colour, alpha):
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return trimesh.visual.material.PBRMaterial(baseColorFactor=[r, g, b, alpha], metallicFactor=0.0, roughnessFactor=0.6,
                                               alphaMode='BLEND' if alpha < 1 else 'OPAQUE', doubleSided=True)


def simplify(mesh, faces):
    if len(mesh.faces) <= faces or faces < 40:
        return mesh
    points, triangles = fast_simplification.simplify(mesh.vertices.astype(np.float32), mesh.faces.astype(np.int32), target_reduction=1 - faces / len(mesh.faces))
    return trimesh.Trimesh(points, triangles, process=False)


def build(source, organ_id, title, budget):
    scene = trimesh.load(source, force='scene')
    groups = OrderedDict()
    for node in scene.graph.nodes_geometry:
        transform, geometry = scene.graph[node]
        mesh = scene.geometry[geometry].copy()
        if not isinstance(mesh, trimesh.Trimesh) or not len(mesh.faces):
            continue
        mesh.apply_transform(transform)
        groups.setdefault(part_key(node), []).append(mesh)
    total = sum(len(m.faces) for meshes in groups.values() for m in meshes)
    out = trimesh.Scene()
    parts = []
    for index, (key, meshes) in enumerate(groups.items()):
        merged = trimesh.util.concatenate(meshes) if len(meshes) > 1 else meshes[0]
        merged = simplify(merged, max(60, int(len(merged.faces) * min(1, budget / total))))
        merged.visual = trimesh.visual.TextureVisuals(material=material(*colour(key, index)))
        part_id = key.replace('_', '-')
        out.add_geometry(merged, node_name=part_id, geom_name=part_id)
        parts.append({'id': part_id, 'label': label(key), 'info': ''})
    OUT.mkdir(parents=True, exist_ok=True)
    out.export(OUT / f'{organ_id}.glb')
    (OUT / f'{organ_id}.json').write_text(json.dumps({'title': title, 'credit': CREDIT, 'parts': parts}, indent=1, ensure_ascii=False))
    print(f'{organ_id:28} {len(parts):3} parts {total:7} -> {sum(len(g.faces) for g in out.geometry.values()):7} faces {(OUT / f"{organ_id}.glb").stat().st_size / 1e6:5.2f} MB')


if __name__ == '__main__':
    folder = Path(sys.argv[1])
    for name, organ_id, title, budget in ORGANS:
        build(folder / f'{name}.glb', organ_id, title, budget)
