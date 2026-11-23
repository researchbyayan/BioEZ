"""Build BioEZ's human musculature with every muscle named, over a faint skeleton, from BodyParts3D 4.0.

Data: "BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International".
Same inputs as build-skeleton-model.py. Left and right copies of a muscle become one part.
Usage: .venv/bin/python scripts/build-muscle-model.py <folder with the tables and obj/isa_BP3D_4.0_obj_99>
"""
import collections
import json
import re
import sys
from pathlib import Path

import fast_simplification
import numpy as np
import trimesh


OUT = Path(__file__).resolve().parents[1] / 'frontend' / 'src' / 'diagrams' / 'models'
CREDIT = 'BodyParts3D 4.0, © The Database Center for Life Science, licensed under CC Attribution 4.0 International. Simplified for BioEZ.'
MUSCLE_ORGAN, BONE_ORGAN = 'FMA5022', 'FMA5018'
MULTIPART = {'deltoid', 'trapezius', 'pectoralis major', 'triceps brachii', 'biceps brachii', 'biceps femoris', 'gastrocnemius',
             'pronator teres', 'flexor carpi ulnaris', 'flexor hallucis brevis', 'adductor pollicis', 'adductor hallucis', 'flexor pollicis brevis', 'longus colli'}
REGION = [  # (pattern, colour) so neighbouring groups are easy to tell apart
    (r'glute|piriformis|gemell|obturator|quadratus femoris|tensor fasciae', '#e11d48'),
    (r'femoris|vastus|sartorius|gracilis|adductor (longus|brevis|magnus|minimus)|pectineus|semi(tendinosus|membranosus)|biceps femoris|iliacus|psoas', '#f43f5e'),
    (r'gastrocnemius|soleus|tibialis|fibularis|plantaris|popliteus|digitorum longus|hallucis longus', '#fb7185'),
    (r'deltoid|supraspinatus|infraspinatus|teres|subscapularis|pectoralis|latissimus|trapezius|rhomboid|serratus|levator scapulae', '#be123c'),
    (r'biceps brachii|triceps|brachialis|brachioradialis|coracobrachialis|anconeus', '#f87171'),
    (r'oblique|rectus abdominis|transversus|intercostal|diaphragm|quadratus lumborum|erector|spinalis|longissimus|iliocostalis|multifidus|rotator|semispinalis', '#e05a6d'),
    (r'masseter|temporalis|pterygoid|orbicularis|zygomaticus|frontalis|occipitalis|buccinator|mentalis|platysma|sternocleidomastoid|scalene|digastric|hyoid', '#fda4af'),
]


def tables(folder):
    import csv
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


def leaves(root, children, elements):
    seen, stack = set(), [root]
    while stack:
        for child in children.get(stack.pop(), ()):
            if child not in seen:
                seen.add(child)
                stack.append(child)
    return [c for c in seen if elements.get(c) and not any(elements.get(k) for k in children.get(c, ()))]


def base_name(name):
    name = re.sub(r'^(left|right) ', '', name)
    return re.sub(r' of (left|right) (foot|hand)$', r' of \2', name)


def load(files, budget):
    mesh = trimesh.util.concatenate([trimesh.load_mesh(f) for f in files])
    if len(mesh.faces) > budget:
        points, faces = fast_simplification.simplify(mesh.vertices.astype(np.float32), mesh.faces.astype(np.int32), target_reduction=1 - budget / len(mesh.faces))
        mesh = trimesh.Trimesh(points, faces, process=False)
    mesh.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0]))
    return mesh


def material(hex_colour, alpha=1.0):
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return trimesh.visual.material.PBRMaterial(baseColorFactor=[r, g, b, alpha], metallicFactor=0, roughnessFactor=0.65,
                                               alphaMode='BLEND' if alpha < 1 else 'OPAQUE', doubleSided=alpha < 1)


def main(folder):
    folder = Path(folder)
    meshes = folder / 'obj' / 'isa_BP3D_4.0_obj_99'
    children, names, elements = tables(folder)
    groups = collections.defaultdict(set)
    for concept in leaves(MUSCLE_ORGAN, children, elements):
        groups[base_name(names[concept])] |= elements[concept]
    # Big muscles are modelled in parts ("clavicular part of left deltoid", "long head of right biceps brachii"):
    # put the parts of each named muscle back together.
    muscles = set(groups) | set(MULTIPART)
    for concept, name in names.items():
        match = re.match(r'^(?:left |right )?.+? (?:part|head|portion|belly) of (?:left |right )?(.+)$', name)
        if elements.get(concept) and match and match.group(1) in muscles and not any(elements.get(k) for k in children.get(concept, ())):
            groups[match.group(1)] |= elements[concept]
    scene, parts = trimesh.Scene(), []
    for name in sorted(groups):
        files = [meshes / f'{f}.obj' for f in sorted(groups[name]) if (meshes / f'{f}.obj').exists()]
        if not files:
            continue
        mesh = load(files, 4000)
        colour = next((c for pattern, c in REGION if re.search(pattern, name)), '#f9a8b8')
        mesh.visual = trimesh.visual.TextureVisuals(material=material(colour))
        part_id = re.sub(r'[^a-z0-9]+', '-', name).strip('-')
        scene.add_geometry(mesh, node_name=part_id, geom_name=part_id)
        parts.append({'id': part_id, 'label': name[:1].upper() + name[1:], 'info': ''})
    bone_files = sorted({f for c in leaves(BONE_ORGAN, children, elements) for f in elements[c]})
    bones = load([meshes / f'{f}.obj' for f in bone_files if (meshes / f'{f}.obj').exists()], 60000)
    bones.visual = trimesh.visual.TextureVisuals(material=material('#efe7da', 0.35))
    scene.add_geometry(bones, node_name='skeleton', geom_name='skeleton')
    parts.append({'id': 'skeleton', 'label': 'Skeleton (for reference)', 'info': 'The bones the muscles attach to.'})
    scene.export(OUT / 'human-muscles.glb')
    (OUT / 'human-muscles.json').write_text(json.dumps({'title': 'Human muscles', 'credit': CREDIT, 'parts': parts}, indent=1, ensure_ascii=False))
    print(len(parts) - 1, 'muscles', round((OUT / 'human-muscles.glb').stat().st_size / 1e6, 2), 'MB')


if __name__ == '__main__':
    main(sys.argv[1])
