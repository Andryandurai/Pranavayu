const fs = require('fs');
const assert = require('assert');
const {chromium} = require('../.tools/ui-preview/node_modules/playwright');
(async () => {
  const browser = await chromium.launch({channel:'msedge',headless:true});
  const rows=[];
  try {
    for (const width of [1440,390]) {
      for (const [name,path] of [
        ['dashboard','/dashboard/'],
        ['api','/api/forecast/mumbai/latest/'],
        ['forecasts','/forecasts/?city=mumbai'],
      ]) {
        const page=await browser.newPage({viewport:{width,height:1000}});
        const errors=[];page.on('pageerror',error=>errors.push(error.message));
        const response=await page.goto('http://127.0.0.1:8000'+path,{waitUntil:'domcontentloaded',timeout:60000});
        assert.equal(response.status(),200);
        if(name==='dashboard') {
          const labels=page.locator('.forecast-method');
          assert.equal(await labels.count(),21);
          const text=await labels.allTextContents();
          assert.equal(text.filter(s=>s.includes('forecast_method: persistence')).length,9);
          assert.equal(text.filter(s=>s.includes('forecast_method: model')).length,12);
          await labels.nth(0).scrollIntoViewIfNeeded();
          assert(await labels.nth(0).isVisible());
        } else if(name==='forecasts') {
          await page.waitForFunction(()=>document.querySelectorAll('.forecast-method').length===3);
          assert((await page.locator('.forecast-method').allTextContents()).every(t=>t.includes('persistence')));
          const cards = await page.locator('#forecast-cards').innerText();
          assert(cards.includes('unavailable for persistence override'));
          assert(!cards.includes('The chosen target interval excludes'));
        } else {
          const method=page.locator('.response-info .prettyprint').filter({hasText:'forecast_method'});
          assert(await method.count()>0);
          await method.first().scrollIntoViewIfNeeded();
          assert(await method.first().isVisible());
          const text=await method.first().innerText();
          assert(text.includes('"forecast_method": "persistence"'));
          assert(text.includes('"policy_source": "phase4-persistence-v1"'));
          assert(text.includes('"fallback_reason": "model_loses_to_persistence_phase4"'));
          const label = method.first().locator('.str').filter({hasText:'"forecast_method"'}).first();
          await label.scrollIntoViewIfNeeded();
          assert(await label.isVisible());
        }
        const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
        assert.equal(overflow,false,name+' horizontal overflow');
        assert.deepEqual(errors,[]);
        const screenshot=`docs/results/phase7-fix-${name}-${width}.png`;
        await page.screenshot({path:screenshot});
        rows.push({name,path,width,status:response.status(),forecast_method_labels_visible:true,horizontal_overflow:overflow,js_errors:errors,screenshot});
        await page.close();
      }
    }
    fs.writeFileSync('data/results/phase7fix/browser.json',JSON.stringify(rows,null,2)+'\n');
    console.log(JSON.stringify(rows,null,2));
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
