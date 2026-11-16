"""Biology tools behind the sequence, rna_fold, gene_map, primers and protein answer blocks.

Every result is calculated here from the model's input or fetched from a public database,
so the numbers a learner sees come from Biopython, ViennaRNA, primer3 or NCBI/UniProt/RCSB,
not from the model. Heavy or optional libraries load only when a block needs them.
"""
import io
import re

TIMEOUT = 12
HEADERS = {'User-Agent': 'BioEZ/0.1 (https://github.com/researchbyayan/BioEZ)'}
DNA = set('ACGTN')
RNA_LETTERS = set('ACGUN')
PROTEIN = set('ACDEFGHIKLMNPQRSTVWYXBZU*')
NAMES = {'dna': 'DNA', 'rna': 'RNA', 'protein': 'protein'}
PURPLE = ['#b765f5', '#8b5cf6', '#d8b8f5', '#6d28d9', '#c084fc', '#a78bfa']


def clean_sequence(text, kind):
    """Strip FASTA headers, spaces, digits and line breaks; reject letters outside the alphabet."""
    lines = [line for line in str(text).splitlines() if not line.startswith('>')]
    sequence = re.sub(r'[\s\d]', '', ''.join(lines)).upper()
    if kind == 'rna':
        sequence = sequence.replace('T', 'U')
    alphabet = {'dna': DNA, 'rna': RNA_LETTERS, 'protein': PROTEIN}[kind]
    bad = sorted(set(sequence) - alphabet)
    if not sequence:
        raise ValueError(f'The {NAMES[kind]} sequence is empty.')
    if bad:
        raise ValueError(f'The {NAMES[kind]} sequence contains letters that are not allowed: {", ".join(bad[:8])}.')
    return sequence


def _get(url, **params):
    import httpx
    response = httpx.get(url, params=params or None, timeout=TIMEOUT, headers=HEADERS, follow_redirects=True)
    if response.status_code == 404:
        raise ValueError('The database has no record with that identifier.')
    response.raise_for_status()
    return response


def _limited(text, limit):
    return text if len(text) <= limit else text[:limit] + '…'


def sequence_result(kind, text):
    from Bio.Seq import Seq
    from Bio.SeqUtils import gc_fraction, molecular_weight
    sequence = clean_sequence(text, kind)
    if len(sequence) > 50000:
        raise ValueError('Sequences are limited to 50,000 letters.')
    facts = []
    result = {'sequence': sequence, 'length': len(sequence)}
    if kind in ('dna', 'rna'):
        seq = Seq(sequence)
        unit = 'nt'
        facts.append(['Length', f'{len(sequence):,} {unit}'])
        facts.append(['GC content', f'{gc_fraction(seq):.1%}'])
        counts = ', '.join(f'{base} {sequence.count(base)}' for base in ('ACGU' if kind == 'rna' else 'ACGT'))
        facts.append(['Base counts', counts])
        if 'N' not in sequence:
            facts.append(['Molecular weight (single strand)', f'{molecular_weight(seq, seq_type="RNA" if kind == "rna" else "DNA") / 1000:,.2f} kDa'])
        result['reverse_complement'] = _limited(str(seq.reverse_complement_rna() if kind == 'rna' else seq.reverse_complement()), 3000)
        if kind == 'dna':
            result['transcript'] = _limited(str(seq.transcribe()), 3000)
        start = sequence.find('ATG' if kind == 'dna' else 'AUG')
        if start >= 0 and len(sequence) - start >= 6:
            coding = seq[start:start + (len(sequence) - start) // 3 * 3]
            protein = str(coding.translate(to_stop=True))
            if protein:
                result['translation'] = _limited(protein, 3000)
                facts.append(['Open reading frame', f'From position {start + 1}: {len(protein)} amino acids'])
    else:
        from Bio.SeqUtils.ProtParam import ProteinAnalysis
        standard = sequence.replace('*', '')
        facts.append(['Length', f'{len(standard):,} amino acids'])
        if standard and set(standard) <= set('ACDEFGHIKLMNPQRSTVWY'):
            analysis = ProteinAnalysis(standard)
            facts.append(['Molecular weight', f'{analysis.molecular_weight() / 1000:,.2f} kDa'])
            facts.append(['Isoelectric point (pI)', f'{analysis.isoelectric_point():.2f}'])
            facts.append(['Hydropathy (GRAVY)', f'{analysis.gravy():.3f}'])
            facts.append(['Instability index', f'{analysis.instability_index():.1f} ({"stable" if analysis.instability_index() < 40 else "unstable"} in a test tube)'])
            top = sorted(((aa, standard.count(aa) / len(standard)) for aa in set(standard)), key=lambda item: (-item[1], item[0]))[:5]
            facts.append(['Most common residues', ', '.join(f'{aa} {share:.1%}' for aa, share in top)])
    result['facts'] = facts
    result['source'] = 'Calculated locally with Biopython.'
    return result


def rna_fold_result(text):
    try:
        import RNA
    except ImportError as exc:
        raise ValueError('RNA folding (ViennaRNA) is not installed in this build of BioEZ.') from exc
    sequence = clean_sequence(text, 'rna')
    if len(sequence) > 1000:
        raise ValueError('RNA folding is limited to 1,000 nucleotides.')
    structure, energy = RNA.fold(sequence)
    import os
    import tempfile
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, 'fold.svg')
        RNA.svg_rna_plot(sequence, structure, path)
        with open(path, encoding='utf-8') as handle:
            svg = handle.read()
    svg = svg[svg.find('<svg'):]
    svg = svg.replace('stroke: red', 'stroke: #8b5cf6').replace('stroke:red', 'stroke:#8b5cf6')
    pairs = structure.count('(')
    return {'sequence': sequence, 'structure': structure, 'mfe': round(energy, 2), 'pairs': pairs, 'svg': svg,
            'source': 'Minimum free energy structure predicted locally with ViennaRNA (RNAfold, 37 °C). A prediction, not a measured structure.'}


