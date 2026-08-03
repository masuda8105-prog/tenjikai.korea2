import asyncio, json, base64, csv, io, os
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]


def browser_launch_options():
    configured=os.environ.get('CHROMIUM_PATH')
    candidates=[
        configured,
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
        '/usr/bin/chromium', '/usr/bin/chromium-browser',
    ]
    executable=next((value for value in candidates if value and Path(value).is_file()),None)
    options={'headless':True,'args':['--no-sandbox']}
    if executable: options['executable_path']=executable
    return options


def storage_shim():
    return """
    (()=>{const makeStore=()=>{const data=new Map();return {getItem:k=>data.has(String(k))?data.get(String(k)):null,setItem:(k,v)=>data.set(String(k),String(v)),removeItem:k=>data.delete(String(k)),clear:()=>data.clear(),key:i=>Array.from(data.keys())[i]||null,get length(){return data.size}}};try{Object.defineProperty(window,'localStorage',{value:makeStore(),configurable:true})}catch{}try{Object.defineProperty(window,'sessionStorage',{value:makeStore(),configurable:true})}catch{}})();
    """


def inline_customer_html(mock_js: str):
    html=(ROOT/'index.html').read_text(encoding='utf-8')
    mock_js=storage_shim()+mock_js
    html=html.replace('<script src="online-config.js"></script>', f'<script>{mock_js}</script><script>{(ROOT/"online-config.js").read_text()}</script>')
    html=html.replace('<script src="vendor/qrcode.min.js"></script>', f'<script>{(ROOT/"vendor/qrcode.min.js").read_text()}</script>')
    # This scenario imports CSV only; the XLSX bundle is unnecessary here.
    html=html.replace('<script src="vendor/xlsx.full.min.js"></script>', '')
    with (ROOT/'product_master_korea.csv').open(encoding='utf-8-sig', newline='') as handle:
        reader=csv.DictReader(handle)
        rows=[row for row in reader if row.get('品番')=='1053']
        output=io.StringIO(newline='')
        writer=csv.DictWriter(output,fieldnames=reader.fieldnames)
        writer.writeheader(); writer.writerows(rows)
    csv_b64=base64.b64encode(('\ufeff'+output.getvalue()).encode('utf-8')).decode()
    html=html.replace("const DATA_FILE = 'product_master_korea.csv';", f"const DATA_FILE = 'data:text/csv;base64,{csv_b64}';")
    return html


def inline_staff_html(mock_js: str):
    html=(ROOT/'staff.html').read_text(encoding='utf-8')
    mock_js=storage_shim()+mock_js
    html=html.replace('<script src="online-config.js"></script>', f'<script>{mock_js}</script><script>{(ROOT/"online-config.js").read_text()}</script>')
    html=html.replace('<script src="vendor/qrcode.min.js"></script>', f'<script>{(ROOT/"vendor/qrcode.min.js").read_text()}</script>')
    html=html.replace('<script src="staff.js"></script>', f'<script>{(ROOT/"staff.js").read_text()}</script>')
    return html


