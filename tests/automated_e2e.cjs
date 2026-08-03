const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..');
const read = (name) => fs.readFileSync(path.join(ROOT, name), 'utf8');
const storageShim = `(()=>{const make=()=>{const data=new Map();return{getItem:k=>data.has(String(k))?data.get(String(k)):null,setItem:(k,v)=>data.set(String(k),String(v)),removeItem:k=>data.delete(String(k)),clear:()=>data.clear(),key:i=>Array.from(data.keys())[i]||null,get length(){return data.size}}};try{Object.defineProperty(window,'localStorage',{value:make(),configurable:true})}catch{}try{Object.defineProperty(window,'sessionStorage',{value:make(),configurable:true})}catch{}})();`;

function customerHtml(mock) {
  new Function(mock);
  let html = read('index.html');
  html = html.replace('<script src="online-config.js"></script>', `<script>${storageShim}${mock}</script><script>${read('online-config.js')}</script>`);
  html = html.replace('<script src="vendor/qrcode.min.js"></script>', `<script>${read('vendor/qrcode.min.js')}</script>`);
  // This scenario imports CSV only; the XLSX bundle is unnecessary here.
  html = html.replace('<script src="vendor/xlsx.full.min.js"></script>', '');
  const csv = read('product_master_korea.csv').split(/\r?\n/);
  const small = `\uFEFF${csv[0]}\n${csv.find((line) => line.startsWith('36,'))}\n${csv.find((line) => line.startsWith('1053,'))}\n`;
  html = html.replace("const DATA_FILE = 'product_master_korea.csv';", `const DATA_FILE = 'data:text/csv;base64,${Buffer.from(small).toString('base64')}';`);
  [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)].forEach((match, index) => { try { new vm.Script(match[1], { filename: `customer-script-${index}.js` }); } catch (error) { throw error; } });
  return html;
}

function staffHtml(mock) {
  new Function(mock);
  let html = read('staff.html');
  html = html.replace('<script src="online-config.js"></script>', `<script>${storageShim}${mock}</script><script>${read('online-config.js')}</script>`);
  html = html.replace('<script src="vendor/qrcode.min.js"></script>', `<script>${read('vendor/qrcode.min.js')}</script>`);
  html = html.replace('<script src="staff.js"></script>', `<script>${read('staff.js').replace("await import('https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.105.4/+esm')", "({createClient(){throw new Error('offline test')}})")}</script>`);
  return html;
}

