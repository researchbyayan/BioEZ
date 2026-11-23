// electron-builder with the Electron chosen for this machine (see electron-target.mjs).
import {spawnSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {legacy,electronVersion,electronDist} from './electron-target.mjs';
const require=createRequire(import.meta.url);
const cli=require.resolve('electron-builder/cli.js');
const args=[cli,...process.argv.slice(2),...(legacy?[`-c.electronVersion=${electronVersion}`,`-c.electronDist=${electronDist}`]:[])];
if(legacy)console.log(`Packaging with Electron ${electronVersion} for this Intel Mac.`);
process.exit(spawnSync(process.execPath,args,{stdio:'inherit'}).status??1);