async def customer_success(browser):
    page=await browser.new_page(viewport={"width":390,"height":844})
    errors=[]
    page.on('pageerror', lambda e: errors.append(str(e)))
    order={"v":9,"status":"new","lang":"ja","orderNo":"K260730-001","createdAt":"2026-07-30T08:00:00.000Z","date":"2026/7/30 17:00:00","eventName":"Korea Optical Exhibition","distributor":"KY-S Corporation.","staffName":"","customerCompany":"Test Optical","customerName":"Kim","customerPhone":"010-1234-5678","notes":"","priceMode":"with","currency":"KRW","total":120000,"items":[{"c":"1053","n":["ヤットコ","푸시록 패드 조정 플라이어"],"q":1,"p":120000,"img":""}]}
    mock=f"""
    window.__postCount=0;
    const __nativeFetch=window.fetch.bind(window);
    window.fetch=async (input,init={{}})=>{{
      const url=String(input);
      if(url.includes('/functions/v1/exhibition-order')){{
        if((init.method||'GET').toUpperCase()==='POST'){{window.__postCount+=1;return new Response({json.dumps(json.dumps({'id':'1','token':'A'*43,'orderNo':'K260730-001','status':'new','createdAt':'2026-07-30T08:00:00.000Z','expiresAt':'2026-08-13T08:00:00.000Z'}))},{{status:201,headers:{{'Content-Type':'application/json'}}}});}}
        return new Response({json.dumps(json.dumps({'order':order,'status':'new','expiresAt':'2026-08-13T08:00:00.000Z','businessCardOriginalUrl':'','businessCardPreviewUrl':''}))},{{status:200,headers:{{'Content-Type':'application/json'}}}});
      }}
      return __nativeFetch(input,init);
    }};
    """
    await page.set_content(inline_customer_html(mock),wait_until='domcontentloaded')
    await page.wait_for_function(r"/\d/.test(document.querySelector('#searchResultStatus')?.textContent||'')",timeout=30000)
    await page.fill('#searchInput','1053'); await page.wait_for_selector('[data-add="1053"]'); await page.click('[data-add="1053"]')
    await page.click('#quickCheckout'); await page.fill('#customerCompany','Test Optical'); await page.fill('#customerName','Kim'); await page.fill('#customerPhone','010-1234-5678'); await page.click('#createQr')
    await page.wait_for_selector('#qrDialog[open]',timeout=10000)
    assert await page.text_content('#handoffOrderNo')=='K260730-001'
    await page.click('#closeQr'); await page.click('#quickCheckout'); await page.click('#createQr'); await page.wait_for_selector('#qrDialog[open]')
    assert await page.evaluate('window.__postCount')==1
    await page.click('#openReceipt'); await page.wait_for_function("document.body.classList.contains('receiptOnly')")
    await page.wait_for_function("document.querySelector('#receiptPrintArea')?.textContent.includes('K260730-001')",timeout=10000)
    receipt=await page.text_content('#receiptPrintArea');
    if not ('K260730-001' in receipt and 'Test Optical' in receipt and '1053' in receipt):
        raise AssertionError(f'Unexpected receipt: {receipt[:1200]}')
    assert not errors, errors
    await page.close()


async def customer_card_failure(browser):
    page=await browser.new_page(viewport={"width":390,"height":844})
    dialogs=[]
    async def dialog_handler(d): dialogs.append(d.message); await d.accept()
    page.on('dialog',dialog_handler)
    mock="""
    const __nativeFetch=window.fetch.bind(window);
    window.fetch=async (input,init={})=>{
      if(String(input).includes('/functions/v1/exhibition-order')) return new Response('{"error":"upload failed"}',{status:500,headers:{'Content-Type':'application/json'}});
      return __nativeFetch(input,init);
    };
    """
    await page.set_content(inline_customer_html(mock),wait_until='domcontentloaded')
    await page.wait_for_function(r"/\d/.test(document.querySelector('#searchResultStatus')?.textContent||'')",timeout=30000)
    await page.fill('#searchInput','1053'); await page.click('[data-add="1053"]'); await page.click('#quickCheckout'); await page.fill('#customerCompany','Card Test'); await page.fill('#customerName','Kim'); await page.fill('#customerPhone','010')
    await page.set_input_files('#businessCardInput',str(ROOT/'assets/sun_nishimura_logo.jpg')); await page.wait_for_selector('#businessCardPreview.show'); await page.click('#createQr'); await page.wait_for_timeout(700)
    assert any('入力内容は保存されています' in message for message in dialogs), dialogs
    assert not await page.locator('#qrDialog').evaluate('(el)=>el.open')
    await page.close()


