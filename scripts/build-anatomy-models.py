"""Build BioEZ's explorable 3D human anatomy models from BodyParts3D.

Data: BodyParts3D, (c) The Database Center for Life Science, licensed under CC Attribution-Share
Alike 2.1 Japan (https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html). The derived GLB
files keep that licence; they are not relicensed under BioEZ's MIT licence.

Usage:
  .venv/bin/python scripts/build-anatomy-models.py <dir with FMA*.stl> <composite_parts.txt>
STL source: https://github.com/Kevin-Mattheus-Moerman/BodyParts3D (assets/BodyParts3D_data).
Needs trimesh and fast-simplification (development only).
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
CREDIT = 'BodyParts3D, © The Database Center for Life Science, CC BY-SA 2.1 Japan. Simplified for BioEZ.'


def load_tables(composite_file):
    rows = list(csv.reader(open(composite_file, encoding='utf-8'), delimiter='\t'))[1:]
    names = {r[0]: r[1] for r in rows}
    names.update({r[2]: r[3] for r in rows})
    children = collections.defaultdict(set)
    for r in rows:
        children[r[0]].add(r[2])
    return names, children


def leaves(fma, children, available):
    out = set()
    for child in children.get(fma, ()):
        out |= leaves(child, children, available) if child in children and child not in available else {child}
    return out | ({fma} if fma in available and fma not in children else set())


def merged(ids, stl_dir, faces):
    meshes = [trimesh.load_mesh(stl_dir / f'{i}.stl') for i in ids]
    mesh = trimesh.util.concatenate(meshes)
    if len(mesh.faces) > faces:
        points, triangles = fast_simplification.simplify(mesh.vertices.astype(np.float32), mesh.faces.astype(np.int32), target_reduction=1 - faces / len(mesh.faces))
        mesh = trimesh.Trimesh(points, triangles, process=True)
    return mesh


def material(hex_colour, alpha=1.0):
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return trimesh.visual.material.PBRMaterial(baseColorFactor=[r, g, b, alpha], metallicFactor=0.0, roughnessFactor=0.6,
                                               alphaMode='BLEND' if alpha < 1 else 'OPAQUE', doubleSided=alpha < 1)


def export(name, title, groups, stl_dir):
    """groups: list of (part id, label, info, fma ids, face budget, colour, alpha)."""
    scene = trimesh.Scene()
    parts = []
    for part_id, label, info, ids, faces, colour, alpha in groups:
        if not ids:
            continue
        mesh = merged(sorted(ids), stl_dir, faces)
        mesh.visual = trimesh.visual.TextureVisuals(material=material(colour, alpha))
        scene.add_geometry(mesh, node_name=part_id, geom_name=part_id)
        parts.append({'id': part_id, 'label': label, 'info': info})
    # BodyParts3D uses millimetres with Z up; three.js expects Y up.
    scene.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0]))
    OUT.mkdir(parents=True, exist_ok=True)
    scene.export(OUT / f'{name}.glb')
    (OUT / f'{name}.json').write_text(json.dumps({'title': title, 'credit': CREDIT, 'parts': parts}, indent=1, ensure_ascii=False))
    print(name, len(parts), 'parts', round((OUT / f'{name}.glb').stat().st_size / 1e6, 2), 'MB')


BONE_REGIONS = [
    ('skull', 'Skull (cranium and face)', 'Protects the brain and supports the face; the cranial bones are fused at sutures.', r'frontal|parietal|occipital|temporal|sphenoid|ethmoid|zygomatic|maxilla|nasal|lacrimal|palatine|vomer|concha|cranium|skull'),
    ('mandible', 'Mandible', 'The lower jaw, the only movable bone of the skull.', r'mandible'),
    ('vertebral-column', 'Vertebral column', 'Stack of vertebrae and discs that supports the body and protects the spinal cord.', r'vertebra|sacrum|coccyx|atlas|axis|intervertebral'),
    ('ribs', 'Ribs and costal cartilages', 'Twelve pairs that form the thoracic cage and move during breathing.', r'\brib\b|costal'),
    ('sternum', 'Sternum', 'The breastbone, joined to the ribs by costal cartilage.', r'sternum|manubrium|xiphoid'),
    ('shoulder-girdle', 'Clavicle and scapula', 'The shoulder girdle that attaches the arm to the trunk.', r'clavicle|scapula'),
    ('humerus', 'Humerus', 'The upper-arm bone.', r'humerus'),
    ('forearm', 'Radius and ulna', 'The two forearm bones; the radius rotates around the ulna.', r'radius|ulna|forearm'),
    ('hand', 'Hand (carpals, metacarpals, phalanges)', 'Twenty-seven bones that give the hand its fine movement.', r'scaphoid|lunate|triquetral|pisiform|trapezi|trapezoid|capitate|hamate|metacarpal|finger|thumb|sesamoid bone of hand'),
    ('pelvis', 'Hip bones (pelvis)', 'Each hip bone is a fused ilium, ischium and pubis; together they bear the body\'s weight.', r'hip bone|pubic|ilium|ischium|pelvi'),
    ('femur', 'Femur', 'The thigh bone, the longest and strongest bone in the body.', r'femur'),
    ('patella', 'Patella', 'The kneecap, a sesamoid bone in the quadriceps tendon.', r'patella'),
    ('leg', 'Tibia and fibula', 'The shin bone (tibia) carries the weight; the fibula anchors muscles.', r'tibia|fibula|of leg'),
    ('foot', 'Foot (tarsals, metatarsals, phalanges)', 'Twenty-six bones forming the arches of the foot.', r'talus|calcaneus|navicular|cuboid|cuneiform|metatarsal|toe|sesamoid bone of foot|plantar'),
]


def main(stl_dir, composite_file):
    stl_dir = Path(stl_dir)
    available = {p.stem for p in stl_dir.glob('*.stl')}
    names, children = load_tables(composite_file)
    find = lambda fma: leaves(fma, children, available) & available
    muscular = next(k for k, v in names.items() if v == 'muscular system')
    heart, vessels = find('FMA7088'), find('FMA7161')

    export('human-body', 'Human body: skin, muscles, skeleton and organs', [
        ('skin', 'Skin', 'The body\'s largest organ: a waterproof, protective barrier that also senses and helps control temperature.', find('FMA7163'), 60000, '#f5d0c5', 0.28),
        ('muscles', 'Skeletal muscles', 'About 600 muscles that move the skeleton by contracting.', find(muscular), 160000, '#e05a6d', 1),
        ('skeleton', 'Skeleton', 'Bones and cartilage that support, protect organs and make blood cells.', find('FMA23881'), 120000, '#efe7da', 1),
        ('brain', 'Brain', 'Controls the body and processes information.', find('FMA50801'), 30000, '#f2b8c6', 1),
        ('heart', 'Heart', 'Muscular pump that drives blood around the body.', heart, 12000, '#c0263b', 1),
        ('blood-vessels', 'Major blood vessels', 'Arteries and veins that carry blood to and from the heart.', vessels - heart, 30000, '#d63a4a', 1),
        ('lungs', 'Lungs', 'Site of gas exchange between air and blood.', find('FMA7195'), 20000, '#f9a8b8', 0.9),
        ('liver', 'Liver', 'Processes nutrients, makes bile and detoxifies the blood.', find('FMA7197'), 8000, '#8b3a2e', 1),
        ('stomach', 'Stomach', 'Stores food and starts protein digestion with acid and pepsin.', find('FMA7148'), 5000, '#e7a07a', 1),
        ('small-intestine', 'Small intestine', 'Where most digestion and absorption of nutrients happen.', find('FMA7200'), 12000, '#f0b27a', 1),
        ('large-intestine', 'Large intestine', 'Absorbs water and forms faeces.', find('FMA7201'), 10000, '#c98a5a', 1),
        ('kidneys', 'Kidneys', 'Filter the blood to make urine and balance water and salts.', find('FMA7203'), 6000, '#a3344a', 1),
    ], stl_dir)

    bones = find('FMA23881')
    groups, used = [], set()
    for part_id, label, info, pattern in BONE_REGIONS:
        ids = {b for b in bones - used if re.search(pattern, names.get(b, ''), re.I)}
        used |= ids
        groups.append((part_id, label, info, ids, 26000 if part_id in ('vertebral-column', 'hand', 'foot', 'skull', 'ribs') else 9000, '#efe7da', 1))
    rest = bones - used
    if rest:
        groups.append(('other-bones', 'Other bones and ligaments', 'Smaller skeletal parts such as the hyoid and ligaments.', rest, 6000, '#d6cfc4', 1))
    palette = ['#f1e4c9', '#e9d5b5', '#efe7da', '#e3d3bd', '#f5ecdc', '#ddccb4']
    groups = [(g[0], g[1], g[2], g[3], g[4], palette[i % len(palette)], g[6]) for i, g in enumerate(groups)]
    export('human-skeleton', 'Human skeleton', groups, stl_dir)

    heart_parts = collections.defaultdict(set)
    rules = [('right-atrium', 'Right atrium', 'Receives deoxygenated blood from the venae cavae.', r'right atrium|right auricle'),
             ('left-atrium', 'Left atrium', 'Receives oxygenated blood from the pulmonary veins.', r'left atrium|left auricle'),
             ('right-ventricle', 'Right ventricle', 'Pumps blood to the lungs through the pulmonary artery.', r'right ventricle'),
             ('left-ventricle', 'Left ventricle', 'Thick-walled chamber that pumps blood to the whole body through the aorta.', r'left ventricle'),
             ('septum', 'Septum', 'Muscular wall separating the left and right sides.', r'septum'),
             ('valves', 'Valves', 'Stop blood flowing backwards.', r'valve|cusp|leaflet'),
             ('coronary', 'Coronary vessels', 'Supply the heart muscle itself with blood.', r'coronary|cardiac vein')]
    info = {}
    for fma in heart:
        n = names.get(fma, '')
        for part_id, label, text, pattern in rules:
            if re.search(pattern, n, re.I):
                heart_parts[part_id].add(fma); info[part_id] = (label, text); break
        else:
            heart_parts['heart-wall'].add(fma); info['heart-wall'] = ('Heart wall (myocardium)', 'Cardiac muscle that contracts to pump blood.')
    colours = {'right-atrium': '#60a5fa', 'right-ventricle': '#3b82f6', 'left-atrium': '#f87171', 'left-ventricle': '#dc2626', 'septum': '#fb7185', 'valves': '#fde68a', 'coronary': '#fbbf24', 'heart-wall': '#e05a6d'}
    export('human-heart', 'Human heart', [(k, info[k][0], info[k][1], v, 10000, colours.get(k, '#e05a6d'), 1) for k, v in heart_parts.items()], stl_dir)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
