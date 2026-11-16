import {useEffect,useRef,useState} from 'react';
import type {Block} from './types';
import {Dialog} from './Dialog';
import {savePNG} from './Blocks';
import {lazy,Suspense} from 'react';
const Explorer=lazy(()=>import('./DiagramExplorer').then(m=>({default:m.DiagramExplorer})));
const Zoom=lazy(()=>import('./DiagramExplorer').then(m=>({default:m.FigureExplorer})));
import {loadSection} from './diagramCatalog';

type Of<T extends Block['type']>=Extract<Block,{type:T}>;
const webgl=()=>{try{const c=document.createElement('canvas');return !!(c.getContext('webgl2')||c.getContext('webgl'));}catch{return false;}};
const svgSrc=(svg:string)=>'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);

function CopyText({label,value}:{label:string;value:string}){
  const [copied,setCopied]=useState(false);
  return <button type="button" className="bio-copy" aria-label={`Copy ${label}`} title={copied?'Copied':`Copy ${label}`} onClick={()=>void navigator.clipboard.writeText(value).then(()=>{setCopied(true);setTimeout(()=>setCopied(false),1400);}).catch(()=>{})}><i className={copied?'fas fa-check':'far fa-copy'} aria-hidden="true"/></button>;
}

function SequenceText({label,value}:{label:string;value:string}){
  return <div className="bio-sequence"><div className="bio-sequence-head"><span>{label}</span><CopyText label={label.toLowerCase()} value={value.replace(/…$/,'')}/></div><code>{value.match(/.{1,10}/g)?.join(' ')}</code></div>;
}

function Card({eyebrow,title,source,children}:{eyebrow:string;title:string;source:string;children:React.ReactNode}){
  return <figure className="chem-card bio-card"><figcaption><span className="eyebrow">{eyebrow}</span>{title&&<strong>{title}</strong>}</figcaption><div className="bio-body">{children}</div><p className="bio-source">{source}</p></figure>;
}

function Facts({rows}:{rows:[string,string][]}){
  return <table className="bio-facts"><tbody>{rows.map(([label,value])=><tr key={label}><th scope="row">{label}</th><td>{value}</td></tr>)}</tbody></table>;
}

function Figure({svg,label}:{svg:string;label:string}){
  const [error,setError]=useState(''),[zoom,setZoom]=useState(false);
  return <div className="bio-figure"><button type="button" className="bio-figure-open" aria-label={`Explore ${label}`} onClick={()=>setZoom(true)}><img src={svgSrc(svg)} alt={label}/></button>
    <div className="bio-figure-actions"><button type="button" className="bio-save" onClick={()=>setZoom(true)}><i className="fas fa-search-plus" aria-hidden="true"/> Explore</button><button type="button" className="bio-save" onClick={()=>void savePNG(svg).catch(e=>setError(String(e)))}><i className="fas fa-download" aria-hidden="true"/> Save PNG</button></div>
    {error&&<p role="alert">{error}</p>}{zoom&&<Suspense fallback={null}><Zoom svg={svg} title={label} onClose={()=>setZoom(false)}/></Suspense>}</div>;
}

function SectionPreview({name,title}:{name:string;title:string}){
  const [svg,setSvg]=useState('');
  useEffect(()=>{let live=true;loadSection(name).then(text=>{if(live)setSvg(text);}).catch(()=>{});return()=>{live=false;};},[name]);
  return svg?<img className="diagram-preview" src={svgSrc(svg)} alt={title}/>:<div className="diagram-preview placeholder"/>;
}

