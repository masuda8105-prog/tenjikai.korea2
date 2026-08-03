(() => {
  'use strict';
  const config = window.ORDER_ONLINE_CONFIG || {};
  const SUPABASE_URL = String(config.supabaseUrl || '').replace(/\/$/, '');
  const ANON_KEY = String(config.anonKey || '');
  const SESSION_KEY = 'koreaExhibitionStaffSessionV2';
  const $ = (id) => document.getElementById(id);
  const state = { session: null, user: null, orders: [], current: null, realtimeClient: null, realtimeChannel: null, pollTimer: null, refreshTimer: null, soundEnabled: false, audioContext: null, knownIds: new Set(), firstLoad: true, activeTab: 'new' };

  function escapeHtml(value) { return String(value ?? '').replace(/[&<>'"]/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char])); }
  function formatMoney(value) { return `₩${Math.round(Number(value || 0)).toLocaleString('ko-KR')}`; }
  function itemName(item) { const value = item?.n; return Array.isArray(value) ? (value[0] || value[1] || item.c || '') : String(value || item?.c || ''); }
  function orderTotal(order) { const data = order.order_data || {}; return Number(data.total ?? (data.items || []).reduce((sum, item) => sum + Number(item.p || 0) * Number(item.q || 0), 0)); }
  function totalQty(order) { return (order.order_data?.items || []).reduce((sum, item) => sum + Number(item.q || 0), 0); }
  function relativeTime(iso) { const diff = Date.now() - new Date(iso).getTime(); if (!Number.isFinite(diff)) return ''; const sec = Math.max(0, Math.floor(diff / 1000)); if (sec < 60) return `${sec}秒前`; const min = Math.floor(sec / 60); if (min < 60) return `${min}分前`; const hour = Math.floor(min / 60); if (hour < 24) return `${hour}時間前`; return new Date(iso).toLocaleDateString('ja-JP'); }
  function statusLabel(status) { return ({new:'NEW',in_progress:'対応中',completed:'完了'})[status] || status; }
  function staffName() { const meta = state.user?.user_metadata || {}; return String(meta.full_name || meta.name || state.user?.email?.split('@')[0] || 'Staff'); }
  function showToast(message) { const el = $('toast'); el.textContent = message; el.classList.add('show'); clearTimeout(showToast.timer); showToast.timer = setTimeout(() => el.classList.remove('show'), 2400); }
  function setSync(mode, text) { $('syncDot').className = `dot${mode ? ` ${mode}` : ''}`; $('syncText').textContent = text; }

  function saveSession(session) { state.session = session; state.user = session?.user || null; if (session) localStorage.setItem(SESSION_KEY, JSON.stringify(session)); else localStorage.removeItem(SESSION_KEY); }
  function loadStoredSession() { try { const parsed = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null'); if (parsed?.access_token && parsed?.refresh_token) saveSession(parsed); } catch { localStorage.removeItem(SESSION_KEY); } }
  function tokenExpiredSoon() { if (!state.session) return true; const expiresAt = Number(state.session.expires_at || 0) * 1000; return !expiresAt || expiresAt - Date.now() < 90_000; }

  async function authRequest(grantType, body) {
    const response = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=${grantType}`, { method:'POST', headers:{apikey:ANON_KEY,'Content-Type':'application/json'}, body:JSON.stringify(body) });
    const json = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(json.error_description || json.msg || json.message || `AUTH_${response.status}`);
    const session = { ...json, expires_at: Math.floor(Date.now() / 1000) + Number(json.expires_in || 3600) };
    saveSession(session);
    return session;
  }
  async function ensureToken() { if (!state.session) throw new Error('LOGIN_REQUIRED'); if (!tokenExpiredSoon()) return state.session.access_token; const session = await authRequest('refresh_token', { refresh_token: state.session.refresh_token }); await startRealtime(); return session.access_token; }
  async function apiFetch(path, options = {}) { const token = await ensureToken(); const headers = { apikey:ANON_KEY, Authorization:`Bearer ${token}`, ...(options.headers || {}) }; const response = await fetch(`${SUPABASE_URL}${path}`, { ...options, headers }); if (response.status === 401) { saveSession(null); showLogin('ログインの有効期限が切れました。もう一度ログインしてください。'); throw new Error('SESSION_EXPIRED'); } return response; }

  async function signIn(email, password) { return authRequest('password', { email, password }); }
  async function signOut() { try { if (state.session) await fetch(`${SUPABASE_URL}/auth/v1/logout`, { method:'POST', headers:{apikey:ANON_KEY,Authorization:`Bearer ${state.session.access_token}`} }); } catch {} stopRealtime(); saveSession(null); state.orders = []; showLogin(''); }

  function showLogin(message = '') { $('loginView').classList.remove('hidden'); $('dashboardView').classList.add('hidden'); $('loginMessage').textContent = message; }
  function showDashboard() { $('loginView').classList.add('hidden'); $('dashboardView').classList.remove('hidden'); $('staffIdentity').innerHTML = `<b>${escapeHtml(staffName())}</b>${escapeHtml(state.user?.email || '')}`; }

  async function loadOrders({notify = false} = {}) {
    if (!state.session) return;
    setSync('', '更新中…');
    const now = encodeURIComponent(new Date().toISOString());
    const select = 'id,order_no,order_data,status,assigned_to,assigned_name,business_card_original_path,business_card_preview_path,expires_at,created_at,updated_at,printed_at,completed_at';
    const response = await apiFetch(`/rest/v1/exhibition_orders?select=${encodeURIComponent(select)}&expires_at=gt.${now}&order=created_at.desc&limit=500`, { headers:{Accept:'application/json'} });
    const json = await response.json().catch(() => []);
    if (!response.ok) throw new Error(json.message || json.error || `ORDERS_${response.status}`);
    const incomingIds = new Set(json.map((order) => order.id));
    const newRows = state.firstLoad ? [] : json.filter((order) => !state.knownIds.has(order.id));
    state.orders = json;
    state.knownIds = incomingIds;
    state.firstLoad = false;
    render();
    setSync(state.realtimeChannel ? 'live' : '', state.realtimeChannel ? 'リアルタイム接続中' : '10秒ごとに自動更新');
    if (notify && newRows.length) notifyNewOrder(newRows[0]);
  }

  async function updateOrder(id, patch) {
    const response = await apiFetch(`/rest/v1/exhibition_orders?id=eq.${encodeURIComponent(id)}`, { method:'PATCH', headers:{'Content-Type':'application/json',Prefer:'return=representation'}, body:JSON.stringify(patch) });
    const json = await response.json().catch(() => []);
    if (!response.ok) throw new Error(json.message || json.error || `UPDATE_${response.status}`);
    await loadOrders();
    const updated = state.orders.find((row) => row.id === id);
    if (updated) { state.current = updated; await renderDetail(updated); }
    return updated;
  }

  function filteredOrders(status) {
    const query = $('searchInput').value.trim().toLowerCase();
    return state.orders.filter((order) => {
      if (order.status !== status) return false;
      if (!query) return true;
      const data = order.order_data || {};
      const searchable = [order.order_no, data.customerCompany, data.customerName, data.customerPhone, data.notes, order.assigned_name, ...(data.items || []).flatMap((item) => [item.c, itemName(item)])].join(' ').toLowerCase();
      return searchable.includes(query);
    });
  }

  function orderCard(order) {
    const data = order.order_data || {};
    return `<article class="orderCard ${escapeHtml(order.status)}" data-order-id="${escapeHtml(order.id)}"><div class="cardTop"><div class="orderNo">${escapeHtml(order.order_no)}</div><span class="statusBadge ${escapeHtml(order.status)}">${escapeHtml(statusLabel(order.status))}</span></div><div class="company">${escapeHtml(data.customerCompany || '-')}</div><div class="person">${escapeHtml(data.customerName || '')}${data.customerPhone ? ` / ${escapeHtml(data.customerPhone)}` : ''}</div>${order.assigned_name ? `<div class="assigned">担当：${escapeHtml(order.assigned_name)}</div>` : ''}<div class="cardMeta"><div class="time">${escapeHtml(relativeTime(order.created_at))}<br>${totalQty(order)}点</div><div class="amount">${formatMoney(orderTotal(order))}</div></div></article>`;
  }

  function renderList(status) { const rows = filteredOrders(status); const list = $(`list-${status}`); list.innerHTML = rows.length ? rows.map(orderCard).join('') : '<div class="empty">該当する注文はありません。</div>'; }
  function render() {
    $('newCount').textContent = state.orders.filter((o) => o.status === 'new').length;
    $('progressCount').textContent = state.orders.filter((o) => o.status === 'in_progress').length;
    $('doneCount').textContent = state.orders.filter((o) => o.status === 'completed').length;
    ['new','in_progress','completed'].forEach(renderList);
    document.querySelectorAll('[data-order-id]').forEach((card) => card.addEventListener('click', () => openDetail(card.dataset.orderId)));
  }

  async function createSignedUrl(path) {
    if (!path) return '';
    const encodedPath = String(path).split('/').map(encodeURIComponent).join('/');
    const response = await apiFetch(`/storage/v1/object/sign/business-cards/${encodedPath}`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({expiresIn:3600}) });
    const json = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(json.message || json.error || `SIGN_${response.status}`);
    const signed = json.signedURL || json.signedUrl || '';
    if (!signed) return '';
    return signed.startsWith('http') ? signed : `${SUPABASE_URL}/storage/v1${signed.startsWith('/') ? '' : '/'}${signed}`;
  }

  async function openDetail(id) { const order = state.orders.find((row) => row.id === id); if (!order) return; state.current = order; await renderDetail(order); $('detailDialog').showModal(); }
  async function renderDetail(order) {
    const data = order.order_data || {};
    $('detailTitle').textContent = `${order.order_no}　${data.customerCompany || ''}`;
    let previewUrl = '', originalUrl = '';
    try { [previewUrl, originalUrl] = await Promise.all([createSignedUrl(order.business_card_preview_path), createSignedUrl(order.business_card_original_path)]); } catch (error) { console.warn(error); }
    const items = data.items || [];
    $('detailBody').innerHTML = `<div class="detailGrid"><section class="infoPanel"><div class="infoGrid"><div class="infoBox"><div class="label">受付番号</div><div class="value">${escapeHtml(order.order_no)}</div></div><div class="infoBox"><div class="label">状態</div><div class="value">${escapeHtml(statusLabel(order.status))}</div></div><div class="infoBox"><div class="label">会社名</div><div class="value">${escapeHtml(data.customerCompany || '-')}</div></div><div class="infoBox"><div class="label">氏名</div><div class="value">${escapeHtml(data.customerName || '-')}</div></div><div class="infoBox"><div class="label">電話番号</div><div class="value">${escapeHtml(data.customerPhone || '-')}</div></div><div class="infoBox"><div class="label">担当</div><div class="value">${escapeHtml(order.assigned_name || '-')}</div></div><div class="infoBox"><div class="label">受付日時</div><div class="value">${escapeHtml(new Date(order.created_at).toLocaleString('ja-JP'))}</div></div><div class="infoBox"><div class="label">印刷</div><div class="value">${order.printed_at ? escapeHtml(new Date(order.printed_at).toLocaleString('ja-JP')) : '未印刷'}</div></div></div>${data.notes ? `<div class="notes"><b>備考</b><br>${escapeHtml(data.notes)}</div>` : ''}<div class="businessCard"><h3>名刺</h3>${previewUrl || originalUrl ? `<a href="${escapeHtml(originalUrl || previewUrl)}" target="_blank" rel="noopener"><img src="${escapeHtml(previewUrl || originalUrl)}" alt="名刺画像"></a>` : '<div class="noCard">名刺画像なし</div>'}</div></section><section class="itemsPanel"><table class="itemsTable"><thead><tr><th>品番</th><th>商品名</th><th class="num">数量</th><th class="num">単価</th><th class="num">小計</th></tr></thead><tbody>${items.map((item) => `<tr><td><b>${escapeHtml(item.c)}</b></td><td>${escapeHtml(itemName(item))}</td><td class="num">${escapeHtml(item.q)}</td><td class="num">${formatMoney(item.p)}</td><td class="num"><b>${formatMoney(Number(item.p || 0) * Number(item.q || 0))}</b></td></tr>`).join('')}</tbody></table><div class="detailTotal"><span>合計</span><span>${formatMoney(orderTotal(order))}</span></div></section></div>`;
    $('startButton').textContent = order.status === 'completed' ? '対応中へ戻す' : order.status === 'in_progress' ? '担当を引き継ぐ' : '対応開始';
    $('startButton').classList.toggle('hidden', false);
    $('completeButton').classList.toggle('hidden', order.status === 'completed');
  }

  async function startHandling() { if (!state.current) return; const targetStatus = state.current.status === 'completed' ? 'in_progress' : 'in_progress'; await updateOrder(state.current.id, { status:targetStatus, assigned_to:state.user.id, assigned_name:staffName() }); showToast(`${state.current.order_no} を対応中にしました。`); }
  async function completeOrder() { if (!state.current) return; await updateOrder(state.current.id, { status:'completed', assigned_to:state.user.id, assigned_name:staffName() }); showToast(`${state.current.order_no} を完了にしました。`); }

  function buildPrint(order, cardUrl = '') {
    const data = order.order_data || {}; const items = data.items || [];
    return `<div class="printHead"><img src="assets/sun_nishimura_logo.jpg" alt="SAN NISHIMURA"><div class="printTitle"><h1>韓国展示会 仮注文書</h1><div>Korea Exhibition Provisional Order</div><b>${escapeHtml(order.order_no)}</b></div></div><div class="printMeta"><div class="printBox"><b>会社名</b>${escapeHtml(data.customerCompany || '-')}</div><div class="printBox"><b>氏名</b>${escapeHtml(data.customerName || '-')}</div><div class="printBox"><b>電話番号</b>${escapeHtml(data.customerPhone || '-')}</div><div class="printBox"><b>受付日時</b>${escapeHtml(new Date(order.created_at).toLocaleString('ja-JP'))}</div><div class="printBox"><b>担当</b>${escapeHtml(order.assigned_name || staffName())}</div><div class="printBox"><b>状態</b>${escapeHtml(statusLabel(order.status))}</div></div><table class="printTable"><thead><tr><th>品番</th><th>商品名</th><th class="num">数量</th><th class="num">単価</th><th class="num">小計</th></tr></thead><tbody>${items.map((item) => `<tr><td>${escapeHtml(item.c)}</td><td>${escapeHtml(itemName(item))}</td><td class="num">${escapeHtml(item.q)}</td><td class="num">${formatMoney(item.p)}</td><td class="num">${formatMoney(Number(item.p || 0) * Number(item.q || 0))}</td></tr>`).join('')}</tbody></table><div class="printTotal">合計 ${formatMoney(orderTotal(order))}</div>${data.notes ? `<div class="notes"><b>備考</b><br>${escapeHtml(data.notes)}</div>` : ''}${cardUrl ? `<img class="printCard" src="${escapeHtml(cardUrl)}" alt="名刺">` : ''}<div class="printFooter">SAN NISHIMURA CO., LTD. / Korea Distributor: KY-S Corporation.</div>`;
  }
  async function printCurrent() { if (!state.current) return; let card = ''; try { card = await createSignedUrl(state.current.business_card_preview_path || state.current.business_card_original_path); } catch {} $('printArea').innerHTML = buildPrint(state.current, card); await updateOrder(state.current.id, { printed_at:new Date().toISOString() }); setTimeout(() => window.print(), 100); }

  function beep() { if (!state.soundEnabled) return; try { const Ctx = window.AudioContext || window.webkitAudioContext; state.audioContext ||= new Ctx(); const osc = state.audioContext.createOscillator(); const gain = state.audioContext.createGain(); osc.frequency.value = 880; gain.gain.setValueAtTime(.0001, state.audioContext.currentTime); gain.gain.exponentialRampToValueAtTime(.18, state.audioContext.currentTime + .02); gain.gain.exponentialRampToValueAtTime(.0001, state.audioContext.currentTime + .28); osc.connect(gain).connect(state.audioContext.destination); osc.start(); osc.stop(state.audioContext.currentTime + .3); } catch {} }
  function notifyNewOrder(order) { beep(); showToast(`新しい注文 ${order.order_no}`); document.title = `🔴 ${order.order_no} 新規注文`; setTimeout(() => { document.title = '韓国展示会 スタッフ注文管理 | SAN NISHIMURA'; }, 6000); const card = document.querySelector(`[data-order-id="${CSS.escape(order.id)}"]`); card?.classList.add('newFlash'); }

  function stopRealtime() { if (state.realtimeChannel && state.realtimeClient) state.realtimeClient.removeChannel(state.realtimeChannel).catch(() => {}); state.realtimeChannel = null; state.realtimeClient = null; clearInterval(state.pollTimer); clearTimeout(state.refreshTimer); }
  async function startRealtime() {
    stopRealtime();
    state.pollTimer = setInterval(() => loadOrders().catch((error) => { console.warn(error); setSync('error', '自動更新エラー'); }), 10_000);
    try {
      const module = await import('https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.105.4/+esm');
      const client = module.createClient(SUPABASE_URL, ANON_KEY, { auth:{persistSession:false,autoRefreshToken:false,detectSessionInUrl:false} });
      client.realtime.setAuth(state.session.access_token);
      const channel = client.channel('korea-exhibition-orders').on('postgres_changes', {event:'*',schema:'public',table:'exhibition_orders'}, (payload) => loadOrders({notify:payload.eventType === 'INSERT'}).catch(console.error)).subscribe((status) => {
        if (status === 'SUBSCRIBED') setSync('live', 'リアルタイム接続中');
        else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') setSync('error', '自動更新へ切替');
      });
      state.realtimeClient = client; state.realtimeChannel = channel;
    } catch (error) { console.warn('Realtime unavailable, polling fallback enabled', error); setSync('', '10秒ごとに自動更新'); }
  }

  function attachEvents() {
    $('loginForm').addEventListener('submit', async (event) => { event.preventDefault(); const button = $('loginButton'); button.disabled = true; $('loginMessage').textContent = 'ログイン中…'; try { await signIn($('email').value.trim(), $('password').value); $('password').value = ''; showDashboard(); await loadOrders(); await startRealtime(); } catch (error) { $('loginMessage').textContent = error.message.includes('Invalid login') ? 'メールアドレスまたはパスワードが違います。' : `ログインできませんでした：${error.message}`; } finally { button.disabled = false; } });
    $('logoutButton').addEventListener('click', signOut);
    $('refreshButton').addEventListener('click', () => loadOrders().catch((error) => showToast(`更新失敗：${error.message}`)));
    $('searchInput').addEventListener('input', render);
    $('soundButton').addEventListener('click', async () => { state.soundEnabled = !state.soundEnabled; if (state.soundEnabled) { beep(); $('soundButton').textContent = '🔔 通知音ON'; } else $('soundButton').textContent = '🔕 通知音OFF'; });
    document.querySelectorAll('[data-tab]').forEach((button) => button.addEventListener('click', () => { state.activeTab = button.dataset.tab; document.querySelectorAll('[data-tab]').forEach((b) => b.classList.toggle('active', b === button)); document.querySelectorAll('.statusColumn').forEach((column) => column.classList.toggle('mobileHidden', column.id !== `column-${state.activeTab}`)); }));
    $('detailTopClose').addEventListener('click', () => $('detailDialog').close()); $('closeDetail').addEventListener('click', () => $('detailDialog').close());
    $('startButton').addEventListener('click', () => startHandling().catch((error) => showToast(`更新失敗：${error.message}`))); $('completeButton').addEventListener('click', () => completeOrder().catch((error) => showToast(`更新失敗：${error.message}`))); $('printButton').addEventListener('click', () => printCurrent().catch((error) => showToast(`印刷準備失敗：${error.message}`)));
  }

  async function init() {
    attachEvents();
    if (!SUPABASE_URL || !ANON_KEY || !config.enabled) { showLogin('Supabase本番設定が未完了です。online-config.jsを確認してください。'); return; }
    loadStoredSession();
    if (!state.session) { showLogin(''); return; }
    try { await ensureToken(); showDashboard(); await loadOrders(); await startRealtime(); } catch (error) { console.warn(error); saveSession(null); showLogin('ログインの有効期限が切れました。'); }
  }
  window.addEventListener('DOMContentLoaded', init);
})();