def _features_from_genbank(accession):
    from Bio import SeqIO
    if not re.fullmatch(r'[A-Za-z]{1,6}_?\d{1,10}(?:\.\d{1,3})?', accession):
        raise ValueError('Use an NCBI nucleotide accession such as NM_000518.')
    text = _get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi', db='nucleotide', id=accession, rettype='gb', retmode='text').text
    if len(text) > 5_000_000:
        raise ValueError('That GenBank record is too large to map.')
    record = SeqIO.read(io.StringIO(text), 'genbank')
    if len(record) > 2_000_000:
        raise ValueError('Gene maps are limited to records of up to 2 Mb.')
    features = []
    for feature in record.features:
        if feature.type not in ('gene', 'CDS', 'exon', "5'UTR", "3'UTR", 'mRNA', 'promoter', 'rep_origin', 'polyA_signal', 'sig_peptide'):
            continue
        qualifiers = feature.qualifiers
        name = (qualifiers.get('gene') or qualifiers.get('product') or qualifiers.get('note') or [feature.type])[0]
        features.append({'name': f'{feature.type}: {name}' if feature.type not in ('gene', 'CDS') else f'{name} ({feature.type})',
                         'start': int(feature.location.start) + 1, 'end': int(feature.location.end),
                         'strand': feature.location.strand or 0, 'kind': feature.type})
        if len(features) >= 40:
            break
    return record.id, record.description, len(record), features


def gene_map_result(block):
    if block.get('accession'):
        accession, title, length, features = _features_from_genbank(block['accession'].strip())
        source = f'Features from NCBI GenBank record {accession}; drawn locally with DNA Features Viewer.'
    else:
        length = int(block.get('length') or 0)
        features = [dict(f) for f in block.get('features') or []]
        if not features:
            raise ValueError('A gene map needs either an NCBI accession or a list of features.')
        length = max(length, max(f['end'] for f in features))
        accession, title = '', block.get('title') or 'Gene map'
        source = 'Feature positions supplied in the answer; drawn locally with DNA Features Viewer.'
    for f in features:
        if not 1 <= f['start'] <= f['end'] <= length:
            raise ValueError(f'Feature "{f["name"]}" lies outside the 1–{length} sequence.')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from dna_features_viewer import GraphicFeature, GraphicRecord
    kinds = sorted({f.get('kind') or 'feature' for f in features})
    colour = {kind: PURPLE[i % len(PURPLE)] for i, kind in enumerate(kinds)}
    graphics = [GraphicFeature(start=f['start'] - 1, end=f['end'], strand=f.get('strand') or 0, color=colour[f.get('kind') or 'feature'], label=_limited(f['name'], 40)) for f in features]
    figure_record = GraphicRecord(sequence_length=length, features=graphics)
    axis, _ = figure_record.plot(figure_width=10)
    output = io.StringIO()
    axis.figure.savefig(output, format='svg', bbox_inches='tight')
    plt.close(axis.figure)
    svg = output.getvalue()
    svg = svg[svg.find('<svg'):]
    return {'title': title, 'accession': accession, 'length': length, 'features': features, 'svg': svg, 'source': source}


