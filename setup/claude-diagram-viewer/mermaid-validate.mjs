#!/usr/bin/env node
import{readFile}from"node:fs/promises";import{createRequire}from"node:module";import{homedir}from"node:os";import{join}from"node:path";
const require=createRequire(import.meta.url);
const HOME=homedir(),MOD_ROOT=join(HOME,".claude","node_modules");
const{JSDOM}=require(join(MOD_ROOT,"jsdom"));
const dom=new JSDOM("<!DOCTYPE html><html><body></body></html>",{url:"http://localhost/",pretendToBeVisual:true});
globalThis.window=dom.window;globalThis.document=dom.window.document;
Object.defineProperty(globalThis,"navigator",{value:dom.window.navigator,configurable:true});
globalThis.Element=dom.window.Element;globalThis.HTMLElement=dom.window.HTMLElement;
globalThis.SVGElement=dom.window.SVGElement;globalThis.Node=dom.window.Node;
globalThis.requestAnimationFrame=cb=>setTimeout(cb,0);globalThis.getComputedStyle=dom.window.getComputedStyle;
const mermaidPath=join(MOD_ROOT,"mermaid","dist","mermaid.esm.mjs");
const{default:mermaid}=await import(mermaidPath);
const arg=process.argv[2];if(!arg){console.error("usage: mermaid-validate.mjs <file.mmd|->");process.exit(2)}
let src;if(arg==="-"){const chunks=[];for await(const c of process.stdin)chunks.push(c);src=Buffer.concat(chunks).toString("utf8")}else{src=await readFile(arg,"utf8")}
try{mermaid.initialize({startOnLoad:false,securityLevel:"loose"});const{diagramType}=await mermaid.parse(src);console.log(`OK: ${diagramType}`);process.exit(0)}catch(e){console.error(`FAIL: ${e.message||e}`);process.exit(1)}
