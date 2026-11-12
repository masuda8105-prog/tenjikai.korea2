const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { stripTypeScriptTypes } = require('node:module');
const { join } = require('node:path');

const origin = 'https://exhibition.test';
const userId = '11111111-1111-4111-8111-111111111111';
const rows = [];
const uploadedPaths = [];
const env = {
  SUPABASE_URL: 'https://db.test',
  SUPABASE_SERVICE_ROLE_KEY: 'mock-server-key',
  SUPABASE_ANON_KEY: 'mock-public-key',
  ALLOWED_ORIGINS: origin,
};

const db = {
  storage: {
    from: () => ({
      upload: async path => { uploadedPaths.push(path); return {}; },
    }),
  },
  auth: {
    getUser: async jwt => ({ data: { user: ['staff', 'non-staff'].includes(jwt) ? { id: jwt === 'staff' ? userId : 'other' } : null } }),
  },
  rpc: async name => ({ data: name === 'next_korea_staff_order_no' ? 'K-0001' : 'K260803-001' }),
  from(table) {
    const filters = [];
    const query = {
      select: () => query,
      eq: (key, value) => { filters.push(row => row[key] === value); return query; },
      neq: (key, value) => { filters.push(row => row[key] !== value); return query; },
      gt: (key, value) => { filters.push(row => row[key] > value); return query; },
      async maybeSingle() {
        const source = table === 'exhibition_staff' ? [{ user_id: userId, active: true, display_name: 'Staff' }] : rows;
        return { data: source.find(row => filters.every(filter => filter(row))) ?? null };
      },
      async insert(row) {
        rows.push({ ...row, created_at: row.updated_at });
        return {};
      },
    };
    return query;
  },
};

let handle;
const source = readFileSync(join(__dirname, '../supabase/functions/exhibition-order/index.ts'), 'utf8').replace(/^import .*;\r?\n/, '');
new Function('createClient', 'Deno', stripTypeScriptTypes(source))(() => db, {
  env: { get: key => env[key] },
  serve: handler => { handle = handler; },
});

function request(query, { jwt, body } = {}) {
  const headers = { Origin: origin, apikey: env.SUPABASE_ANON_KEY };
  if (jwt) headers.Authorization = `Bearer ${jwt}`;
  return handle(new Request(`${origin}/exhibition-order?${query}`, {
    method: body ? 'POST' : 'GET',
    headers,
    body,
  }));
}

function createBody() {
  const form = new FormData();
  form.set('order', JSON.stringify({
    clientSubmissionId: '22222222-2222-4222-8222-222222222222',
    customerPhone: '010-private',
    total: 200,
    items: [{ c: '1053', n: ['ヤットコ', '플라이어'], q: 2, p: 100, img: 'private-test' }],
  }));
  form.set('businessCardOriginal', new File(['test image'], 'card.jpg', { type: 'image/jpeg' }));
  form.append('additionalBusinessCards', new File(['test image'], 'card-2.jpg', { type: 'image/jpeg' }));
  return form;
}

(async () => {
  assert.equal((await request('', { body: createBody() })).status, 403);
  assert.equal((await request('staffIntake=1', { body: createBody() })).status, 401);
  assert.equal((await request('staffIntake=1', { jwt: 'non-staff', body: createBody() })).status, 403);
  const created = await request('staffIntake=1', { jwt: 'staff', body: createBody() });
  assert.equal(created.status, 201);
  const result = await created.json();
  assert.equal(result.orderNo, 'K-0001');
  assert.equal(result.status, 'confirmed');
  assert.equal(rows[0].assigned_to, userId);
  assert.equal(rows[0].order_data._additionalBusinessCardPaths.length, 1);
  assert.match(rows[0].order_data._additionalBusinessCardPaths[0], /\/business-card-2\.jpg$/);
  assert.equal(result.token, undefined);
  const duplicate = await (await request('staffIntake=1', { jwt: 'staff', body: createBody() })).json();
  assert.equal(duplicate.receipt, result.receipt);
  assert.equal(duplicate.duplicatePrevented, true);
  assert.equal(rows.length, 1);
  assert.equal(uploadedPaths.length, 2);

  assert.equal((await request(`issueReceiptFor=${result.id}`, { jwt: 'non-staff' })).status, 403);
  assert.equal((await (await request(`issueReceiptFor=${result.id}`, { jwt: 'staff' })).json()).receipt, result.receipt);
  const publicResult = await (await request(`receipt=${result.receipt}`)).json();
  assert.deepEqual(Object.keys(publicResult).sort(), ['createdAt', 'items', 'orderNo']);
  assert.deepEqual(Object.keys(publicResult.items[0]).sort(), ['c', 'n', 'p', 'q']);
  assert.equal((await request(`receipt=${result.id}.${'0'.repeat(64)}`)).status, 404);
  assert.equal((await request(`token=${result.receipt}`)).status, 400);
  assert.equal((await request(`token=${rows[0].public_token}`)).status, 404);
  rows[0].status = 'deleted';
  assert.equal((await request(`receipt=${result.receipt}`)).status, 404);
  console.log('EXHIBITION_ORDER_EDGE_PASS');
})().catch(error => { console.error(error); process.exitCode = 1; });