export function DiagramView({block:b}:{block:Of<'diagram'>}){
  const [open,setOpen]=useState(false);
  return <figure className="chem-card bio-card diagram-card"><figcaption><span className="eyebrow">{b.kind==='model'?'3D model':b.section||'Diagram'}</span><strong>{b.title}</strong></figcaption>
    <button type="button" className="diagram-open" onClick={()=>setOpen(true)} aria-label={`Explore ${b.title}`}>
      {b.kind==='section'?<SectionPreview name={b.name} title={b.title}/>:<div className="diagram-preview model-preview"><i className="fas fa-cube" aria-hidden="true"/><span>Interactive 3D model</span></div>}
      <span className="bio-action diagram-explore"><i className="fas fa-search-plus" aria-hidden="true"/> {b.kind==='model'?'Explore in 3D':'Explore labelled parts'}</span>
    </button>
    {b.caption&&<p className="bio-source diagram-caption">{b.caption}</p>}
    {open&&<Suspense fallback={null}><Explorer id={b.name} onClose={()=>setOpen(false)}/></Suspense>}
  </figure>;
}

export function SequenceView({block:b}:{block:Of<'sequence'>}){
  const kind=b.kind==='protein'?'Protein':b.kind.toUpperCase();
  return <Card eyebrow={`${kind} sequence`} title={b.label} source={b.source}>
    <Facts rows={b.facts}/>
    <SequenceText label={b.kind==='protein'?'Sequence':'Sequence (5′→3′)'} value={b.sequence.length>3000?b.sequence.slice(0,3000)+'…':b.sequence}/>
    {b.reverse_complement&&<SequenceText label="Reverse complement (5′→3′)" value={b.reverse_complement}/>}
    {b.transcript&&<SequenceText label="mRNA transcript" value={b.transcript}/>}
    {b.translation&&<SequenceText label="Translation (first open reading frame)" value={b.translation}/>}
  </Card>;
}

export function RnaFoldView({block:b}:{block:Of<'rna_fold'>}){
  return <Card eyebrow="RNA secondary structure" title={b.label} source={b.source}>
    <Figure svg={b.svg} label={`Predicted secondary structure of ${b.label||'the RNA'}`}/>
    <Facts rows={[['Free energy (MFE)',`${b.mfe.toFixed(1)} kcal/mol`],['Base pairs',String(b.pairs)],['Length',`${b.sequence.length} nt`]]}/>
    <div className="bio-sequence"><div className="bio-sequence-head"><span>Dot-bracket notation</span><CopyText label="dot-bracket structure" value={b.structure}/></div><code className="bio-dotbracket">{b.sequence}{'\n'}{b.structure}</code></div>
  </Card>;
}

export function GeneMapView({block:b}:{block:Of<'gene_map'>}){
  return <Card eyebrow={b.accession?`Gene map · ${b.accession}`:'Gene map'} title={b.title} source={b.source}>
    <Figure svg={b.svg} label={`Feature map of ${b.title||'the sequence'}`}/>
    <details className="bio-details"><summary>{b.features.length} features · {b.length.toLocaleString()} bp</summary>
      <table className="bio-facts"><thead><tr><th>Feature</th><th>Position</th><th>Strand</th></tr></thead><tbody>{b.features.map((f,i)=><tr key={i}><td>{f.name}</td><td>{f.start.toLocaleString()}–{f.end.toLocaleString()}</td><td>{f.strand>0?'+':f.strand<0?'−':'·'}</td></tr>)}</tbody></table>
    </details>
  </Card>;
}

const dg=(value:number|null)=>value===null?'None found':`${value.toFixed(1)} kcal/mol`;
export function PrimersView({block:b}:{block:Of<'primers'>}){
  return <Card eyebrow="PCR primers" title={b.primers.length===2?'Primer pair':''} source={b.source}>
    <div className="bio-scroll"><table className="bio-facts bio-primers"><thead><tr><th>Primer</th><th>Sequence (5′→3′)</th><th>Length</th><th>Tm</th><th>GC</th><th>Hairpin ΔG</th><th>Self-dimer ΔG</th></tr></thead>
      <tbody>{b.primers.map(p=><tr key={p.name+p.sequence}><td>{p.name}</td><td><code>{p.sequence}</code></td><td>{p.length} nt</td><td>{p.tm.toFixed(1)} °C</td><td>{p.gc.toFixed(0)}%</td><td>{dg(p.hairpin_dg)}</td><td>{dg(p.self_dimer_dg)}</td></tr>)}</tbody></table></div>
    {b.pair&&<Facts rows={[['Tm difference',`${b.pair.tm_difference.toFixed(1)} °C${b.pair.tm_difference>5?' (more than 5 °C apart)':''}`],['Cross-dimer ΔG',dg(b.pair.cross_dimer_dg)]]}/>}
  </Card>;
}

