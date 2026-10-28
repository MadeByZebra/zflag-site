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
  for(const route of ['/', '/docs/', '/library/', '/smooth-scroll.js','/zflag-logo.png','/build-status.txt']) {
    const resp=await context.request.get(base+route+'?audit=20261028', {timeout:25000});
    check('HTTP '+route,resp.status()===200,{status:resp.status(),type:resp.headers()['content-type'],bytes:(await resp.body()).length});
    if(route==='/build-status.txt')console.log('LIVE BUILD MARKER '+(await resp.text()).slice(0,200));
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
  check('Homepage original Z',home.logo.includes('zflag-logo.png'),home.logo);
  check('White default chosen',home.pickerDefault==='#ffffff' && home.accent==='#ffffff',{pickerDefault:home.pickerDefault,accent:home.accent});
  check('Shared scroll JS loaded',home.jsLoaded,home.jsLoaded);
  await page.locator('[data-accent="#4f8cff"]').first().click({timeout:5000});
  let changed=await page.evaluate(()=>({
    accent:getComputedStyle(document.documentElement).getPropertyValue('--app-accent').trim(),
    selectedMain:document.querySelector('[data-accent].active')?.dataset.accent,
    selectedFull:document.querySelector('[data-z2-color].is-selected')?.dataset.z2Color,
    selectedMini:document.querySelector('[data-mini-color].selected')?.dataset.miniColor,
    status:document.querySelector('#accentStatus')?.textContent,
    stageAccent:getComputedStyle(document.querySelector('.z2-window')).getPropertyValue('--z2accent').trim(),
  }));
  check('Click Blue updates all pickers',changed.accent==='#4f8cff'&&changed.selectedMain==='#4f8cff'&&changed.selectedFull==='#4f8cff'&&changed.selectedMini==='#4f8cff',changed);
  await page.reload({waitUntil:'domcontentloaded'});
  await page.waitForTimeout(350);
  let persisted=await page.evaluate(()=>document.querySelector('[data-accent].active')?.dataset.accent);
  check('Picker persists after reload',persisted==='#4f8cff',persisted);
  let initial=await page.evaluate(()=>window.scrollY);
  await page.mouse.move(860,490);
  await page.mouse.wheel(0,760);
  await page.waitForTimeout(600);
  let wheelPos=await page.evaluate(()=>window.scrollY);
  check('Mouse wheel scroll changes position',wheelPos>initial+20,{initial,wheelPos});
  await page.locator('a[href="#features"]').first().click({timeout:7000});
  await page.waitForTimeout(900);
  let featurePos=await page.evaluate(()=>({hash:location.hash,y:window.scrollY,header:document.querySelector('#features')?.getBoundingClientRect().top}));
  check('Homepage anchor scroll',featurePos.hash==='#features' && Math.abs(featurePos.header)<180,featurePos);
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
  check('Docs black and guides',docInfo.bg==='rgb(0, 0, 0)' && docInfo.docSections===15,docInfo);
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
  await browser.close();
  const failed=results.filter(x=>!x.ok);
  console.log('\nSUMMARY '+JSON.stringify({passed:results.length-failed.length,total:results.length,failed:failed.map(x=>x.label)}));
  if(failed.length)process.exitCode=1;
})().catch(e=>{console.error('AUDIT FATAL',e);process.exitCode=1;});
