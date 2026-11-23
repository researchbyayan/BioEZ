import {useEffect,useMemo,useRef,useState,type PointerEvent as ReactPointerEvent} from 'react';
import {createPortal} from 'react-dom';
import {Dialog} from './Dialog';
import {DIAGRAMS,loadModel,loadSection,type DiagramEntry,type Part} from './diagramCatalog';

const webgl=()=>{try{const c=document.createElement('canvas');return !!(c.getContext('webgl2')||c.getContext('webgl'));}catch{return false;}};

/** Starts work only once the element is on screen, so a long chat doesn't open many WebGL contexts. */
function useVisible(ref:React.RefObject<HTMLElement|null>,always:boolean){
  const [visible,setVisible]=useState(always);
  useEffect(()=>{if(always||visible||!ref.current)return;const observer=new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting)){setVisible(true);observer.disconnect();}},{rootMargin:'200px'});observer.observe(ref.current);return()=>observer.disconnect();},[always,visible,ref]);
  return visible;
}

function PartList({parts,active,hidden,onHover,onSelect,onToggle}:{parts:Part[];active:string|null;hidden?:Set<string>;onHover:(id:string|null)=>void;onSelect:(id:string)=>void;onToggle?:(id:string)=>void}){
  return <ul className="explorer-parts" aria-label="Parts">{parts.map(p=><li key={p.id}>
    <button type="button" className="explorer-part" aria-pressed={active===p.id} onMouseEnter={()=>onHover(p.id)} onMouseLeave={()=>onHover(null)} onFocus={()=>onHover(p.id)} onBlur={()=>onHover(null)} onClick={()=>onSelect(p.id)} title="Click to zoom to this part">
      {p.colour&&<span className="explorer-swatch" style={{background:p.colour}}/>}<span>{p.label}</span>
    </button>
    {onToggle&&<button type="button" className="explorer-eye" aria-label={`${hidden?.has(p.id)?'Show':'Hide'} ${p.label}`} aria-pressed={!hidden?.has(p.id)} onClick={()=>onToggle(p.id)}><i className={hidden?.has(p.id)?'fas fa-eye-slash':'fas fa-eye'} aria-hidden="true"/></button>}
  </li>)}</ul>;
}

function Info({part}:{part:Part|undefined}){
  return <div className="explorer-info" aria-live="polite">{part?<><strong>{part.label}</strong>{part.info&&<p>{part.info}</p>}</>:<p className="muted">Hover a part to identify it; click it to zoom in.</p>}</div>;
}

export type Cut={mode:'off'|'ts'|'ls';t:number};
interface ViewerProps {cut?:Cut;toolsTarget?:HTMLElement|null;entry:DiagramEntry;focus?:string;compact?:boolean;hologram:boolean;onParts?:(parts:Part[])=>void;active:string|null;setActive:(id:string|null)=>void;zoomTo:{id:string;n:number}|null;hidden?:Set<string>}

