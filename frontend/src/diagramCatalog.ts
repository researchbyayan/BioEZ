import catalog from '../../shared/diagrams.json';

export interface Part {id:string;label:string;info?:string;colour?:string}
export interface DiagramEntry {id:string;kind:'model'|'section';group:string;title:string;section?:string;keywords:string;credit:string}

const ORIGINAL='Original BioEZ illustration (MIT).';
const ANATOMY='BodyParts3D, © The Database Center for Life Science, CC BY-SA 2.1 Japan. Simplified for BioEZ.';
export const DIAGRAMS:DiagramEntry[]=(catalog as Omit<DiagramEntry,'credit'>[]).map(d=>({...d,credit:d.id.startsWith('human-')?ANATOMY:ORIGINAL}));

// Assets are bundled into lazily loaded chunks: the packaged app loads from file://, where fetch is unavailable.
const sections=import.meta.glob<string>('./diagrams/sections/*.svg',{query:'?raw',import:'default'});
const models=import.meta.glob<string>('./diagrams/models/*.glb',{query:'?inline',import:'default'});
const modelParts=import.meta.glob<{parts:Part[]}>('./diagrams/models/*.json',{import:'default'});

export async function loadSection(id:string){
  const load=sections[`./diagrams/sections/${id}.svg`];
  if(!load)throw new Error('Unknown diagram.');
  return load();
}

export async function loadModel(id:string){
  const [url,meta]=await Promise.all([models[`./diagrams/models/${id}.glb`]?.(),modelParts[`./diagrams/models/${id}.json`]?.()]);
  if(!url||!meta)throw new Error('Unknown model.');
  const binary=atob(url.slice(url.indexOf(',')+1)),bytes=new Uint8Array(binary.length);
  for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);
  return {glb:bytes.buffer,parts:meta.parts};
}
