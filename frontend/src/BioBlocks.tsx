import {useEffect,useRef,useState} from 'react';
import type {Block} from './types';
import {Dialog} from './Dialog';
import {savePNG} from './Blocks';
import {DIAGRAMS} from './diagramCatalog';
import {lazy,Suspense} from 'react';
const Explorer=lazy(()=>import('./DiagramExplorer').then(m=>({default:m.DiagramExplorer})));
const Viewer=lazy(()=>import('./DiagramExplorer').then(m=>({default:m.DiagramViewer})));
const Zoom=lazy(()=>import('./DiagramExplorer').then(m=>({default:m.FigureExplorer})));

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

export function DiagramView({block:b}:{block:Of<'diagram'>}){
  const [open,setOpen]=useState(false),[view,setView]=useState<string|undefined>();
  // The heading follows what is on screen: the 3D model first when the drawing has one.
  const base=DIAGRAMS.find(d=>d.id===b.name),twin=base?.twin?DIAGRAMS.find(d=>d.id===base.twin):undefined;
  const shownEntry=DIAGRAMS.find(d=>d.id===(view??(base?.kind==='section'&&twin?.kind==='model'?twin.id:b.name)));
  // Diagrams sit apart from the prose: a floating glass stage, not a boxed card.
  return <figure className="diagram-float">
    <figcaption className="diagram-float-head"><span className="eyebrow">{shownEntry?.kind==='model'?'3D model':shownEntry?.section||'Diagram'}</span><strong>{shownEntry?.title||b.title}</strong></figcaption>
    {open?<div className="diagram-inline paused" aria-hidden="true"/>:<Suspense fallback={<div className="diagram-inline loading"/>}><Viewer id={b.name} focus={b.focus||undefined} cut={b.cut||''} compact onExpand={()=>setOpen(true)} view={view} onView={setView}/></Suspense>}
    {b.caption&&<p className="diagram-float-caption">{b.caption}</p>}
    {open&&<Suspense fallback={null}><Explorer id={b.name} focus={b.focus||undefined} cut={b.cut||''} onClose={()=>setOpen(false)} view={view} onView={setView}/></Suspense>}
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

type ProteinStyle='cartoon'|'sticks';
const PROTEIN_STYLES:[ProteinStyle,string][]=[['cartoon','Ribbon'],['sticks','Atoms']];

/** Live 3D protein (3Dmol), used inline in answers and in the full view. Starts when scrolled into view. */
function ProteinCanvas({pdb,compact,style,colour}:{pdb:string;compact?:boolean;style:ProteinStyle;colour:'spectrum'|'chain'}){
  const host=useRef<HTMLDivElement>(null),viewer=useRef<any>(null);
  const [state,setState]=useState<'idle'|'loading'|'ready'|'nowebgl'|string>('idle');
  useEffect(()=>{
    if(!host.current)return;
    const observer=new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting)){observer.disconnect();setState(s=>s==='idle'?'loading':s);}},{rootMargin:'200px'});
    observer.observe(host.current);return()=>observer.disconnect();
  },[]);
  // Start once when it scrolls into view; cleared only on unmount or a different structure (not on the state change to 'ready').
  const started=state!=='idle';
  useEffect(()=>{
    if(!started)return;
    if(!webgl()){setState('nowebgl');return;}
    let live=true;
    (async()=>{try{
      const [{data},$3Dmol]=await Promise.all([window.bioez.request('proteinStructure',{pdb}),import('3dmol')]);
      if(!live||!host.current)return;
      const v=$3Dmol.createViewer(host.current,{backgroundColor:'black',backgroundAlpha:0,antialias:true});viewer.current=v;
      v.addModel(data,'pdb');v.zoomTo();setState('ready');
    }catch(error){if(live)setState(error instanceof Error&&error.message?error.message.replace(/^Error invoking remote method '[^']+': (?:Error: )?/,''):'This structure could not be loaded.');}})();
    return()=>{live=false;viewer.current?.clear();viewer.current=null;};
  },[started,pdb]);
  useEffect(()=>{
    const v=viewer.current;if(!v||state!=='ready')return;
    const paint=colour==='chain'?{colorscheme:'chain'}:{color:'spectrum'};
    v.setStyle({},{});
    if(style==='cartoon'){v.setStyle({},{cartoon:{...paint,opacity:0.95}});v.setStyle({hetflag:true},{stick:{radius:0.2}});}
    if(style==='sticks')v.setStyle({},{stick:{radius:0.14,colorscheme:'Jmol'},sphere:{scale:0.22,colorscheme:'Jmol'}});
    v.render();
  },[style,colour,state]);
  return <div className={'explorer-stage protein-stage hologram'+(compact?' compact':'')}>
    <div ref={host} className="protein-3d" aria-label={`3D structure of PDB entry ${pdb}`}/>
    {(state==='loading'||state==='idle')&&<p className="smiles-explorer-status explorer-overlay" role="status">Downloading {pdb} from RCSB PDB…</p>}
    {state==='nowebgl'&&<p className="notice explorer-overlay">The 3D view needs graphics acceleration (WebGL), which is unavailable here. <button type="button" className="reference-link" onClick={()=>void window.bioez.openReference?.(`https://www.rcsb.org/3d-view/${pdb}`)}>Open {pdb} on RCSB</button>.</p>}
    {!['idle','loading','ready','nowebgl'].includes(state)&&<p className="notice error explorer-overlay" role="alert">{state}</p>}
    {state==='ready'&&<p className="explorer-hint">{compact?'Drag to rotate · Full view to zoom':'Drag to rotate · scroll to zoom · right-drag to pan'}</p>}
  </div>;
}

function ProteinControls({style,setStyle,colour,setColour}:{style:ProteinStyle;setStyle:(s:ProteinStyle)=>void;colour:'spectrum'|'chain';setColour:(c:'spectrum'|'chain')=>void}){
  return <>
    <div className="cut-control" role="group" aria-label="Display">{PROTEIN_STYLES.map(([k,l])=><button type="button" key={k} className="cut-mode" aria-pressed={style===k} onClick={()=>setStyle(k)}>{l}</button>)}</div>
    {style!=='sticks'&&<div className="dimension-switch" role="group" aria-label="Colour"><button type="button" className="cut-mode" aria-pressed={colour==='spectrum'} onClick={()=>setColour('spectrum')} title="N-terminus blue to C-terminus red">Rainbow</button><button type="button" className="cut-mode" aria-pressed={colour==='chain'} onClick={()=>setColour('chain')}>By chain</button></div>}
  </>;
}

export function ProteinView({block:b}:{block:Of<'protein'>}){
  const [open,setOpen]=useState(false),[style,setStyle]=useState<ProteinStyle>('cartoon'),[colour,setColour]=useState<'spectrum'|'chain'>('spectrum');
  const rows:[string,string][]=[];
  if(b.gene)rows.push(['Gene',b.gene]);
  if(b.organism)rows.push(['Organism',b.organism]);
  if(b.length)rows.push(['Length',`${b.length} amino acids`]);
  if(b.location)rows.push(['Location',b.location]);
  if(b.uniprot)rows.push(['UniProt',b.uniprot]);
  if(b.pdb)rows.push(['Structure',`${b.pdb}${b.method?` · ${b.method}`:''}${b.resolution?` · ${b.resolution} Å`:''}`]);
  const controls=<ProteinControls style={style} setStyle={setStyle} colour={colour} setColour={setColour}/>;
  return <Card eyebrow="Protein" title={b.name||b.label} source={b.source}>
    {b.pdb&&<div className="diagram-inline protein-inline">
      {open?<div className="diagram-inline paused" aria-hidden="true"/>:<ProteinCanvas pdb={b.pdb} compact style={style} colour={colour}/>}
      <div className="diagram-inline-bar">{controls}<span className="diagram-inline-status">{b.pdb_title&&<span className="protein-caption">{b.pdb_title.charAt(0)+b.pdb_title.slice(1).toLowerCase()}</span>}</span>
        <button type="button" className="holo-toggle expand" onClick={()=>setOpen(true)}><i className="fas fa-expand" aria-hidden="true"/> Full view</button></div>
    </div>}
    <Facts rows={rows}/>
    {b.function&&<p className="bio-function"><strong>Function.</strong> {b.function}</p>}
    {open&&b.pdb&&<Dialog title={`${b.name||b.label} · PDB ${b.pdb}`} onClose={()=>setOpen(false)} className="diagram-explorer protein-viewer">
      <div className="protein-full"><ProteinCanvas pdb={b.pdb} style={style} colour={colour}/><div className="protein-full-tools">{controls}</div></div>
      <p className="explorer-credit">Structure {b.pdb} from the RCSB Protein Data Bank; drawn with 3Dmol.js. {style!=='sticks'&&colour==='spectrum'?'Rainbow runs from the N-terminus (blue) to the C-terminus (red).':''}</p>
    </Dialog>}
  </Card>;
}