/* ---------- 2D sections (T.S. / L.S. / V.S.) ---------- */
function SectionViewer({entry,focus,compact,hologram,onParts,active,setActive,zoomTo,toolsTarget}:ViewerProps){
  const host=useRef<HTMLDivElement>(null),stage=useRef<HTMLDivElement>(null);
  const [labels,setLabels]=useState(true),[error,setError]=useState(''),[ready,setReady]=useState(false);
  const [view,setView]=useState({x:0,y:0,k:1,animate:false});
  const drag=useRef<{x:number;y:number;vx:number;vy:number;moved:boolean}|null>(null);
  useEffect(()=>{let live=true;loadSection(entry.id).then(svg=>{
    if(!live||!host.current)return;
    // Bundled, first-party SVG (never model output), so it is safe to place inline for hover highlighting.
    host.current.innerHTML=svg;
    const root=host.current.querySelector('svg');root?.removeAttribute('width');root?.removeAttribute('height');
    onParts?.(Array.from(host.current.querySelectorAll<SVGGElement>('g.part')).map(g=>({id:g.id,label:g.dataset.label||g.id,info:g.dataset.info||''})));
    setReady(true);
  }).catch(()=>live&&setError('This diagram could not be loaded.'));return()=>{live=false;};},[entry.id]);
  useEffect(()=>{const root=host.current;if(!root)return;
    root.querySelectorAll('g.part').forEach(g=>g.classList.toggle('is-active',g.id===active));
    root.querySelector('svg')?.classList.toggle('has-active',!!active);
  },[active,ready]);
  useEffect(()=>{host.current?.querySelector('svg')?.classList.toggle('labels-hidden',!labels);},[labels,ready]);
  // Zoom so the part fills about half the stage, centred.
  const frame=(id:string)=>{
    const part=host.current?.querySelector<SVGGElement>(`g.part#${CSS.escape(id)}`),box=stage.current?.getBoundingClientRect(),svgBox=host.current?.getBoundingClientRect();
    if(!part||!box||!svgBox)return;
    const r=part.getBoundingClientRect(),k0=view.k;
    const bx=(r.left-svgBox.left)/k0,by=(r.top-svgBox.top)/k0,bw=r.width/k0,bh=r.height/k0;
    const k=Math.max(1,Math.min(5,Math.min(box.width*0.5/bw,box.height*0.5/bh)));
    setView({k,x:box.width/2-(bx+bw/2)*k,y:box.height/2-(by+bh/2)*k,animate:true});setActive(id);
  };
  useEffect(()=>{if(ready&&focus)requestAnimationFrame(()=>frame(focus));},[ready,focus]);
  useEffect(()=>{if(ready&&zoomTo)frame(zoomTo.id);},[zoomTo]);
  const zoom=(factor:number,cx?:number,cy?:number)=>setView(v=>{const k=Math.max(.6,Math.min(8,v.k*factor));const r=stage.current?.getBoundingClientRect();const px=cx??(r?r.width/2:0),py=cy??(r?r.height/2:0);return {k,x:px-(px-v.x)*k/v.k,y:py-(py-v.y)*k/v.k,animate:false};});
  const tools=<div className="explorer-tools"><button type="button" aria-label="Zoom in" title="Zoom in" onClick={()=>zoom(1.25)}><i className="fas fa-plus"/></button><button type="button" aria-label="Zoom out" title="Zoom out" onClick={()=>zoom(1/1.25)}><i className="fas fa-minus"/></button><button type="button" aria-label="Reset view" title="Reset view" onClick={()=>{setView({x:0,y:0,k:1,animate:true});setActive(null);}}><i className="fas fa-compress"/></button><button type="button" className="text-tool" aria-pressed={labels} onClick={()=>setLabels(!labels)}>{labels?'Hide labels':'Show labels'}</button></div>;
  const pointerDown=(e:ReactPointerEvent)=>{drag.current={x:e.clientX,y:e.clientY,vx:view.x,vy:view.y,moved:false};};
  const pointerMove=(e:ReactPointerEvent)=>{
    if(drag.current&&(e.buttons&1)){const dx=e.clientX-drag.current.x,dy=e.clientY-drag.current.y;if(Math.abs(dx)+Math.abs(dy)>3)drag.current.moved=true;setView(v=>({...v,x:drag.current!.vx+dx,y:drag.current!.vy+dy,animate:false}));return;}
    const part=(e.target as Element).closest?.('g.part');setActive(part?part.id:null);
  };
  const pointerUp=(e:ReactPointerEvent)=>{const wasDrag=drag.current?.moved;drag.current=null;if(wasDrag)return;const part=(e.target as Element).closest?.('g.part');if(part)frame(part.id);};
  return <div className={'explorer-stage section'+(hologram?' hologram':'')+(compact?' compact':'')} ref={stage}
    onWheel={e=>{if(compact&&!e.ctrlKey&&!e.metaKey)return;const r=stage.current!.getBoundingClientRect();zoom(e.deltaY<0?1.15:1/1.15,e.clientX-r.left,e.clientY-r.top);}}
    onPointerDown={pointerDown} onPointerMove={pointerMove} onPointerUp={pointerUp} onPointerLeave={()=>{drag.current=null;setActive(null);}}>
    {error?<p className="notice error" role="alert">{error}</p>:<div className={'explorer-svg'+(view.animate?' animate':'')} ref={host} style={{transform:`translate(${view.x}px,${view.y}px) scale(${view.k})`}}/>}
    {!compact&&tools}
    {compact&&toolsTarget&&createPortal(tools,toolsTarget)}
  </div>;
}

