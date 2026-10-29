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

const CATEGORIES=["All Flags","FPS & Scheduling","Rendering & Graphics","Textures & Lighting","Networking & Ping","Caching & Memory","Physics & Movement","UI & Accessibility","Audio & Voice","Security & Telemetry","Assets & Loading","Other & Experimental"];
const CATEGORY_IDS=["catAll","catFps","catGraphics","catTextures","catNetwork","catMemory","catPhysics","catUi","catAudio","catSecurity","catAssets","catOther"];
const TYPES=["boolean","integer","number","string","unverified"];
const TYPE_LOCALES={
 es:["booleano","entero","número","texto","sin verificar"],
 fr:["booléen","entier","nombre","texte","non vérifié"],
 de:["Boolesch","Ganzzahl","Zahl","Text","ungeprüft"],
 pt:["booleano","inteiro","número","texto","não verificado"],
 ru:["логический","целое число","число","текст","не проверено"],
 tr:["mantıksal","tamsayı","sayı","metin","doğrulanmamış"],
 zh:["布尔值","整数","数字","文本","未经验证"],
 ja:["真偽値","整数","数値","文字列","未確認"],
 ko:["불리언","정수","숫자","문자열","미확인"]
};

const PREVIEW_LABELS=["Frame scheduler target","Texture quality override","Texture quality level","Graphics renderer preference","Rendering quality setting","Fullscreen handling"];
const PREVIEW_TRANSLATIONS={
 es:["Objetivo de frecuencia de fotogramas","Calidad de texturas forzada","Nivel de calidad de texturas","Preferencia del motor gráfico","Nivel de calidad de renderizado","Gestión de pantalla completa"],
 fr:["Fréquence cible des images","Qualité de texture forcée","Niveau de qualité des textures","Préférence du moteur graphique","Niveau de rendu","Gestion du plein écran"],
 de:["Ziel-Bildrate des Schedulers","Texturqualität überschreiben","Texturqualitätsstufe","Grafik-Renderer-Präferenz","Rendering-Qualitätsstufe","Vollbildverwaltung"],
 pt:["Meta de taxa de quadros","Substituir qualidade das texturas","Nível de qualidade das texturas","Preferência do renderizador gráfico","Nível de qualidade de renderização","Gerenciamento de tela cheia"],
 ru:["Целевая частота кадров","Принудительное качество текстур","Уровень качества текстур","Предпочтение графического рендерера","Уровень качества рендеринга","Полноэкранный режим"],
 tr:["Hedef kare hızı","Doku kalitesini geçersiz kılma","Doku kalite seviyesi","Grafik işleyici tercihi","İşleme kalite düzeyi","Tam ekran yönetimi"],
 zh:["目标帧率","覆盖纹理质量","纹理质量等级","图形渲染器偏好","渲染质量等级","全屏模式管理"],
 ja:["目標フレームレート","テクスチャ品質の上書き","テクスチャ品質レベル","グラフィックス描画方式","描画品質レベル","全画面表示の管理"],
 ko:["목표 프레임 속도","텍스처 품질 재정의","텍스처 품질 수준","그래픽 렌더러 선택","렌더링 품질 수준","전체 화면 관리"]
};
const DYNAMIC_TERMS={
 es:["Página","de","Añadir","flags","REFERENCIA:"],fr:["Page","sur","Ajouter","flags","RÉFÉRENCE :"],
 de:["Seite","von","Hinzufügen","Flags","REFERENZ:"],pt:["Página","de","Adicionar","flags","REFERÊNCIA:"],
 ru:["Страница","из","Добавить","флагов","ИСТОЧНИК:"],tr:["Sayfa","/","Ekle","flag","KAYNAK:"],
 zh:["第","共","添加","个旗标","参考："],ja:["ページ","全","追加","フラグ","参照："],ko:["페이지","전체","추가","플래그","출처:"]
};

