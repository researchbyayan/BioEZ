// Intel Macs get Electron 39: from Electron 40 on, Chromium's software WebGL fallback crashes on
// Intel Mac GPUs that Chromium can't drive (for example an OpenCore-patched MacBook Air), so 3D
// models would not show. Everything else uses the current Electron (see package.json).
// Override with BIOEZ_ELECTRON=current or BIOEZ_ELECTRON=legacy.
import {createRequire} from 'node:module';
import path from 'node:path';
const require=createRequire(import.meta.url);
const choice=process.env.BIOEZ_ELECTRON;
export const legacy=choice?choice==='legacy':process.platform==='darwin'&&process.arch==='x64';
const packageName=legacy?'electron39':'electron';
export const electronBinary=require(packageName);
export const electronVersion=require(`${packageName}/package.json`).version;
export const electronDist=path.join(path.dirname(require.resolve(`${packageName}/package.json`)),'dist');
