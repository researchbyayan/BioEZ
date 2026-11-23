"""Build BioEZ's explorable 3D ear (middle and inner ear) from the SPL Inner Ear Atlas.

Data: SPL Inner Ear Atlas, release 2018-02 (Bartling, Jakab, Kikinis), Open Anatomy Project,
https://www.openanatomy.org/atlas-pages/atlas-spl-inner-ear.html, licensed under the 3D Slicer License
(section B); see licenses/3d-slicer-license.txt. Download: https://www.openanatomy.org/atlases/nac/inner-ear-2018-02.zip

Reads the atlas's legacy binary VTK POLYDATA models and writes one named part per structure.
Usage: .venv/bin/python scripts/build-ear-model.py <unzipped inner-ear-2018-02 folder>
"""
import json
import re
import sys
from pathlib import Path

import fast_simplification
import numpy as np
import trimesh

OUT = Path(__file__).resolve().parents[1] / 'frontend' / 'src' / 'diagrams' / 'models'
CREDIT = 'SPL Inner Ear Atlas (Bartling, Jakab, Kikinis), Open Anatomy Project, 3D Slicer License. Simplified for BioEZ.'
PARTS = {  # atlas name: (BioEZ label, colour, opacity, explanation)
    'Tympanic_Membrane': ('Tympanic membrane (eardrum)', '#f9a8d4', 0.85, 'Thin membrane that vibrates with sound and passes the vibration to the malleus.'),
    'Malleus_Bone': ('Malleus (hammer)', '#fde68a', 1, 'First ossicle; its handle is attached to the eardrum.'),
    'Incus_Bone': ('Incus (anvil)', '#fcd34d', 1, 'Middle ossicle linking the malleus to the stapes.'),
    'Stapes_Bone': ('Stapes (stirrup)', '#fbbf24', 1, 'Smallest bone in the body; its footplate pushes on the oval window of the cochlea.'),
    'Labyrinth': ('Bony labyrinth (cochlea, vestibule, semicircular canals)', '#c4b5fd', 0.9, 'Fluid-filled inner ear: the cochlea for hearing, the vestibule and semicircular canals for balance.'),
    'Osseous_Spiral_Lamina': ('Osseous spiral lamina', '#a78bfa', 1, 'Bony shelf spiralling inside the cochlea that supports the basilar membrane.'),
    'Fenestra_Rotunda': ('Round window', '#f0abfc', 1, 'Membrane-covered opening that bulges to release pressure as the stapes moves.'),
    'Tensor_Tympani_Muscle': ('Tensor tympani muscle', '#fb7185', 1, 'Pulls the malleus to stiffen the eardrum against loud sounds.'),
    'Stapedius_Muscle': ('Stapedius muscle', '#f43f5e', 1, 'Smallest skeletal muscle; damps stapes movement in the acoustic reflex.'),
    'Cochlear_Nerve': ('Cochlear nerve', '#facc15', 1, 'Carries hearing signals from the cochlea to the brainstem.'),
    'Vestibular_Nerve': ('Vestibular nerve', '#eab308', 1, 'Carries balance signals from the vestibule and semicircular canals.'),
    'Facial_Nerve': ('Facial nerve', '#ca8a04', 1, 'Runs through the temporal bone close to the middle ear; supplies the stapedius.'),
    'Internal_Carotid_Artery': ('Internal carotid artery', '#ef4444', 1, 'Major artery to the brain, passing just in front of the middle ear.'),
    'Internal_Jugular_Vein': ('Internal jugular vein', '#3b82f6', 1, 'Main vein draining the head, below the middle ear.'),
}


def read_vtk_polydata(path):
    """Legacy binary VTK POLYDATA: big-endian float32 POINTS and int32 POLYGONS (count, i0, i1, ...)."""
    data = path.read_bytes()
    points_header = re.search(rb'POINTS (\d+) float\n', data)
    count = int(points_header.group(1))
    start = points_header.end()
    points = np.frombuffer(data, dtype='>f4', count=count * 3, offset=start).reshape(-1, 3).astype(np.float64)
    polygons_header = re.search(rb'POLYGONS (\d+) (\d+)\n', data)
    total = int(polygons_header.group(2))
    raw = np.frombuffer(data, dtype='>i4', count=total, offset=polygons_header.end())
    faces, i = [], 0
    while i < len(raw):
        n = raw[i]
        ring = raw[i + 1:i + 1 + n]
        faces.extend([ring[0], ring[k], ring[k + 1]] for k in range(1, n - 1))
        i += n + 1
    return trimesh.Trimesh(points, np.array(faces), process=True)


def main(folder):
    models = Path(folder) / 'models'
    scene, parts = trimesh.Scene(), []
    for name, (label, colour, alpha, info) in PARTS.items():
        files = list(models.glob(f'Model_*_{name}.vtk'))
        if not files:
            continue
        mesh = read_vtk_polydata(files[0])
        budget = 30000 if name in ('Temporal_Bone', 'Labyrinth') else 12000
        if len(mesh.faces) > budget:
            points, faces = fast_simplification.simplify(mesh.vertices.astype(np.float32), mesh.faces.astype(np.int32), target_reduction=1 - budget / len(mesh.faces))
            mesh = trimesh.Trimesh(points, faces, process=False)
        r, g, b = (int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
        mesh.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
            baseColorFactor=[r, g, b, alpha], metallicFactor=0, roughnessFactor=0.6, alphaMode='BLEND' if alpha < 1 else 'OPAQUE', doubleSided=True))
        part_id = re.sub(r'[^a-z0-9]+', '-', label.lower().split(' (')[0]).strip('-')
        scene.add_geometry(mesh, node_name=part_id, geom_name=part_id)
        parts.append({'id': part_id, 'label': label, 'info': info})
    # Atlas coordinates are RAS millimetres with Z up; three.js expects Y up.
    scene.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0]))
    scene.export(OUT / 'organ-ear.glb')
    (OUT / 'organ-ear.json').write_text(json.dumps({'title': 'Human middle and inner ear', 'credit': CREDIT, 'parts': parts}, indent=1, ensure_ascii=False))
    print(len(parts), 'parts', round((OUT / 'organ-ear.glb').stat().st_size / 1e6, 2), 'MB')


if __name__ == '__main__':
    main(sys.argv[1])
