"""Representative offline workload for profiling BioEZ's backend (no network, no AI provider).

It runs the answer pipeline the way a chat does: validating and drawing molecules, reactions,
mechanisms and resonance, cleaning Markdown, and the offline biology tools. Used with
fast-anything: fast-anything scan -- .venv/bin/python scripts/perf_workload.py
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

from bioez import mechanisms  # noqa: E402
from bioez.app import prepare_answer  # noqa: E402

FAMILIES = [
    ('SN2', ['CCBr', '[OH-]']), ('E1', ['CC(C)(C)Br', 'O']), ('HX addition', ['CC=C', 'Br']),
    ('halogen addition', ['C=C', 'BrBr']), ('nucleophilic addition', ['CC=O', '[C-]#N']),
    ('hydride reduction', ['CC(C)=O', '[BH4-]']), ('nucleophilic acyl substitution', ['CC(=O)Cl', 'N']),
    ('saponification', ['CC(=O)OCC', '[OH-]']), ('electrophilic aromatic substitution', ['c1ccccc1', 'O=[N+]=O']),
    ('Diels-Alder', ['C=CC=C', 'C=C']), ('aldol', ['CC=O']), ('Michael addition', ['CC(C)=O', 'C=CC(C)=O']),
    ('pinacol', ['CC(C)(O)C(C)(C)O']), ('acid-base', ['CC(=O)O', 'N']),
]
MOLECULES = ['CCO', 'CC(=O)Oc1ccccc1C(=O)O', 'CC(C)Cc1ccc(C(C)C(=O)O)cc1', 'CN1C=NC2=C1C(=O)N(C(=O)N2C)C',
             'OC[C@H]1OC(O)[C@H](O)[C@@H](O)[C@@H]1O', 'NC(Cc1ccccc1)C(=O)O', 'C1=CC=C2C(=C1)C=CC=C2',
             'CC(C)=O', 'OC(=O)CC(O)(CC(=O)O)C(=O)O', 'Nc1ncnc2[nH]cnc12']
PROSE = ('Glucose ($\\ce{C6H12O6}$) is oxidised in **cellular respiration**: glycolysis in the cytoplasm, '
         'then the Krebs cycle and oxidative phosphorylation in the mitochondria.\n\n| Stage | ATP |\n|---|---|\n'
         '| Glycolysis | 2 |\n| Krebs cycle | 2 |\n| Oxidative phosphorylation | ~28 |\n\n'
         '$$\n\\ce{C6H12O6 + 6O2 -> 6CO2 + 6H2O}\n$$')
DNA = ('ATGGTGCATCTGACTCCTGAGGAGAAGTCTGCCGTTACTGCCCTGTGGGGCAAGGTGAACGTGGATGAAGTTGGTGGTGAGGCCCTGGGCAGG'
       'CTGCTGGTGGTCTACCCTTGGACCCAGAGGTTCTTTGAGTCCTTTGGGGATCTGTCCACTCCTGATGCTGTTATGGGCAACCCTAAGGTGAAG') * 3


def answers():
    yield {'blocks': [{'type': 'markdown', 'text': PROSE}] * 3}
    yield {'blocks': [{'type': 'molecule', 'smiles': s, 'label': s} for s in MOLECULES]}
    yield {'blocks': [{'type': 'reaction', 'reactants': [{'smiles': 'CCO'}, {'smiles': 'CC(=O)O'}],
                       'products': [{'smiles': 'CCOC(C)=O'}, {'smiles': 'O'}], 'reagents': 'H2SO4', 'conditions': 'heat'}]}
    yield {'blocks': [{'type': 'resonance', 'caption': 'Acetate', 'contributors': [{'smiles': 'CC(=O)[O-]'}, {'smiles': 'CC([O-])=O'}]}]}
    for name, reactants in FAMILIES:
        yield {'blocks': [mechanisms.build(name, reactants)]}
    yield {'blocks': [{'type': 'sequence', 'kind': 'dna', 'sequence': DNA},
                      {'type': 'primers', 'primers': [{'name': 'F', 'sequence': 'ATGGTGCATCTGACTCCTGA'}, {'name': 'R', 'sequence': 'TTAGTGATACTTGTGGGCCA'}]},
                      {'type': 'rna_fold', 'sequence': 'GGGCGCAAGCCUUCGGGCUUGCGCCCAGGGAAACCCUGCAUGCAAAGCAUGC'}]}


def main(rounds=3):
    started = time.perf_counter()
    blocks = 0
    for _ in range(rounds):
        for answer in answers():
            result, _ = prepare_answer(json.dumps(answer))
            blocks += len(result)
    print(f'{blocks} blocks in {time.perf_counter() - started:.2f}s')


if __name__ == '__main__':
    main()
