import {useEffect,useState} from 'react';
export interface UpdateState {state:'available'|'downloading'|'ready'|'opened'|'error';version?:string;percent?:number}
export function UpdateCard(){
  const [update,setUpdate]=useState<UpdateState|null>(null);
  useEffect(()=>window.bioez.onUpdate?.(setUpdate),[]);
  if(!update)return null;
  const close=<button className="update-later" onClick={()=>setUpdate(null)}>{update.state==='available'?'Later':'Close'}</button>;
  return <div className="update-card" role="status">
    <b>{update.state==='ready'?'Update ready':update.state==='opened'?'Update downloaded':`BioEZ ${update.version} is available`}</b>
    {update.state==='available'&&<><p>Download it in the background while you keep working.</p><div>{close}<button className="update-go" onClick={()=>void window.bioez.downloadUpdate?.()}>Update</button></div></>}
    {update.state==='downloading'&&<><p>Downloading… {update.percent??0}%</p><progress max={100} value={update.percent??0}/></>}
    {update.state==='ready'&&<><p>Restart BioEZ to finish updating to {update.version}. Your chats stay as they are.</p><div>{close}<button className="update-go" onClick={()=>void window.bioez.installUpdate?.()}>Restart to update</button></div></>}
    {update.state==='opened'&&<><p>Drag BioEZ into Applications to replace this version, then reopen it.</p><div>{close}</div></>}
    {update.state==='error'&&<><p>The update could not be downloaded. BioEZ will offer it again next week.</p><div>{close}</div></>}
  </div>;
}