async def staff_flow(browser):
    page=await browser.new_page(viewport={"width":1280,"height":900})
    errors=[]; page.on('pageerror',lambda e: errors.append(str(e)))
    async def accept_dialog(dialog): await dialog.accept()
    page.on('dialog',accept_dialog)
    mock="""
    let __status='new',__printed=null,__updated=1,__batch=null;
    window.print=()=>{window.__printed=true};
    const __order={id:'00000000-0000-0000-0000-000000000001',order_no:'K260730-001',status:'new',assigned_to:null,assigned_name:null,business_card_original_path:null,business_card_preview_path:null,expires_at:'2026-08-13T08:00:00.000Z',created_at:'2026-07-30T08:00:00.000Z',updated_at:'2026-07-30T08:00:00.000Z',printed_at:null,completed_at:null,event_id:'korea-exhibition-2026',event_name:'Korea Optical Exhibition 2026',event_date:'2026-07-30',event_day:1,revision_count:0,requires_resend:false,pending_batch_id:null,order_data:{customerCompany:'Test Optical',customerName:'Kim',customerPhone:'010-1234',notes:'',eventId:'korea-exhibition-2026',eventName:'Korea Optical Exhibition 2026',eventDate:'2026-07-30',total:120000,items:[{c:'1053',n:['ヤットコ','플라이어'],q:1,p:120000}]}};
    window.fetch=async (input,init={})=>{
      const url=String(input),method=(init.method||'GET').toUpperCase();
      if(url.includes('/auth/v1/token')) return new Response(JSON.stringify({access_token:'test-access',refresh_token:'test-refresh',expires_in:3600,user:{id:'11111111-1111-1111-1111-111111111111',email:'staff@example.com',user_metadata:{full_name:'増田'}}}),{status:200,headers:{'Content-Type':'application/json'}});
      if(url.includes('/rest/v1/exhibition_staff')) return new Response(JSON.stringify([{display_name:'増田',role:'staff',active:true}]),{status:200,headers:{'Content-Type':'application/json'}});
      if(url.includes('/rest/v1/rpc/create_exhibition_order_batch')){__batch='KY-20260730-01';__order.pending_batch_id=__batch;return new Response(JSON.stringify([{batch_id:__batch,order_count:1,total_quantity:1,total_amount:120000}]),{status:200,headers:{'Content-Type':'application/json'}})}
      if(url.includes('/rest/v1/rpc/mark_exhibition_order_batch_sent')){__status='sent';__order.status='sent';__order.pending_batch_id=null;__order.batch_id=__batch;return new Response('1',{status:200,headers:{'Content-Type':'application/json'}})}
      if(url.includes('/rest/v1/rpc/cancel_exhibition_order_batch')){__order.pending_batch_id=null;return new Response('1',{status:200,headers:{'Content-Type':'application/json'}})}
      if(url.includes('/rest/v1/order_activity_logs')||url.includes('/rest/v1/order_revisions')) return new Response('',{status:201,headers:{'Content-Type':'application/json'}});
      if(url.includes('/rest/v1/exhibition_orders')&&method==='PATCH'){const data=JSON.parse(init.body||'{}');Object.assign(__order,data);if(data.status)__status=data.status;if(data.printed_at)__printed=data.printed_at;__updated+=1;__order.updated_at=`2026-07-30T08:00:${String(__updated).padStart(2,'0')}.000Z`;return new Response(JSON.stringify([{...__order,status:__status}]),{status:200,headers:{'Content-Type':'application/json'}})}
      if(url.includes('/rest/v1/exhibition_orders')){const row={...__order,status:__status,assigned_name:__status==='new'?null:'増田',printed_at:__printed};return new Response(JSON.stringify([row]),{status:200,headers:{'Content-Type':'application/json'}})}
      if(url.includes('/rest/v1/order_batches')) return new Response('[]',{status:200,headers:{'Content-Type':'application/json'}});
      if(url.includes('/storage/v1/object/sign/')) return new Response('{"signedURL":""}',{status:200,headers:{'Content-Type':'application/json'}});
      if(url.includes('/auth/v1/logout')) return new Response('',{status:204});
      throw new Error('unexpected fetch '+url);
    };
    """
    html=inline_staff_html(mock).replace("await import('https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.105.4/+esm')","({createClient(){throw new Error('offline test')}})")
    await page.set_content(html,wait_until='domcontentloaded')
    await page.fill('#email','staff@example.com'); await page.fill('#password','password'); await page.click('#loginButton'); await page.wait_for_selector('[data-order-id]',timeout=10000)
    assert await page.text_content('#newCount')=='1'
    await page.click('[data-order-id]'); await page.wait_for_selector('#detailDialog[open]'); detail=await page.text_content('#detailBody'); assert 'Test Optical' in detail and '1053' in detail
    await page.click('#startButton'); await page.wait_for_timeout(250); assert await page.text_content('#progressCount')=='1'
    await page.click('#completeButton'); await page.wait_for_timeout(250); assert await page.text_content('#completedCount')=='1'
    await page.click('#printButton'); await page.wait_for_timeout(350); assert await page.evaluate('window.__printed===true')
    await page.click('#deleteButton'); await page.wait_for_selector('#deleteDialog[open]'); await page.select_option('#deleteReason',label='テスト注文'); await page.click('#confirmDeleteButton'); await page.wait_for_timeout(300)
    await page.click('.utilityMenu > summary'); await page.click('#historyButton'); await page.wait_for_selector('[data-restore-id]'); await page.click('[data-restore-id]'); await page.wait_for_timeout(300); assert await page.text_content('#completedCount')=='1'; await page.click('#historyTopClose')
    await page.click('#batchButton'); await page.wait_for_selector('#batchDialog[open]'); await page.click('#createBatchPdfButton'); await page.wait_for_timeout(350); assert await page.evaluate('window.__printed===true')
    await page.check('#pdfSavedCheck'); await page.check('#mailSentCheck'); await page.click('#markBatchSentButton'); await page.wait_for_timeout(350); assert await page.text_content('#sentCount')=='1'
    assert not errors, errors
    await page.close()


