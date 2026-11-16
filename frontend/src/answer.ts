import type {Block,Molecule} from './types';
import {displayName,formulaText,plainChem} from './chemText';
const species=(m:Pick<Molecule,'iupac_name'|'label'|'formula'>)=>`${displayName(m.iupac_name||m.label||'Molecule')}${m.formula?` (${formulaText(m.formula)})`:''}`;
export function answerText(blocks:Block[]):string {
  return blocks.map(b=>{
    if(b.type==='markdown'||b.type==='error')return b.text;
    if(b.type==='clarification')return b.question+'\n'+b.options.join('\n');
    if(b.type==='molecule')return species(b);
    if(b.type==='reaction'){
      const conditions=[b.reagents,b.conditions].map(text=>plainChem(text||'').trim()).filter(Boolean).join('; ');
      return [b.caption,`${b.reactants.map(species).join(' + ')} → ${b.products.map(species).join(' + ')}`,conditions&&`Conditions: ${conditions}`].filter(Boolean).join('\n');
    }
    if(b.type==='resonance')return [b.caption||'Resonance structures',b.contributors.map((c,i)=>c.label||`Contributor ${i+1}`).join(' ↔ ')+(b.hybrid?' ≡ '+b.hybrid.label:'')].join('\n');
    if(b.type==='sequence')return [`${b.label||b.kind.toUpperCase()+' sequence'}`,...b.facts.map(([k,v])=>`${k}: ${v}`),b.sequence].join('\n');
    if(b.type==='rna_fold')return [b.label||'RNA secondary structure',b.sequence,b.structure,`MFE: ${b.mfe} kcal/mol`].join('\n');
    if(b.type==='gene_map')return [b.title||'Gene map',...b.features.map(f=>`${f.name}: ${f.start}–${f.end}`)].join('\n');
    if(b.type==='primers')return b.primers.map(p=>`${p.name}: ${p.sequence} (Tm ${p.tm} °C, GC ${p.gc}%)`).join('\n');
    if(b.type==='diagram')return [b.title+(b.focus_label?` (${b.focus_label})`:''),b.caption].filter(Boolean).join('\n');
    if(b.type==='protein')return [b.name||b.label,b.gene&&`Gene: ${b.gene}`,b.uniprot&&`UniProt: ${b.uniprot}`,b.pdb&&`PDB: ${b.pdb}`,b.function].filter(Boolean).join('\n');
    return b.steps.map((s,i)=>`${i+1}. ${s.label}\n${s.iupac_name?displayName(s.iupac_name):'IUPAC name unavailable'}${s.formula?' ('+formulaText(s.formula)+')':''}${s.limitation?'\n'+s.limitation:''}`).join('\n\n');
  }).join('\n\n');
}
