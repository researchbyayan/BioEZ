"""Build BioEZ's explorable 3D cell models (animal, plant, bacterium) as GLB files.

Original procedural geometry (MIT, like the rest of BioEZ). Each organelle is its own named
node so the viewer can highlight, hide and label it. Outer layers are cut away (a wedge is
removed) so the inside is visible, as in a textbook cutaway.

Usage: .venv/bin/python scripts/build-cell-models.py
Needs trimesh and manifold3d (development only).
"""
import json
import math
from pathlib import Path

import numpy as np
import trimesh
from trimesh.creation import capsule, cylinder, icosphere, torus

OUT = Path(__file__).resolve().parents[1] / 'frontend' / 'src' / 'diagrams' / 'models'
RNG = np.random.default_rng(7)


def material(hex_colour, alpha=1.0, rough=0.55):
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return trimesh.visual.material.PBRMaterial(baseColorFactor=[r, g, b, alpha], metallicFactor=0.0, roughnessFactor=rough,
                                               alphaMode='BLEND' if alpha < 1 else 'OPAQUE', doubleSided=True)


def paint(mesh, hex_colour, alpha=1.0):
    mesh.visual = trimesh.visual.TextureVisuals(material=material(hex_colour, alpha))
    return mesh


def cutaway(mesh, size=40):
    """Remove the front-right-top octant so the inside shows."""
    box = trimesh.creation.box(extents=[size, size, size])
    box.apply_translation([size / 2, size / 2, size / 2])
    return mesh.difference(box, engine='manifold')


def shell(outer, thickness):
    inner = outer.copy()
    inner.apply_scale(1 - thickness)
    return outer.difference(inner, engine='manifold')


def scattered(count, radius, avoid=(), size=0.12, keep=lambda p: True):
    pieces = []
    while len(pieces) < count:
        p = RNG.uniform(-radius, radius, 3)
        if np.linalg.norm(p) > radius or not keep(p) or any(np.linalg.norm(p - c) < r for c, r in avoid):
            continue
        s = icosphere(subdivisions=1, radius=size)
        s.apply_translation(p)
        pieces.append(s)
    return trimesh.util.concatenate(pieces)


def outside_cut(p):
    return not (p[0] > 0 and p[1] > 0 and p[2] > 0)


def oriented(mesh, direction, at):
    mesh.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], direction))
    mesh.apply_translation(at)
    return mesh


def mitochondrion(length, radius, at, direction):
    outer = capsule(height=length, radius=radius, count=[24, 24])
    folds = []
    for k in np.linspace(-length / 2 + radius * 0.4, length / 2 - radius * 0.4, 5):
        fold = cylinder(radius=radius * 0.78, height=radius * 0.12, sections=24)
        fold.apply_translation([0, 0, k])
        folds.append(fold)
    return oriented(outer, direction, at), oriented(trimesh.util.concatenate(folds), direction, at)


def er_sheets(center, inner, outer, layers, open_angle):
    sheets = []
    for i in range(layers):
        r = inner + (outer - inner) * i / max(1, layers - 1)
        ring = torus(major_radius=r, minor_radius=0.12, major_sections=64, minor_sections=8)
        ring.apply_scale([1, 1, 2.6])
        ring.apply_translation(center)
        sheets.append(ring)
    return trimesh.util.concatenate(sheets)