async def tablet_smoke(browser):
    page=await browser.new_page(viewport={"width":820,"height":1180})
    errors=[]; page.on('pageerror',lambda e: errors.append(str(e)))
    mock="""
    const __nativeFetch=window.fetch.bind(window);
    window.fetch=async (input,init={})=>__nativeFetch(input,init);
    """
    await page.set_content(inline_customer_html(mock),wait_until='domcontentloaded')
    await page.wait_for_function(r"/\d/.test(document.querySelector('#searchResultStatus')?.textContent||'')",timeout=30000)
    await page.fill('#searchInput','1053'); await page.wait_for_selector('[data-add="1053"]'); await page.click('[data-add="1053"]')
    await page.click('#quickCheckout'); await page.wait_for_selector('#customerDialog[open]')
    assert await page.locator('#customerCompany').is_visible()
    assert await page.locator('#businessCardInput').count()==1
    assert not errors, errors
    await page.close()

    staff=await browser.new_page(viewport={"width":820,"height":1180})
    errors=[]; staff.on('pageerror',lambda e: errors.append(str(e)))
    staff_mock="""
    window.fetch=async (input,init={})=>{
      const url=String(input);
      if(url.includes('/auth/v1/token')) return new Response(JSON.stringify({access_token:'tablet-access',refresh_token:'tablet-refresh',expires_in:3600,user:{id:'22222222-2222-2222-2222-222222222222',email:'tablet@example.com',user_metadata:{full_name:'Tablet Staff'}}}),{status:200,headers:{'Content-Type':'application/json'}});
      if(url.includes('/rest/v1/exhibition_staff')) return new Response(JSON.stringify([{display_name:'Tablet Staff',role:'staff',active:true}]),{status:200,headers:{'Content-Type':'application/json'}});
      if(url.includes('/rest/v1/exhibition_orders')) return new Response('[]',{status:200,headers:{'Content-Type':'application/json'}});
      throw new Error('unexpected fetch '+url);
    };
    """
    html=inline_staff_html(staff_mock).replace("await import('https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.105.4/+esm')","({createClient(){throw new Error('offline test')}})")
    await staff.set_content(html,wait_until='domcontentloaded')
    await staff.fill('#email','tablet@example.com'); await staff.fill('#password','password'); await staff.click('#loginButton')
    await staff.wait_for_selector('#dashboardView:not(.hidden)',timeout=10000)
    assert await staff.locator('.summary').is_visible()
    assert await staff.locator('[data-tab]').count()==4
    assert not errors, errors
    await staff.close()


async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(**browser_launch_options())
        await customer_success(browser); await customer_card_failure(browser); await staff_flow(browser); await tablet_smoke(browser)
        await browser.close()
    print('E2E_PASS')

if __name__ == '__main__':
    asyncio.run(main())
