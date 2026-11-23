# Third-party sources

## seq_encode

Vendored `seq_encode/smiles.py` and package marker from hcji/seq_encode,
commit 9515620390910dba252c67feb17223717448e119.
Source: https://github.com/hcji/seq_encode
Copyright and MIT terms are preserved in backend/vendor/seq_encode/LICENSE.
The vendored source is unmodified. BioEZ wraps it for optional diagnostics;
the alphabet is returned with each encoding because upstream uses set ordering.

## chatbot-template

Architecture reference: https://github.com/IndrajeetPatil/chatbot-template
Reviewed commit: 8b5aa31392f98987814097ad2b1bd4e513b67c8e.
No license file was present in the reviewed repository. No source code or assets
from that repository are redistributed here. BioEZ independently implements
its documented React/FastAPI and Markdown/math architecture.

## Installed dependencies

RDKit (BSD), Electron (MIT), React (MIT), FastAPI (MIT), KaTeX (MIT), and other
runtime dependencies retain their respective upstream licenses in distributions.
The Python bundle includes dependency metadata/licenses collected by PyInstaller.
Electron Builder includes Chromium/Electron license files with the application.

## Vitrio

Liquid-glass refraction at the composer and sidebar edges uses vitrio by Eamon Liu, MIT License.
Source: https://github.com/eamonliu/vitrio, commit 3fed16666d3f6b5a0c9657182199aeb72c510db1.
The repository's built `dist/vitrio.esm.js` (newer than the npm 0.1.2 release; it adds `attachTo`)
is vendored unmodified in `frontend/src/vendor/vitrio` with its LICENSE; the type declarations
file is renamed to sit beside it. Only a static decorative light layer is cloned and refracted;
chat content and credentials are never sampled.

## chem-skill

Common-molecule data (PubChem isomeric SMILES and aliases) from ghutchis/chem-skill,
MIT License, Copyright (c) 2025 Geoff Hutchison. Source: https://github.com/ghutchis/chem-skill
Commit: bdb58112cd010cbf6a68a244ed904f4dfb90496f. The MOLECULES and ALIASES tables are
vendored in `backend/bioez/chem_skill_molecules.py`; two generic aliases ("acid", "alcohol")
are not used for structure substitution. Its ETKDG + MMFF conformer approach informed the 3D view.

## ChemClaw

Feature reference only: https://github.com/InternScience/ChemClaw (MIT), reviewed commit
58c9efc72886af6ef9356c14387fb36e9432d597. Its 3D viewer and molecular-property skills informed
BioEZ's 3D model and RDKit property panel. No ChemClaw code or data is redistributed.

## 3Dmol.js

3D model rendering uses the `3dmol` npm package (BSD-3-Clause), https://github.com/3dmol/3Dmol.js.
Its license is included in the generated JavaScript dependency license bundle.

## chemdraw-mcp, openmolclaw, ChemCP (feature references)

Reviewed for features only; no code or data redistributed:
jurimaxam-dotcom/chemdraw-mcp (Apache-2.0, commit 7bc67d0) informed functional-group
highlighting and "highlight changes" comparison; scottmreed/openmolclaw (Apache-2.0,
commit c32ab53) informed CIP stereo labels and InChI/InChIKey; scottmreed/ChemCP
(commit fb1c28e) matched the existing RDKit property panel. BioEZ implements these
independently with RDKit.

## Drawing conventions

BioEZ's own code follows published conventions from these projects; no source code from
them is included:

- ReShiki (MIT OR Apache-2.0, Ameyanagi): notched arrowhead and one-sided fishhook geometry.
- markdown-simplechem (MIT, Dmitry Shintyakov): plain-text arrow tokens (`<=>`, `->`, `hnu`).
- chemdraw-mcp (Apache-2.0): equilibrium arrow layout and tangent-oriented arrowheads.
- Chemaxon documentation (Marvin MEFlow, Structure Checker): electron-flow source and target rules and structure checks, re-implemented with RDKit.

## BodyParts3D (3D human anatomy models)

`frontend/src/diagrams/models/human-body.glb` and `human-heart.glb` are simplified
from BodyParts3D release 3.0 (2011-09-15), via the STL conversion at
https://github.com/Kevin-Mattheus-Moerman/BodyParts3D, by `scripts/build-anatomy-models.py`.
"BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International"
(https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html, licence updated 2025-02-27; it supersedes the older
CC BY-SA 2.1 Japan notice in the source files). Please cite: Mitsuhashi N. et al. BodyParts3D: 3D structure database
for anatomical concepts. Nucleic Acids Res. 2009;37:D782-5.

## BioEZ diagrams

The 3D cell models (`scripts/build-cell-models.py`) and the section diagrams in `frontend/src/diagrams/sections`
are original BioEZ work under BioEZ's MIT licence.

## HuBMAP Human Reference Atlas (3D organ models)

`frontend/src/diagrams/models/organ-*.glb` are simplified by `scripts/build-organ-models.py` from the HuBMAP
CCF 3D Reference Object Library v1.2 (https://hubmapconsortium.github.io/ccf/pages/ccf-3d-reference-library.html,
https://github.com/hubmapconsortium/ccf-releases), licensed under CC BY 4.0. Structures are merged across left/right
copies and sub-pieces, simplified and recoloured by tissue type. Please cite: Börner K. et al. Human BioMolecular Atlas
Program (HuBMAP): 3D Human Reference Atlas construction and usage. Nature Methods (2025).

`frontend/src/diagrams/models/human-skeleton.glb` (118 individually named bones) and `human-muscles.glb` (156 named
muscles) are built by `scripts/build-skeleton-model.py` and `scripts/build-muscle-model.py` from BodyParts3D 4.0 (`isa_BP3D_4.0_obj_99.zip`), under the same CC BY 4.0 licence.

## SPL Inner Ear Atlas (3D ear model)

`frontend/src/diagrams/models/organ-ear.glb` is built by `scripts/build-ear-model.py` from the SPL Inner Ear Atlas,
release 2018-02, by Bartling, Jakab and Kikinis (German Cancer Research Center and the Surgical Planning Laboratory,
Brigham and Women's Hospital), Open Anatomy Project: https://www.openanatomy.org/atlas-pages/atlas-spl-inner-ear.html.
All or portions of this licensed product have been obtained under license from The Brigham and Women's Hospital, Inc.
and are subject to the 3D Slicer License, section B (`licenses/3d-slicer-license.txt`). For education only; not for
clinical use. Meshes are simplified and recoloured.
