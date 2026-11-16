import {useEffect,useMemo,useRef,useState,type PointerEvent as ReactPointerEvent} from 'react';
import {Dialog} from './Dialog';
import {DIAGRAMS,loadModel,loadSection,type DiagramEntry,type Part} from './diagramCatalog';

const webgl=()=>{try{const c=document.createElement('canvas');return !!(c.getContext('webgl2')||c.getContext('webgl'));}catch{return false;}};

function PartList({parts,active,hidden,onHover,onToggle}:{parts:Part[];active:string|null;hidden?:Set<string>;onHover:(id:string|null)=>void;onToggle?:(id:string)=>void}){
  return <ul className="explorer-parts" aria-label="Parts">{parts.map(p=><li key={p.id}>
    <button type="button" className="explorer-part" aria-pressed={active===p.id} onMouseEnter={()=>onHover(p.id)} onMouseLeave={()=>onHover(null)} onFocus={()=>onHover(p.id)} onBlur={()=>onHover(null)} onClick={()=>onHover(p.id)}>
      {p.colour&&<span className="explorer-swatch" style={{background:p.colour}}/>}<span>{p.label}</span>
    </button>
    {onToggle&&<button type="button" className="explorer-eye" aria-label={`${hidden?.has(p.id)?'Show':'Hide'} ${p.label}`} aria-pressed={!hidden?.has(p.id)} onClick={()=>onToggle(p.id)}><i className={hidden?.has(p.id)?'fas fa-eye-slash':'fas fa-eye'} aria-hidden="true"/></button>}
  </li>)}</ul>;
}

function Info({part}:{part:Part|undefined}){
  return <div className="explorer-info" aria-live="polite">{part?<><strong>{part.label}</strong>{part.info&&<p>{part.info}</p>}</>:<p className="muted">Hover or tap a part to identify it.</p>}</div>;
}

/* ---------- 2D section diagrams (T.S. / L.S. / V.S.) ---------- */
function SectionExplorer({entry}:{entry:DiagramEntry}){
  const host=useRef<HTMLDivElement>(null),stage=useRef<HTMLDivElement>(null);
  const [parts,setParts]=useState<Part[]>([]),[active,setActive]=useState<string|null>(null),[labels,setLabels]=useState(true),[error,setError]=useState('');
  const [view,setView]=useState({x:0,y:0,k:1});
  const drag=useRef<{x:number;y:number;vx:number;vy:number}|null>(null);
  useEffect(()=>{let live=true;loadSection(entry.id).then(svg=>{
    if(!live||!host.current)return;
    // Bundled, first-party SVG (never model output), so it is safe to place inline for hover highlighting.
    host.current.innerHTML=svg;
    const root=host.current.querySelector('svg');root?.removeAttribute('width');root?.removeAttribute('height');
    setParts(Array.from(host.current.querySelectorAll<SVGGElement>('g.part')).map(g=>({id:g.id,label:g.dataset.label||g.id,info:g.dataset.info||''})));
  }).catch(()=>live&&setError('This diagram could not be loaded.'));return()=>{live=false;};},[entry.id]);
  useEffect(()=>{const root=host.current;if(!root)return;
    root.querySelectorAll('g.part').forEach(g=>g.classList.toggle('is-active',g.id===active));
    root.querySelector('svg')?.classList.toggle('has-active',!!active);
  },[active,parts]);
  useEffect(()=>{host.current?.querySelector('svg')?.classList.toggle('labels-hidden',!labels);},[labels,parts]);
  const zoom=(factor:number,cx?:number,cy?:number)=>setView(v=>{const k=Math.max(.6,Math.min(8,v.k*factor));const r=stage.current?.getBoundingClientRect();const px=cx??(r?r.width/2:0),py=cy??(r?r.height/2:0);return {k,x:px-(px-v.x)*k/v.k,y:py-(py-v.y)*k/v.k};});
  const pointerDown=(e:ReactPointerEvent)=>{drag.current={x:e.clientX,y:e.clientY,vx:view.x,vy:view.y};(e.target as Element).setPointerCapture?.(e.pointerId);};
  const pointerMove=(e:ReactPointerEvent)=>{
    if(drag.current){setView(v=>({...v,x:drag.current!.vx+e.clientX-drag.current!.x,y:drag.current!.vy+e.clientY-drag.current!.y}));return;}
    const part=(e.target as Element).closest?.('g.part');setActive(part?part.id:null);
  };
  return <div className="explorer-layout">
    <div className="explorer-stage" ref={stage} onWheel={e=>{const r=stage.current!.getBoundingClientRect();zoom(e.deltaY<0?1.15:1/1.15,e.clientX-r.left,e.clientY-r.top);}} onPointerDown={pointerDown} onPointerMove={pointerMove} onPointerUp={()=>{drag.current=null;}} onPointerLeave={()=>{drag.current=null;}}>
      {error?<p className="notice error" role="alert">{error}</p>:<div className="explorer-svg" ref={host} style={{transform:`translate(${view.x}px,${view.y}px) scale(${view.k})`}}/>}
      <div className="explorer-tools"><button type="button" aria-label="Zoom in" onClick={()=>zoom(1.25)}><i className="fas fa-plus"/></button><button type="button" aria-label="Zoom out" onClick={()=>zoom(1/1.25)}><i className="fas fa-minus"/></button><button type="button" aria-label="Reset view" onClick={()=>setView({x:0,y:0,k:1})}><i className="fas fa-compress"/></button><button type="button" aria-pressed={labels} onClick={()=>setLabels(!labels)}>{labels?'Hide labels':'Show labels'}</button></div>
    </div>
    <aside className="explorer-side"><Info part={parts.find(p=>p.id===active)}/><PartList parts={parts} active={active} onHover={setActive}/></aside>
  </div>;
}

