/* ZFLAG Complete Website Localization v1
 * Loads pretranslated, offline-ready language packs (no translation API in visitor browsers).
 * Translates content, paragraphs, dialogs, tooltips, dynamic library cards and presets.
 * Technical FastFlag identifiers, JSON data, code, numbers and input values stay intact.
 */
(()=>{
"use strict";
const LANGS=new Set(["en","es","fr","de","pt","ru","tr","zh","ja","ko"]);
const EXCLUDED="script,style,svg,pre,code,kbd,textarea,option[value],.flagname,.zflag-locale,.zflag-locale-item,.language-option,[data-notranslate],[translate='no'],[contenteditable]";
const TECH=/^(?:D?FFlag|D?FInt|D?FString|SFFlag|SInt|SString|FLog|DFLog)[a-zA-Z0-9_]+$|^[\d.,/\\+%\- ]+$/i;
const SPACES=/^(\s*)([\s\S]*?)(\s*)$/;
const DESCRIPTION=/^Name suggests “(.+?)” controls (.+?)\. This interpretation is inferred; its real purpose, supported values and effect have not been independently documented\.$/;
const TEMPLATE="Name suggests “ZZZFLAGNAMEZZZ” controls ZZZPURPOSEZZZ. This interpretation is inferred; its real purpose, supported values and effect have not been independently documented.";
const keys=new WeakMap(),attributes=new WeakMap();
let current="en",loading=0,pack={},ready=false,observer=null,pending=new Set(),raf=0;
try{let stored=localStorage.getItem("zflag-language");if(LANGS.has(stored))current=stored;}catch(e){}
const normalize=s=>String(s).replace(/\u00a0/g," ").replace(/\s+/g," ").trim();
function technical(s){
 if(!s||TECH.test(s))return true;
 if(/^(?:https?:\/\/|\.\/|\.\.\/|#|--|var\(|rgba?\(|\{|<)/.test(s))return true;
 return false;
}
function textTranslation(original){
 if(current==="en"||technical(original))return original;
 if(Object.prototype.hasOwnProperty.call(pack,original))return pack[original];
 const match=DESCRIPTION.exec(original);
 if(match){
   const format=pack[TEMPLATE];
   const scope=pack[match[2]]||match[2];
   if(format&&format.includes("ZZZFLAGNAMEZZZ")&&format.includes("ZZZPURPOSEZZZ"))
     return format.replaceAll("ZZZFLAGNAMEZZZ",match[1]).replaceAll("ZZZPURPOSEZZZ",scope);
 }
 // Safety: never invent translations for unknown technical keys. The packs
 // contain all source copy and dynamic string templates from the website.
 return original;
}
function localizeText(node){
 const parent=node.parentElement;
 if(!parent||parent.closest(EXCLUDED))return;
 let original=keys.get(node);
 if(original===undefined){
   const raw=node.nodeValue;
   original=normalize(raw);
   if(!original||!/[A-Za-z]/.test(original)||technical(original))return;
   keys.set(node,{source:original,prefix:(raw.match(/^\s*/)||[""])[0],suffix:(raw.match(/\s*$/)||[""])[0]});
 }
 const base=keys.get(node);
 if(!base||!base.source)return;
 const translated=textTranslation(base.source);
 const newText=base.prefix+translated+base.suffix;
 if(node.nodeValue!==newText)node.nodeValue=newText;
}
function localizeAttributes(element){
 if(!element||element.closest(EXCLUDED))return;
 let history=attributes.get(element);
 if(!history){history={};attributes.set(element,history);}
 for(const attr of ["placeholder","title","aria-label","alt"]){
   const actual=element.getAttribute(attr);
   if(!actual)continue;
   if(!(attr in history))history[attr]=actual;
   const original=normalize(history[attr]);
   if(!original||technical(original))continue;
   const translated=textTranslation(original);
   if(actual!==translated)element.setAttribute(attr,translated);
 }
}
function translateSubtree(root){
 if(!root)return;
 if(root.nodeType===Node.TEXT_NODE){localizeText(root);return;}
 if(root.nodeType!==Node.ELEMENT_NODE)return;
 if(root.matches(EXCLUDED))return;
 localizeAttributes(root);
 const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT|NodeFilter.SHOW_ELEMENT);
 let node;
 while((node=walker.nextNode())){
   if(node.nodeType===Node.TEXT_NODE)localizeText(node);
   else if(node.nodeType===Node.ELEMENT_NODE)localizeAttributes(node);
 }
}
function flush(){
 raf=0;
 const roots=[...pending];pending.clear();
 if(roots.some(node=>node===document.body)){translateSubtree(document.body);return;}
 for(const root of roots)if(root.isConnected)translateSubtree(root);
}
function schedule(root){
 if(!root)return;
 pending.add(root);
 if(!raf)raf=requestAnimationFrame(flush);
}
function startObserver(){
 if(observer)return;
 observer=new MutationObserver(records=>{
   if(!ready)return;
   for(const m of records){
     if(m.type==="childList")for(const node of m.addedNodes)schedule(node);
     // Text nodes that have been replaced by the site's scripts create childList;
     // translations performed by this component never trigger childList.
   }
 });
 observer.observe(document.body,{subtree:true,childList:true});
}
function reportCoverage(){
 let total=0,covered=0;
 const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
 let node;
 while((node=walker.nextNode())){
  const el=node.parentElement;if(!el||el.closest(EXCLUDED))continue;
  const original=keys.get(node)?.source||normalize(node.nodeValue);
  if(!original||!/[A-Za-z]/.test(original)||technical(original))continue;
  total++;
  if(Object.prototype.hasOwnProperty.call(pack,original)||DESCRIPTION.test(original)||current==="en")covered++;
 }
 return {language:current,covered,total,percentage:total?Math.round(100*covered/total):100};
}
async function setLanguage(next){
 if(!LANGS.has(next))next="en";
 const ticket=++loading;
 current=next;
 document.documentElement.lang=next;
 try{localStorage.setItem("zflag-language",next)}catch(e){}
 if(next==="en"){pack={};ready=true;schedule(document.body);startObserver();window.dispatchEvent(new CustomEvent("zflag:translated",{detail:{lang:next}}));return;}
 try{
   const response=await fetch("../".repeat(location.pathname.split("/").filter(Boolean).length)+"i18n/"+next+".json?v=1",{cache:"force-cache"});
   if(!response.ok)throw Error("Missing translation pack: "+response.status);
   const translations=await response.json();
   if(ticket!==loading)return;
   pack=translations;ready=true;
   schedule(document.body);startObserver();
   window.dispatchEvent(new CustomEvent("zflag:translated",{detail:{lang:next}}));
 }catch(error){
   if(ticket!==loading)return;
   console.error("[ZFLAG] Site translation pack failed:",error);
   pack={};ready=true;schedule(document.body);
   document.documentElement.dataset.translationError="true";
 }
}
function onLanguage(event){
 const lang=event.detail?.lang;
 if(LANGS.has(lang)&&lang!==current)setLanguage(lang);
}
window.addEventListener("zflag:languagechange",onLanguage);
window.ZFLAGFullLanguage=Object.freeze({
 set:setLanguage,
 get:()=>current,
 coverage:reportCoverage,
 languagePacks:true
});
setLanguage(current);
})();