function launchOptions() {
  const candidates = [process.env.CHROMIUM_PATH, 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', 'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe', '/usr/bin/chromium'];
  const executablePath = candidates.find((candidate) => candidate && fs.existsSync(candidate));
  return { headless: true, args: ['--no-sandbox'], ...(executablePath ? { executablePath } : {}) };
}

async function customerFlow(browser) {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = [];
  page.on('pageerror', (error) => errors.push(String(error)));
  const order = { v: 10, status: 'new', lang: 'ja', orderNo: 'K260803-001', createdAt: '2026-08-03T08:00:00.000Z', eventName: 'Korea Optical Exhibition 2026', customerCompany: 'Test Optical', customerName: 'Kim', customerPhone: '010-1234-5678', total: 120000, items: [{ c: '1053', n: ['ヤットコ', '플라이어'], q: 1, p: 120000 }] };
  const mock = `window.__postCount=0;window.__cardParts=null;const __nativeFetch=window.fetch.bind(window);window.fetch=async(input,init={})=>{const url=String(input);if(url.includes('/functions/v1/exhibition-order')){if((init.method||'GET').toUpperCase()==='POST'){window.__postCount+=1;window.__cardParts={original:init.body.get('businessCardOriginal')?.size||0,preview:init.body.get('businessCardPreview')?.size||0};return new Response(JSON.stringify({id:'1',token:'${'A'.repeat(43)}',orderNo:'K260803-001',status:'new',createdAt:'2026-08-03T08:00:00.000Z',expiresAt:'2026-08-17T08:00:00.000Z'}),{status:201,headers:{'Content-Type':'application/json'}})}return new Response(JSON.stringify({order:${JSON.stringify(order)},status:'new',expiresAt:'2026-08-17T08:00:00.000Z',businessCardOriginalUrl:'',businessCardPreviewUrl:''}),{status:200,headers:{'Content-Type':'application/json'}})}return __nativeFetch(input,init)};`;
  await page.setContent(customerHtml(mock), { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => /\d/.test(document.querySelector('#searchResultStatus')?.textContent || ''), null, { timeout: 30000 });
  await page.selectOption('#langSelect', 'ja');
  const packedProduct = await page.evaluate(() => { const product = products.find((item) => String(item.packQty || '').trim()); return product ? { code: product.code, pack: product.packQty } : null; });
  if (!packedProduct) throw new Error('入り数を持つ検証用商品がありません');
  await page.fill('#searchInput', packedProduct.code);
  await page.waitForSelector(`[data-add="${packedProduct.code}"]`);
  if (await page.locator('.packBadge').count() || (await page.textContent('#results')).includes(packedProduct.pack)) throw new Error('商品一覧に入り数が表示されています');
  await page.fill('#searchInput', '1053');
  await page.click('[data-add="1053"]');
  await page.click('#quickCheckout');
  if (!(await page.textContent('#createQr')).includes('受付番号を発行')) throw new Error('主操作が「受付番号を発行」になっていません');
  await page.fill('#customerCompany', 'Test Optical');
  await page.fill('#customerName', 'Kim');
  await page.fill('#customerPhone', '010-1234-5678');
  await page.setInputFiles('#businessCardInput', path.join(ROOT, 'assets', 'sun_nishimura_logo.jpg'));
  await page.waitForSelector('#businessCardPreview.show');
  await page.click('#createQr');
  await page.waitForSelector('#qrDialog[open]');
  if (await page.textContent('#handoffOrderNo') !== 'K260803-001') throw new Error('受付番号が表示されません');
  if (!(await page.textContent('.handoffCustomer')).includes('近くのスタッフにお見せください')) throw new Error('受付番号発行後のスタッフ提示案内がありません');
  await page.click('#closeQr'); await page.click('#quickCheckout'); await page.click('#createQr');
  await page.waitForSelector('#qrDialog[open]');
  if (await page.evaluate(() => window.__postCount) !== 1) throw new Error('同じ注文が二重送信されました');
  if (!await page.evaluate(() => window.__cardParts?.original > 0 && window.__cardParts?.preview > 0)) throw new Error('名刺の原本とプレビューが分離されていません');
  await page.click('#openReceipt');
  await page.waitForFunction(() => document.querySelector('#receiptPrintArea')?.textContent.includes('K260803-001'));
  const receipt = await page.textContent('#receiptPrintArea');
  if (!receipt.includes('スタッフ確認待ち') || !receipt.includes('1053')) throw new Error('控えの状態または商品が不正です');
  if (errors.length) throw new Error(errors.join('\n'));
  await page.close();
}

async function customerFailure(browser) {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const dialogs = [];
  page.on('dialog', async (dialog) => { dialogs.push(dialog.message()); await dialog.accept(); });
  const mock = `const __nativeFetch=window.fetch.bind(window);window.fetch=async(input,init={})=>String(input).includes('/functions/v1/exhibition-order')?new Response('{"error":"server unavailable"}',{status:500,headers:{'Content-Type':'application/json'}}):__nativeFetch(input,init);`;
  await page.setContent(customerHtml(mock), { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => /\d/.test(document.querySelector('#searchResultStatus')?.textContent || ''), null, { timeout: 30000 });
  await page.fill('#searchInput', '1053'); await page.click('[data-add="1053"]'); await page.click('#quickCheckout');
  await page.fill('#customerCompany', 'Failure Test'); await page.fill('#customerName', 'Kim'); await page.fill('#customerPhone', '010');
  await page.click('#createQr'); await page.waitForTimeout(300);
  if (!dialogs.some((message) => message.includes('入力内容は保存されています'))) throw new Error('通信失敗時の保持案内がありません');
  if (await page.inputValue('#customerCompany') !== 'Failure Test') throw new Error('通信失敗で入力が消えました');
  await page.close();
}

async function staffFlow(browser) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const errors = [];
  page.on('pageerror', (error) => errors.push(String(error)));
  page.on('dialog', async (dialog) => dialog.accept());
  const mock = `let __status='new',__updated=1,__batch=null;window.print=()=>{window.__printed=true};const __order={id:'00000000-0000-0000-0000-000000000001',public_token:'${'A'.repeat(43)}',order_no:'K260803-001',status:'new',assigned_to:null,assigned_name:null,business_card_original_path:null,business_card_preview_path:null,expires_at:'2026-08-17T08:00:00.000Z',created_at:'2026-08-03T08:00:00.000Z',updated_at:'2026-08-03T08:00:01.000Z',printed_at:null,completed_at:null,event_id:'korea-exhibition-2026',event_name:'Korea Optical Exhibition 2026',event_date:'2026-08-03',event_day:1,revision_count:0,requires_resend:false,pending_batch_id:null,order_data:{customerCompany:'Test Optical',customerName:'Kim',customerPhone:'010-1234',notes:'',eventId:'korea-exhibition-2026',eventName:'Korea Optical Exhibition 2026',eventDate:'2026-08-03',total:120000,items:[{c:'1053',n:['ヤットコ','플라이어'],q:1,p:120000,img:'product-images/1053_1.jpg'}]}};window.fetch=async(input,init={})=>{const url=String(input),method=(init.method||'GET').toUpperCase();if(url.includes('/auth/v1/token'))return new Response(JSON.stringify({access_token:'test-access',refresh_token:'test-refresh',expires_in:3600,user:{id:'11111111-1111-1111-1111-111111111111',email:'staff@example.com',user_metadata:{full_name:'増田'}}}),{status:200,headers:{'Content-Type':'application/json'}});if(url.includes('/rest/v1/exhibition_staff'))return new Response(JSON.stringify([{display_name:'増田',role:'staff',active:true}]),{status:200,headers:{'Content-Type':'application/json'}});if(url.includes('/rest/v1/rpc/create_exhibition_order_batch')){__batch='KY-20260803-01';__order.pending_batch_id=__batch;return new Response(JSON.stringify([{batch_id:__batch,order_count:1,total_quantity:1,total_amount:120000}]),{status:200,headers:{'Content-Type':'application/json'}})}if(url.includes('/rest/v1/rpc/mark_exhibition_order_batch_sent')){__status='sent';__order.status='sent';__order.pending_batch_id=null;__order.batch_id=__batch;return new Response('1',{status:200,headers:{'Content-Type':'application/json'}})}if(url.includes('/rest/v1/rpc/cancel_exhibition_order_batch')){__order.pending_batch_id=null;return new Response('1',{status:200,headers:{'Content-Type':'application/json'}})}if(url.includes('/rest/v1/order_activity_logs')||url.includes('/rest/v1/order_revisions'))return new Response('',{status:201,headers:{'Content-Type':'application/json'}});if(url.includes('/rest/v1/exhibition_orders')&&method==='PATCH'){const data=JSON.parse(init.body||'{}');Object.assign(__order,data);if(data.status)__status=data.status;__updated+=1;__order.updated_at='2026-08-03T08:00:'+String(__updated).padStart(2,'0')+'.000Z';return new Response(JSON.stringify([{...__order,status:__status}]),{status:200,headers:{'Content-Type':'application/json'}})}if(url.includes('/rest/v1/exhibition_orders'))return new Response(JSON.stringify([{...__order,status:__status,assigned_name:__status==='new'?null:'増田'}]),{status:200,headers:{'Content-Type':'application/json'}});if(url.includes('/rest/v1/order_batches'))return new Response('[]',{status:200,headers:{'Content-Type':'application/json'}});if(url.includes('/auth/v1/logout'))return new Response('',{status:204});throw new Error('unexpected fetch '+url)};`;
  await page.setContent(staffHtml(mock.replace('product-images/1053_1.jpg', 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==')), { waitUntil: 'domcontentloaded' });
  await page.fill('#email', 'staff@example.com'); await page.fill('#password', 'password'); await page.click('#loginButton');
  await page.waitForSelector('[data-order-id]');
  await page.evaluate(() => { window.__stableOrderCard = document.querySelector('[data-order-id]'); });
  await page.evaluate(() => document.querySelector('#refreshButton').click());
  await page.waitForFunction(() => !document.querySelector('#refreshButton').disabled);
  if (!await page.evaluate(() => window.__stableOrderCard === document.querySelector('[data-order-id]'))) throw new Error('無変更の自動更新で注文一覧が再描画されています');
  await page.click('[data-order-id]'); await page.waitForSelector('#detailDialog[open]');
  if (!await page.locator('.detailProductThumb').count()) throw new Error('スタッフ注文詳細に商品画像欄が表示されません');
  await page.fill('#editCompany', 'Protected Optical');
  await page.evaluate(() => document.querySelector('#refreshButton').click());
  await page.waitForTimeout(250);
  if (await page.inputValue('#editCompany') !== 'Protected Optical') throw new Error('自動更新で編集中の入力が消えました');
  await page.fill('#editCompany', 'Test Optical'); await page.click('#saveEditButton');
  await page.click('#customerQrButton'); await page.waitForSelector('#customerQrDialog[open]');
  if (!await page.locator('#customerQrCode img, #customerQrCode canvas').count()) throw new Error('お客様用QRが生成されません');
  await page.click('#customerQrTopClose');
  await page.click('#startButton'); await page.waitForFunction(() => document.querySelector('#progressCount')?.textContent === '1');
  await page.click('#completeButton'); await page.waitForFunction(() => document.querySelector('#completedCount')?.textContent === '1');
  const confirmedText = await page.textContent('.confirmedOrderRow');
  if (!confirmedText.includes('Kim') || !confirmedText.includes('増田') || !confirmedText.includes('K260803-001')) throw new Error('注文確定分の一行表示が不正です');
  await page.click('#printButton'); await page.waitForFunction(() => window.__printed === true);
  await page.emulateMedia({ media: 'print' });
  const singleOrderPdf = await page.pdf({ format: 'A4', preferCSSPageSize: true, printBackground: true });
  const singleOrderPageCount = (singleOrderPdf.toString('latin1').match(/\/Type\s*\/Page\b/g) || []).length;
  if (singleOrderPageCount !== 1) throw new Error(`注文書が${singleOrderPageCount}ページになっています`);
  await page.emulateMedia({ media: 'screen' });
  await page.click('#deleteButton'); await page.selectOption('#deleteReason', { label: 'テスト注文' }); await page.click('#confirmDeleteButton');
  await page.waitForFunction(() => !document.querySelector('#detailDialog').open);
  await page.click('.utilityMenu > summary'); await page.click('#historyButton'); await page.waitForSelector('[data-restore-id]'); await page.click('[data-restore-id]');
  await page.waitForFunction(() => document.querySelector('#completedCount')?.textContent === '1'); await page.click('#historyTopClose');
  await page.evaluate(() => { window.__printed = false; });
  await page.click('#batchButton'); await page.waitForSelector('#batchDialog[open]'); await page.click('#createBatchPdfButton');
  await page.waitForFunction(() => window.__printed === true); await page.check('#pdfSavedCheck'); await page.check('#mailSentCheck'); await page.click('#markBatchSentButton');
  await page.waitForFunction(() => document.querySelector('#sentCount')?.textContent === '1');
  await page.click('#sentOrdersButton'); await page.waitForSelector('#sentOrdersDialog[open]');
  if (!(await page.textContent('#list-sent')).includes('K260803-001')) throw new Error('送付済み注文をメニューから確認できません');
  await page.click('#sentOrdersTopClose');
  if (errors.length) throw new Error(errors.join('\n'));
  await page.close();
}

async function responsiveSmoke(browser) {
  const customer = await browser.newPage({ viewport: { width: 1280, height: 700 } });
  const customerErrors = [];
  customer.on('pageerror', (error) => customerErrors.push(String(error)));
  const customerMock = `const __nativeFetch=window.fetch.bind(window);window.fetch=(input,init={})=>__nativeFetch(input,init);`;
  await customer.setContent(customerHtml(customerMock), { waitUntil: 'domcontentloaded' });
  await customer.waitForFunction(() => /\d/.test(document.querySelector('#searchResultStatus')?.textContent || ''), null, { timeout: 30000 });
  await customer.fill('#searchInput', '1053'); await customer.click('[data-add="1053"]'); await customer.click('#quickCheckout');
  if (!await customer.locator('#customerCompany').isVisible() || await customer.locator('#businessCardInput').count() !== 1) throw new Error('タブレット注文画面の表示が不正です');
  const checkoutLayout = await customer.evaluate(() => {
    const dialog = document.querySelector('#customerDialog').getBoundingClientRect();
    const button = document.querySelector('#createQr').getBoundingClientRect();
    const body = document.querySelector('.customerSheetBody');
    return { buttonVisible: button.top >= dialog.top && button.bottom <= dialog.bottom + 1, rows: getComputedStyle(document.querySelector('#customerDialog')).gridTemplateRows.split(' ').length, bodyScrollable: body.scrollHeight >= body.clientHeight };
  });
  if (!checkoutLayout.buttonVisible || checkoutLayout.rows !== 3 || !checkoutLayout.bodyScrollable) throw new Error(`PC注文画面の送信欄レイアウトが不正です: ${JSON.stringify(checkoutLayout)}`);
  if (customerErrors.length) throw new Error(customerErrors.join('\n'));
  await customer.close();

  const staff = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const staffErrors = [];
  staff.on('pageerror', (error) => staffErrors.push(String(error)));
  const staffMock = `window.fetch=async(input,init={})=>{const url=String(input);if(url.includes('/auth/v1/token'))return new Response(JSON.stringify({access_token:'mobile-access',refresh_token:'mobile-refresh',expires_in:3600,user:{id:'22222222-2222-2222-2222-222222222222',email:'mobile@example.com',user_metadata:{full_name:'Mobile Staff'}}}),{status:200,headers:{'Content-Type':'application/json'}});if(url.includes('/rest/v1/exhibition_staff'))return new Response(JSON.stringify([{display_name:'Mobile Staff',role:'staff',active:true}]),{status:200,headers:{'Content-Type':'application/json'}});if(url.includes('/rest/v1/exhibition_orders')||url.includes('/rest/v1/order_batches'))return new Response('[]',{status:200,headers:{'Content-Type':'application/json'}});throw new Error('unexpected fetch '+url)};`;
  await staff.setContent(staffHtml(staffMock), { waitUntil: 'domcontentloaded' });
  await staff.fill('#email', 'mobile@example.com'); await staff.fill('#password', 'password'); await staff.click('#loginButton');
  await staff.waitForSelector('#dashboardView:not(.hidden)');
  if (!await staff.locator('.summary').isVisible() || await staff.locator('[data-tab]').count() !== 2) throw new Error('スマホスタッフ画面の表示が不正です');
  if (staffErrors.length) throw new Error(staffErrors.join('\n'));
  await staff.close();
}

(async () => {
  const browser = await chromium.launch(launchOptions());
  try {
    await customerFlow(browser);
    await customerFailure(browser);
    await staffFlow(browser);
    await responsiveSmoke(browser);
  } finally {
    await browser.close();
  }
  console.log('E2E_PASS');
})().catch((error) => { console.error(error); process.exit(1); });