/* ---------- 3D models (cells, human body) ---------- */
function ModelExplorer({entry}:{entry:DiagramEntry}){
  const host=useRef<HTMLDivElement>(null);
  const [parts,setParts]=useState<Part[]>([]),[active,setActive]=useState<string|null>(null),[hidden,setHidden]=useState<Set<string>>(new Set()),[state,setState]=useState<'loading'|'ready'|'nowebgl'|'error'>('loading');
  const api=useRef<{highlight:(id:string|null)=>void;visible:(id:string,on:boolean)=>void}|null>(null);
  useEffect(()=>{
    if(!webgl()){setState('nowebgl');return;}
    let live=true,dispose=()=>{};
    (async()=>{try{
      const [THREE,{GLTFLoader},{OrbitControls},model]=await Promise.all([import('three'),import('three/examples/jsm/loaders/GLTFLoader.js'),import('three/examples/jsm/controls/OrbitControls.js'),loadModel(entry.id)]);
      if(!live||!host.current)return;
      const el=host.current,width=el.clientWidth,height=el.clientHeight;
      const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});renderer.setPixelRatio(Math.min(2,window.devicePixelRatio));renderer.setSize(width,height);renderer.setClearColor(0x000000,0);el.appendChild(renderer.domElement);
      const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(40,width/height,0.01,5000);
      scene.add(new THREE.HemisphereLight(0xffffff,0x332244,1.6));const sun=new THREE.DirectionalLight(0xffffff,1.6);sun.position.set(3,5,4);scene.add(sun);const fill=new THREE.DirectionalLight(0xc4b5fd,0.6);fill.position.set(-4,-2,-3);scene.add(fill);
      const gltf=await new GLTFLoader().parseAsync(model.glb,'');
      const root=gltf.scene;scene.add(root);
      const box=new THREE.Box3().setFromObject(root),size=box.getSize(new THREE.Vector3()).length(),center=box.getCenter(new THREE.Vector3());
      root.position.sub(center);
      // Fit the whole model: distance from the larger of its height and width against the field of view.
      const dims=box.getSize(new THREE.Vector3()),fov=camera.fov*Math.PI/180,fitH=dims.y/2/Math.tan(fov/2),fitW=Math.max(dims.x,dims.z)/2/Math.tan(fov/2)/camera.aspect,distance=Math.max(fitH,fitW)*1.25+Math.max(dims.x,dims.z)/2;
      camera.position.copy(new THREE.Vector3(0.55,0.25,0.8).normalize().multiplyScalar(distance));camera.near=size/500;camera.far=size*20;camera.updateProjectionMatrix();
      const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.autoRotate=true;controls.autoRotateSpeed=0.8;controls.addEventListener('start',()=>{controls.autoRotate=false;});
      const byPart=new Map<string,import('three').Mesh[]>();
      root.traverse(o=>{const m=o as import('three').Mesh;if(!m.isMesh)return;const id=m.name.replace(/_\d+$/,'');const key=model.parts.find(p=>id===p.id||id.startsWith(p.id))?.id||id;(byPart.get(key)||byPart.set(key,[]).get(key)!).push(m);m.material=(m.material as import('three').Material).clone();});
      const swatch=(id:string)=>{const m=byPart.get(id)?.[0]?.material as import('three').MeshStandardMaterial|undefined;return m?.color?'#'+m.color.getHexString():undefined;};
      setParts(model.parts.filter(p=>byPart.has(p.id)).map(p=>({...p,colour:swatch(p.id)})));
      api.current={
        highlight:id=>byPart.forEach((meshes,key)=>meshes.forEach(m=>{const mat=m.material as import('three').MeshStandardMaterial;mat.emissive?.setHex(key===id?0x6d28d9:0x000000);mat.emissiveIntensity=key===id?0.9:0;})),
        visible:(id,on)=>byPart.get(id)?.forEach(m=>{m.visible=on;}),
      };
      const ray=new THREE.Raycaster(),pointer=new THREE.Vector2();
      const pick=(event:PointerEvent)=>{const r=renderer.domElement.getBoundingClientRect();pointer.set(((event.clientX-r.left)/r.width)*2-1,-((event.clientY-r.top)/r.height)*2+1);ray.setFromCamera(pointer,camera);
        const hit=ray.intersectObjects(root.children,true).find(h=>h.object.visible);if(!hit){setActive(null);return;}
        for(const [key,meshes] of byPart)if(meshes.includes(hit.object as import('three').Mesh)){setActive(key);return;}};
      renderer.domElement.addEventListener('click',pick);
      const resize=()=>{const w=el.clientWidth,h=el.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();};
      const observer=new ResizeObserver(resize);observer.observe(el);
      let frame=0;const tick=()=>{frame=requestAnimationFrame(tick);controls.update();renderer.render(scene,camera);};tick();
      setState('ready');
      dispose=()=>{cancelAnimationFrame(frame);observer.disconnect();renderer.domElement.removeEventListener('click',pick);controls.dispose();renderer.dispose();scene.traverse(o=>{const m=o as import('three').Mesh;m.geometry?.dispose();(m.material as import('three').Material|undefined)?.dispose?.();});renderer.domElement.remove();};
    }catch{if(live)setState('error');}})();
    return()=>{live=false;dispose();};
  },[entry.id]);
  useEffect(()=>{api.current?.highlight(active);},[active]);
  const toggle=(id:string)=>setHidden(previous=>{const next=new Set(previous);const on=next.has(id);on?next.delete(id):next.add(id);api.current?.visible(id,on);return next;});
  return <div className="explorer-layout">
    <div className="explorer-stage model" ref={host}>
      {state==='loading'&&<p className="smiles-explorer-status explorer-overlay" role="status">Building the 3D model…</p>}
      {state==='error'&&<p className="notice error explorer-overlay" role="alert">This 3D model could not be loaded.</p>}
      {state==='nowebgl'&&<p className="notice explorer-overlay">The 3D view needs graphics acceleration (WebGL), which is turned off or unavailable on this computer.</p>}
      {state==='ready'&&<p className="explorer-hint">Drag to rotate · scroll to zoom · right-drag to pan · click a part</p>}
    </div>
    <aside className="explorer-side"><Info part={parts.find(p=>p.id===active)}/><PartList parts={parts} active={active} hidden={hidden} onHover={setActive} onToggle={toggle}/></aside>
  </div>;
}

