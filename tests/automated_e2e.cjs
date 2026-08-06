const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');
const vm = require('vm');
const { pathToFileURL } = require('url');

const ROOT = path.resolve(__dirname, '..');
const read = (name) => fs.readFileSync(path.join(ROOT, name), 'utf8');
const storageShim = `(()=>{const make=()=>{const data=new Map();return{getItem:k=>data.has(String(k))?data.get(String(k)):null,setItem:(k,v)=>data.set(String(k),String(v)),removeItem:k=>data.delete(String(k)),clear:()=>data.clear(),key:i=>Array.from(data.keys())[i]||null,get length(){return data.size}}};try{Object.defineProperty(window,'localStorage',{value:make(),configurable:true})}catch{}try{Object.defineProperty(window,'sessionStorage',{value:make(),configurable:true})}catch{}})();`;

function customerHtml(mock) {
  new Function(mock);
  let html = read('index.html');
  html = html.replace('<script src="online-config.js"></script>', `<script>${storageShim}${mock}</script><script>${read('online-config.js')}</script>`);
  html = html.replace('<script src="vendor/qrcode.min.js"></script>', `<script>${read('vendor/qrcode.min.js')}</script>`);
  html = html.replace('<script src="vendor/html2canvas.min.js"></script>', `<script>${read('vendor/html2canvas.min.js')}</script>`);
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
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/138.0 Mobile/15E148 Safari/604.1' });
  const errors = [];
  page.on('pageerror', (error) => errors.push(String(error)));
  page.on('dialog', async (dialog) => dialog.accept());
  const order = { v: 10, status: 'submitted', clientSubmissionId: '11111111-1111-4111-8111-111111111111', lang: 'ja', orderNo: 'K260803-001', createdAt: '2026-08-03T08:00:00.000Z', eventName: 'Korea Optical Exhibition 2026', customerCompany: 'Test Optical', customerName: 'Kim', customerPhone: '010-1234-5678', shippingAddress: '04524 Seoul Test Address', notes: '', total: 120000, items: [{ c: '1053', n: ['ヤットコ', '플라이어'], q: 1, p: 120000 }] };
  const cardData = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==';
  const mock = `window.__postCount=0;window.__patchCount=0;window.__cardParts=null;window.__postedOrder=null;window.__patchedOrder=null;window.__remoteOrder=${JSON.stringify(order)};window.__remoteStatus='submitted';window.__updatedAt='2026-08-03T08:00:01.000Z';window.__confirmOrder=()=>{window.__remoteStatus='confirmed';window.__remoteOrder.status='confirmed';window.__updatedAt='2026-08-03T08:00:09.000Z'};const __nativeFetch=window.fetch.bind(window);window.fetch=async(input,init={})=>{const url=String(input),method=(init.method||'GET').toUpperCase();if(url.includes('/functions/v1/exhibition-order')){if(method==='POST'){window.__postCount+=1;window.__postedOrder=JSON.parse(init.body.get('order'));window.__remoteOrder={...window.__remoteOrder,...window.__postedOrder,items:(window.__postedOrder.items||[]).map(item=>({...item,img:'${cardData}'})),orderNo:'K260803-001',status:'submitted',createdAt:'2026-08-03T08:00:00.000Z'};window.__cardParts={original:init.body.get('businessCardOriginal')?.size||0,preview:init.body.get('businessCardPreview')?.size||0};return new Response(JSON.stringify({id:'00000000-0000-0000-0000-000000000001',token:'${'A'.repeat(43)}',orderNo:'K260803-001',status:'submitted',createdAt:'2026-08-03T08:00:00.000Z',updatedAt:window.__updatedAt,expiresAt:'2026-08-17T08:00:00.000Z',hasBusinessCard:true,editable:true}),{status:201,headers:{'Content-Type':'application/json'}})}if(method==='PATCH'){window.__patchCount+=1;window.__patchedOrder=JSON.parse(init.body.get('order'));if(window.__remoteStatus==='confirmed')return new Response(JSON.stringify({error:'order_already_confirmed',status:'confirmed',editable:false}),{status:409,headers:{'Content-Type':'application/json'}});window.__remoteOrder={...window.__remoteOrder,...window.__patchedOrder,items:(window.__patchedOrder.items||[]).map(item=>({...item,img:'${cardData}'})),orderNo:'K260803-001',status:window.__remoteStatus};window.__updatedAt='2026-08-03T08:00:02.000Z';return new Response(JSON.stringify({id:'00000000-0000-0000-0000-000000000001',token:'${'A'.repeat(43)}',orderNo:'K260803-001',status:window.__remoteStatus,revisionCount:1,createdAt:'2026-08-03T08:00:00.000Z',updatedAt:window.__updatedAt,expiresAt:'2026-08-17T08:00:00.000Z',hasBusinessCard:true,editable:true}),{status:200,headers:{'Content-Type':'application/json'}})}return new Response(JSON.stringify({id:'00000000-0000-0000-0000-000000000001',token:'${'A'.repeat(43)}',orderNo:'K260803-001',updatedAt:window.__updatedAt,editable:window.__remoteStatus!=='confirmed',order:{...window.__remoteOrder,status:window.__remoteStatus},status:window.__remoteStatus,expiresAt:'2026-08-17T08:00:00.000Z',businessCardOriginalUrl:'${cardData}',businessCardPreviewUrl:'${cardData}'}),{status:200,headers:{'Content-Type':'application/json'}})}return __nativeFetch(input,init)};`;
  await page.setContent(customerHtml(mock), { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => /\d/.test(document.querySelector('#searchResultStatus')?.textContent || ''), null, { timeout: 30000 });
  await page.selectOption('#langSelect', 'ja');
  const packedProduct = await page.evaluate(() => { const product = products.find((item) => String(item.packQty || '').trim()); return product ? { code: product.code, pack: product.packQty } : null; });
  if (!packedProduct) throw new Error('入り数を持つ検証用商品がありません');
  await page.fill('#searchInput', packedProduct.code);
  await page.waitForSelector(`[data-add="${packedProduct.code}"]`);
  if (await page.locator('.packBadge').count() || (await page.textContent('#results')).includes(packedProduct.pack)) throw new Error('商品一覧に入り数が表示されています');
  await page.fill('#searchInput', '１０５３');
  await page.waitForSelector('[data-add="1053"]');
  if (!(await page.textContent('#results')).includes('1053')) throw new Error('全角数字で品番検索できません');
  await page.evaluate(() => { window.__catalogOnlyProductCode = products[0].code; products[0].catalog = '987654321'; prepareProducts(products); renderResults(); });
  await page.fill('#searchInput', '９８７６５４３２１');
  if (await page.locator(`[data-add="${await page.evaluate(() => window.__catalogOnlyProductCode)}"]`).count()) throw new Error('カタログページ番号が数字検索にヒットしています');
  await page.fill('#searchInput', '1053');
  await page.click('[data-add="1053"]');
  await page.click('#quickCheckout');
  if (!(await page.textContent('#createQr')).includes('受付番号を発行')) throw new Error('主操作が「受付番号を発行」になっていません');
  await page.fill('#customerCompany', 'Test Optical');
  await page.fill('#customerName', 'Kim');
  await page.fill('#customerPhone', '010-1234-5678');
  await page.fill('#shippingAddress', '04524 Seoul Test Address');
  await page.setInputFiles('#businessCardInput', path.join(ROOT, 'assets', 'sun_nishimura_logo.jpg'));
  await page.waitForSelector('#businessCardPreview.show');
  await page.click('#createQr');
  await page.waitForSelector('#qrDialog[open]');
  if (await page.textContent('#handoffOrderNo') !== 'K260803-001') throw new Error('受付番号が表示されません');
  if (!(await page.textContent('.handoffCustomer')).includes('近くのスタッフにお見せください')) throw new Error('受付番号発行後のスタッフ提示案内がありません');
  if (!await page.locator('#editOrderFromHandoff').isVisible()) throw new Error('受付番号画面に注文修正ボタンがありません');
  const firstStaffQr = await page.textContent('#receiptUrl');
  if (!firstStaffQr.includes('staff.html#order=') || !await page.locator('#qrCode img, #qrCode canvas').count()) throw new Error('スタッフ詳細へ開くQRが表示されません');
  await page.click('#editOrderFromHandoff');
  await page.waitForFunction(() => !document.body.classList.contains('receiptOnly'));
  if (await page.inputValue('#customerCompany') !== 'Test Optical' || await page.inputValue('#shippingAddress') !== '04524 Seoul Test Address') throw new Error('注文編集へ戻るとお客様情報が消えました');
  if (await page.inputValue('[data-qty]') !== '1' || !await page.locator('#businessCardPreview.show').count()) throw new Error('注文編集へ戻ると商品・数量・名刺が消えました');
  await page.click('[data-plus]');
  await page.click('#quickCheckout'); await page.fill('#notes', 'Customer updated note');
  if (!(await page.textContent('#createQr')).includes('修正内容を保存')) throw new Error('編集時の保存ボタンが分かりにくい表示です');
  await page.click('#createQr');
  await page.waitForSelector('#qrDialog[open]');
  if (await page.evaluate(() => window.__postCount) !== 1) throw new Error('同じ注文が二重送信されました');
  if (await page.evaluate(() => window.__patchCount) !== 1) throw new Error('修正が同じ注文へのPATCHになっていません');
  if (await page.evaluate(() => window.__patchedOrder?.items?.[0]?.q) !== 2 || await page.evaluate(() => window.__patchedOrder?.notes) !== 'Customer updated note') throw new Error('修正した数量・備考が更新データへ反映されません');
  if (await page.textContent('#handoffOrderNo') !== 'K260803-001' || await page.textContent('#receiptUrl') !== firstStaffQr) throw new Error('修正時に受付番号またはQRが変わりました');
  if (!await page.evaluate(() => window.__cardParts?.original > 0 && window.__cardParts?.preview > 0)) throw new Error('名刺の原本とプレビューが分離されていません');
  if (await page.evaluate(() => window.__postedOrder?.shippingAddress) !== '04524 Seoul Test Address') throw new Error('発送先住所が注文データへ送信されていません');
  await page.evaluate(() => { const originalHtml2Canvas = window.html2canvas; window.__htmlCaptureCalled = false; window.html2canvas = (...args) => { window.__htmlCaptureCalled = true; return originalHtml2Canvas(...args); }; });
  await page.click('#openReceipt');
  await page.waitForFunction(() => document.querySelector('#receiptPrintArea')?.textContent.includes('K260803-001'));
  const receipt = await page.textContent('#receiptPrintArea');
  if (!receipt.includes('スタッフ確認待ち') || !receipt.includes('1053') || !receipt.includes('04524 Seoul Test Address') || !receipt.includes('K260803-001')) throw new Error('控えの状態・商品・発送先住所・受付番号が不正です');
  if (!await page.locator('#receiptPrintArea .receiptOrderQrBlock img').count()) throw new Error('注文控え・印刷用データにQRがありません');
  const receiptQrLayout = await page.evaluate(() => { const block=document.querySelector('#receiptPrintArea .receiptOrderQrBlock'),footer=document.querySelector('#receiptPrintArea .receiptFooterMini'),img=block?.querySelector('img'),strong=block?.querySelector('strong'); return { beforeFooter:block?.nextElementSibling===footer, blockWidth:block?.getBoundingClientRect().width||0, imageWidth:img?.getBoundingClientRect().width||0, fontSize:Number.parseFloat(getComputedStyle(strong).fontSize)||0 }; });
  if (!receiptQrLayout.beforeFooter || receiptQrLayout.blockWidth > 350 || receiptQrLayout.imageWidth > 52 || receiptQrLayout.fontSize > 16) throw new Error(`受付番号・QRが控え下部の小型表示になっていません: ${JSON.stringify(receiptQrLayout)}`);
  if (!await page.locator('#editOrderFromReceipt').isVisible() || !await page.locator('#editOrderFromImage').isVisible()) throw new Error('注文控え・画像保存画面に注文修正ボタンがありません');
  if (!(await page.textContent('#deviceSaveText')).includes('長押しして保存してください') || await page.locator('[data-save-device]').count()) throw new Error('長押し保存案内が簡潔に表示されていません');
  if (await page.locator('#saveReceiptImage, #downloadReceiptImage, #receiptImageDownloadFab, #shareReceiptImage').count()) throw new Error('不要な画像表示・ダウンロード・共有ボタンが残っています');
  await page.waitForSelector('#receiptImagePanel.ready', { timeout: 30000 });
  const imagePreview = await page.evaluate(() => ({ src: document.querySelector('#receiptImagePreview').src, width: document.querySelector('#receiptImagePreview').naturalWidth, panelText: document.querySelector('#receiptImagePanel').textContent, htmlCaptureCalled: window.__htmlCaptureCalled }));
  if (!imagePreview.src.startsWith('data:image/png') || imagePreview.src.length < 1000 || imagePreview.width !== 900 || imagePreview.htmlCaptureCalled) throw new Error(`スマホ用の安全なPNG自動プレビューが不正です: ${JSON.stringify(imagePreview)}`);
  if (imagePreview.panelText.includes('長押しできない場合') || imagePreview.panelText.includes('共有')) throw new Error(`控え画像画面に不要な補助案内が残っています: ${imagePreview.panelText}`);
  await page.evaluate(() => window.__confirmOrder());
  await page.click('#editOrderFromImage');
  await page.waitForTimeout(150);
  if (await page.evaluate(() => window.__patchCount) !== 1 || await page.locator('#editOrderFromReceipt').isVisible()) throw new Error('スタッフ確定後もお客様が注文を修正できます');
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
  const mock = `let __status='submitted',__updated=1,__batch=null;window.print=()=>{window.__printed=true};const __order={id:'00000000-0000-0000-0000-000000000001',public_token:'${'A'.repeat(43)}',order_no:'K260803-001',status:'submitted',assigned_to:null,assigned_name:null,business_card_original_path:null,business_card_preview_path:null,expires_at:'2026-08-17T08:00:00.000Z',created_at:'2026-08-03T08:00:00.000Z',updated_at:'2026-08-03T08:00:01.000Z',printed_at:null,completed_at:null,event_id:'korea-exhibition-2026',event_name:'Korea Optical Exhibition 2026',event_date:'2026-08-03',event_day:1,revision_count:0,requires_resend:false,pending_batch_id:null,order_data:{customerCompany:'Test Optical',customerName:'Kim',customerPhone:'010-1234',notes:'',eventId:'korea-exhibition-2026',eventName:'Korea Optical Exhibition 2026',eventDate:'2026-08-03',total:120000,items:[{c:'1053',n:['ヤットコ','플라이어'],q:1,p:120000,img:'product-images/1053_1.jpg'}]}};window.fetch=async(input,init={})=>{const url=String(input),method=(init.method||'GET').toUpperCase();if(url.includes('/auth/v1/token'))return new Response(JSON.stringify({access_token:'test-access',refresh_token:'test-refresh',expires_in:3600,user:{id:'11111111-1111-1111-1111-111111111111',email:'staff@example.com',user_metadata:{full_name:'増田'}}}),{status:200,headers:{'Content-Type':'application/json'}});if(url.includes('/rest/v1/exhibition_staff'))return new Response(JSON.stringify([{display_name:'増田',role:'staff',active:true}]),{status:200,headers:{'Content-Type':'application/json'}});if(url.includes('/rest/v1/rpc/create_exhibition_order_batch')){__batch='KY-20260803-01';__order.pending_batch_id=__batch;return new Response(JSON.stringify([{batch_id:__batch,order_count:1,total_quantity:1,total_amount:120000}]),{status:200,headers:{'Content-Type':'application/json'}})}if(url.includes('/rest/v1/rpc/mark_exhibition_order_batch_sent')){__status='sent';__order.status='sent';__order.pending_batch_id=null;__order.batch_id=__batch;return new Response('1',{status:200,headers:{'Content-Type':'application/json'}})}if(url.includes('/rest/v1/rpc/cancel_exhibition_order_batch')){__order.pending_batch_id=null;return new Response('1',{status:200,headers:{'Content-Type':'application/json'}})}if(url.includes('/rest/v1/order_activity_logs')||url.includes('/rest/v1/order_revisions'))return new Response('',{status:201,headers:{'Content-Type':'application/json'}});if(url.includes('/rest/v1/exhibition_orders')&&method==='PATCH'){const data=JSON.parse(init.body||'{}');Object.assign(__order,data);if(data.status)__status=data.status;__updated+=1;__order.updated_at='2026-08-03T08:00:'+String(__updated).padStart(2,'0')+'.000Z';return new Response(JSON.stringify([{...__order,status:__status}]),{status:200,headers:{'Content-Type':'application/json'}})}if(url.includes('/rest/v1/exhibition_orders'))return new Response(JSON.stringify([{...__order,status:__status,assigned_name:['submitted','new'].includes(__status)?null:'増田'}]),{status:200,headers:{'Content-Type':'application/json'}});if(url.includes('/rest/v1/order_batches'))return new Response('[]',{status:200,headers:{'Content-Type':'application/json'}});if(url.includes('/auth/v1/logout'))return new Response('',{status:204});throw new Error('unexpected fetch '+url)};`;
  const enhancedMock = `history.replaceState(null,'','#order=${'A'.repeat(43)}');${mock}`
    .replace("let __status='submitted',__updated=1,__batch=null;", "let __status='submitted',__updated=1,__batch=null,__patches=[];window.__orderPatchCount=()=>__patches.length;")
    .replace("const data=JSON.parse(init.body||'{}');Object.assign(__order,data);", "const data=JSON.parse(init.body||'{}');__patches.push(data);Object.assign(__order,data);")
    .replace("customerPhone:'010-1234',notes:''", "customerPhone:'010-1234',shippingAddress:'04524 Seoul Test Address',notes:''")
    .replace(']}};window.fetch=', `]}};const __orders=[__order];window.__addSecondOrder=()=>{if(__orders.length>1)return;const second=JSON.parse(JSON.stringify(__order));Object.assign(second,{id:'00000000-0000-0000-0000-000000000002',order_no:'K260804-002',status:'completed',assigned_name:'増田',created_at:'2026-08-04T08:00:00.000Z',updated_at:'2026-08-04T08:00:01.000Z',event_date:'2026-08-04',event_day:2,pending_batch_id:null});second.order_data={...second.order_data,customerCompany:'Day 2 Optical',customerName:'Lee',shippingAddress:'04600 Seoul Day 2 Address',eventDate:'2026-08-04',eventDay:2};__orders.push(second)};window.fetch=`)
    .replace("JSON.stringify([{...__order,status:__status,assigned_name:['submitted','new'].includes(__status)?null:'増田'}])", "JSON.stringify(__orders.map(order=>({...order,status:order===__order?__status:order.status,assigned_name:order.assigned_name||(order===__order&&['submitted','new'].includes(__status)?null:'増田')})))")
    .replace('product-images/1053_1.jpg', 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==');
  await page.setContent(staffHtml(enhancedMock), { waitUntil: 'domcontentloaded' });
  await page.fill('#email', 'staff@example.com'); await page.fill('#password', 'password'); await page.click('#loginButton');
  await page.waitForSelector('[data-order-id]');
  await page.waitForSelector('#detailDialog[open]');
  if (!(await page.textContent('#detailTitle')).includes('K260803-001')) throw new Error('スタッフ用QRの直リンクで該当注文が開きません');
  await page.click('#closeDetail');
  await page.evaluate(() => { const input = document.querySelector('#searchInput'); input.value = '０１０－１２３４'; input.dispatchEvent(new Event('input', { bubbles: true })); });
  await page.waitForFunction(() => document.querySelectorAll('[data-order-id]').length === 1);
  if (await page.locator('[data-order-id]').count() !== 1) throw new Error('スタッフ画面で全角数字の電話番号検索ができません');
  await page.evaluate(() => { const input = document.querySelector('#searchInput'); input.value = ''; input.dispatchEvent(new Event('input', { bubbles: true })); });
  await page.evaluate(() => { window.__stableOrderCard = document.querySelector('[data-order-id]'); });
  await page.evaluate(() => document.querySelector('#refreshButton').click());
  await page.waitForFunction(() => !document.querySelector('#refreshButton').disabled);
  if (!await page.evaluate(() => window.__stableOrderCard === document.querySelector('[data-order-id]'))) throw new Error('無変更の自動更新で注文一覧が再描画されています');
  await page.click('[data-order-id]'); await page.waitForSelector('#detailDialog[open]');
  if (!await page.locator('.detailProductThumb').count()) throw new Error('スタッフ注文詳細に商品画像欄が表示されません');
  if (await page.inputValue('#editShippingAddress') !== '04524 Seoul Test Address') throw new Error('スタッフ画面に発送先住所が表示されません');
  await page.fill('#editCompany', 'Protected Optical');
  await page.fill('#editShippingAddress', '04525 Seoul Updated Address');
  await page.evaluate(() => document.querySelector('#refreshButton').click());
  await page.waitForTimeout(250);
  if (await page.inputValue('#editCompany') !== 'Protected Optical') throw new Error('自動更新で編集中の入力が消えました');
  if (await page.inputValue('#editShippingAddress') !== '04525 Seoul Updated Address') throw new Error('自動更新で編集中の発送先住所が消えました');
  await page.fill('#editCompany', 'Test Optical'); await page.click('#saveEditButton');
  await page.click('#customerQrButton'); await page.waitForSelector('#customerQrDialog[open]');
  if (!await page.locator('#customerQrCode img, #customerQrCode canvas').count()) throw new Error('お客様用QRが生成されません');
  await page.click('#customerQrTopClose');
  await page.click('#startButton'); await page.waitForFunction(() => document.querySelector('#progressCount')?.textContent === '1');
  await page.click('#completeButton'); await page.waitForFunction(() => document.querySelector('#completedCount')?.textContent === '1');
  const confirmedText = await page.textContent('.confirmedOrderRow');
  if (!confirmedText.includes('Test Optical') || !confirmedText.includes('Kim') || !confirmedText.includes('増田') || !confirmedText.includes('K260803-001')) throw new Error('注文確定分の会社名・お客様名を含む一行表示が不正です');
  await page.click('#closeDetail');
  const patchCountBeforeConfirmedView = await page.evaluate(() => window.__orderPatchCount());
  await page.click('.confirmedOrderRow'); await page.waitForSelector('#detailDialog[open]');
  const patchCountAfterConfirmedView = await page.evaluate(() => window.__orderPatchCount());
  if (patchCountAfterConfirmedView !== patchCountBeforeConfirmedView) throw new Error('注文確定分を開いただけで注文データが更新されています');
  await page.click('#printButton'); await page.waitForFunction(() => window.__printed === true);
  if (!(await page.textContent('#printArea')).includes('04525 Seoul Updated Address')) throw new Error('スタッフ注文書に発送先住所が反映されません');
  if (!await page.locator('#printArea .receiptOrderQrBlock img').count() || !(await page.textContent('#printArea .receiptOrderQrBlock')).includes('K260803-001')) throw new Error('スタッフ注文書に受付番号とQRがありません');
  if (!await page.evaluate(() => document.querySelector('#printArea .receiptOrderQrBlock')?.nextElementSibling?.classList.contains('receiptFooterMini'))) throw new Error('スタッフ注文書の受付番号・QRがフッター直前にありません');
  await page.evaluate(() => {
    const card = document.createElement('div');
    card.className = 'receiptBusinessCard';
    card.innerHTML = '<div class="receiptBusinessCardLabel">名刺写真 / 명함 사진<small>印刷サイズ検証</small></div><div class="receiptBusinessCardImage"><img src="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22600%22 height=%22300%22%3E%3Crect width=%22600%22 height=%22300%22 fill=%22%23ffffff%22/%3E%3C/svg%3E" alt="名刺写真"></div>';
    document.querySelector('#printArea .receiptShippingAddress')?.after(card);
  });
  await page.emulateMedia({ media: 'print' });
  const printedCard = await page.locator('#printArea .receiptBusinessCardImage img').boundingBox();
  if (!printedCard || printedCard.height < 130) throw new Error('名刺画像が注文書で十分な大きさになっていません');
  const singleOrderPdf = await page.pdf({ format: 'A4', preferCSSPageSize: true, printBackground: true });
  const singleOrderPageCount = (singleOrderPdf.toString('latin1').match(/\/Type\s*\/Page\b/g) || []).length;
  if (singleOrderPageCount !== 1) throw new Error(`注文書が${singleOrderPageCount}ページになっています`);
  await page.emulateMedia({ media: 'screen' });
  await page.click('#deleteButton'); await page.selectOption('#deleteReason', { label: 'テスト注文' }); await page.click('#confirmDeleteButton');
  await page.waitForFunction(() => !document.querySelector('#detailDialog').open);
  await page.click('.utilityMenu > summary'); await page.click('#historyButton'); await page.waitForSelector('[data-restore-id]'); await page.click('[data-restore-id]');
  await page.waitForFunction(() => document.querySelector('#completedCount')?.textContent === '1'); await page.click('#historyTopClose');
  await page.evaluate(() => { window.__printed = false; });
  await page.evaluate(() => window.__addSecondOrder()); await page.click('#refreshButton');
  await page.waitForFunction(() => document.querySelector('#completedCount')?.textContent === '2');
  await page.click('#batchButton'); await page.waitForSelector('#batchDialog[open]');
  const batchOptions = await page.locator('#batchDateSelect option').evaluateAll((options) => options.map((option) => ({ value: option.value, text: option.textContent })));
  if (batchOptions.length !== 2 || !batchOptions.some((option) => option.text.includes('2026/08/03')) || !batchOptions.some((option) => option.text.includes('2026/08/04'))) throw new Error('日付別の一括送信選択肢が不正です');
  await page.selectOption('#batchDateSelect', batchOptions.find((option) => option.text.includes('2026/08/04')).value);
  if (!(await page.textContent('#batchOrderList')).includes('Day 2 Optical') || (await page.textContent('#batchOrderList')).includes('Test Optical')) throw new Error('別日の注文が一括送信に混在しています');
  await page.selectOption('#batchDateSelect', batchOptions.find((option) => option.text.includes('2026/08/03')).value);
  if (!(await page.textContent('#batchOrderList')).includes('Test Optical') || (await page.textContent('#batchOrderList')).includes('Day 2 Optical')) throw new Error('選択した展示会日の注文が表示されません');
  await page.click('#createBatchPdfButton');
  await page.waitForFunction(() => window.__printed === true);
  await page.emulateMedia({ media: 'print' });
  const batchPdf = await page.pdf({ format: 'A4', preferCSSPageSize: true, printBackground: true, displayHeaderFooter: true, headerTemplate: '<span></span>', footerTemplate: '<span style="font-size:7px">mobile print footer</span>' });
  const batchPages = await pdfPageTexts(batchPdf);
  if (batchPages.length !== 2 || !batchPages[0].includes('KY-20260803-01') || !batchPages[0].includes('KY-S Corporation') || !batchPages[1].includes('K260803-001')) throw new Error(`一括送付PDFの表紙が1ページに収まっていません: ${JSON.stringify(batchPages.map((text) => text.slice(0, 260)))}`);
  await page.emulateMedia({ media: 'screen' });
  await page.check('#pdfSavedCheck'); await page.check('#mailSentCheck'); await page.click('#markBatchSentButton');
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

async function pdfPageTexts(buffer) {
  const pdfModule = await import(pathToFileURL(require.resolve('pdfjs-dist/legacy/build/pdf.mjs')).href);
  const document = await pdfModule.getDocument({ data: new Uint8Array(buffer), disableWorker: true }).promise;
  const pages = [];
  for (let number = 1; number <= document.numPages; number += 1) {
    const page = await document.getPage(number);
    const content = await page.getTextContent();
    pages.push(content.items.map((item) => item.str || '').join(' ').replace(/\s+/g, ' ').trim());
  }
  await document.destroy();
  return pages;
}

async function platformPrintSmoke(browser) {
  const token = 'B'.repeat(43);
  const items = Array.from({ length: 34 }, (_, index) => ({ c: `P${String(index + 1).padStart(3, '0')}`, n: [`印刷検証商品 ${index + 1}`, `인쇄 확인 상품 ${index + 1}`], q: index % 3 + 1, p: 10000 + index * 100, img: 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==' }));
  const order = { v: 10, status: 'submitted', lang: 'ja', orderNo: 'K260804-PRINT', createdAt: '2026-08-04T08:00:00.000Z', eventName: 'Korea Optical Exhibition 2026', customerCompany: 'Cross Platform Optical', customerName: 'Print Test', customerPhone: '010-0000-0000', shippingAddress: 'Seoul print test address', notes: '備考欄と合計欄、受付番号、QRコードを不自然に分断しないための複数ページ印刷検証です。', total: items.reduce((sum, item) => sum + item.q * item.p, 0), items };
  const platforms = [
    { name: 'iPhone Chrome', viewport: { width: 390, height: 844 }, ua: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/138.0 Mobile/15E148 Safari/604.1', mobile: true },
    { name: 'Android Chrome', viewport: { width: 412, height: 915 }, ua: 'Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0 Mobile Safari/537.36', mobile: true },
    { name: 'Windows Edge', viewport: { width: 1365, height: 900 }, ua: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0 Safari/537.36 Edg/138.0' },
    { name: 'Mac Safari', viewport: { width: 1440, height: 900 }, ua: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15' },
  ];
  for (const platform of platforms) {
    const page = await browser.newPage({ viewport: platform.viewport, userAgent: platform.ua });
    const errors = [];
    page.on('pageerror', (error) => errors.push(String(error)));
    const mock = `history.replaceState(null,'','#online-receipt=${token}');const __nativeFetch=window.fetch.bind(window);window.fetch=async(input,init={})=>String(input).includes('/functions/v1/exhibition-order')?new Response(JSON.stringify({id:'00000000-0000-0000-0000-000000000099',token:'${token}',orderNo:'K260804-PRINT',updatedAt:'2026-08-04T08:00:01.000Z',editable:true,order:${JSON.stringify(order)},status:'submitted',expiresAt:'2026-08-18T08:00:00.000Z',businessCardOriginalUrl:'',businessCardPreviewUrl:''}),{status:200,headers:{'Content-Type':'application/json'}}):__nativeFetch(input,init);`;
    await page.setContent(customerHtml(mock), { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => document.querySelectorAll('#receiptPrintArea .receiptTable tbody tr').length === 34, null, { timeout: 30000 });
    await page.waitForSelector('#receiptPrintArea .receiptOrderQrBlock img');
    if (platform.mobile && !(await page.textContent('#deviceSaveText')).includes('長押し')) throw new Error(`${platform.name}: 共通の長押し保存案内が表示されません`);
    await page.emulateMedia({ media: 'print' });
    const layout = await page.evaluate(() => ({
      tableDisplay: getComputedStyle(document.querySelector('.receiptTable')).display,
      rowBreak: getComputedStyle(document.querySelector('.receiptTable tbody tr')).breakInside,
      qrBreak: getComputedStyle(document.querySelector('.receiptOrderQrBlock')).breakInside,
      qrBlockWidth: document.querySelector('.receiptOrderQrBlock').getBoundingClientRect().width,
      qrImageWidth: document.querySelector('.receiptOrderQrBlock img').getBoundingClientRect().width,
      qrBeforeFooter: document.querySelector('.receiptOrderQrBlock').nextElementSibling?.classList.contains('receiptFooterMini'),
      summaryBreak: getComputedStyle(document.querySelector('.receiptSummaryBox')).breakInside,
      pageWidth: document.querySelector('#receiptPrintArea').getBoundingClientRect().width,
    }));
    if (layout.tableDisplay !== 'table' || layout.rowBreak !== 'avoid' || layout.qrBreak !== 'avoid' || layout.summaryBreak !== 'avoid' || !layout.qrBeforeFooter || layout.qrBlockWidth > 240 || layout.qrImageWidth > 40) throw new Error(`${platform.name}: 印刷用CSSまたはフッターQR配置が不正です ${JSON.stringify(layout)}`);
    const pdf = await page.pdf({ format: 'A4', preferCSSPageSize: true, printBackground: true });
    const pages = await pdfPageTexts(pdf);
    if (pages.length < 2 || pages.length > 8) throw new Error(`${platform.name}: 複数ページ数が不自然です (${pages.length})`);
    if (pages.some((text) => text.length < 8)) throw new Error(`${platform.name}: 不要な空白ページがあります`);
    if (!pages.join(' ').includes('K260804-PRINT') || !pages.join(' ').includes('Cross Platform Optical')) throw new Error(`${platform.name}: 受付番号または注文情報が印刷されません`);
    if (errors.length) throw new Error(`${platform.name}: ${errors.join('\n')}`);
    await page.close();
  }
}

(async () => {
  const browser = await chromium.launch(launchOptions());
  try {
    await customerFlow(browser);
    await customerFailure(browser);
    await staffFlow(browser);
    await responsiveSmoke(browser);
    await platformPrintSmoke(browser);
  } finally {
    await browser.close();
  }
  console.log('E2E_PASS');
})().catch((error) => { console.error(error); process.exit(1); });