def primers_result(primers):
    try:
        import primer3
    except ImportError as exc:
        raise ValueError('Primer analysis (primer3) is not installed in this build of BioEZ.') from exc
    from Bio.SeqUtils import gc_fraction
    rows = []
    sequences = []
    for primer in primers:
        sequence = clean_sequence(primer['sequence'], 'dna')
        if not 8 <= len(sequence) <= 60:
            raise ValueError(f'Primer "{primer.get("name") or sequence}" must be 8–60 nucleotides long.')
        sequences.append(sequence)
        hairpin = primer3.calc_hairpin(sequence)
        dimer = primer3.calc_homodimer(sequence)
        rows.append({'name': primer.get('name') or f'Primer {len(rows) + 1}', 'sequence': sequence, 'length': len(sequence),
                     'tm': round(primer3.calc_tm(sequence), 1), 'gc': round(gc_fraction(sequence) * 100, 1),
                     'hairpin_dg': round(hairpin.dg / 1000, 2) if hairpin.structure_found else None,
                     'self_dimer_dg': round(dimer.dg / 1000, 2) if dimer.structure_found else None})
    pair = None
    if len(sequences) == 2:
        hetero = primer3.calc_heterodimer(*sequences)
        pair = {'tm_difference': round(abs(rows[0]['tm'] - rows[1]['tm']), 1),
                'cross_dimer_dg': round(hetero.dg / 1000, 2) if hetero.structure_found else None}
    return {'primers': rows, 'pair': pair,
            'source': 'Calculated locally with primer3 (SantaLucia nearest-neighbour model, 50 mM Na⁺, 50 nM primer). ΔG values in kcal/mol; below about −9 is a concern.'}


def protein_result(block):
    result = {'source': []}
    if block.get('uniprot'):
        accession = block['uniprot'].strip().upper()
        if not re.fullmatch(r'[A-Z0-9]{6,10}(?:-\d+)?', accession):
            raise ValueError('Use a UniProt accession such as P68871.')
        data = _get(f'https://rest.uniprot.org/uniprotkb/{accession}.json').json()
        description = data.get('proteinDescription', {})
        name = (description.get('recommendedName') or (description.get('submissionNames') or [{}])[0]).get('fullName', {}).get('value', '')
        function = next((c['texts'][0]['value'] for c in data.get('comments', []) if c.get('commentType') == 'FUNCTION' and c.get('texts')), '')
        location = next((', '.join(l['location']['value'] for l in c.get('subcellularLocations', [])[:4]) for c in data.get('comments', []) if c.get('commentType') == 'SUBCELLULAR LOCATION'), '')
        result.update({'uniprot': data.get('primaryAccession', accession), 'name': name,
                       'gene': ((data.get('genes') or [{}])[0].get('geneName') or {}).get('value', ''),
                       'organism': data.get('organism', {}).get('scientificName', ''),
                       'length': data.get('sequence', {}).get('length'), 'function': _limited(re.sub(r'\s*\(PubMed:[^)]*\)', '', function), 900),
                       'location': location})
        result['source'].append(f'UniProt {result["uniprot"]}')
    if block.get('pdb'):
        pdb = block['pdb'].strip().upper()
        if not re.fullmatch(r'[0-9][A-Z0-9]{3}', pdb):
            raise ValueError('Use a four-character PDB ID such as 4HHB.')
        entry = _get(f'https://data.rcsb.org/rest/v1/core/entry/{pdb}').json()
        info = entry.get('rcsb_entry_info', {})
        resolution = (info.get('resolution_combined') or [None])[0]
        result.update({'pdb': pdb, 'pdb_title': _limited(entry.get('struct', {}).get('title', ''), 300),
                       'method': (info.get('experimental_method') or '').title(),
                       'resolution': round(resolution, 2) if isinstance(resolution, (int, float)) else None})
        result['source'].append(f'RCSB PDB {pdb}')
    if not result['source']:
        raise ValueError('A protein block needs a UniProt accession, a PDB ID, or both.')
    result['source'] = 'Looked up live from ' + ' and '.join(result['source']) + '.'
    return result


async def protein_structure(pdb):
    """Coordinates for the 3D viewer, fetched on demand rather than stored in the chat."""
    import httpx
    pdb = pdb.strip().upper()
    if not re.fullmatch(r'[0-9][A-Z0-9]{3}', pdb):
        raise ValueError('Use a four-character PDB ID such as 4HHB.')
    async with httpx.AsyncClient(timeout=20, headers=HEADERS, follow_redirects=True) as client:
        response = await client.get(f'https://files.rcsb.org/download/{pdb}.pdb')
        if response.status_code == 404:
            raise ValueError('This entry has no PDB-format file (large structures are mmCIF only).')
        response.raise_for_status()
        if len(response.content) > 8_000_000:
            raise ValueError('This structure is too large to show in the 3D viewer.')
        return {'pdb': pdb, 'data': response.text}
