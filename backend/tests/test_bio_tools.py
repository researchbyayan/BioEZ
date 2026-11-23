import json
import pytest
from bioez.app import prepare_answer
from bioez import bio_tools


def render(*blocks):
    return prepare_answer(json.dumps({'blocks': list(blocks)}))


def test_dna_sequence_facts_translation_and_reverse_complement():
    blocks, failed = render({'type': 'sequence', 'kind': 'dna', 'sequence': '>demo\nATG GCC ATT GTA ATG GGC CGC TGA AAG', 'label': 'Demo'})
    assert not failed and blocks[0]['type'] == 'sequence'
    facts = dict(blocks[0]['facts'])
    assert facts['Length'] == '27 nt' and facts['GC content'] == '51.9%'
    assert blocks[0]['translation'] == 'MAIVMGR'
    assert blocks[0]['reverse_complement'] == 'CTTTCAGCGGCCCATTACAATGGCCAT'
    assert blocks[0]['transcript'].startswith('AUGGCC')


def test_protein_sequence_properties():
    blocks, failed = render({'type': 'sequence', 'kind': 'protein', 'sequence': 'MVHLTPEEKSAVTALWGKVNVDEVGGEALGRLLVVYPWTQRFFESFGDLSTPDAVMGNPKVKAHGKKVLGAFSDGLAHLDNLKGTFATLSELHCDKLHVDPENFRLLGNVLVCVLAHHFGKEFTPPVQAAYQKVVAGVANALAHKYH'})
    facts = dict(blocks[0]['facts'])
    assert not failed and facts['Length'] == '147 amino acids' and facts['Molecular weight'].startswith('16.')


def test_invalid_letters_are_a_readable_error():
    blocks, failed = render({'type': 'sequence', 'kind': 'dna', 'sequence': 'ATGXQ'})
    assert failed and blocks[0]['type'] == 'error' and 'DNA sequence contains letters' in blocks[0]['text']


def test_rna_fold_returns_structure_energy_and_drawing():
    pytest.importorskip('RNA')
    blocks, failed = render({'type': 'rna_fold', 'sequence': 'GGGAAAUCCCAGGGAAACCCU'})
    assert not failed and blocks[0]['structure'] == '(((....)))((((...))))'
    assert blocks[0]['mfe'] < 0 and blocks[0]['svg'].startswith('<svg')


def test_primer_pair_analysis():
    pytest.importorskip('primer3')
    blocks, failed = render({'type': 'primers', 'primers': [{'name': 'F', 'sequence': 'ATGGTGCATCTGACTCCTGA'}, {'name': 'R', 'sequence': 'TTAGTGATACTTGTGGGCCA'}]})
    assert not failed and [p['tm'] for p in blocks[0]['primers']] == [58.4, 56.1]
    assert blocks[0]['pair']['tm_difference'] == 2.3


def test_gene_map_from_listed_features_is_drawn_and_bounds_checked():
    pytest.importorskip('dna_features_viewer')
    blocks, failed = render({'type': 'gene_map', 'title': 'Operon', 'length': 3000, 'features': [{'name': 'lacZ', 'start': 100, 'end': 2000, 'kind': 'gene'}]})
    assert not failed and blocks[0]['svg'].startswith('<svg') and blocks[0]['length'] == 3000
    blocks, failed = render({'type': 'gene_map', 'length': 500, 'features': [{'name': 'x', 'start': 400, 'end': 300}]})
    assert failed and 'outside' in blocks[0]['text']


def test_protein_lookup_uses_uniprot_and_pdb(monkeypatch):
    replies = {
        'https://rest.uniprot.org/uniprotkb/P68871.json': {'primaryAccession': 'P68871', 'proteinDescription': {'recommendedName': {'fullName': {'value': 'Hemoglobin subunit beta'}}},
            'genes': [{'geneName': {'value': 'HBB'}}], 'organism': {'scientificName': 'Homo sapiens'}, 'sequence': {'length': 147},
            'comments': [{'commentType': 'FUNCTION', 'texts': [{'value': 'Involved in oxygen transport (PubMed:123).'}]}]},
        'https://data.rcsb.org/rest/v1/core/entry/4HHB': {'struct': {'title': 'DEOXYHAEMOGLOBIN'}, 'rcsb_entry_info': {'experimental_method': 'X-ray', 'resolution_combined': [1.74]}},
    }
    class Reply:
        def __init__(self, data): self.data = data
        def json(self): return self.data
    monkeypatch.setattr(bio_tools, '_get', lambda url, **params: Reply(replies[url]))
    blocks, failed = render({'type': 'protein', 'uniprot': 'P68871', 'pdb': '4HHB'})
    assert not failed
    b = blocks[0]
    assert (b['name'], b['gene'], b['length'], b['pdb'], b['resolution']) == ('Hemoglobin subunit beta', 'HBB', 147, '4HHB', 1.74)
    assert b['function'] == 'Involved in oxygen transport.'


def test_offline_lookup_is_a_readable_error(monkeypatch):
    import httpx
    def offline(url, **params):
        raise httpx.ConnectError('offline')
    monkeypatch.setattr(bio_tools, '_get', offline)
    blocks, failed = render({'type': 'protein', 'pdb': '4HHB'})
    assert failed and 'could not be reached' in blocks[0]['text']


def test_diagram_blocks_use_the_built_in_catalog():
    blocks, failed = render({'type': 'diagram', 'name': 'organ-heart', 'caption': 'Look at the valves.'})
    assert not failed and blocks[0]['title'] == 'Human heart' and blocks[0]['kind'] == 'model'
    blocks, failed = render({'type': 'diagram', 'name': 'ts-dicot-stem'})
    assert not failed and blocks[0]['kind'] == 'section'  # drawn 2D sections are available alongside the 3D organs
    assert len(blocks[0]['id']) == 36  # the block keeps its own id; the diagram is named separately
    blocks, failed = render({'type': 'diagram', 'name': 'made-up-diagram'})
    assert failed and 'no built-in diagram' in blocks[0]['text']


def test_every_catalog_diagram_has_its_asset():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / 'frontend' / 'src' / 'diagrams'
    for entry in bio_tools.diagram_catalog():
        folder, suffix = ('models', '.glb') if entry['kind'] == 'model' else ('sections', '.svg')
        assert (root / folder / (entry['id'] + suffix)).exists(), entry['id']


def test_diagram_focus_matches_a_named_part():
    blocks, failed = render({'type': 'diagram', 'name': 'human-skeleton', 'focus': 'Femur'})
    assert not failed and (blocks[0]['focus'], blocks[0]['focus_label']) == ('femur', 'Femur')
    blocks, _ = render({'type': 'diagram', 'name': 'organ-kidney', 'focus': 'renal pyramid', 'cut': 'ls'})
    assert (blocks[0]['focus'], blocks[0]['cut']) == ('renal-pyramid', 'ls')
    blocks, failed = render({'type': 'diagram', 'name': 'organ-heart', 'focus': 'not a part'})
    assert not failed and blocks[0]['focus'] == ''  # an unknown focus still shows the whole diagram
