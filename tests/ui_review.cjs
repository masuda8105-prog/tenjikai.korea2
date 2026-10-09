const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');
const ROOT = path.resolve(__dirname, '..');
// Reuse offline fixtures so this review never creates or updates live orders.
const source = fs.readFileSync(path.join(__dirname, 'automated_e2e.cjs'), 'utf8');
const fixtures = new Function('require', '__dirname', source.slice(0, source.lastIndexOf('(async () => {')) + '\nreturn { customerHtml, staffHtml, launchOptions };')(require, __dirname);
const output = path.join(ROOT, 'tests', 'artifacts', process.env.UI_REVIEW_LABEL || 'redesign');
const image = 'data:image/jpeg;base64,' + fs.readFileSync(path.join(ROOT, 'product-images', '1053_1.jpg')).toString('base64');
const rows = Array.from({ length: 5 }, (_, i) => ({
  id: `00000000-0000-0000-0000-${String(i + 1).padStart(12, '0')}`,
  order_no: `K261009-${String(i + 1).padStart(3, '0')}`, status: i === 3 ? 'in_progress' : i === 4 ? 'confirmed' : 'submitted',
  public_token: 'A'.repeat(43), created_at: new Date(Date.now() - i * 60000).toISOString(), updated_at: '2026-10-09T01:00:00Z',
  event_date: '2026-10-09', assigned_name: i > 2 ? '増田' : null,
  order_data: { customerCompany: ['Seoul Optical', '株式会社サンプル眼鏡店', 'Han Vision', 'Busan Optics', '明洞眼鏡'][i], customerName: 'Kim', customerPhone: '010-1234-5678', total: 83300, items: [{ c: '1053', n: ['ヤットコ', '플라이어'], q: 1, p: 83300, img: image }] }
}));
const csv = fs.readFileSync(path.join(ROOT,'product_master_korea.csv'),'utf8');
const staffMock = `window.fetch=async(input,init={})=>{const u=String(input);if(u.includes('product_master_korea.csv'))return new Response(${JSON.stringify(csv)},{status:200});let data=[];if(u.includes('/auth/v1/token'))data={access_token:'test',refresh_token:'test',expires_in:3600,user:{id:'staff-id',email:'staff@example.com'}};else if(u.includes('/exhibition_staff'))data=[{display_name:'増田',role:'staff',active:true}];else if(u.includes('/exhibition_orders'))data=${JSON.stringify(rows)};return new Response(JSON.stringify(data),{status:200,headers:{'Content-Type':'application/json'}})};`;

(async () => {
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch(fixtures.launchOptions());
  try {
    for (const width of [390, 820, 1440]) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      await page.setContent(fixtures.customerHtml(''), { waitUntil: 'domcontentloaded' });
      await page.waitForFunction(() => products.some(p => p.code === '1053'));
      await page.evaluate(image => { products.forEach(p => p.image = image); renderResults(); }, image);
      await page.screenshot({ path: path.join(output, `customer-${width}-empty.png`) });
      await page.fill('#searchInput', '1053');
      await page.click('[data-add="1053"]');
      await page.screenshot({ path: path.join(output, `customer-${width}.png`) });
      await page.selectOption('#langSelect','ja');
      await page.screenshot({ path: path.join(output, `customer-${width}-ja.png`) });
      const layout = await page.evaluate(() => {
        const box = id => { const r=document.getElementById(id).getBoundingClientRect(); return { top:r.top,bottom:r.bottom,height:r.height }; };
        return { viewport:innerWidth, overflow:document.documentElement.scrollWidth>innerWidth, keypad:box('keypadPanel'), cart:box('cartPanel'), search:box('searchCard'), product:document.querySelector('.product').getBoundingClientRect().bottom };
      });
      if (layout.overflow || (width <= 760 && layout.cart.bottom > layout.keypad.top + 1)) throw new Error('Customer layout overlap: '+JSON.stringify(layout));
      await page.click('#quickCheckout');
      await page.screenshot({ path: path.join(output, `customer-${width}-form.png`) });
      await page.close();
      const staff = await browser.newPage({ viewport: { width, height: 900 } });
      const logo='data:image/jpeg;base64,'+fs.readFileSync(path.join(ROOT,'assets','sun_nishimura_logo.jpg')).toString('base64');
      await staff.setContent(fixtures.staffHtml(staffMock).replaceAll('src="assets/sun_nishimura_logo.jpg"', `src="${logo}"`), { waitUntil: 'domcontentloaded' });
      await staff.fill('#email','staff@example.com'); await staff.fill('#password','password'); await staff.click('#loginButton');
      await staff.waitForSelector('[data-order-id]');
      await staff.screenshot({ path:path.join(output,`staff-${width}.png`) });
      await staff.locator('[data-order-id]').first().click();
      await staff.waitForSelector('#detailDialog[open]');
      await staff.screenshot({ path:path.join(output,`staff-${width}-detail.png`) });
      await staff.click('#detailTopClose'); await staff.click('#priceCheckButton');
      await staff.fill('#priceSearchInput','１０５３');
      await staff.waitForSelector('[data-price-code="1053"]');
      await staff.evaluate(image=>{const frame=document.querySelector('[data-price-code="1053"] .priceProductImage');const img=new Image();img.alt='1053 商品画像';img.src=image;frame.replaceChildren(img);},image);
      await staff.screenshot({ path:path.join(output,`staff-${width}-price.png`) });
      if (await staff.evaluate(() => document.documentElement.scrollWidth>innerWidth)) throw new Error('Staff page overflow');
      await staff.close();
      console.log(`UI_REVIEW_OK ${width}`);
    }
  } finally { await browser.close(); }
  console.log(output);
})().catch(e => { console.error(e); process.exit(1); });
