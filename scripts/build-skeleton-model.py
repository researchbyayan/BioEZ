"""Build BioEZ's human skeleton with every bone named, from BodyParts3D 4.0.

Data: "BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0
International" (https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html). Inputs, from
https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/: isa_BP3D_4.0_obj_99.zip (unzipped),
isa_element_parts.txt and isa_inclusion_relation_list.txt.

Left and right copies of a bone become one part ("femur"), each finger and toe bone is named,
and costal cartilages and the sternum are added. Usage:
  .venv/bin/python scripts/build-skeleton-model.py <folder with the tables and obj/isa_BP3D_4.0_obj_99>
"""
import collections
import csv
import json
import re
import sys
from pathlib import Path

import fast_simplification
import numpy as np
import trimesh

OUT = Path(__file__).resolve().parents[1] / 'frontend' / 'src' / 'diagrams' / 'models'
CREDIT = 'BodyParts3D 4.0, © The Database Center for Life Science, licensed under CC Attribution 4.0 International. Simplified for BioEZ.'
BONE_ORGAN = 'FMA5018'
EXTRA = {'sternum': r'^(manubrium|body of sternum|xiphoid process)$', 'costal cartilages': r'costal cartilage$'}
INFO = {
    'femur': 'The thigh bone, the longest and strongest bone in the body.', 'humerus': 'The upper-arm bone.',
    'radius': 'Forearm bone on the thumb side; it rotates around the ulna.', 'ulna': 'Forearm bone on the little-finger side.',
    'tibia': 'The shin bone, which carries the body\'s weight to the foot.', 'fibula': 'Thin outer leg bone that anchors muscles.',
    'patella': 'The kneecap, a sesamoid bone in the quadriceps tendon.', 'scapula': 'The shoulder blade.', 'clavicle': 'The collarbone, a strut between the sternum and scapula.',
    'hip bone': 'Fused ilium, ischium and pubis; the two hip bones and sacrum form the pelvis.', 'sacrum': 'Five fused vertebrae joining the spine to the pelvis.',
    'mandible': 'The lower jaw, the only movable bone of the skull.', 'sternum': 'The breastbone: manubrium, body and xiphoid process.',
    'atlas': 'First cervical vertebra; it holds up the skull.', 'axis': 'Second cervical vertebra; its dens lets the head turn.',
    'hyoid bone': 'U-shaped neck bone that anchors the tongue; it touches no other bone.', 'costal cartilages': 'Hyaline cartilage joining the ribs to the sternum.',
}


def tables(folder):
    relations = list(csv.reader(open(folder / 'isa_inclusion_relation_list.txt', encoding='utf-8'), delimiter='\t'))[1:]
    children, names = collections.defaultdict(set), {}
    for parent, parent_name, child, child_name in relations:
        children[parent].add(child)
        names[parent], names[child] = parent_name, child_name
    elements = collections.defaultdict(set)
    for row in list(csv.reader(open(folder / 'isa_element_parts.txt', encoding='utf-8'), delimiter='\t'))[1:]:
        elements[row[0]].add(row[2])
        names.setdefault(row[0], row[1])
    return children, names, elements


def base_name(name):
    name = re.sub(r'^(left|right) ', '', name)
    name = re.sub(r' of (left|right) (foot|hand)$', r' of \2', name)
    name = re.sub(r' of (left|right) ', ' of ', name)  # 'distal phalanx of left thumb' -> 'distal phalanx of thumb'
    return name


ORDINAL = {w: i for i, w in enumerate('first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth'.split(), 1)}
REGIONS = [r'frontal|parietal|occipital|temporal|sphenoid|ethmoid', r'zygomatic|maxilla|nasal|lacrimal|palatine|vomer|concha', r'mandible', r'hyoid',
           r'atlas|axis|cervical', r'thoracic vertebra', r'lumbar', r'sacrum|coccyx', r'sternum', r'rib$', r'costal', r'clavicle|scapula', r'humerus',
           r'radius|ulna', r'scaphoid|lunate|triquetral|pisiform|trapez|capitate|hamate', r'metacarpal', r'phalanx of (thumb|index|middle|ring|little) finger|phalanx of thumb', r'hip bone', r'femur', r'patella',
           r'tibia|fibula', r'talus|calcaneus|navicular|cuboid|cuneiform', r'metatarsal', r'phalanx of (big|second|third|fourth|little) toe|sesamoid']


