import {spawnSync} from 'node:child_process';
import {python,root,runtimePython} from './python-path.mjs';
const args=['-m','PyInstaller','--noconfirm','--onedir','--name','bioez-backend','--distpath','backend-dist','--workpath','build/python','--specpath','build','--paths','backend','--paths','backend/vendor','--collect-data','pint','--collect-data','rdkit','--collect-binaries','rdkit','--hidden-import','seq_encode.smiles','--hidden-import','uvicorn.logging','--hidden-import','uvicorn.loops.auto','--hidden-import','uvicorn.protocols.http.auto','--hidden-import','uvicorn.protocols.http.h11_impl','--hidden-import','uvicorn.lifespan.on'];
if(process.env.BIOEZ_CLEAN_BUILD==='1')args.push('--clean');
for(const dependency of ['fastapi','uvicorn','httpx','pydantic','rdkit','numpy','tqdm','pint','molmass','flexcache','flexparser','platformdirs']) args.push('--recursive-copy-metadata',dependency);
// The question map is read at run time, so it ships beside the bioez package.
args.push('--add-data',root+'/backend/bioez/question_map.json:bioez');
args.push('--add-data',root+'/backend/bioez/data/c13_shifts.json.gz:bioez/data');
args.push('--add-data',root+'/licenses/nmrshiftdb2-database-license.txt:bioez/data');
args.push('--add-data',root+'/backend/bioez/data/NOTICE.txt:bioez/data');
args.push('backend/run.py');
for(const module of ['pytest','tkinter','IPython','matplotlib'])args.push('--exclude-module',module);
const result=spawnSync(runtimePython,args,{cwd:root,stdio:'inherit',env:{...process.env,PYINSTALLER_CONFIG_DIR:root+'/build/pyinstaller-cache'}});
process.exit(result.status??1);