/* ---------- 3D models (cells, human body) ---------- */
const HOLO_VERTEX='varying vec3 vN;varying vec3 vV;void main(){vec4 mv=modelViewMatrix*vec4(position,1.0);vN=normalize(normalMatrix*normal);vV=normalize(-mv.xyz);gl_Position=projectionMatrix*mv;}';
const HOLO_FRAGMENT='uniform vec3 tint;uniform float strength;varying vec3 vN;varying vec3 vV;void main(){float f=pow(1.0-abs(dot(vN,vV)),2.4);gl_FragColor=vec4(tint*f*strength,f*strength);}';

const props_tools=(target?:HTMLElement|null)=>target?createPortal(<span className="footer-hint">Drag to rotate · Full view to zoom</span>,target):null;

/** X-ray look: shells (skin, membranes) become see-through, solid parts stay nearly solid, colours unchanged. */
const xray=(base:number,on:boolean)=>on?(base<1?base*0.6:0.88):base;

type ModelApi={cut:(cut:Cut)=>void;highlight:(id:string|null)=>void;visible:(id:string,on:boolean)=>void;focus:(id:string|null)=>void;hologram:(on:boolean)=>void};

function ModelViewer({entry,focus,compact,hologram,onParts,active,setActive,zoomTo,hidden,toolsTarget,cut}:ViewerProps){
  const host=useRef<HTMLDivElement>(null);
  const visible=useVisible(host,!compact);
  const [state,setState]=useState<'idle'|'loading'|'ready'|'nowebgl'|'error'>('idle');
  const api=useRef<ModelApi|null>(null);
  useEffect(()=>{
    if(!visible)return;
    if(!webgl()){setState('nowebgl');return;}
    setState('loading');
    let live=true,dispose=()=>{};
    (async()=>{try{
      const [THREE,{GLTFLoader},{OrbitControls},model]=await Promise.all([import('three'),import('three/examples/jsm/loaders/GLTFLoader.js'),import('three/examples/jsm/controls/OrbitControls.js'),loadModel(entry.id)]);
      if(!live||!host.current)return;
      type Mesh=import('three').Mesh;type Std=import('three').MeshStandardMaterial;
      const el=host.current,width=el.clientWidth,height=el.clientHeight;
      const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});renderer.setPixelRatio(Math.min(2,window.devicePixelRatio));renderer.setSize(width,height);renderer.setClearColor(0x000000,0);renderer.localClippingEnabled=true;renderer.domElement.classList.add('model-canvas');el.querySelectorAll('canvas.model-canvas').forEach(c=>c.remove());el.prepend(renderer.domElement);
      const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(40,width/height,0.01,5000);
      scene.add(new THREE.HemisphereLight(0xffffff,0x332244,1.6));const sun=new THREE.DirectionalLight(0xffffff,1.6);sun.position.set(3,5,4);scene.add(sun);const rim=new THREE.DirectionalLight(0xc084fc,1.1);rim.position.set(-4,-2,-3);scene.add(rim);
      const gltf=await new GLTFLoader().parseAsync(model.glb,'');
      // Cancelled while parsing (closed, or React re-running the effect): don't leave a frozen canvas behind.
      if(!live){renderer.dispose();renderer.domElement.remove();return;}
      const root=gltf.scene;scene.add(root);
      const box=new THREE.Box3().setFromObject(root),size=box.getSize(new THREE.Vector3()).length(),center=box.getCenter(new THREE.Vector3());
      root.position.sub(center);root.updateMatrixWorld(true);
      const fit=(target:import('three').Box3,margin:number)=>{const dims=target.getSize(new THREE.Vector3()),fov=camera.fov*Math.PI/180;return Math.max(dims.y/2/Math.tan(fov/2),Math.max(dims.x,dims.z)/2/Math.tan(fov/2)/camera.aspect)*margin+Math.max(dims.x,dims.z)/2;};
      const direction=new THREE.Vector3(0.55,0.25,0.8).normalize();
      camera.position.copy(direction.clone().multiplyScalar(fit(new THREE.Box3().setFromObject(root),1.25)));camera.near=size/500;camera.far=size*20;camera.updateProjectionMatrix();
      const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.autoRotate=!focus;controls.autoRotateSpeed=0.8;controls.enableZoom=!compact;controls.addEventListener('start',()=>{controls.autoRotate=false;});
      const byPart=new Map<string,Mesh[]>(),holo:Mesh[]=[];
      const holoMaterial=new THREE.ShaderMaterial({vertexShader:HOLO_VERTEX,fragmentShader:HOLO_FRAGMENT,uniforms:{tint:{value:new THREE.Color(0xb47cff)},strength:{value:0.42}},transparent:true,blending:THREE.AdditiveBlending,depthWrite:false});
      const meshes:Mesh[]=[];root.traverse(o=>{if((o as Mesh).isMesh)meshes.push(o as Mesh);});meshes.forEach(m=>{if(!m.geometry.getAttribute('normal'))m.geometry.computeVertexNormals();const id=m.name.replace(/_\d+$/,'');const key=(model.parts.find(p=>id===p.id)||model.parts.find(p=>id.startsWith(p.id+'_')))?.id||id;(byPart.get(key)||byPart.set(key,[]).get(key)!).push(m);m.material=(m.material as Std).clone();
        const glow=new THREE.Mesh(m.geometry,holoMaterial);glow.raycast=()=>{};m.add(glow);holo.push(glow);});
      const swatch=(id:string)=>{const m=byPart.get(id)?.[0]?.material as Std|undefined;return m?.color?'#'+m.color.getHexString():undefined;};
      onParts?.(model.parts.filter(p=>byPart.has(p.id)).map(p=>({...p,colour:swatch(p.id)})));
      // Smoothly move the camera to frame one part (or the whole model).
      let tween:{from:import('three').Vector3;to:import('three').Vector3;tFrom:import('three').Vector3;tTo:import('three').Vector3;t:number}|null=null;let holoOn=hologram;let lastCut:Cut['mode']='off';
      const plane=new THREE.Plane(),modelBox=new THREE.Box3().setFromObject(root);
      const focusOn=(id:string|null)=>{
        const meshes=id?byPart.get(id):null,target=new THREE.Box3();
        if(meshes?.length)meshes.forEach(m=>target.expandByObject(m));else target.setFromObject(root);
        const c=target.getCenter(new THREE.Vector3()),distance=fit(target,meshes?.length?1.9:1.25);
        const dir=camera.position.clone().sub(controls.target).normalize();
        tween={from:camera.position.clone(),to:c.clone().add(dir.multiplyScalar(distance)),tFrom:controls.target.clone(),tTo:c,t:performance.now()};controls.autoRotate=false;
      };
      api.current={
        highlight:id=>byPart.forEach((meshes,key)=>meshes.forEach(m=>{const mat=m.material as Std;const base=(mat.userData.opacity??=mat.opacity);const on=key===id;
          mat.emissive?.setHex(on?0x9333ea:0x000000);mat.emissiveIntensity=on?1.1:0;
          const faded=!!id&&!on;mat.opacity=faded?Math.min(base,0.2):xray(base,holoOn);mat.transparent=mat.opacity<1;mat.depthWrite=!faded;mat.needsUpdate=true;})),
        visible:(id,on)=>byPart.get(id)?.forEach(m=>{m.visible=on;}),
        focus:focusOn,
        cut:({mode,t})=>{
          const planes=mode==='off'?[]:[plane];
          if(mode!=='off'){
            const dims=modelBox.getSize(new THREE.Vector3()),axes=[new THREE.Vector3(1,0,0),new THREE.Vector3(0,1,0),new THREE.Vector3(0,0,1)];
            const lengths=[dims.x,dims.y,dims.z],long=lengths.indexOf(Math.max(...lengths));
            // T.S.: across the organ's long axis. L.S.: lengthwise, viewed from the front (or the side for front-to-back organs).
            const normal=mode==='ts'?axes[long].clone():(long===2?axes[0].clone():axes[2].clone());
            const lo=modelBox.min.dot(normal),hi=modelBox.max.dot(normal);
            plane.set(normal,-(lo+(hi-lo)*t));
            if(lastCut!==mode){
              // Three.js keeps the side the normal points to, so look from the removed side straight at the cut face,
              // framing it by the organ's size across the cut rather than along it.
              const centre=modelBox.getCenter(new THREE.Vector3()),onPlane=centre.clone().add(normal.clone().multiplyScalar(lo+(hi-lo)*t-centre.dot(normal)));
              const across=[dims.x,dims.y,dims.z].filter((_,i)=>i!==axes.findIndex(a=>Math.abs(a.dot(normal))>0.5)),fov=camera.fov*Math.PI/180;
              const distance=Math.max(across[0]/2/Math.tan(fov/2)/camera.aspect,across[1]/2/Math.tan(fov/2),across[0]/2/Math.tan(fov/2))*1.45;
              tween={from:camera.position.clone(),to:onPlane.clone().add(normal.clone().multiplyScalar(-distance)).add(Math.abs(normal.y)>0.9?new THREE.Vector3(0,0,distance*0.06):new THREE.Vector3(0,0,0)),tFrom:controls.target.clone(),tTo:onPlane,t:performance.now()};controls.autoRotate=false;}
          }else if(lastCut!=='off'){focusOn(null);}
          lastCut=mode;
          byPart.forEach(meshes=>meshes.forEach(m=>{const mat=m.material as Std;mat.clippingPlanes=planes;mat.clipShadows=true;mat.needsUpdate=true;}));
          holoMaterial.clippingPlanes=planes;holoMaterial.needsUpdate=true;
        },
        hologram:on=>{holoOn=on;holo.forEach(g=>{g.visible=on;});byPart.forEach(meshes=>meshes.forEach(m=>{const mat=m.material as Std;const base=(mat.userData.opacity??=mat.opacity);mat.opacity=xray(base,on);mat.transparent=mat.opacity<1;mat.needsUpdate=true;}));},
      };
      api.current.hologram(hologram);
      hidden?.forEach(id=>api.current?.visible(id,false));
      if(cut&&cut.mode!=='off')api.current.cut(cut);
      if(focus){api.current.highlight(focus);if(!cut||cut.mode==='off')focusOn(focus);setActive(focus);}
      const ray=new THREE.Raycaster(),pointer=new THREE.Vector2();
      let down={x:0,y:0};
      const press=(e:PointerEvent)=>{down={x:e.clientX,y:e.clientY};};
      const pick=(event:PointerEvent)=>{if(Math.abs(event.clientX-down.x)+Math.abs(event.clientY-down.y)>4)return;const r=renderer.domElement.getBoundingClientRect();pointer.set(((event.clientX-r.left)/r.width)*2-1,-((event.clientY-r.top)/r.height)*2+1);ray.setFromCamera(pointer,camera);
        const hit=ray.intersectObjects(root.children,true).find(h=>h.object.visible&&(h.object as Mesh).isMesh&&h.object.raycast!==undefined&&!holo.includes(h.object as Mesh));if(!hit){setActive(null);return;}
        for(const [key,meshes] of byPart)if(meshes.includes(hit.object as Mesh)){setActive(key);if(!compact)focusOn(key);return;}};
      renderer.domElement.addEventListener('pointerdown',press);renderer.domElement.addEventListener('pointerup',pick);
      const resize=()=>{const w=el.clientWidth,h=el.clientHeight;if(!w||!h)return;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();};
      const observer=new ResizeObserver(resize);observer.observe(el);
      let frame=0;const tick=()=>{frame=requestAnimationFrame(tick);
        if(tween){const p=Math.min(1,(performance.now()-tween.t)/700),e=1-Math.pow(1-p,3);camera.position.lerpVectors(tween.from,tween.to,e);controls.target.lerpVectors(tween.tFrom,tween.tTo,e);if(p>=1)tween=null;}
        holoMaterial.uniforms.strength.value=0.42+Math.sin(performance.now()/700)*0.08;
        controls.update();renderer.render(scene,camera);};tick();
      setState('ready');requestAnimationFrame(()=>renderer.domElement.classList.add('shown'));
      dispose=()=>{cancelAnimationFrame(frame);observer.disconnect();renderer.domElement.removeEventListener('pointerdown',press);renderer.domElement.removeEventListener('pointerup',pick);controls.dispose();renderer.dispose();holoMaterial.dispose();scene.traverse(o=>{const m=o as Mesh;if(!holo.includes(m)){m.geometry?.dispose();(m.material as import('three').Material|undefined)?.dispose?.();}});renderer.domElement.remove();};
    }catch(error){console.error('3D model failed',error);if(live)setState('error');}})();
    return()=>{live=false;dispose();api.current=null;};
  },[entry.id,visible]);
  useEffect(()=>{api.current?.highlight(active);},[active]);
  useEffect(()=>{api.current?.hologram(hologram);},[hologram]);
  useEffect(()=>{if(cut)api.current?.cut(cut);},[cut?.mode,cut?.t]);
  useEffect(()=>{if(zoomTo)api.current?.focus(zoomTo.id);},[zoomTo]);
  const shown=useRef<Set<string>>(new Set());
  useEffect(()=>{if(!api.current||!hidden)return;
    hidden.forEach(id=>{if(!shown.current.has(id))api.current?.visible(id,false);});
    shown.current.forEach(id=>{if(!hidden.has(id))api.current?.visible(id,true);});
    shown.current=new Set(hidden);},[hidden]);
  return <div className={'explorer-stage model'+(hologram?' hologram':'')+(compact?' compact':'')} ref={host}>
    {(state==='loading'||state==='idle')&&<p className="smiles-explorer-status explorer-overlay" role="status">Building the 3D model…</p>}
    {state==='error'&&<p className="notice error explorer-overlay" role="alert">This 3D model could not be loaded.</p>}
    {state==='nowebgl'&&<p className="notice explorer-overlay">The 3D view needs graphics acceleration (WebGL), which is turned off or unavailable on this computer.</p>}
    {state==='ready'&&!compact&&<p className="explorer-hint">Drag to rotate · scroll to zoom · right-drag to pan · click a part to zoom to it</p>}
    {state==='ready'&&compact&&props_tools(toolsTarget)}
  </div>;
}