function ProteinStructure({pdb,onClose}:{pdb:string;onClose:()=>void}){
  const host=useRef<HTMLDivElement>(null);
  const [state,setState]=useState<'loading'|'ready'|string>('loading');
  useEffect(()=>{
    let live=true,viewer:{clear:()=>void}|null=null;
    if(!webgl()){setState('nowebgl');return;}
    (async()=>{
      try{
        const [{data},$3Dmol]=await Promise.all([window.bioez.request('proteinStructure',{pdb}),import('3dmol')]);
        if(!live||!host.current)return;
        const v=$3Dmol.createViewer(host.current,{backgroundColor:'#150f1a',antialias:true});viewer=v;
        v.addModel(data,'pdb');v.setStyle({},{cartoon:{color:'spectrum'}});v.setStyle({hetflag:true},{stick:{radius:0.18}});v.zoomTo();v.render();
        setState('ready');
      }catch(error){if(live)setState(error instanceof Error&&error.message?error.message.replace(/^Error invoking remote method '[^']+': (?:Error: )?/,''):'This structure could not be loaded.');}
    })();
    return()=>{live=false;viewer?.clear();};
  },[pdb]);
  return <Dialog title={`PDB ${pdb}`} onClose={onClose} className="smiles-explorer protein-viewer">
    <p className="smiles-explorer-help">Cartoon coloured from the N-terminus (blue) to the C-terminus (red); ligands and hemes as sticks. Drag to rotate, scroll to zoom.</p>
    {state==='nowebgl'?<p className="notice">The 3D viewer needs graphics acceleration (WebGL), which is turned off or unavailable on this computer. <button type="button" className="reference-link" onClick={()=>void window.bioez.openReference?.(`https://www.rcsb.org/3d-view/${pdb}`)}>Open {pdb} in the RCSB 3D viewer</button> instead.</p>:<>
    {state!=='ready'&&<p className={state==='loading'?'smiles-explorer-status':'notice error'} role={state==='loading'?'status':'alert'}>{state==='loading'?'Downloading the structure from RCSB PDB…':state}</p>}
    <div ref={host} className="protein-3d" aria-label={`3D structure of PDB entry ${pdb}`}/></>}
  </Dialog>;
}

export function ProteinView({block:b}:{block:Of<'protein'>}){
  const [open,setOpen]=useState(false);
  const rows:[string,string][]=[];
  if(b.gene)rows.push(['Gene',b.gene]);
  if(b.organism)rows.push(['Organism',b.organism]);
  if(b.length)rows.push(['Length',`${b.length} amino acids`]);
  if(b.location)rows.push(['Location',b.location]);
  if(b.uniprot)rows.push(['UniProt',b.uniprot]);
  if(b.pdb)rows.push(['Structure',`${b.pdb}${b.method?` · ${b.method}`:''}${b.resolution?` · ${b.resolution} Å`:''}`]);
  return <Card eyebrow="Protein" title={b.name||b.label} source={b.source}>
    <Facts rows={rows}/>
    {b.function&&<p className="bio-function"><strong>Function.</strong> {b.function}</p>}
    {b.pdb_title&&<p className="bio-pdb-title">{b.pdb_title.charAt(0)+b.pdb_title.slice(1).toLowerCase()}</p>}
    {b.pdb&&<button type="button" className="bio-action" onClick={()=>setOpen(true)}><i className="fas fa-cube" aria-hidden="true"/> View 3D structure</button>}
    {open&&b.pdb&&<ProteinStructure pdb={b.pdb} onClose={()=>setOpen(false)}/>}
  </Card>;
}