const keys=new WeakMap(),attributes=new WeakMap();
let current="en",loading=0,pack={},ready=false,observer=null,pending=new Set(),raf=0;
const englishPageTitle=document.title;
try{let stored=localStorage.getItem("zflag-language");if(LANGS.has(stored))current=stored;}catch(e){}
const normalize=s=>String(s).replace(/\u00a0/g," ").replace(/\s+/g," ").trim();
function technical(s){
 if(!s||TECH.test(s)||["ZFLAG","Roblox","JSON","FPS"].includes(s))return true;
 if(/^(?:https?:\/\/|\.\/|\.\.\/|#|--|var\(|rgba?\(|\{|<)/.test(s))return true;
 return false;
}
function textTranslation(original){
 if(current==="en"||technical(original))return original;
 if(Object.prototype.hasOwnProperty.call(pack,original))return pack[original];

 const previewIndex=PREVIEW_LABELS.indexOf(original);
 if(previewIndex>=0)return PREVIEW_TRANSLATIONS[current]?.[previewIndex]||original;
 if(original==="Integer"||original==="Boolean"){
   const index=original==="Integer"?1:0;
   const type=TYPE_LOCALES[current]?.[index]||original;
   return type.charAt(0).toUpperCase()+type.slice(1);
 }
 const terms=DYNAMIC_TERMS[current];
 if(terms){
   const pager=original.match(/^Page (\d+) of (\d+)$/);
   if(pager){
     if(current==="zh")return "第 "+pager[1]+" 页，共 "+pager[2]+" 页";
     if(current==="ja")return pager[1]+" / "+pager[2]+" ページ";
     if(current==="ko")return pager[1]+" / "+pager[2]+" 페이지";
     return terms[0]+" "+pager[1]+" "+terms[1]+" "+pager[2];
   }
   const count=original.match(/^\+ Add (\d+) flags$/);
   if(count)return "+ "+terms[2]+" "+count[1]+" "+terms[3];
   const counter=original.match(/^(\d+) \/ (\d+) flags$/);
   if(counter)return counter[1]+" / "+counter[2]+" "+terms[3];
   if(original.startsWith("REFERENCE: ")){
     const ref=original.slice(11);
     return (pack["REFERENCE:"]||terms[4])+" "+(pack[ref]||ref);
   }
 }


 const cat=CATEGORIES.indexOf(original);
 if(cat>=0)return window.ZFLAGChromeDictionary?.[current]?.[CATEGORY_IDS[cat]]||original;
 const typ=TYPES.indexOf(original);
 if(typ>=0)return TYPE_LOCALES[current]?.[typ]||original;
 const label=original.match(/^ACTUAL JSON VALUE \((boolean|integer|number|string|unverified)\)$/);
 if(label)return (pack["ACTUAL JSON VALUE"]||"ACTUAL JSON VALUE")+" ("+textTranslation(label[1])+")";
 if(original.startsWith("SOURCE: "))return (pack["SOURCE:"]||"SOURCE:")+" "+original.slice(8);
 const matches=original.match(/^(\d[\d,]*) matching flags$/);
 if(matches)return matches[1]+" "+(pack["matching flags"]||"flags");

 const match=DESCRIPTION.exec(original);
 if(match){
   const format=pack[TEMPLATE];
   const scope=pack[match[2]]||match[2];
   if(format&&format.includes("ZZZFLAGNAMEZZZ")&&format.includes("ZZZPURPOSEZZZ"))
     return format.replaceAll("ZZZFLAGNAMEZZZ",match[1]).replaceAll("ZZZPURPOSEZZZ",scope);
 }
 // Preserve technical identifiers while translating surrounding dynamically generated labels.
 const dyn=original.match(/^(Added|Value for|Actual value for|Removed) ((?:D?FFlag|D?FInt|D?FString)[A-Za-z0-9_]+)(.*)$/);
 if(dyn){return (pack[dyn[1]]||dyn[1])+" "+dyn[2]+(dyn[3]?(pack[dyn[3].trim()]||dyn[3]):"");}
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
 if(!ready)return;
 if(roots.some(node=>node===document.body))translateSubtree(document.body);
 else for(const root of roots)if(root.isConnected)translateSubtree(root);
 document.title=current==="en"?englishPageTitle:(pack[englishPageTitle]||englishPageTitle);
 document.documentElement.dataset.translatedLanguage=current;
 window.dispatchEvent(new CustomEvent("zflag:translationready",{detail:{lang:current,coverage:reportCoverage()}}));
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
 let total=0,covered=0;const uncovered=[];
 const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
 let node;
 while((node=walker.nextNode())){
  const el=node.parentElement;if(!el||el.closest(EXCLUDED))continue;
  const original=keys.get(node)?.source||normalize(node.nodeValue);
  if(!original||!/[A-Za-z]/.test(original)||technical(original))continue;
  total++;
  if(Object.prototype.hasOwnProperty.call(pack,original)||DESCRIPTION.test(original)||textTranslation(original)!==original||current==="en")covered++;
  else if(uncovered.length<35&&!uncovered.includes(original))uncovered.push(original);
 }
 return {language:current,covered,total,percentage:total?Math.round(100*covered/total):100,uncovered};
}
async function setLanguage(next){
 if(!LANGS.has(next))next="en";
 if(next===current && (ready || loading>0))return;
 const ticket=++loading;
 ready=false;
 delete document.documentElement.dataset.translatedLanguage;
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
 translate:textTranslation,
 languagePacks:true
});
setLanguage(current);
})();