function CutControl({cut,setCut}:{cut:Cut;setCut:(cut:Cut)=>void}){
  return <div className="cut-control" role="group" aria-label="Section cut">
    {(['off','ts','ls'] as const).map(mode=><button type="button" key={mode} className="cut-mode" aria-pressed={cut.mode===mode} onClick={()=>setCut({mode,t:0.5})} title={mode==='ts'?'Transverse section: cut across':mode==='ls'?'Longitudinal section: cut lengthwise':'Whole organ'}>{mode==='off'?'Whole':mode==='ts'?'T.S.':'L.S.'}</button>)}
    {cut.mode!=='off'&&<input type="range" min={0.05} max={0.95} step={0.01} value={cut.t} aria-label="Move the cut" onChange={e=>setCut({...cut,t:Number(e.target.value)})}/>}
  </div>;
}

/** Live viewer used inline in answers and inside the explorer dialog. */
/** Switches a diagram between its 3D model and its linked 2D section drawing, when it has one. */
export function DiagramViewer({id,focus,cut,compact=false,onExpand}:{id:string;focus?:string;cut?:'ts'|'ls'|'';compact?:boolean;onExpand?:()=>void}){
  const [current,setCurrent]=useState(id);
  useEffect(()=>setCurrent(id),[id]);
  const base=DIAGRAMS.find(d=>d.id===id),twin=base?.twin?DIAGRAMS.find(d=>d.id===base.twin):undefined;
  const switcher=twin&&base?<div className="dimension-switch" role="group" aria-label="View">
    {[base,twin].sort((a,b)=>a.kind==='model'?-1:b.kind==='model'?1:0).map(d=><button type="button" key={d.id} className="cut-mode" aria-pressed={current===d.id} onClick={()=>setCurrent(d.id)} title={d.title}>{d.kind==='model'?'3D':'2D'}</button>)}
  </div>:null;
  return <ViewerBody key={current} id={current} focus={current===id?focus:undefined} cut={current===id?cut:''} compact={compact} onExpand={onExpand} switcher={switcher}/>;
}