export function DiagramExplorer({id,onClose}:{id:string;onClose:()=>void}){
  const entry=useMemo(()=>DIAGRAMS.find(d=>d.id===id),[id]);
  if(!entry)return null;
  return <Dialog title={entry.title} onClose={onClose} className="diagram-explorer">
    {entry.kind==='model'?<ModelExplorer entry={entry}/>:<SectionExplorer entry={entry}/>}
    <p className="explorer-credit">{entry.credit}</p>
  </Dialog>;
}

/* ---------- Any generated figure (gene map, RNA fold): zoom and pan ---------- */
export function FigureExplorer({svg,title,onClose}:{svg:string;title:string;onClose:()=>void}){
  const stage=useRef<HTMLDivElement>(null);
  const [view,setView]=useState({x:0,y:0,k:1});
  const drag=useRef<{x:number;y:number;vx:number;vy:number}|null>(null);
  const zoom=(factor:number,cx?:number,cy?:number)=>setView(v=>{const k=Math.max(.5,Math.min(10,v.k*factor));const r=stage.current?.getBoundingClientRect();const px=cx??(r?r.width/2:0),py=cy??(r?r.height/2:0);return {k,x:px-(px-v.x)*k/v.k,y:py-(py-v.y)*k/v.k};});
  return <Dialog title={title} onClose={onClose} className="diagram-explorer">
    <div className="explorer-stage figure" ref={stage} onWheel={e=>{const r=stage.current!.getBoundingClientRect();zoom(e.deltaY<0?1.15:1/1.15,e.clientX-r.left,e.clientY-r.top);}}
      onPointerDown={e=>{drag.current={x:e.clientX,y:e.clientY,vx:view.x,vy:view.y};}} onPointerMove={e=>{if(drag.current)setView(v=>({...v,x:drag.current!.vx+e.clientX-drag.current!.x,y:drag.current!.vy+e.clientY-drag.current!.y}));}} onPointerUp={()=>{drag.current=null;}} onPointerLeave={()=>{drag.current=null;}}>
      <img draggable={false} src={'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg)} alt={title} style={{transform:`translate(${view.x}px,${view.y}px) scale(${view.k})`}}/>
      <div className="explorer-tools"><button type="button" aria-label="Zoom in" onClick={()=>zoom(1.25)}><i className="fas fa-plus"/></button><button type="button" aria-label="Zoom out" onClick={()=>zoom(1/1.25)}><i className="fas fa-minus"/></button><button type="button" aria-label="Reset view" onClick={()=>setView({x:0,y:0,k:1})}><i className="fas fa-compress"/></button></div>
    </div>
  </Dialog>;
}

/* ---------- Browse every built-in diagram ---------- */
export function DiagramLibrary({onClose}:{onClose:()=>void}){
  const [open,setOpen]=useState<string|null>(null),[query,setQuery]=useState('');
  const shown=DIAGRAMS.filter(d=>(d.title+' '+d.keywords).toLowerCase().includes(query.toLowerCase()));
  const groups=[...new Set(shown.map(d=>d.group))];
  return <Dialog title="Diagram library" onClose={onClose} className="diagram-library">
    <input className="library-search" type="search" placeholder="Search diagrams (e.g. stem, kidney, mitochondria)" value={query} onChange={e=>setQuery(e.target.value)} aria-label="Search diagrams"/>
    {groups.map(group=><section key={group}><h3>{group}</h3><div className="library-grid">{shown.filter(d=>d.group===group).map(d=><button type="button" key={d.id} className="library-card" onClick={()=>setOpen(d.id)}>
      <span className="library-kind">{d.kind==='model'?'3D':d.section}</span><span>{d.title}</span></button>)}</div></section>)}
    {!shown.length&&<p className="muted">No diagram matches “{query}”.</p>}
    {open&&<DiagramExplorer id={open} onClose={()=>setOpen(null)}/>}
  </Dialog>;
}
