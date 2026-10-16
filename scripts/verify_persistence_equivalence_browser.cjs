const fs=require('fs'),assert=require('assert');
const {chromium}=require('../.tools/ui-preview/node_modules/playwright');
(async()=>{
 const missing=JSON.parse(fs.readFileSync('data/results/phase7verify/missing-response.json','utf8'));
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const rows=[];
 try{
  for(const width of [1440,390]){
   const page=await browser.newPage({viewport:{width,height:1000}}),errors=[];
   page.on('pageerror',e=>errors.push(e.message));
   for(const [city,method] of [['mumbai','persistence'],['delhi','model']]){
    await page.goto('http://localhost:8000/dashboard/');
    await page.locator('#serving-city').selectOption(city);
    await page.locator('#check-serving').click();
    await page.waitForFunction(()=>document.querySelector('#serving-status').dataset.state==='available');
    assert((await page.locator('#serving-status').innerText()).includes('forecast_method: '+method));
    await page.locator('#serving-status').scrollIntoViewIfNeeded();
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    await page.screenshot({path:`docs/results/phase7-verify-dashboard-${city}-${width}.png`});
    await page.goto(`http://localhost:8000/api/forecast/${city}/latest/`);
    const label=page.locator('.response-info .prettyprint .str').filter({hasText:'"forecast_method"'}).first();
    await label.scrollIntoViewIfNeeded();
    assert((await page.locator('.response-info').innerText()).includes(`"forecast_method": "${method}"`));
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    await page.screenshot({path:`docs/results/phase7-verify-api-${city}-${width}.png`});
    rows.push({width,city,method,live_api_status:200,dashboard_label_visible:true,api_label_visible:true,horizontal_overflow:false});
   }
   await page.route('**/api/forecast/mumbai/latest/',route=>route.fulfill({status:missing.status,contentType:'application/json',body:JSON.stringify(missing.body)}));
   for(const name of ['dashboard','forecasts']){
    await page.goto(`http://localhost:8000/${name}/?city=mumbai`);
    const status=name==='dashboard'?'#serving-status':'#forecast-status';
    if(name==='dashboard'){
     await page.locator('#serving-city').selectOption('mumbai');
     await page.locator('#check-serving').click();
    }
    await page.waitForFunction(selector=>document.querySelector(selector).textContent.includes('No forecast: input data missing for this issue date.'),status);
    await page.locator(status).scrollIntoViewIfNeeded();
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    await page.screenshot({path:`docs/results/phase7-verify-${name}-missing-${width}.png`});
    rows.push({width,page:name,fixture_status:503,message:await page.locator(status).innerText(),horizontal_overflow:false});
   }
   await page.goto('http://localhost:8000/api/forecast/mumbai/latest/');
   assert((await page.locator('body').innerText()).includes('No forecast: input data missing for this issue date.'));
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   await page.screenshot({path:`docs/results/phase7-verify-api-missing-${width}.png`});
   rows.push({width,page:'api',fixture_status:503,message:missing.body.detail,horizontal_overflow:false});
   assert.deepEqual(errors,[]);
   await page.close();
  }
  fs.writeFileSync('data/results/phase7verify/browser.json',JSON.stringify(rows,null,2)+'\n');console.log(JSON.stringify(rows,null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