function ViewerBody({id,focus,cut:initialCut,compact=false,onExpand,switcher}:{id:string;focus?:string;cut?:'ts'|'ls'|'';compact?:boolean;onExpand?:()=>void;switcher?:React.ReactNode}){
  const [cut,setCut]=useState<Cut>({mode:initialCut||'off',t:0.5});
  const entry=useMemo(()=>DIAGRAMS.find(d=>d.id===id),[id]);
  const [parts,setParts]=useState<Part[]>([]),[active,setActive]=useState<string|null>(focus||null),[hidden,setHidden]=useState<Set<string>>(new Set());
  const [hologram,setHologram]=useState(true),[zoomTo,setZoomTo]=useState<{id:string;n:number}|null>(null);
  const [toolsTarget,setToolsTarget]=useState<HTMLDivElement|null>(null);
  if(!entry)return null;
  const select=(partId:string)=>{setActive(partId);setZoomTo(z=>({id:partId,n:(z?.n||0)+1}));};
  const toggle=(partId:string)=>setHidden(previous=>{const next=new Set(previous);next.has(partId)?next.delete(partId):next.add(partId);return next;});
  const props={entry,focus,compact,hologram,onParts:setParts,active,setActive,zoomTo,hidden,toolsTarget,cut};
  const cutControl=entry.sectionable?<CutControl cut={cut} setCut={setCut}/>:null;
  const viewer=entry.kind==='model'?<ModelViewer {...props}/>:<SectionViewer {...props}/>;
  const focusLabel=focus?parts.find(p=>p.id===focus)?.label:'';
  if(compact)return <div className="diagram-inline">
    {viewer}
    <div className="diagram-inline-bar">
      <div className="diagram-inline-tools" ref={setToolsTarget}/>
      {switcher}
      {cutControl}
      <span className="diagram-inline-status">{focusLabel&&<span className="diagram-focus-chip"><i className="fas fa-crosshairs" aria-hidden="true"/> {focusLabel}</span>}{active&&active!==focus&&<span className="diagram-focus-chip muted-chip">{parts.find(p=>p.id===active)?.label}</span>}</span>
      <button type="button" className="holo-toggle" aria-pressed={hologram} onClick={()=>setHologram(!hologram)}><i className="fas fa-magic" aria-hidden="true"/> Hologram</button>
      {onExpand&&<button type="button" className="holo-toggle expand" onClick={onExpand}><i className="fas fa-expand" aria-hidden="true"/> Full view</button>}
    </div>
  </div>;
  return <div className="explorer-layout">
    {viewer}
    <aside className="explorer-side">
      {(switcher||cutControl)&&<div className="explorer-cut">{switcher}{cutControl}</div>}
      <div className="explorer-side-tools"><button type="button" className="holo-toggle" aria-pressed={hologram} onClick={()=>setHologram(!hologram)}><i className="fas fa-magic" aria-hidden="true"/> Hologram</button></div>
      <Info part={parts.find(p=>p.id===active)}/>
      <PartList parts={parts} active={active} hidden={entry.kind==='model'?hidden:undefined} onHover={partId=>setActive(partId??(focus||null))} onSelect={select} onToggle={entry.kind==='model'?toggle:undefined}/>
    </aside>
  </div>;
}

