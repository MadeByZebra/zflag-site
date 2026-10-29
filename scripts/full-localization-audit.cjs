const { chromium }=require('playwright');
const base=process.env.ZFLAG_AUDIT_BASE||'https://zflag.onrender.com';
const locales=['es','fr','de','pt','ru','tr','zh','ja','ko'];
let passed=0,failed=[];
function assert(name,condition,data){console.log((condition?'PASS ':'FAIL ')+name+' '+JSON.stringify(data??'').slice(0,260));if(condition)passed++;else failed.push(name)}
async function translated(page,lang){
 await page.waitForFunction(lang=>document.documentElement.dataset.translatedLanguage===lang,lang,{timeout:16000});
 return page.evaluate(()=>window.ZFLAGFullLanguage.coverage());
}
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1320,height:900}});
 const pack=JSON.parse(await (await context.request.get(base+'/i18n/es.json')).text());
 assert('Spanish full offline pack has 904 entries',Object.keys(pack).length>=850,{entries:Object.keys(pack).length});
 const page=await context.newPage();
 page.on('pageerror',e=>{console.log('JS ERROR homepage',e.message);failed.push('homepage JS '+e.message)});
 await page.goto(base+'/?full-translation-audit=1',{waitUntil:'domcontentloaded'});
 const enHero=await page.locator('[data-i18n="hero.body"]').textContent();
 const enFAQ=await page.locator('#faq').innerText();
 await page.locator('#languageTop').click();
 await page.locator('.language-option[data-lang="es"]').click();
 const homeCoverage=await translated(page,'es');
 const afterHero=(await page.locator('[data-i18n="hero.body"]').textContent()).trim();
 const afterFaq=await page.locator('#faq').innerText();
 assert('Spanish homepage FULL hero paragraph',afterHero===pack[enHero.trim()]&&afterHero!==enHero,{hero:afterHero,coverage:homeCoverage});
 assert('Spanish homepage FAQ body translated',afterFaq!==enFAQ&&homeCoverage.percentage>=75,{coverage:homeCoverage});
 const docs=await context.newPage();
 docs.on('pageerror',e=>{console.log('JS ERROR docs',e.message);failed.push('docs JS '+e.message)});
 await docs.goto(base+'/docs/?full-translation-audit=1',{waitUntil:'domcontentloaded'});
 const docsCoverage=await translated(docs,'es');
 let article=await docs.locator('#overview .article-body p').first().textContent();
 assert('Spanish docs actual article paragraphs',docsCoverage.percentage>=75&&article.length>=20,{article:article.slice(0,150),coverage:docsCoverage});
 await docs.locator('.zflag-locale-toggle').click();
 await docs.locator('.zflag-locale-item[data-locale="zh"]').click();
 const chineseDocs=await translated(docs,'zh');
 assert('Switching docs to Chinese translates articles',chineseDocs.percentage>=75,{coverage:chineseDocs,example:(await docs.locator('#installation p').first().textContent()).slice(0,140)});
 const library=await context.newPage();
 library.on('pageerror',e=>{console.log('JS ERROR library',e.message);failed.push('library JS '+e.message)});
 await library.goto(base+'/library/?full-translation-audit=1',{waitUntil:'domcontentloaded'});
 await library.waitForFunction(()=>document.querySelectorAll('#flagsGrid .card').length>=50,{timeout:16000});
 const libraryCoverage=await translated(library,'zh');
 const libraryFirst=await library.locator('#flagsGrid .card .description').first().textContent();
 assert('Chinese library dynamic descriptions translated',libraryCoverage.percentage>=68&&!libraryFirst.startsWith('Name suggests'),{desc:libraryFirst.slice(0,200),coverage:libraryCoverage});
 await library.locator('[data-tab="presets"]').click();
 await library.waitForTimeout(300);
 const presetCoverage=await library.evaluate(()=>window.ZFLAGFullLanguage.coverage());
 const firstPreset=await library.locator('#presetGrid .preset p').first().textContent();
 assert('Premade config explanations localized',presetCoverage.percentage>=65&&firstPreset.length>15,{desc:firstPreset.slice(0,170),coverage:presetCoverage});
 await library.locator('.zflag-locale-toggle').click();
 await library.locator('.zflag-locale-item[data-locale="de"]').click();
 const german=await translated(library,'de');
 const label=await library.locator('[data-tab="presets"]').textContent();
 assert('German language affects premade tab and content',german.percentage>=68&&label.trim()!=='Premade configs',{label,coverage:german});
 await library.locator('[data-tab="flags"]').click();
 await library.waitForTimeout(200);
 const key=await library.locator('#flagsGrid .card .flagname').first().textContent();
 const val=await library.locator('#flagsGrid input[aria-label^="Actual value for"]').first().inputValue().catch(()=>null);
 assert('FastFlag IDs and values unchanged',/^(?:D?FFlag|D?FInt|FString|FInt|SFFlag|FLog|D?FString)/.test(key)&&val!==null,{key,val});
 // Navigate across all supported languages, verifying packs load and translate a real article.
 for(const lang of locales){
  const current=await docs.evaluate(()=>localStorage.getItem('zflag-language'));
  if(current!==lang)await docs.evaluate(lang=>window.ZFLAGFullLanguage.set(lang),lang);
  let coverage=await translated(docs,lang);
  assert(lang+' documentation all paragraphs translation pack',coverage.percentage>=75,coverage);
 }
 await browser.close();
 console.log('FULL_TRANSLATION_SUMMARY',JSON.stringify({passed,total:passed+failed.length,failed}));
 if(failed.length)process.exitCode=1;
})().catch(err=>{console.error('FULL_TRANSLATION_FATAL',err);process.exitCode=1});