def golgi(at, direction, count=5):
    discs = []
    for i in range(count):
        d = cylinder(radius=1.1 - 0.08 * abs(i - count // 2), height=0.14, sections=40)
        d.apply_scale([1.0, 0.55, 1.0])
        d.apply_translation([0, 0, i * 0.32])
        discs.append(d)
    stack = trimesh.util.concatenate(discs)
    stack.apply_translation([0, 0, -count * 0.16])
    return oriented(stack, direction, at)


def save(name, parts, meta):
    scene = trimesh.Scene()
    for part_id, (mesh, colour, alpha) in parts.items():
        scene.add_geometry(paint(mesh, colour, alpha), node_name=part_id, geom_name=part_id)
    OUT.mkdir(parents=True, exist_ok=True)
    scene.export(OUT / f'{name}.glb')
    (OUT / f'{name}.json').write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    print(name, round((OUT / f'{name}.glb').stat().st_size / 1e6, 2), 'MB')


def animal_cell():
    membrane = cutaway(shell(icosphere(subdivisions=4, radius=10), 0.03))
    nucleus_env = cutaway(shell(icosphere(subdivisions=4, radius=3.2), 0.06))
    nucleolus = icosphere(subdivisions=3, radius=1.1); nucleolus.apply_translation([-0.6, -0.4, 0.2])
    chromatin = scattered(60, 2.7, avoid=[(np.array([-0.6, -0.4, 0.2]), 1.3)], size=0.16, keep=outside_cut)
    rer = cutaway(er_sheets([0, 0, 0], 3.9, 5.2, 4, 0))
    ribosomes_er = scattered(220, 5.4, avoid=[(np.zeros(3), 3.7)], size=0.09, keep=outside_cut)
    ribosomes_free = scattered(160, 9.2, avoid=[(np.zeros(3), 5.8)], size=0.08, keep=outside_cut)
    mitos, cristae = [], []
    for at in ([-6.5, 2.5, -1], [-2, -7, 1.5], [5.5, -4, -3], [-4, 5, -5], [2, 3, -7.5], [-7, -2.5, 3]):
        a, b = mitochondrion(2.4, 0.75, at, RNG.normal(size=3)); mitos.append(a); cristae.append(b)
    golgi_body = golgi([6, -1, -1.5], [1, -0.3, 0.2])
    lysosomes = trimesh.util.concatenate([icosphere(2, 0.55).apply_translation(p) for p in ([-5, -5, -4], [3.5, -7, -2], [-7.5, 3.5, 2])])
    vesicles = trimesh.util.concatenate([icosphere(2, 0.3).apply_translation(p) for p in ([7.4, -2.4, -0.4], [7.6, 0.6, -2.4], [8.3, -1.2, -1.2])])
    centrioles = trimesh.util.concatenate([cylinder(0.22, 1.1, sections=18).apply_translation([4, 4.5, -4]),
                                           oriented(cylinder(0.22, 1.1, sections=18), [1, 0, 0], [4.6, 4.5, -4])])
    smooth_er = trimesh.util.concatenate([oriented(capsule(height=2.5, radius=0.18), RNG.normal(size=3), p) for p in ([-6, -5.5, 1], [-5.5, -6.2, -1], [-4.8, -6.8, 0.5], [-6.6, -4.4, -0.6])])
    parts = {
        'cell-membrane': (membrane, '#c4b5fd', 0.45), 'nucleus': (nucleus_env, '#7c3aed', 0.9),
        'nucleolus': (nucleolus, '#4c1d95', 1), 'chromatin': (chromatin, '#a78bfa', 1),
        'rough-er': (rer, '#60a5fa', 0.85), 'ribosomes': (trimesh.util.concatenate([ribosomes_er, ribosomes_free]), '#e0e7ff', 1),
        'smooth-er': (smooth_er, '#38bdf8', 1), 'mitochondria': (trimesh.util.concatenate(mitos), '#f97316', 0.75),
        'cristae': (trimesh.util.concatenate(cristae), '#fdba74', 1), 'golgi': (golgi_body, '#fbbf24', 1),
        'lysosomes': (lysosomes, '#f87171', 1), 'vesicles': (vesicles, '#fde68a', 1), 'centrioles': (centrioles, '#f0abfc', 1)}
    save('animal-cell', parts, {'title': 'Animal (eukaryotic) cell', 'parts': [
        {'id': 'cell-membrane', 'label': 'Cell membrane', 'info': 'Phospholipid bilayer that controls what enters and leaves the cell.'},
        {'id': 'nucleus', 'label': 'Nucleus (nuclear envelope)', 'info': 'Double membrane with pores enclosing the DNA.'},
        {'id': 'nucleolus', 'label': 'Nucleolus', 'info': 'Makes ribosomal RNA and assembles ribosome subunits.'},
        {'id': 'chromatin', 'label': 'Chromatin', 'info': 'DNA wound around histone proteins.'},
        {'id': 'rough-er', 'label': 'Rough endoplasmic reticulum', 'info': 'Membrane sheets studded with ribosomes; makes and folds secreted and membrane proteins.'},
        {'id': 'smooth-er', 'label': 'Smooth endoplasmic reticulum', 'info': 'Tubules that make lipids and detoxify drugs.'},
        {'id': 'ribosomes', 'label': 'Ribosomes', 'info': 'Translate mRNA into protein, free in the cytoplasm or on the rough ER.'},
        {'id': 'mitochondria', 'label': 'Mitochondria', 'info': 'Site of aerobic respiration, making most of the cell\'s ATP.'},
        {'id': 'cristae', 'label': 'Cristae', 'info': 'Folds of the inner mitochondrial membrane that hold the electron transport chain.'},
        {'id': 'golgi', 'label': 'Golgi apparatus', 'info': 'Stacked cisternae that modify, sort and package proteins.'},
        {'id': 'vesicles', 'label': 'Secretory vesicles', 'info': 'Carry packaged proteins to the membrane for exocytosis.'},
        {'id': 'lysosomes', 'label': 'Lysosomes', 'info': 'Contain hydrolytic enzymes that digest waste and worn-out organelles.'},
        {'id': 'centrioles', 'label': 'Centrioles', 'info': 'Pair of microtubule cylinders that organise the spindle in animal cells.'}]})


def plant_cell():
    wall = cutaway(shell(trimesh.creation.box(extents=[22, 14, 14]), 0.04))
    membrane_box = trimesh.creation.box(extents=[20.8, 12.8, 12.8])
    membrane = cutaway(shell(membrane_box, 0.015))
    vacuole = icosphere(subdivisions=4, radius=1); vacuole.apply_scale([7.5, 4.6, 4.6]); vacuole.apply_translation([1.2, -0.3, -0.4])
    vacuole = cutaway(vacuole)
    nucleus = cutaway(shell(icosphere(subdivisions=3, radius=2.2), 0.08)); nucleus.apply_translation([-8, 2.5, -2.5])
    nucleolus = icosphere(2, 0.8); nucleolus.apply_translation([-8.2, 2.3, -2.7])
    chloroplasts, grana = [], []
    for at in ([-8.5, -4, 3], [-3, -5, -4.5], [4, -5.2, -4.5], [8.5, 4.5, -4], [-6, 5, -4.8], [8.8, -4.5, 2.5], [-9, -4.5, -3], [3, 5.2, -4.5]):
        c = icosphere(3, 1); c.apply_scale([1.8, 1.0, 0.7]); d = RNG.normal(size=3)
        chloroplasts.append(oriented(c, d, at))
        stacks = trimesh.util.concatenate([cylinder(0.32, 0.5, sections=16).apply_translation([x, 0, 0]) for x in (-0.9, 0, 0.9)])
        grana.append(oriented(stacks, d, at))
    mitos = [mitochondrion(1.6, 0.5, at, RNG.normal(size=3))[0] for at in ([-5, 3.5, 4.5], [6, 5, 2], [-9.2, -1, 4.5])]
    golgi_body = golgi([-5.5, -1.5, -5], [0.2, 0.1, 1], 4)
    plasmodesmata = trimesh.util.concatenate([cylinder(0.18, 1.2, sections=10).apply_translation([x, -7, z]) for x, z in ((-6, -3), (-2, -3), (2, -3), (6, -3))])
    parts = {
        'cell-wall': (wall, '#fbbf24', 0.55), 'cell-membrane': (membrane, '#c4b5fd', 0.35),
        'vacuole': (vacuole, '#7dd3fc', 0.35), 'nucleus': (nucleus, '#7c3aed', 0.95), 'nucleolus': (nucleolus, '#4c1d95', 1),
        'chloroplasts': (trimesh.util.concatenate(chloroplasts), '#4ade80', 0.85), 'grana': (trimesh.util.concatenate(grana), '#166534', 1),
        'mitochondria': (trimesh.util.concatenate(mitos), '#f97316', 1), 'golgi': (golgi_body, '#fde68a', 1),
        'plasmodesmata': (plasmodesmata, '#f0abfc', 1)}
    save('plant-cell', parts, {'title': 'Plant (eukaryotic) cell', 'parts': [
        {'id': 'cell-wall', 'label': 'Cellulose cell wall', 'info': 'Rigid wall that supports the cell and resists bursting.'},
        {'id': 'cell-membrane', 'label': 'Cell membrane', 'info': 'Controls entry and exit of substances; pressed against the wall.'},
        {'id': 'vacuole', 'label': 'Large central vacuole', 'info': 'Stores cell sap and keeps the cell turgid; bounded by the tonoplast.'},
        {'id': 'nucleus', 'label': 'Nucleus', 'info': 'Holds the DNA; often pushed to the side by the vacuole.'},
        {'id': 'nucleolus', 'label': 'Nucleolus', 'info': 'Makes ribosomal RNA.'},
        {'id': 'chloroplasts', 'label': 'Chloroplasts', 'info': 'Site of photosynthesis.'},
        {'id': 'grana', 'label': 'Grana (thylakoid stacks)', 'info': 'Hold chlorophyll; where the light-dependent reactions happen.'},
        {'id': 'mitochondria', 'label': 'Mitochondria', 'info': 'Aerobic respiration; plant cells have them as well as chloroplasts.'},
        {'id': 'golgi', 'label': 'Golgi apparatus', 'info': 'Processes proteins and makes cell-wall polysaccharides.'},
        {'id': 'plasmodesmata', 'label': 'Plasmodesmata', 'info': 'Channels through the wall linking the cytoplasm of neighbouring cells.'}]})


def helix(radius, pitch, turns, tube, start, axis):
    pts = [[radius * math.cos(t), radius * math.sin(t), pitch * t / (2 * math.pi)] for t in np.linspace(0, 2 * math.pi * turns, int(60 * turns))]
    segments = []
    for a, b in zip(pts[:-1], pts[1:]):
        seg = cylinder(radius=tube, segment=[a, b], sections=8)
        segments.append(seg)
    return oriented(trimesh.util.concatenate(segments), axis, start)


def bacterium():
    body = lambda r: capsule(height=9, radius=r, count=[48, 48])
    def oriented_body(r):
        m = body(r); m.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], [1, 0, 0])); return m
    capsule_layer = cutaway(shell(oriented_body(3.6), 0.05))
    wall = cutaway(shell(oriented_body(3.25), 0.05))
    membrane = cutaway(shell(oriented_body(3.0), 0.03))
    nucleoid = helix(1.0, 0.7, 7, 0.12, [-3.2, 0, 0], [1, 0.15, 0.1])
    plasmids = trimesh.util.concatenate([torus(0.55, 0.07).apply_translation(p) for p in ([2.8, -1.2, -1.0], [4.0, 0.8, -0.8], [-4.2, 1.1, -1.2])])
    ribosomes = scattered(260, 2.8, size=0.11, keep=lambda p: outside_cut(p) and True)
    ribosomes.apply_scale([2.3, 1, 1])
    flagellum = helix(0.5, 2.2, 6, 0.12, [7.2, 0, 0], [1, 0, 0])
    pili = trimesh.util.concatenate([cylinder(0.05, 1.8, sections=6).apply_transform(trimesh.geometry.align_vectors([0, 0, 1], d)).apply_translation(np.array(d) * 4.4)
                                     for d in ([0, 0.7, 0.7], [0.3, -0.8, 0.5], [-0.4, 0.6, -0.7], [0.2, -0.6, -0.8], [-0.5, -0.9, 0.2], [0.6, 0.9, -0.1])])
    parts = {'capsule': (capsule_layer, '#fde68a', 0.3), 'cell-wall': (wall, '#fbbf24', 0.6), 'cell-membrane': (membrane, '#c4b5fd', 0.6),
             'nucleoid': (nucleoid, '#a78bfa', 1), 'plasmids': (plasmids, '#f472b6', 1), 'ribosomes': (ribosomes, '#e0e7ff', 1),
             'flagellum': (flagellum, '#94a3b8', 1), 'pili': (pili, '#cbd5e1', 1)}
    save('bacterium', parts, {'title': 'Bacterial (prokaryotic) cell', 'parts': [
        {'id': 'capsule', 'label': 'Capsule (slime layer)', 'info': 'Sticky polysaccharide coat that protects against drying and immune attack.'},
        {'id': 'cell-wall', 'label': 'Cell wall (peptidoglycan)', 'info': 'Murein wall that keeps the cell\'s shape; target of penicillin.'},
        {'id': 'cell-membrane', 'label': 'Cell membrane', 'info': 'Controls transport; also the site of respiration in bacteria.'},
        {'id': 'nucleoid', 'label': 'Nucleoid (circular DNA)', 'info': 'A single circular chromosome, not enclosed by a nuclear membrane.'},
        {'id': 'plasmids', 'label': 'Plasmids', 'info': 'Small extra DNA loops, often carrying antibiotic-resistance genes.'},
        {'id': 'ribosomes', 'label': '70S ribosomes', 'info': 'Smaller than eukaryotic 80S ribosomes; make proteins.'},
        {'id': 'flagellum', 'label': 'Flagellum', 'info': 'Rotating helical filament that moves the bacterium.'},
        {'id': 'pili', 'label': 'Pili', 'info': 'Hair-like projections for attachment and passing DNA in conjugation.'}]})


if __name__ == '__main__':
    animal_cell()
    plant_cell()
    bacterium()
