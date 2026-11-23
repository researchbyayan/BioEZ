import {spawn} from 'node:child_process';
import net from 'node:net';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {root} from './python-path.mjs';
import {electronBinary,electronVersion,legacy} from './electron-target.mjs';
if(legacy)console.log(`Using Electron ${electronVersion} (Intel Mac).`);
const require=createRequire(import.meta.url);
const vite=spawn(process.execPath,[fileURLToPath(new URL('../node_modules/vite/bin/vite.js',import.meta.url))],{cwd:root,stdio:'inherit'});
let desktop;
const stop=()=>{desktop?.kill();vite.kill();};
process.on('SIGINT',stop);process.on('SIGTERM',stop);
// Wait for Vite with a plain TCP check (Node 24's fetch can throw outside a try block here).
const listening=()=>new Promise(resolve=>{const socket=net.connect(5173,'127.0.0.1');socket.once('connect',()=>{socket.destroy();resolve(true);});socket.once('error',()=>resolve(false));});
for(let i=0;i<150&&!(await listening());i++)await new Promise(r=>setTimeout(r,100));
desktop=spawn(electronBinary,['.'],{cwd:root,stdio:'inherit',env:{...process.env,BIOEZ_DEV:'1'}});
desktop.on('exit',code=>{vite.kill();process.exitCode=code??1;});