def anatomical_order(name):
    """Head to feet, then numbered bones in order (C1, C2 ... first rib, second rib ...)."""
    region = next((i for i, pattern in enumerate(REGIONS) if re.search(pattern, name)), len(REGIONS))
    number = 1 if name == 'atlas' else 2 if name == 'axis' else ORDINAL.get(name.split()[0], 0)
    return region, number, name


def colour(name):
    if 'cartilage' in name:
        return [0.6, 0.95, 0.9, 1]
    if 'vertebra' in name or name in ('atlas', 'axis', 'sacrum', 'coccyx'):
        return [0.95, 0.89, 0.78, 1]
    if 'rib' in name or name == 'sternum':
        return [0.96, 0.92, 0.84, 1]
    return [0.94, 0.91, 0.85, 1]


def main(folder):
    folder = Path(folder)
    meshes = folder / 'obj' / 'isa_BP3D_4.0_obj_99'
    children, names, elements = tables(folder)
    seen, stack = set(), [BONE_ORGAN]
    while stack:
        for child in children.get(stack.pop(), ()):
            if child not in seen:
                seen.add(child)
                stack.append(child)
    leaves = [c for c in seen if elements.get(c) and not any(elements.get(k) for k in children.get(c, ()))]
    groups = collections.defaultdict(set)
    for concept in leaves:
        groups[base_name(names[concept])] |= elements[concept]
    for part, pattern in EXTRA.items():
        for concept, name in names.items():
            if elements.get(concept) and re.search(pattern, name) and not any(elements.get(k) for k in children.get(concept, ())):
                groups[part] |= elements[concept]
    scene, parts = trimesh.Scene(), []
    rotate = trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])
    for name in sorted(groups, key=anatomical_order):
        files = [meshes / f'{f}.obj' for f in sorted(groups[name]) if (meshes / f'{f}.obj').exists()]
        if not files:
            continue
        mesh = trimesh.util.concatenate([trimesh.load_mesh(f) for f in files])
        budget = 2500 if re.search(r'rib|vertebra|cuneiform|carpal|metatarsal|phalan|lunate|hamate|capitate|pisiform|triquetral|trapez|scaphoid|lacrimal|nasal|vomer|palatine|concha|sesamoid|hyoid', name) else 9000
        if len(mesh.faces) > budget:
            points, faces = fast_simplification.simplify(mesh.vertices.astype(np.float32), mesh.faces.astype(np.int32), target_reduction=1 - budget / len(mesh.faces))
            mesh = trimesh.Trimesh(points, faces, process=False)
        mesh.apply_transform(rotate)
        r, g, b, a = colour(name)
        mesh.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(baseColorFactor=[r, g, b, a], metallicFactor=0, roughnessFactor=0.6))
        part_id = re.sub(r'[^a-z0-9]+', '-', name).strip('-')
        scene.add_geometry(mesh, node_name=part_id, geom_name=part_id)
        parts.append({'id': part_id, 'label': name[:1].upper() + name[1:], 'info': INFO.get(name, '')})
    scene.export(OUT / 'human-skeleton.glb')
    (OUT / 'human-skeleton.json').write_text(json.dumps({'title': 'Human skeleton', 'credit': CREDIT, 'parts': parts}, indent=1, ensure_ascii=False))
    print(len(parts), 'bones', round((OUT / 'human-skeleton.glb').stat().st_size / 1e6, 2), 'MB')


if __name__ == '__main__':
    main(sys.argv[1])
