const { chromium } = require('playwright');
const base='https://zflag.onrender.com';
const results=[];
function check(label, ok, data='') {
  results.push({label,ok:!!ok,data});
  console.log((ok?'PASS ':'FAIL ')+label+(data?' '+JSON.stringify(data).slice(0,550):''));
}
async function safe(fn){try{return await fn()}catch(e){return {error:String(e)}}}
(async()=>{
  const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
  const context=await browser.newContext({viewport:{width:1365,height:860},reducedMotion:'no-preference'});
  context.setDefaultTimeout(8500);
  for(const route of ['/', '/docs/', '/library/', '/smooth-scroll.js','/zflag-logo.png','/build-status.txt']) {
    const resp=await context.request.get(base+route+'?audit=20261028', {timeout:25000});
    check('HTTP '+route,resp.status()===200,{status:resp.status(),type:resp.headers()['content-type'],bytes:(await resp.body()).length});
    if(route==='/build-status.txt'){const marker=await resp.text();console.log('LIVE BUILD MARKER '+marker.slice(0,200));check('Live build status cites v2.0.61',marker.includes('Latest official Windows installer: v2.0.61'),marker.slice(0,120));}
  }
  const page=await context.newPage();
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  let resp=await page.goto(base+'/?audit=20261028', {waitUntil:'domcontentloaded',timeout:30000});
  await page.waitForTimeout(500);
  let home=await page.evaluate(()=>({
    build:document.querySelector('meta[name="zflag-site-build"]')?.content,
    theme:document.documentElement.dataset.theme,
    rootBg:getComputedStyle(document.body).backgroundColor,
    logo:getComputedStyle(document.querySelector('.zmark')).backgroundImage,
    favicon:document.querySelector('link[rel="icon"]')?.getAttribute('href'),
    flagPicker:document.querySelectorAll('[data-accent]').length,
    studioPicker:document.querySelectorAll('[data-z2-color]').length,
    compactPicker:document.querySelectorAll('[data-mini-color]').length,
    pickerDefault:document.querySelector('[data-accent].active')?.dataset.accent,
    accent: getComputedStyle(document.documentElement).getPropertyValue('--app-accent').trim(),
    jsLoaded:performance.getEntriesByType('resource').some(x=>x.name.includes('smooth-scroll.js'))
  }));
  check('Homepage black',home.rootBg==='rgb(0, 0, 0)',home);
  check('Latest homepage deployed',home.build==='2026-10-28-locale-preview-v1',home.build);
  const homepageDownload=await page.locator('a[href*="/releases/download/v2.0.61/ZFLAG_Setup.exe"]').count();
  check('Homepage v2.0.61 downloads',homepageDownload>=1,{found:homepageDownload});
  check('Homepage original Z',home.logo.includes('zflag-logo.png'),home.logo);
  check('White default chosen',home.pickerDefault==='#ffffff' && home.accent==='#ffffff',{pickerDefault:home.pickerDefault,accent:home.accent});
  check('Shared scroll JS loaded',home.jsLoaded,home.jsLoaded);
  const websiteColorsBefore=await page.evaluate(()=>({
    button:getComputedStyle(document.querySelector('.hero-actions .btn.primary')).background,
    title:getComputedStyle(document.querySelector('.site-library-copy h2 span')).color,
    body:getComputedStyle(document.body).backgroundColor
  }));
  await page.locator('[data-accent="#4f8cff"]').first().click({timeout:5000});
  let changed=await page.evaluate(()=>({
    accent:getComputedStyle(document.documentElement).getPropertyValue('--app-accent').trim(),
    selectedMain:document.querySelector('[data-accent].active')?.dataset.accent,
    selectedFull:document.querySelector('[data-z2-color].is-selected')?.dataset.z2Color,
    selectedMini:document.querySelector('[data-mini-color].selected')?.dataset.miniColor,
    status:document.querySelector('#accentStatus')?.textContent,
    stageAccent:getComputedStyle(document.querySelector('.z2-window')).getPropertyValue('--z2accent').trim(),
  }));
  check('Click Blue updates only preview pickers',changed.accent==='#ffffff'&&changed.stageAccent==='#4f8cff'&&changed.selectedMain==='#4f8cff'&&changed.selectedFull==='#4f8cff'&&changed.selectedMini==='#4f8cff',changed);
  const websiteColorsAfter=await page.evaluate(()=>({
    button:getComputedStyle(document.querySelector('.hero-actions .btn.primary')).background,
    title:getComputedStyle(document.querySelector('.site-library-copy h2 span')).color,
    body:getComputedStyle(document.body).backgroundColor,
    preview:getComputedStyle(document.querySelector('.z2-window')).getPropertyValue('--app-accent').trim(),
    root:getComputedStyle(document.documentElement).getPropertyValue('--app-accent').trim()
  }));
  check('Accent stays INSIDE previews only',
    websiteColorsAfter.button===websiteColorsBefore.button &&
    websiteColorsAfter.title===websiteColorsBefore.title &&
    websiteColorsAfter.body===websiteColorsBefore.body &&
    websiteColorsAfter.root==='#ffffff'&&websiteColorsAfter.preview==='#4f8cff',
    {before:websiteColorsBefore,after:websiteColorsAfter});
  await page.reload({waitUntil:'domcontentloaded'});
  await page.waitForTimeout(350);
  let persisted=await page.evaluate(()=>document.querySelector('[data-accent].active')?.dataset.accent);
  check('Picker persists after reload',persisted==='#4f8cff',persisted);
  check('Smooth scroll V2 loaded',await page.evaluate(()=>window.__zflagScrollV2?.version==='4.0'));
  await page.evaluate(()=>window.scrollTo({top:800,behavior:"instant"}));
  await page.waitForTimeout(100);
  await page.evaluate(()=>{
    window.__zflagScrollSamples=[];
    const t0=performance.now();
    const sample=(t)=>{
      window.__zflagScrollSamples.push({t:Math.round(t-t0),y:Math.round(window.scrollY)});
      if(t-t0<800)requestAnimationFrame(sample);
    };
    requestAnimationFrame(sample);
  });
  await page.mouse.move(22,390);
  await page.mouse.wheel(0,450);
  await page.waitForTimeout(900);
  const wheel=await page.evaluate(()=>{
    const samples=window.__zflagScrollSamples||[];
    const first=samples[0]?.y??0,final=samples[samples.length-1]?.y??0;
    const changed=[...new Set(samples.map(x=>x.y))];
    const moves=samples.filter(x=>x.t<500 && x.y>first+1);
    return {start:first,finish:final,distinctPositions:changed.length,
      firstFrame:moves[0]||null,intermediate:samples.find(x=>x.t>90&&x.t<160)||null,
      durationMs:samples[samples.length-1]?.t,
      sampleCount:samples.length,active:window.__zflagScrollV2?.isAnimating()};
  });
  check('Mouse wheel actually eases over many frames',
    wheel.finish>wheel.start+300&&wheel.distinctPositions>=8&&
    wheel.intermediate.y>wheel.start&&wheel.intermediate.y<wheel.finish-25&&!wheel.active,wheel);
  // Precision trackpad values must NOT be bypassed as they were in V1.
  await page.evaluate(()=>window.scrollTo({top:800,behavior:"instant"}));
  await page.waitForTimeout(70);
  await page.evaluate(()=>{
    window.__zflagPrecisionSamples=[];
    const start=performance.now();
    const next=(t)=>{window.__zflagPrecisionSamples.push({t:Math.round(t-start),y:Math.round(scrollY)});if(t-start<500)requestAnimationFrame(next)};
    requestAnimationFrame(next);
  });
  await page.mouse.wheel(0,22);
  await page.waitForTimeout(600);
  const precise=await page.evaluate(()=>{
    const samples=window.__zflagPrecisionSamples||[];
    return {start:samples[0]?.y,finish:samples[samples.length-1]?.y,
      distinct:[...new Set(samples.map(x=>x.y))].length};
  });
  check('Small precision trackpad wheel event is smoothed',precise.finish>precise.start+12&&precise.distinct>=4,precise);
  await page.locator('a[href="#features"]').first().click({timeout:7000});
  await page.waitForTimeout(900);
  let featurePos=await page.evaluate(()=>({hash:location.hash,y:window.scrollY,header:document.querySelector('#features')?.getBoundingClientRect().top}));
  check('Homepage anchor scroll',featurePos.hash==='#features' && Math.abs(featurePos.header)<180,featurePos);
  // Real interaction: language picker, persistent choice across pages, and switching again.
  await page.locator('#languageTop').click();
  const chooseSpanish=page.locator('.language-option[data-lang="es"]');
  check('Homepage language selector opens',await chooseSpanish.isVisible());
  await chooseSpanish.click();
  const spanish=await page.evaluate(()=>({
    lang:document.documentElement.lang,
    nav:document.querySelector('.navlinks a[href="./library/"]')?.textContent.trim(),
    hero:document.querySelector('[data-i18n="hero.body"]')?.textContent.trim(),
    saved:localStorage.getItem('zflag-language')
  }));
  check('Homepage Spanish selection actually translates',spanish.lang==='es'&&spanish.saved==='es'&&spanish.nav.includes('Biblioteca')&&spanish.hero.startsWith('ZFLAG'),spanish);
  check('No homepage JS exceptions',errors.length===0,errors.slice(0,8));
  await page.screenshot({path:'audit-home.png',fullPage:false});
  const docs=await context.newPage();
  let docErrors=[];docs.on('pageerror',e=>docErrors.push(e.message));
  await docs.goto(base+'/docs/?audit=20261028',{waitUntil:'domcontentloaded'});
  const docInfo=await docs.evaluate(()=>({
    icon:document.querySelector('link[rel=icon]')?.getAttribute('href'),
    logo:getComputedStyle(document.querySelector('.logo')).backgroundImage,
    bg:getComputedStyle(document.body).backgroundColor,
    docSections:document.querySelectorAll('.doc-section').length,
    scrollBehavior:getComputedStyle(document.documentElement).scrollBehavior
  }));
  check('Docs Z logo',docInfo.icon?.includes('zflag-logo.png')&&docInfo.logo.includes('zflag-logo.png'),docInfo);
  check('Docs have smooth wheel v2',await docs.evaluate(()=>window.__zflagScrollV2?.version==='4.0'));
  check('Docs v2.0.61 download',await docs.locator('a[href*="/releases/download/v2.0.61/ZFLAG_Setup.exe"]').count()>=1);
  check('Docs black and guides',docInfo.bg==='rgb(0, 0, 0)' && docInfo.docSections===15,docInfo);
  const spanishDocs=await docs.evaluate(()=>({
    lang:document.documentElement.lang,nav:document.querySelector('.toplinks a[href="./"]')?.textContent.trim(),
    heading:document.querySelector('#overview>h2')?.textContent.trim(),hasPicker:!!document.querySelector('.zflag-locale-toggle')
  }));
  check('Docs inherit Spanish and translate guide navigation',spanishDocs.lang==='es'&&spanishDocs.nav==='Documentación'&&spanishDocs.heading==='Introducción'&&spanishDocs.hasPicker,spanishDocs);
  await docs.locator('.zflag-locale-toggle').click();
  await docs.locator('.zflag-locale-item[data-locale="zh"]').click();
  check('Docs selector changes language to Chinese',await docs.evaluate(()=>document.documentElement.lang==='zh'&&document.querySelector('.toplinks a[href="./"]')?.textContent.trim()==='文档'));
  await docs.locator('a.side-link[href="#installation"]').first().click();
  await docs.waitForTimeout(700);
  check('Docs navigation scroll',await docs.evaluate(()=>location.hash==='#installation'));
  check('No docs exceptions',docErrors.length===0,docErrors);
  await docs.screenshot({path:'audit-docs.png',fullPage:false});
  const lib=await context.newPage();
  let libErrors=[];lib.on('pageerror',e=>libErrors.push(e.message));
  await lib.goto(base+'/library/?audit=20261028',{waitUntil:'domcontentloaded'});
  await lib.waitForFunction(()=>document.querySelector('#resultsCount')?.textContent?.includes('matching flags'),{timeout:30000}).catch(()=>{});
  let libInfo=await lib.evaluate(()=>({
    count:document.querySelector('#countFlags')?.textContent,
    results:document.querySelector('#resultsCount')?.textContent,
    cards:document.querySelectorAll('#flagsGrid .card').length,
    smooth:getComputedStyle(document.documentElement).scrollBehavior,
    script:performance.getEntriesByType('resource').some(x=>x.name.includes('smooth-scroll.js'))
  }));
  check('Library catalog loads',/\d/.test(libInfo.count)&&libInfo.cards>=10,libInfo);
  const chineseLibrary=await lib.evaluate(()=>({
    lang:document.documentElement.lang,nav:document.querySelector('header nav a[href="./"]')?.textContent.trim(),
    title:document.querySelector('.container>h1')?.textContent.trim(),
    picker:!!document.querySelector('.zflag-locale-toggle')
  }));
  check('Library retains Chinese across navigation',chineseLibrary.lang==='zh'&&chineseLibrary.nav==='旗标库'&&chineseLibrary.title.startsWith('所有旗标')&&chineseLibrary.picker,chineseLibrary);
  await lib.locator('.zflag-locale-toggle').click();
  await lib.locator('.zflag-locale-item[data-locale="de"]').click();
  const germanLibrary=await lib.evaluate(()=>({lang:document.documentElement.lang,
    tab:document.querySelector('[data-tab="flags"]')?.textContent.trim(),
    search:document.querySelector('#search')?.placeholder}));
  check('Library selector changes UI without changing flag names',germanLibrary.lang==='de'&&germanLibrary.tab==='Einzelne Flags'&&germanLibrary.search.startsWith('Flags,'),germanLibrary);
  check('Library has smooth wheel v2',await lib.evaluate(()=>window.__zflagScrollV2?.version==='4.0'));
  await lib.locator('#search').fill('_note');
  await lib.waitForTimeout(250);
  let noteCards=await lib.locator('#flagsGrid .card').count();
  let noteSamples=await lib.locator('#flagsGrid .flagname').allTextContents();
  check('NO false flags from _note metadata',noteCards===0,{noteCards,noteSamples:noteSamples.slice(0,5)});
  await lib.locator('#search').fill('FFlagDebugGraphicsPreferD3D11');
  await lib.waitForTimeout(300);
  let val=await safe(()=>lib.locator('#flagsGrid input[aria-label^="Actual value for"]').first().inputValue());
  check('Library actual flag lookup',typeof val==='string'&&!val.includes('logging causes'),val);
  const auditSource=await lib.evaluate(()=>({notes:window.zflagArchiveAudit?.notes,malformed:window.zflagArchiveAudit?.malformed?.length,valid:window.zflagArchiveAudit?.validNames}));
  check('Archive metadata properly classified',auditSource.notes===81&&auditSource.malformed===9&&auditSource.valid===15875,auditSource);
  const actualInput=lib.locator('#flagsGrid input[aria-label="Actual value for FFlagDebugGraphicsPreferD3D11"]');
  await actualInput.fill('this is a description, not a boolean');
  const invalidBlocked=await lib.locator('#flagsGrid .card').filter({has:lib.locator('.flagname',{hasText:/^FFlagDebugGraphicsPreferD3D11$/})}).getByRole('button',{name:'+ Add to config'}).isDisabled();
  check('Invalid typed value blocked',invalidBlocked);
  await actualInput.fill('true');
  const sampleCard=lib.locator('#flagsGrid .card').filter({has:lib.locator('.flagname', {hasText:/^FFlagDebugGraphicsPreferD3D11$/})});
  await sampleCard.getByRole('button',{name:'+ Add to config'}).click();
  await lib.locator('[data-tab="draft"]').click();
  const draftValue=await lib.evaluate(()=>{try{return JSON.parse(document.querySelector('#draftContent').textContent).FFlagDebugGraphicsPreferD3D11}catch(e){return null}});
  check('Flag added as real JSON boolean',draftValue===true,{actualType:typeof draftValue,value:draftValue});
  check('No library exceptions',libErrors.length===0,libErrors);
  await lib.screenshot({path:'audit-library.png',fullPage:false});
  const reducedContext=await browser.newContext({viewport:{width:900,height:650},reducedMotion:'reduce'});
  const reducedPage=await reducedContext.newPage();
  await reducedPage.goto(base+'/?audit=reduce',{waitUntil:'domcontentloaded'});
  check('Reduced-motion users retain native wheel scrolling',await reducedPage.evaluate(()=>window.__zflagScrollV2?.isReducedMotion()===true));
  await reducedContext.close();
  const mobile=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  mobile.setDefaultTimeout(6000);
  const mobileHome=await mobile.newPage();
  await mobileHome.goto(base+'/?audit=mobile-locale',{waitUntil:'domcontentloaded'});
  const homeMobile=await mobileHome.evaluate(()=>({scrollWidth:document.documentElement.scrollWidth,viewport:innerWidth,langButton:!!document.getElementById('languageTop')}));
  check('Mobile homepage layout fits screen',homeMobile.scrollWidth<=homeMobile.viewport+4&&homeMobile.langButton,homeMobile);
  const mobileDocs=await mobile.newPage();
  await mobileDocs.goto(base+'/docs/?audit=mobile-locale',{waitUntil:'domcontentloaded'});
  const docMobile=await mobileDocs.evaluate(()=>({
    scrollWidth:document.documentElement.scrollWidth,viewport:innerWidth,
    langBtn:!!document.querySelector('.zflag-locale-toggle'),
    langVisible:!!document.querySelector('.zflag-locale-toggle')&&getComputedStyle(document.querySelector('.zflag-locale-toggle')).display!=='none'
  }));
  check('Mobile documentation fits and shows language selector',docMobile.scrollWidth<=docMobile.viewport+4&&docMobile.langVisible,docMobile);
  const mobileLib=await mobile.newPage();
  await mobileLib.goto(base+'/library/?audit=mobile-locale',{waitUntil:'domcontentloaded'});
  const libMobile=await mobileLib.evaluate(()=>({
    scrollWidth:document.documentElement.scrollWidth,viewport:innerWidth,
    localeVisible:!!document.querySelector('.zflag-locale-toggle')&&getComputedStyle(document.querySelector('.zflag-locale-toggle')).display!=='none'
  }));
  check('Mobile library fits and shows language selector',libMobile.scrollWidth<=libMobile.viewport+4&&libMobile.localeVisible,libMobile);
  await mobile.close();
  await browser.close();
  const failed=results.filter(x=>!x.ok);
  console.log('\nSUMMARY '+JSON.stringify({passed:results.length-failed.length,total:results.length,failed:failed.map(x=>x.label)}));
  if(failed.length)process.exitCode=1;
})().catch(e=>{console.error('AUDIT FATAL',e);process.exitCode=1;});