export function DiagramExplorer({id,focus,cut,onClose}:{id:string;focus?:string;cut?:'ts'|'ls'|'';onClose:()=>void}){
  const entry=useMemo(()=>DIAGRAMS.find(d=>d.id===id),[id]);
  if(!entry)return null;
  return <Dialog title={entry.title} onClose={onClose} className="diagram-explorer">
    <DiagramViewer id={id} focus={focus} cut={cut}/>
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
    <div className="explorer-stage figure hologram" ref={stage} onWheel={e=>{const r=stage.current!.getBoundingClientRect();zoom(e.deltaY<0?1.15:1/1.15,e.clientX-r.left,e.clientY-r.top);}}
      onPointerDown={e=>{drag.current={x:e.clientX,y:e.clientY,vx:view.x,vy:view.y};}} onPointerMove={e=>{if(drag.current)setView(v=>({...v,x:drag.current!.vx+e.clientX-drag.current!.x,y:drag.current!.vy+e.clientY-drag.current!.y}));}} onPointerUp={()=>{drag.current=null;}} onPointerLeave={()=>{drag.current=null;}}>
      <img draggable={false} src={'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg)} alt={title} style={{transform:`translate(${view.x}px,${view.y}px) scale(${view.k})`}}/>
      <div className="explorer-tools"><button type="button" aria-label="Zoom in" onClick={()=>zoom(1.25)}><i className="fas fa-plus"/></button><button type="button" aria-label="Zoom out" onClick={()=>zoom(1/1.25)}><i className="fas fa-minus"/></button><button type="button" aria-label="Reset view" onClick={()=>setView({x:0,y:0,k:1})}><i className="fas fa-compress"/></button></div>
    </div>
  </Dialog>;
}

/* ---------- Browse every built-in diagram ---------- */
export function DiagramLibrary({onClose}:{onClose:()=>void}){
  const [open,setOpen]=useState<string|null>(null),[query,setQuery]=useState('');
  const shown=DIAGRAMS.filter(d=>!d.hidden&&(d.title+' '+d.keywords).toLowerCase().includes(query.toLowerCase()));
  const groups=[...new Set(shown.map(d=>d.group))];
  return <Dialog title="Diagram library" onClose={onClose} className="diagram-library">
    <input className="library-search" type="search" placeholder="Search diagrams (e.g. stem, kidney, mitochondria)" value={query} onChange={e=>setQuery(e.target.value)} aria-label="Search diagrams"/>
    {groups.map(group=><section key={group}><h3>{group}</h3><div className="library-grid">{shown.filter(d=>d.group===group).map(d=><button type="button" key={d.id} className="library-card" onClick={()=>setOpen(d.id)}>
      <span className="library-kind">{d.kind==='model'?'3D':d.section}</span><span>{d.title}</span></button>)}</div></section>)}
    {!shown.length&&<p className="muted">No diagram matches “{query}”.</p>}
    {open&&<DiagramExplorer id={open} onClose={()=>setOpen(null)}/>}
  </Dialog>;
}
