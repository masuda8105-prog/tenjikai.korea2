(() => {
  'use strict';

  const config = window.ORDER_ONLINE_CONFIG || {};
  const SUPABASE_URL = String(config.supabaseUrl || '').replace(/\/$/, '');
  const ANON_KEY = String(config.anonKey || '');
  const SESSION_KEY = 'koreaExhibitionStaffSessionV3';
  const $ = (id) => document.getElementById(id);
  const state = {
    session: null,
    user: null,
    staff: null,
    orders: [],
    current: null,
    editItems: [],
    productMaster: null,
    realtimeClient: null,
    realtimeChannel: null,
    pollTimer: null,
    soundEnabled: false,
    audioContext: null,
    knownIds: new Set(),
    firstLoad: true,
    activeTab: 'open',
    loadVersion: 0,
    orderViewSignature: null,
    workflowReady: true,
    batch: null,
    editDirty: false,
    editRefreshPending: false,
    customerQrUrl: '',
  };

  const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  }[char]));
  const formatMoney = (value) => `₩${Math.round(Number(value || 0)).toLocaleString('ko-KR')}`;
  const itemName = (item) => {
    if (!Array.isArray(item?.n)) return String(item?.n || item?.c || '');
    const names = item.n.slice(0, 2).map((name) => String(name || '').trim()).filter(Boolean);
    return [...new Set(names)].join('\n') || String(item?.c || '');
  };
  const detailItemImage = (item) => {
    const src = String(item?.img || '').trim();
    if (!src) return '<div class="detailProductThumb missing" aria-label="商品画像なし"></div>';
    return `<div class="detailProductThumb"><img src="${escapeHtml(src)}" alt="${escapeHtml(item?.c || '商品')}" loading="lazy" onerror="this.parentElement.classList.add('missing');this.remove()"></div>`;
  };
  const orderTotal = (order) => Number(order?.order_data?.total ?? (order?.order_data?.items || []).reduce((sum, item) => sum + Number(item.p || 0) * Number(item.q || 0), 0));
  const totalQty = (order) => (order?.order_data?.items || []).reduce((sum, item) => sum + Number(item.q || 0), 0);
  const isDeleted = (order) => order?.status === 'deleted';
  const groupForStatus = (status) => {
    if (status === 'new') return 'open';
    if (status === 'in_progress') return 'progress';
    if (status === 'completed' || status === 'resend_required') return 'completed';
    if (status === 'sent') return 'sent';
    return 'open';
  };
  const statusLabel = (status) => ({
    new: '確認待ち', in_progress: '確認中', completed: '注文確定', sent: '送付済み',
    resend_required: '修正版・再送必要', deleted: '削除済み',
  }[status] || '確認待ち');
  const staffName = () => String(state.staff?.display_name || state.user?.user_metadata?.full_name || state.user?.email?.split('@')[0] || 'Staff');
  const staffRole = () => String(state.staff?.role || 'staff');
  const eventIdOf = (order) => String(order?.event_id || order?.order_data?.eventId || config.eventId || 'korea-exhibition');
  const eventNameOf = (order) => String(order?.event_name || order?.order_data?.eventName || config.eventName || '韓国展示会');
  const dateOf = (order) => String(order?.event_date || order?.order_data?.eventDate || new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Seoul' }).format(new Date(order?.created_at || Date.now())));

  function relativeTime(iso) {
    const diff = Date.now() - new Date(iso).getTime();
    if (!Number.isFinite(diff)) return '';
    const sec = Math.max(0, Math.floor(diff / 1000));
    if (sec < 60) return `${sec}秒前`;
    const min = Math.floor(sec / 60);
    if (min < 60) return `${min}分前`;
    const hour = Math.floor(min / 60);
    if (hour < 24) return `${hour}時間前`;
    return new Date(iso).toLocaleDateString('ja-JP');
  }

  function showToast(message, duration = 3000) {
    const el = $('toast');
    el.textContent = message;
    el.classList.add('show');
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => el.classList.remove('show'), duration);
  }

  function setSync(mode, text) {
    $('syncDot').className = `dot${mode ? ` ${mode}` : ''}`;
    $('syncText').textContent = text;
  }

  function saveSession(session) {
    state.session = session;
    state.user = session?.user || null;
    if (session) localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    else localStorage.removeItem(SESSION_KEY);
  }

  function loadStoredSession() {
    try {
      const parsed = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null');
      if (parsed?.access_token && parsed?.refresh_token) saveSession(parsed);
    } catch {
      localStorage.removeItem(SESSION_KEY);
    }
  }

  function tokenExpiredSoon() {
    if (!state.session) return true;
    const expiresAt = Number(state.session.expires_at || 0) * 1000;
    return !expiresAt || expiresAt - Date.now() < 90000;
  }

  async function fetchWithTimeout(url, options = {}, timeoutMs = 30000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      return await fetch(url, { ...options, signal: options.signal || controller.signal });
    } finally {
      clearTimeout(timer);
    }
  }

  async function authRequest(grantType, body) {
    const response = await fetchWithTimeout(`${SUPABASE_URL}/auth/v1/token?grant_type=${grantType}`, {
      method: 'POST',
      headers: { apikey: ANON_KEY, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const json = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(json.error_description || json.msg || json.message || `AUTH_${response.status}`);
    const session = { ...json, expires_at: Math.floor(Date.now() / 1000) + Number(json.expires_in || 3600) };
    saveSession(session);
    return session;
  }

  async function ensureToken() {
    if (!state.session) throw new Error('LOGIN_REQUIRED');
    if (!tokenExpiredSoon()) return state.session.access_token;
    const session = await authRequest('refresh_token', { refresh_token: state.session.refresh_token });
    await startRealtime();
    return session.access_token;
  }

  async function apiFetch(path, options = {}) {
    const token = await ensureToken();
    const headers = { apikey: ANON_KEY, Authorization: `Bearer ${token}`, ...(options.headers || {}) };
    const response = await fetchWithTimeout(`${SUPABASE_URL}${path}`, { ...options, headers }, options.timeoutMs || 30000);
    if (response.status === 401) {
      saveSession(null);
      state.staff = null;
      showLogin('ログインの有効期限が切れました。もう一度ログインしてください。');
      throw new Error('SESSION_EXPIRED');
    }
    return response;
  }

  async function apiJson(path, options = {}) {
    const response = await apiFetch(path, options);
    const json = await response.json().catch(() => null);
    if (!response.ok) throw new Error(json?.message || json?.error || `API_${response.status}`);
    return json;
  }

  async function rpc(name, body) {
    return apiJson(`/rest/v1/rpc/${encodeURIComponent(name)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  }

  async function signIn(email, password) {
    return authRequest('password', { email, password });
  }

  async function signOut() {
    try {
      if (state.session) await fetchWithTimeout(`${SUPABASE_URL}/auth/v1/logout`, {
        method: 'POST', headers: { apikey: ANON_KEY, Authorization: `Bearer ${state.session.access_token}` },
      }, 10000);
    } catch {}
    stopRealtime();
    saveSession(null);
    state.staff = null;
    state.orders = [];
    showLogin('');
  }

  function showLogin(message = '') {
    $('loginView').classList.remove('hidden');
    $('dashboardView').classList.add('hidden');
    $('loginMessage').textContent = message;
  }

  function showDashboard() {
    $('loginView').classList.add('hidden');
    $('dashboardView').classList.remove('hidden');
    $('staffIdentity').innerHTML = `<b>${escapeHtml(staffName())}</b>${escapeHtml(state.user?.email || '')} / ${staffRole() === 'admin' ? '管理者' : 'スタッフ'}`;
    $('utilityIdentity').innerHTML = `<b>${escapeHtml(staffName())}</b><br>${escapeHtml(state.user?.email || '')}`;
  }

  async function loadStaffProfile() {
    const id = state.user?.id;
    if (!id) throw new Error('LOGIN_REQUIRED');
    let rows;
    try {
      rows = await apiJson(`/rest/v1/exhibition_staff?select=display_name,role,active&user_id=eq.${encodeURIComponent(id)}&active=is.true&limit=1`, { headers: { Accept: 'application/json' } });
    } catch (error) {
      if (/role|column/i.test(error.message)) {
        rows = await apiJson(`/rest/v1/exhibition_staff?select=display_name,active&user_id=eq.${encodeURIComponent(id)}&active=is.true&limit=1`, { headers: { Accept: 'application/json' } });
      } else throw error;
    }
    if (!Array.isArray(rows) || !rows[0]) throw new Error('このアカウントにはスタッフ権限がありません。管理者へ連絡してください。');
    state.staff = { role: 'staff', ...rows[0] };
  }

  const legacySelect = 'id,public_token,order_no,order_data,status,assigned_to,assigned_name,business_card_original_path,business_card_preview_path,expires_at,created_at,updated_at,printed_at,completed_at';
  const workflowSelect = `${legacySelect},event_id,event_name,event_date,event_day,updated_by,updated_by_name,revision_count,revision_reason,requires_resend,sent_at,sent_by,sent_by_name,batch_id,pending_batch_id,deleted_at,deleted_by,deleted_by_name,delete_reason,status_before_delete`;

  async function fetchOrders(select) {
    const now = encodeURIComponent(new Date().toISOString());
    return apiJson(`/rest/v1/exhibition_orders?select=${encodeURIComponent(select)}&expires_at=gt.${now}&order=created_at.desc&limit=1000`, { headers: { Accept: 'application/json' } });
  }

  function ordersSnapshotSignature(orders) {
    return orders.map((order) => [
      order.id, order.updated_at, order.status, order.deleted_at,
      order.assigned_to, order.assigned_name, order.revision_count,
      order.resend_required, order.order_no,
    ].map((value) => String(value ?? '')).join(':')).join('|');
  }

  async function loadOrders({ notify = false, forceDetail = false, silent = false } = {}) {
    if (!state.session) return;
    const version = ++state.loadVersion;
    if (!silent) setSync('', '更新中…');
    let json;
    try {
      json = await fetchOrders(workflowSelect);
      state.workflowReady = true;
    } catch (error) {
      if (!/column|schema cache|42703|PGRST204/i.test(error.message)) throw error;
      json = await fetchOrders(legacySelect);
      state.workflowReady = false;
    }
    if (version !== state.loadVersion) return;
    const incomingIds = new Set(json.map((order) => order.id));
    const newRows = state.firstLoad ? [] : json.filter((order) => !state.knownIds.has(order.id));
    const nextViewSignature = ordersSnapshotSignature(json);
    const viewChanged = nextViewSignature !== state.orderViewSignature;
    state.orders = json;
    state.knownIds = incomingIds;
    state.firstLoad = false;
    if (viewChanged) {
      const scrollPosition = { left: window.scrollX, top: window.scrollY };
      state.orderViewSignature = nextViewSignature;
      populateFilters();
      render();
      window.scrollTo(scrollPosition);
    }
    if (state.current) {
      const fresh = state.orders.find((row) => row.id === state.current.id);
      if (fresh && $('detailDialog').open) {
        const detailChanged = fresh.updated_at !== state.current.updated_at || fresh.status !== state.current.status;
        if (state.editDirty && !forceDetail) {
          if (detailChanged) {
            state.editRefreshPending = true;
            setEditProtection('新しい更新を受信しました。入力中の内容は保護しています。保存時に他スタッフの更新との競合を確認します。', 'pending');
          } else {
            setEditProtection('入力中の内容を保護しています。自動更新が入っても、この画面の入力は消えません。', 'dirty');
          }
        } else if (forceDetail || detailChanged) {
          state.current = fresh;
          await renderDetail(fresh);
        } else {
          state.current = fresh;
        }
      }
    }
    if (!state.workflowReady) setSync('error', 'DB更新が必要です');
    else if (state.editDirty && state.editRefreshPending) setSync('live', '編集中・入力を保護中');
    else setSync(state.realtimeChannel ? 'live' : '', state.realtimeChannel ? 'リアルタイム接続中' : '10秒ごとに自動更新');
    if (notify && newRows.length) notifyNewOrder(newRows[0]);
  }

  async function updateOrder(order, patch) {
    const expected = order.updated_at;
    const lock = expected ? `&updated_at=eq.${encodeURIComponent(expected)}` : '';
    const response = await apiFetch(`/rest/v1/exhibition_orders?id=eq.${encodeURIComponent(order.id)}${lock}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', Prefer: 'return=representation' },
      body: JSON.stringify(patch),
    });
    const json = await response.json().catch(() => []);
    if (!response.ok) throw new Error(json.message || json.error || `UPDATE_${response.status}`);
    if (!Array.isArray(json) || json.length !== 1) throw new Error('CONFLICT');
    state.editDirty = false;
    state.editRefreshPending = false;
    await loadOrders({ forceDetail: true });
    const updated = state.orders.find((row) => row.id === order.id);
    if (updated) state.current = updated;
    return updated;
  }

  async function logActivity(order, action, details = {}) {
    try {
      await apiJson('/rest/v1/order_activity_logs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Prefer: 'return=minimal' },
        body: JSON.stringify({ order_id: order?.id || null, event_id: eventIdOf(order), action, performed_by: state.user.id, performed_by_name: staffName(), details }),
      });
    } catch (error) {
      console.warn('activity log unavailable', error);
    }
  }

  function humanError(error) {
    const message = String(error?.message || error || '不明なエラー');
    if (message === 'CONFLICT') return '別のスタッフがこの注文を更新しました。最新内容を読み込み直してください。';
    if (/AbortError|Failed to fetch|NetworkError/i.test(`${error?.name || ''} ${message}`)) return '通信できませんでした。入力内容は画面に残っています。接続を確認して再試行してください。';
    if (/check constraint|status/i.test(message)) return 'DBのワークフローマイグレーションが未適用です。Supabase設定手順を確認してください。';
    if (/permission|privilege|row-level|policy/i.test(message)) return 'この操作の権限がありません。スタッフ登録とRLS設定を確認してください。';
    return message;
  }

  async function withBusy(buttonIds, task) {
    const buttons = buttonIds.map($).filter(Boolean);
    if (buttons.some((button) => button.disabled)) return;
    buttons.forEach((button) => { button.disabled = true; button.setAttribute('aria-busy', 'true'); });
    try {
      return await task();
    } finally {
      buttons.forEach((button) => { button.disabled = false; button.removeAttribute('aria-busy'); });
    }
  }

  function populateFilters() {
    const currentEvent = $('eventFilter').value;
    const currentDate = $('dateFilter').value;
    const events = [...new Map(state.orders.filter((o) => !isDeleted(o)).map((o) => [eventIdOf(o), eventNameOf(o)])).entries()].sort((a, b) => a[1].localeCompare(b[1], 'ja'));
    $('eventFilter').innerHTML = '<option value="all">すべての展示会</option>' + events.map(([id, name]) => `<option value="${escapeHtml(id)}">${escapeHtml(name)}</option>`).join('');
    if ([...$('eventFilter').options].some((option) => option.value === currentEvent)) $('eventFilter').value = currentEvent;
    const eventFilter = $('eventFilter').value;
    const dates = [...new Set(state.orders.filter((o) => !isDeleted(o) && (eventFilter === 'all' || eventIdOf(o) === eventFilter)).map(dateOf))].sort();
    $('dateFilter').innerHTML = '<option value="all">すべての日付</option>' + dates.map((date, index) => `<option value="${escapeHtml(date)}">${index + 1}日目　${escapeHtml(new Date(`${date}T00:00:00`).toLocaleDateString('ja-JP'))}</option>`).join('');
    if ([...$('dateFilter').options].some((option) => option.value === currentDate)) $('dateFilter').value = currentDate;
  }

  function filteredBase({ includeDeleted = false } = {}) {
    const query = $('searchInput').value.trim().toLowerCase();
    const eventFilter = $('eventFilter').value;
    const dateFilter = $('dateFilter').value;
    return state.orders.filter((order) => {
      if (!includeDeleted && isDeleted(order)) return false;
      if (includeDeleted && !isDeleted(order)) return false;
      if (eventFilter !== 'all' && eventIdOf(order) !== eventFilter) return false;
      if (dateFilter !== 'all' && dateOf(order) !== dateFilter) return false;
      if (!query) return true;
      const data = order.order_data || {};
      const searchable = [order.order_no, data.customerCompany, data.customerName, data.customerPhone, data.shippingAddress, data.notes, order.assigned_name, eventNameOf(order), dateOf(order), ...(data.items || []).flatMap((item) => [item.c, itemName(item)])].join(' ').toLowerCase();
      return searchable.includes(query);
    });
  }

  function filteredOrders(group) {
    return filteredBase().filter((order) => groupForStatus(order.status) === group);
  }

  function orderCard(order) {
    const data = order.order_data || {};
    const klass = order.status === 'in_progress' ? 'progress' : order.status;
    const revised = order.status === 'resend_required' ? '<div class="eventMeta">⚠ 修正理由あり・再送が必要</div>' : '';
    return `<article class="orderCard ${escapeHtml(klass)}" data-order-id="${escapeHtml(order.id)}" tabindex="0" role="button" aria-label="${escapeHtml(order.order_no)} を開く"><div class="cardTop"><div class="orderNo">${escapeHtml(order.order_no)}</div><span class="statusBadge ${escapeHtml(klass)}">${statusLabel(order.status)}</span></div><div class="company">${escapeHtml(data.customerCompany || '-')}</div><div class="person">${escapeHtml(data.customerName || '')}${data.customerPhone ? ` / ${escapeHtml(data.customerPhone)}` : ''}</div><div class="eventMeta">${escapeHtml(eventNameOf(order))} / ${escapeHtml(dateOf(order))}</div>${revised}${order.assigned_name ? `<div class="assigned">最終担当：${escapeHtml(order.assigned_name)}</div>` : ''}<div class="cardMeta"><div class="time">${escapeHtml(relativeTime(order.created_at))}<br>${totalQty(order)}点</div><div class="amount">${formatMoney(orderTotal(order))}</div></div></article>`;
  }

  function confirmedOrderRow(order) {
    const data = order.order_data || {};
    const time = new Date(order.created_at).toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
    const customer = data.customerName || data.customerCompany || '-';
    const assigned = order.assigned_name || data.staffName || '-';
    const revised = order.status === 'resend_required' ? ' revised' : '';
    return `<article class="confirmedOrderRow${revised}" data-order-id="${escapeHtml(order.id)}" tabindex="0" role="button" aria-label="${escapeHtml(order.order_no)} ${escapeHtml(customer)} を開く"><span class="confirmedTime">${escapeHtml(time)}</span><span class="confirmedCustomer" title="${escapeHtml(customer)}">${escapeHtml(customer)}</span><span class="confirmedStaff" title="${escapeHtml(assigned)}">${escapeHtml(assigned)}</span><strong class="confirmedOrderNo">${escapeHtml(order.order_no)}</strong></article>`;
  }

  function renderList(group) {
    const rows = filteredOrders(group);
    const list = $(`list-${group}`);
    const renderer = group === 'completed' ? confirmedOrderRow : orderCard;
    list.innerHTML = rows.length ? rows.map(renderer).join('') : '<div class="empty">該当する注文はありません。</div>';
  }

  function render() {
    const base = filteredBase();
    $('newCount').textContent = base.filter((o) => o.status === 'new').length;
    $('progressCount').textContent = base.filter((o) => o.status === 'in_progress').length;
    $('completedCount').textContent = base.filter((o) => ['completed', 'resend_required'].includes(o.status)).length;
    $('sentCount').textContent = base.filter((o) => o.status === 'sent').length;
    $('visibleCount').textContent = base.length;
    $('visibleQty').textContent = base.reduce((sum, order) => sum + totalQty(order), 0);
    $('visibleAmount').textContent = formatMoney(base.reduce((sum, order) => sum + orderTotal(order), 0));
    ['open', 'progress', 'completed', 'sent'].forEach(renderList);
    document.querySelectorAll('[data-order-id]').forEach((card) => {
      const open = () => openDetail(card.dataset.orderId).catch((error) => showToast(`表示失敗：${humanError(error)}`));
      card.addEventListener('click', open);
      card.addEventListener('keydown', (event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); open(); } });
    });
    renderUnsentAlert(base);
  }

  function renderUnsentAlert(base) {
    const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Seoul' }).format(new Date());
    const old = base.filter((order) => ['completed', 'resend_required'].includes(order.status) && dateOf(order) < today);
    $('unsentAlert').classList.toggle('hidden', old.length === 0);
    $('unsentAlertText').textContent = `前日までの代理店未送信注文が${old.length}件あります。`;
  }

  async function createSignedUrl(path) {
    if (!path) return '';
    const encodedPath = String(path).split('/').map(encodeURIComponent).join('/');
    const json = await apiJson(`/storage/v1/object/sign/business-cards/${encodedPath}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ expiresIn: 3600 }),
    });
    const signed = json.signedURL || json.signedUrl || '';
    return signed ? (signed.startsWith('http') ? signed : `${SUPABASE_URL}/storage/v1${signed.startsWith('/') ? '' : '/'}${signed}`) : '';
  }

  function setEditProtection(message, mode = '') {
    const notice = $('editProtectionNotice');
    if (!notice) return;
    notice.className = `editProtectionNotice${mode ? ` ${mode}` : ''}`;
    notice.textContent = message;
  }

  function markEditDirty() {
    if (!$('detailDialog').open) return;
    state.editDirty = true;
    setEditProtection('入力中の内容を保護しています。自動更新が入っても、この画面の入力は消えません。', 'dirty');
    setSync('live', '編集中・入力を保護中');
  }

  function requireSavedEditor() {
    if (!state.editDirty) return true;
    setEditProtection('未保存の変更があります。先に「変更を保存」してください。', 'pending');
    $('saveEditButton')?.focus();
    showToast('未保存の変更を先に保存してください。', 4500);
    return false;
  }

  function closeDetailSafely() {
    if (state.editDirty && !window.confirm('保存していない変更があります。変更を破棄して閉じますか？')) return;
    state.editDirty = false;
    state.editRefreshPending = false;
    state.current = null;
    $('detailDialog').close();
  }

  async function openDetail(id) {
    const order = state.orders.find((row) => row.id === id);
    if (!order) return;
    if ($('sentOrdersDialog')?.open) $('sentOrdersDialog').close();
    state.current = order;
    state.editDirty = false;
    state.editRefreshPending = false;
    await renderDetail(order);
    $('detailDialog').showModal();
  }

  function editDraftFromOrder(order) {
    const data = order.order_data || {};
    return { customerCompany: data.customerCompany || '', customerName: data.customerName || '', customerPhone: data.customerPhone || '', shippingAddress: data.shippingAddress || '', notes: data.notes || '', items: (data.items || []).map((item) => ({ ...item })) };
  }

  function currentEditDraft() {
    if (!$('editCompany')) return editDraftFromOrder(state.current);
    const items = state.editItems.map((item, index) => ({ ...item, q: Math.max(0, Math.min(9999, Math.floor(Number(document.querySelector(`[data-qty-input="${index}"]`)?.value || 0)))) }));
    return { customerCompany: $('editCompany').value.trim(), customerName: $('editName').value.trim(), customerPhone: $('editPhone').value.trim(), shippingAddress: $('editShippingAddress').value.trim(), notes: $('editNotes').value.trim(), items };
  }

  async function renderDetail(order, draft = null) {
    const data = order.order_data || {};
    const edit = draft || editDraftFromOrder(order);
    if (draft) state.editDirty = true;
    else {
      state.editDirty = false;
      state.editRefreshPending = false;
    }
    let productMaster = null;
    if (edit.items.some((item) => !String(item?.img || '').trim())) {
      try { productMaster = await loadProductMaster(); } catch (error) { console.warn(error); }
    }
    state.editItems = edit.items.map((item) => {
      const masterItem = productMaster?.get(String(item?.c || '').trim().toUpperCase());
      return { ...(masterItem || {}), ...item, img: String(item?.img || masterItem?.img || '') };
    });
    $('detailTitle').textContent = `${order.order_no}　注文内容`;
    let previewUrl = '', originalUrl = '';
    try {
      [previewUrl, originalUrl] = await Promise.all([createSignedUrl(order.business_card_preview_path), createSignedUrl(order.business_card_original_path)]);
    } catch (error) {
      console.warn(error);
    }
    const sentWarning = order.status === 'sent' ? '<div class="revisionNotice"><b>この注文は代理店送付済みです。</b><br>変更すると修正版・再送待ちへ移動し、修正理由が必要です。</div>' : '';
    const resendWarning = order.status === 'resend_required' ? `<div class="revisionNotice"><b>修正版・再送待ち</b><br>${escapeHtml(order.revision_reason || data._lastRevisionReason || '')}</div>` : '';
    $('detailBody').innerHTML = `${sentWarning}${resendWarning}<div class="detailGrid"><section class="infoPanel"><div class="infoGrid"><div class="infoBox"><div class="label">受付番号</div><div class="value">${escapeHtml(order.order_no)}</div></div><div class="infoBox"><div class="label">状態</div><div class="value">${statusLabel(order.status)}</div></div><div class="infoBox"><div class="label">受付日時</div><div class="value">${escapeHtml(new Date(order.created_at).toLocaleString('ja-JP'))}</div></div><div class="infoBox"><div class="label">展示会日</div><div class="value">${escapeHtml(dateOf(order))}</div></div><div class="infoBox"><div class="label">最終担当</div><div class="value">${escapeHtml(order.assigned_name || '-')}</div></div><div class="infoBox"><div class="label">改訂</div><div class="value">Revision ${Number(order.revision_count || data._revisionCount || 0)}</div></div></div><div class="editBlock"><h3>お客様情報・備考を編集</h3><div class="editGrid"><div class="editField"><label for="editCompany">会社名</label><input id="editCompany" maxlength="160" value="${escapeHtml(edit.customerCompany)}"></div><div class="editField"><label for="editName">氏名</label><input id="editName" maxlength="120" value="${escapeHtml(edit.customerName)}"></div><div class="editField full"><label for="editPhone">電話番号</label><input id="editPhone" maxlength="30" value="${escapeHtml(edit.customerPhone)}"></div><div class="editField full"><label for="editNotes">備考</label><textarea id="editNotes" maxlength="2000">${escapeHtml(edit.notes)}</textarea></div></div></div><div class="businessCard"><h3>名刺</h3>${previewUrl || originalUrl ? `<a href="${escapeHtml(originalUrl || previewUrl)}" target="_blank" rel="noopener"><img src="${escapeHtml(previewUrl || originalUrl)}" alt="名刺画像"></a>` : '<div class="noCard">名刺画像なし</div>'}</div></section><section class="itemsPanel"><h3>商品・数量</h3><table class="itemsTable"><thead><tr><th>品番</th><th>商品名</th><th class="num">数量</th><th class="num">単価</th><th class="num">小計</th></tr></thead><tbody>${state.editItems.map((item, index) => `<tr><td><b>${escapeHtml(item.c)}</b></td><td><div class="detailProductIdentity">${detailItemImage(item)}<span>${escapeHtml(itemName(item))}</span></div></td><td class="num"><div class="qtyControl"><button type="button" data-qty-minus="${index}" aria-label="数量を減らす">−</button><input data-qty-input="${index}" type="number" min="0" max="9999" step="1" value="${Number(item.q || 0)}" aria-label="${escapeHtml(item.c)}の数量"><button type="button" data-qty-plus="${index}" aria-label="数量を増やす">＋</button></div></td><td class="num">${formatMoney(item.p)}</td><td class="num" data-subtotal="${index}"><b>${formatMoney(Number(item.p || 0) * Number(item.q || 0))}</b></td></tr>`).join('')}</tbody></table><div class="detailTotal"><span>合計</span><span id="editedTotal">${formatMoney(orderTotal(order))}</span></div><div class="productAdder"><input id="addProductCode" type="text" placeholder="追加する品番を入力（例 1053）" aria-label="追加する品番"><button id="addProductButton" class="secondary" type="button">商品を追加</button><div id="productSuggest" class="productSuggest">品番を完全一致で入力してください。商品マスターから名称・価格を取得します。</div></div><div class="saveRow"><button id="saveEditButton" class="primary" type="button">変更を保存</button></div></section></div>`;
    $('editPhone').closest('.editField').insertAdjacentHTML('afterend', `<div class="editField full"><label for="editShippingAddress">発送先住所（任意）</label><textarea id="editShippingAddress" maxlength="500" autocomplete="shipping street-address">${escapeHtml(edit.shippingAddress)}</textarea></div>`);
    $('detailBody').insertAdjacentHTML('afterbegin', '<div id="editProtectionNotice" class="editProtectionNotice">編集中の入力は自動更新から保護されます。</div>');
    $('saveEditButton').insertAdjacentHTML('beforebegin', '<span class="saveHint">保存後、お客様用QRにも最新内容が反映されます。</span>');
    const refreshEditedTotal = () => {
      let total = 0;
      document.querySelectorAll('[data-qty-input]').forEach((input) => {
        const index = Number(input.dataset.qtyInput);
        const qty = Math.max(0, Math.min(9999, Number(input.value || 0)));
        total += Number(state.editItems[index]?.p || 0) * qty;
        const subtotal = document.querySelector(`[data-subtotal="${index}"]`);
        if (subtotal) subtotal.innerHTML = `<b>${formatMoney(Number(state.editItems[index]?.p || 0) * qty)}</b>`;
      });
      $('editedTotal').textContent = formatMoney(total);
    };
    ['editCompany', 'editName', 'editPhone', 'editShippingAddress', 'editNotes'].forEach((id) => $(id).addEventListener('input', markEditDirty));
    document.querySelectorAll('[data-qty-minus]').forEach((button) => button.addEventListener('click', () => { const input = document.querySelector(`[data-qty-input="${button.dataset.qtyMinus}"]`); input.value = Math.max(0, Number(input.value || 0) - 1); refreshEditedTotal(); markEditDirty(); }));
    document.querySelectorAll('[data-qty-plus]').forEach((button) => button.addEventListener('click', () => { const input = document.querySelector(`[data-qty-input="${button.dataset.qtyPlus}"]`); input.value = Math.min(9999, Number(input.value || 0) + 1); refreshEditedTotal(); markEditDirty(); }));
    document.querySelectorAll('[data-qty-input]').forEach((input) => input.addEventListener('input', () => { refreshEditedTotal(); markEditDirty(); }));
    $('saveEditButton').addEventListener('click', () => withBusy(['saveEditButton'], saveEditedOrder).catch((error) => showToast(`保存失敗：${humanError(error)}`, 6000)));
    $('addProductButton').addEventListener('click', () => withBusy(['addProductButton'], addProductToCurrent).catch((error) => showToast(`商品追加失敗：${humanError(error)}`)));
    refreshEditedTotal();
    if (state.editDirty) setEditProtection('入力中の内容を保護しています。自動更新が入っても、この画面の入力は消えません。', 'dirty');
    $('startButton').classList.toggle('hidden', order.status !== 'new');
    $('completeButton').classList.toggle('hidden', !['new', 'in_progress'].includes(order.status));
    $('reopenButton').classList.toggle('hidden', !['completed', 'resend_required'].includes(order.status));
  }

  function parseCsv(text) {
    const rows = [];
    let row = [], cell = '', quoted = false;
    for (let i = 0; i < text.length; i += 1) {
      const char = text[i], next = text[i + 1];
      if (char === '"' && quoted && next === '"') { cell += '"'; i += 1; continue; }
      if (char === '"') { quoted = !quoted; continue; }
      if (char === ',' && !quoted) { row.push(cell); cell = ''; continue; }
      if ((char === '\n' || char === '\r') && !quoted) { if (cell || row.length) { row.push(cell); rows.push(row); row = []; cell = ''; } if (char === '\r' && next === '\n') i += 1; continue; }
      cell += char;
    }
    if (cell || row.length) { row.push(cell); rows.push(row); }
    const headers = (rows.shift() || []).map((value) => value.trim().replace(/^\uFEFF/, ''));
    return rows.map((values) => Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ''])));
  }

  async function loadProductMaster() {
    if (state.productMaster) return state.productMaster;
    const response = await fetchWithTimeout('product_master_korea.csv', { cache: 'default' }, 20000);
    if (!response.ok) throw new Error('商品マスターを読み込めません。');
    const rows = parseCsv(await response.text());
    state.productMaster = new Map(rows.map((row) => [String(row['品番'] || '').trim().toUpperCase(), {
      c: String(row['品番'] || '').trim(), n: [String(row['商品名_JA'] || ''), String(row['商品名_KO'] || '')], q: 1,
      p: Number(row['韓国眼鏡店への販売価格（KRW）'] || 0), img: String(row['画像ファイル名'] || '') ? `product-images/${row['画像ファイル名']}` : '',
    }]));
    return state.productMaster;
  }

  async function addProductToCurrent() {
    const code = $('addProductCode').value.trim().toUpperCase();
    if (!code) throw new Error('品番を入力してください。');
    const draft = currentEditDraft();
    const master = await loadProductMaster();
    const product = master.get(code);
    if (!product) throw new Error('商品マスターに一致する品番がありません。');
    const existing = draft.items.find((item) => String(item.c).trim().toUpperCase() === code);
    if (existing) existing.q = Math.min(9999, Number(existing.q || 0) + 1);
    else draft.items.push({ ...product });
    await renderDetail(state.current, draft);
    showToast(`${product.c} を追加しました。`);
  }

  async function saveEditedOrder() {
    if (!state.current) return;
    const order = state.current;
    const oldData = order.order_data || {};
    const draft = currentEditDraft();
    const items = draft.items.filter((item) => Number(item.q || 0) > 0);
    if (!draft.customerCompany || !draft.customerName || !draft.customerPhone) throw new Error('会社名・氏名・電話番号は必須です。');
    if (!items.length) throw new Error('商品を1点以上残してください。');
    const total = items.reduce((sum, item) => sum + Number(item.p || 0) * Number(item.q || 0), 0);
    const changed = JSON.stringify({ ...draft, items }) !== JSON.stringify({ customerCompany: oldData.customerCompany || '', customerName: oldData.customerName || '', customerPhone: oldData.customerPhone || '', shippingAddress: oldData.shippingAddress || '', notes: oldData.notes || '', items: oldData.items || [] });
    if (!changed) {
      state.editDirty = false;
      state.editRefreshPending = false;
      setEditProtection('変更はありません。自動更新からの保護を解除しました。');
      showToast('変更はありません。');
      return;
    }
    let reason = 'スタッフによる内容確認・修正';
    let nextStatus = order.status;
    let requiresResend = Boolean(order.requires_resend || oldData._requiresResend);
    if (order.status === 'sent') {
      if (!window.confirm('この注文は代理店送付済みです。\n内容を変更すると修正版を再送する必要があります。')) return;
      reason = window.prompt('修正理由を入力してください。', '')?.trim() || '';
      if (!reason) throw new Error('送付済み注文の修正理由は必須です。');
      nextStatus = 'resend_required';
      requiresResend = true;
    } else if (['completed', 'resend_required'].includes(order.status)) {
      if (!window.confirm('この注文は確定済みです。変更内容は代理店へ送る注文書にも反映されます。保存しますか？')) return;
      reason = window.prompt('修正理由を入力してください。', order.revision_reason || '')?.trim() || '';
      if (!reason) throw new Error('確定済み注文の修正理由は必須です。');
    }
    const revisionCount = Number(order.revision_count || oldData._revisionCount || 0) + 1;
    const now = new Date().toISOString();
    const orderData = { ...oldData, customerCompany: draft.customerCompany, customerName: draft.customerName, customerPhone: draft.customerPhone, shippingAddress: draft.shippingAddress, notes: draft.notes, items, total, status: nextStatus, _revisionCount: revisionCount, _lastRevisionAt: now, _lastRevisionBy: staffName(), _lastRevisionReason: reason, _requiresResend: requiresResend };
    if (order.status === 'sent') {
      orderData._previousBatchId = order.batch_id || oldData._batchId || '';
      orderData._previousSentAt = order.sent_at || oldData._sentAt || '';
      orderData._previousSentBy = order.sent_by_name || oldData._sentBy || '';
    }
    const patch = { order_data: orderData, status: nextStatus, revision_count: revisionCount, revision_reason: reason, requires_resend: requiresResend };
    const updated = await updateOrder(order, patch);
    try {
      await apiJson('/rest/v1/order_revisions', {
        method: 'POST', headers: { 'Content-Type': 'application/json', Prefer: 'return=minimal' },
        body: JSON.stringify({ order_id: order.id, event_id: eventIdOf(order), revision_number: revisionCount, changed_by: state.user.id, changed_by_name: staffName(), change_reason: reason, status_before: order.status, status_after: nextStatus, before_data: oldData, after_data: orderData, batch_id_before: order.batch_id || null }),
      });
    } catch (error) { console.warn('revision history unavailable', error); }
    await logActivity(updated || order, order.status === 'sent' ? 'sent_order_revised' : 'order_updated', { reason, revision_count: revisionCount });
    if (updated) await renderDetail(updated);
    showToast(`${order.order_no} を保存しました。お客様用QRにも最新内容が反映されています。`, 5000);
  }

  async function startOrder() {
    if (!state.current) return;
    if (!requireSavedEditor()) return;
    const order = state.current;
    const updated = await updateOrder(order, { status: 'in_progress' });
    await logActivity(updated || order, 'review_started');
    if (updated) await renderDetail(updated);
    showToast(`${order.order_no} の確認を開始しました。`);
  }

  async function completeOrder() {
    if (!state.current) return;
    if (!requireSavedEditor()) return;
    const order = state.current;
    if (!window.confirm(`${order.order_no} をこの内容で確定しますか？\n確定後は画面下の「注文確定分」へ移動します。`)) return;
    const updated = await updateOrder(order, { status: 'completed', completed_at: new Date().toISOString(), requires_resend: false });
    await logActivity(updated || order, 'order_completed');
    if (updated) await renderDetail(updated);
    showToast(`${order.order_no} を確定しました。`);
  }

  async function reopenOrder() {
    if (!state.current) return;
    if (!requireSavedEditor()) return;
    const order = state.current;
    if (!window.confirm(`${order.order_no} を確認待ちへ戻しますか？`)) return;
    const data = { ...(order.order_data || {}), status: 'new', _requiresResend: false };
    const updated = await updateOrder(order, { status: 'new', completed_at: null, requires_resend: false, pending_batch_id: null, order_data: data });
    await logActivity(updated || order, 'order_reopened');
    if (updated) await renderDetail(updated);
    showToast(`${order.order_no} を確認待ちへ戻しました。`);
  }

  function openDeleteDialog() {
    if (!state.current) return;
    if (!requireSavedEditor()) return;
    const data = state.current.order_data || {};
    $('deleteTarget').innerHTML = `<b>${escapeHtml(state.current.order_no)}（${escapeHtml(data.customerCompany || '')}）</b><br>通常の注文一覧には表示されなくなります。データは削除履歴から元に戻せます。`;
    $('deleteReason').value = '';
    $('deleteReasonOther').value = '';
    $('deleteReasonOtherWrap').classList.add('hidden');
    $('deleteDialog').showModal();
  }

  async function confirmSoftDelete() {
    if (!state.current) return;
    const order = state.current;
    const selected = $('deleteReason').value;
    const reason = selected === 'その他' ? $('deleteReasonOther').value.trim() : selected;
    if (!reason) throw new Error('削除理由を選択または入力してください。');
    const now = new Date().toISOString();
    const orderData = { ...(order.order_data || {}), status: 'deleted', _deletedAt: now, _deletedBy: staffName(), _deletedById: state.user.id, _deleteReason: reason, _statusBeforeDelete: order.status };
    const updated = await updateOrder(order, { status: 'deleted', order_data: orderData, deleted_at: now, deleted_by: state.user.id, deleted_by_name: staffName(), delete_reason: reason, status_before_delete: order.status });
    await logActivity(updated || order, 'order_soft_deleted', { reason, status_before: order.status });
    state.current = null;
    $('deleteDialog').close();
    $('detailDialog').close();
    showToast(`${order.order_no} を削除履歴へ移しました。`);
  }

  function deletedOrders() {
    return filteredBase({ includeDeleted: true }).sort((a, b) => new Date(b.deleted_at || b.order_data?._deletedAt || b.updated_at) - new Date(a.deleted_at || a.order_data?._deletedAt || a.updated_at));
  }

  function renderHistory() {
    const rows = deletedOrders();
    $('historyList').innerHTML = rows.length ? rows.map((order) => {
      const data = order.order_data || {};
      const before = order.status_before_delete || data._statusBeforeDelete || 'new';
      const reason = order.delete_reason || data._deleteReason || '-';
      return `<article class="historyRow"><div class="historyMain"><div class="historyNo">${escapeHtml(order.order_no)}</div><div class="historyCompany">${escapeHtml(data.customerCompany || '-')}　${escapeHtml(data.customerName || '')}</div><div class="historyMeta">削除：${escapeHtml(new Date(order.deleted_at || data._deletedAt || order.updated_at).toLocaleString('ja-JP'))} / ${escapeHtml(order.deleted_by_name || data._deletedBy || '-')}<br>理由：${escapeHtml(reason)} / 削除前：${statusLabel(before)}</div></div><div class="historyActions"><button class="secondary small" data-restore-id="${escapeHtml(order.id)}" type="button">元に戻す</button></div></article>`;
    }).join('') : '<div class="empty">削除履歴はありません。</div>';
  }

  function openHistory() {
    renderHistory();
    $('historyDialog').showModal();
  }

  async function restoreDeleted(id) {
    const order = state.orders.find((row) => row.id === id);
    if (!order) return;
    const data = { ...(order.order_data || {}) };
    const restoreStatus = order.status_before_delete || data._statusBeforeDelete || 'new';
    if (restoreStatus === 'sent' && !window.confirm('この注文は代理店送付済みの状態へ復元されます。送信履歴は残っています。続けますか？')) return;
    delete data._deletedAt; delete data._deletedBy; delete data._deletedById; delete data._deleteReason; delete data._statusBeforeDelete;
    data.status = restoreStatus;
    const updated = await updateOrder(order, { status: restoreStatus, order_data: data, deleted_at: null, deleted_by: null, deleted_by_name: null, delete_reason: null, status_before_delete: null });
    await logActivity(updated || order, 'order_restored', { restored_status: restoreStatus });
    renderHistory();
    showToast(`${order.order_no} を${statusLabel(restoreStatus)}へ戻しました。`);
  }

  function customerReceiptUrl(order) {
    const token = String(order?.public_token || '').trim();
    if (!/^[A-Za-z0-9_-]{30,80}$/.test(token)) return '';
    const configured = String(config.publicAppUrl || '').trim();
    const fallback = `${location.origin}${location.pathname.replace(/staff\.html(?:\?.*)?$/i, '')}`;
    const base = (configured || fallback).replace(/#.*$/, '');
    return `${base}#online-receipt=${encodeURIComponent(token)}`;
  }

  function openCustomerQr() {
    if (!state.current) return;
    if (!requireSavedEditor()) return;
    const url = customerReceiptUrl(state.current);
    if (!url) {
      showToast('この注文にはお客様用QRを作成できる公開トークンがありません。最新情報に更新してください。', 6000);
      return;
    }
    state.customerQrUrl = url;
    $('customerQrCode').innerHTML = '';
    $('customerQrLink').textContent = url;
    $('openCustomerQrLink').href = url;
    try {
      if (!window.QRCode) throw new Error('QR_LIBRARY_UNAVAILABLE');
      new QRCode($('customerQrCode'), { text: url, width: 220, height: 220, correctLevel: QRCode.CorrectLevel.M });
    } catch (error) {
      console.warn(error);
      $('customerQrCode').textContent = 'QRコードを生成できませんでした。下のURLをコピーしてください。';
    }
    $('customerQrDialog').showModal();
  }

  async function copyCustomerQrUrl() {
    if (!state.customerQrUrl) return;
    try {
      await navigator.clipboard.writeText(state.customerQrUrl);
    } catch {
      const input = document.createElement('textarea');
      input.value = state.customerQrUrl;
      input.style.position = 'fixed';
      input.style.opacity = '0';
      document.body.appendChild(input);
      input.select();
      document.execCommand('copy');
      input.remove();
    }
    showToast('お客様用URLをコピーしました。');
  }

  function revisedMark(order) {
    const revision = Number(order.revision_count || order.order_data?._revisionCount || 0);
    return order.status === 'resend_required' || revision > 0 ? `<div class="revisedMark">REVISED ORDER / 修正版 / Revision ${revision}</div>` : '';
  }

  function printItemNames(item) {
    const names = Array.isArray(item?.n) ? item.n : [String(item?.n || ''), ''];
    const ja = String(names[0] || item?.c || '');
    const ko = String(names[1] || '');
    return `<span class="receiptItemName">${escapeHtml(ja)}</span>${ko && ko !== ja ? `<span class="receiptItemSub">${escapeHtml(ko)}</span>` : ''}`;
  }

  function buildPrint(order, cardUrl = '', wrapperClass = 'printOrder') {
    const data = order.order_data || {}, items = data.items || [];
    const hasBusinessCard = Boolean(order.business_card_original_path || order.business_card_preview_path);
    const businessCard = cardUrl ? `<div class="receiptBusinessCard"><div class="receiptBusinessCardLabel">名刺写真 / 명함 사진<small>お客様からお預かりした名刺画像 / 고객 명함 이미지</small></div><div class="receiptBusinessCardImage"><img src="${escapeHtml(cardUrl)}" alt="名刺写真 / 명함 사진"></div></div>` : hasBusinessCard ? '<div class="receiptBusinessCard receiptBusinessCardMissing"><div class="receiptBusinessCardLabel">名刺写真 / 명함 사진</div><div>画像を取得できませんでした。スタッフ画面で原本を確認してください。<br>명함 이미지를 불러오지 못했습니다. 직원 화면에서 원본을 확인해 주세요.</div></div>' : '';
    const shippingAddress = data.shippingAddress ? `<div class="receiptShippingAddress"><div class="receiptInfoLabel">Shipping address / 배송지 주소</div><div class="receiptInfoValue">${escapeHtml(data.shippingAddress).replace(/\n/g, '<br>')}</div></div>` : '';
    const notes = data.notes ? `<div class="receiptNote"><b>備考 / 비고</b>${escapeHtml(data.notes).replace(/\n/g, '<br>')}</div>` : '';
    return `<section class="${wrapperClass}">${revisedMark(order)}
      <div class="receiptHeaderSimple"><div class="receiptBrandBlock"><img class="receiptBrandLogo" src="assets/sun_nishimura_logo.jpg" alt="SAN NISHIMURA"><div><div class="receiptBrandName">SAN NISHIMURA CO., LTD.</div><div class="receiptBrandSub">サンニシムラ株式会社 / 선 니시무라 주식회사<br>Korea Distributor: KY-S Corporation | TEL +82-2-3789-2440</div></div></div><div class="receiptDocMeta"><div class="receiptDocTitle">確定注文書 / 확정 주문서</div><div class="receiptDocSub">Confirmed exhibition order sheet</div><div class="receiptMetaLine"><b>注文番号 / 주문번호</b> ${escapeHtml(order.order_no)}<br><b>状態 / 상태</b> ${escapeHtml(statusLabel(order.status))}<br><b>作成日時 / 작성일시</b> ${escapeHtml(new Date(order.created_at).toLocaleString('ja-JP'))}</div></div></div>
      <div class="receiptInfoBand"><div class="receiptInfoCard"><div class="receiptInfoLabel">Company / 회사명</div><div class="receiptInfoValue">${escapeHtml(data.customerCompany || '-')}</div></div><div class="receiptInfoCard"><div class="receiptInfoLabel">Name / 성명</div><div class="receiptInfoValue">${escapeHtml(data.customerName || '-')}</div></div><div class="receiptInfoCard"><div class="receiptInfoLabel">Phone / 연락처</div><div class="receiptInfoValue">${escapeHtml(data.customerPhone || '-')}</div></div><div class="receiptInfoCard"><div class="receiptInfoLabel">Event / 전시회</div><div class="receiptInfoValue">${escapeHtml(eventNameOf(order))}<br>${escapeHtml(dateOf(order))}</div></div><div class="receiptInfoCard"><div class="receiptInfoLabel">Distributor / 대리점</div><div class="receiptInfoValue">${escapeHtml(data.distributor || config.distributorName || 'KY-S Corporation')}</div></div><div class="receiptInfoCard"><div class="receiptInfoLabel">Staff / 담당자</div><div class="receiptInfoValue">${escapeHtml(order.assigned_name || data.staffName || staffName())}</div></div></div>
      ${shippingAddress}
      ${businessCard}
      <div class="receiptSection"><div class="receiptSectionHead"><div class="receiptSectionTitle">注文明細 / 주문 내역</div><div class="receiptSectionHint">Main order details</div></div><table class="receiptTable"><colgroup><col class="code"><col class="image"><col><col class="qty"><col class="unit"><col class="subtotal"></colgroup><thead><tr><th>品番 / 품번</th><th></th><th>商品名 / 상품명</th><th class="num">数量 / 수량</th><th class="num">単価 / 단가</th><th class="num">金額 / 금액</th></tr></thead><tbody>${items.map((item) => `<tr><td><b>${escapeHtml(item.c)}</b></td><td>${item.img ? `<div class="receiptThumb"><img src="${escapeHtml(item.img)}" alt="${escapeHtml(item.c)}"></div>` : ''}</td><td>${printItemNames(item)}</td><td class="num">${escapeHtml(item.q)}</td><td class="num">${formatMoney(item.p)}</td><td class="num"><b>${formatMoney(Number(item.p || 0) * Number(item.q || 0))}</b></td></tr>`).join('')}</tbody></table><div class="receiptImageNote">※ 商品画像は参考表示です。 / 상품 이미지는 참고용입니다.</div></div>
      <div class="receiptFooterGrid"><div class="receiptMemoStack">${notes}<div class="receiptNote"><b>ご案内 / 안내</b>本書は展示会場で受け付けた注文をスタッフが確認した注文書です。最終在庫・納期は代理店よりご案内します。<br><br>본 문서는 전시장에서 접수한 주문을 직원이 확인한 주문서입니다. 최종 재고 및 납기는 대리점에서 안내합니다.</div></div><div><div class="receiptSummaryBox"><div class="receiptSummaryRow"><span>点数 / 수량 합계</span><span>${totalQty(order)}</span></div><div class="receiptSummaryRow total"><span>合計 / 합계</span><span>${formatMoney(orderTotal(order))}</span></div></div><div class="receiptCurrencyNote">Currency / 통화 : KRW</div></div></div>
      <div class="receiptFooterMini"><div>KY-S Corporation | 3F, 16 Sowol-ro, Jung-gu, Seoul, Korea</div><div>TEL +82-2-3789-2440 / FAX +82-2-3789-2441${state.batch?.batchId ? ` / ${escapeHtml(state.batch.batchId)}` : ''}</div></div></section>`;
  }

  async function signedBusinessCardUrl(order) {
    const paths = [...new Set([order?.business_card_original_path, order?.business_card_preview_path].filter(Boolean))];
    for (const path of paths) {
      try {
        const url = await createSignedUrl(path);
        if (url) return url;
      } catch (error) {
        console.warn('business card URL unavailable', error);
      }
    }
    return '';
  }

  async function waitForPrintImages(timeoutMs = 10000) {
    const images = [...$('printArea').querySelectorAll('img')];
    await Promise.all(images.map(async (img) => {
      if (!img.complete) {
        await Promise.race([
          new Promise((resolve) => { img.addEventListener('load', resolve, { once: true }); img.addEventListener('error', resolve, { once: true }); }),
          new Promise((resolve) => setTimeout(resolve, timeoutMs)),
        ]);
      }
      if (img.decode) await Promise.race([img.decode().catch(() => {}), new Promise((resolve) => setTimeout(resolve, timeoutMs))]);
    }));
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  }

  async function openPrintWhenImagesReady() {
    await waitForPrintImages();
    window.print();
  }

  async function printCurrent() {
    if (!state.current) return;
    if (!requireSavedEditor()) return;
    const order = state.current;
    const card = await signedBusinessCardUrl(order);
    $('printArea').innerHTML = buildPrint(order, card);
    try { await updateOrder(order, { printed_at: new Date().toISOString() }); } catch (error) { if (error.message !== 'CONFLICT') throw error; }
    await openPrintWhenImagesReady();
  }

  function selectedBatchOrders() {
    const checked = [...document.querySelectorAll('[data-batch-order]:checked')].map((input) => input.value);
    const source = state.batch?.orders || [];
    return source.filter((order) => checked.includes(order.id));
  }

  function batchGroupKey(order) {
    return `${eventIdOf(order)}::${dateOf(order)}`;
  }

  function batchDateText(order) {
    if (!order) return '-';
    const day = Number(order.event_day || order.order_data?.eventDay || 0);
    return `${dateOf(order).replace(/-/g, '/')}${day ? `（${day}日目）` : ''}`;
  }

  function batchScopedOrders() {
    const eventFilter = $('eventFilter').value;
    return state.orders.filter((order) => !isDeleted(order) && ['completed', 'resend_required'].includes(order.status) && (eventFilter === 'all' || eventIdOf(order) === eventFilter));
  }

  function batchEligibleOrders() {
    return batchScopedOrders().filter((order) => !order.pending_batch_id);
  }

  function batchGroups(orders) {
    const grouped = new Map();
    orders.forEach((order) => {
      const key = batchGroupKey(order);
      if (!grouped.has(key)) grouped.set(key, []);
      grouped.get(key).push(order);
    });
    return [...grouped.entries()].map(([key, rows]) => ({ key, rows })).sort((a, b) => dateOf(a.rows[0]).localeCompare(dateOf(b.rows[0])) || eventNameOf(a.rows[0]).localeCompare(eventNameOf(b.rows[0]), 'ja'));
  }

  function renderBatchOrderList() {
    const rows = state.batch?.orders || [];
    const locked = Boolean(state.batch?.batchId);
    $('batchOrderList').innerHTML = rows.map((order) => {
      const time = new Date(order.created_at).toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
      return `<label class="batchOrderRow"><span><input data-batch-order type="checkbox" value="${escapeHtml(order.id)}" checked ${locked ? 'disabled' : ''}> <b>${escapeHtml(order.order_no)}</b>　${escapeHtml(order.order_data?.customerCompany || '-')}<small class="batchOrderDate">${escapeHtml(time)}受付</small></span><span>${totalQty(order)}点 / ${formatMoney(orderTotal(order))}${order.status === 'resend_required' ? ' / 修正版' : ''}</span></label>`;
    }).join('');
    document.querySelectorAll('[data-batch-order]').forEach((input) => input.addEventListener('change', updateBatchDialogSummary));
    updateBatchDialogSummary();
  }

  function selectBatchDateGroup(key) {
    if (!state.batch || state.batch.batchId) return;
    const group = state.batch.groups.find((item) => item.key === key) || state.batch.groups[0];
    if (!group) return;
    state.batch.selectedGroupKey = group.key;
    state.batch.orders = group.rows;
    $('batchDateSelect').value = group.key;
    $('pdfSavedCheck').checked = false;
    $('mailSentCheck').checked = false;
    $('openBatchMailButton').disabled = true;
    $('markBatchSentButton').disabled = true;
    $('batchMessage').textContent = `${batchDateText(group.rows[0])} の注文確定分を表示しています。対象を確認してPDFを作成してください。`;
    renderBatchOrderList();
  }

  function updateBatchDialogSummary() {
    const rows = selectedBatchOrders();
    const qty = rows.reduce((sum, order) => sum + totalQty(order), 0);
    const amount = rows.reduce((sum, order) => sum + orderTotal(order), 0);
    const revised = rows.filter((order) => order.status === 'resend_required').length;
    const targetOrder = state.batch?.orders?.[0];
    $('batchSummary').innerHTML = `<div><span>注文件数</span><b>${rows.length}件</b></div><div><span>合計数量</span><b>${qty}点</b></div><div><span>合計金額</span><b>${formatMoney(amount)}</b></div><div><span>再送注文</span><b>${revised}件</b></div><div><span>対象日</span><b>${escapeHtml(batchDateText(targetOrder))}</b></div><div><span>Batch ID</span><b>${escapeHtml(state.batch?.batchId || 'PDF作成時に採番')}</b></div>`;
    $('createBatchPdfButton').disabled = rows.length === 0;
    const inputs = [...document.querySelectorAll('[data-batch-order]')];
    const checked = inputs.filter((input) => input.checked).length;
    $('batchSelectAll').checked = inputs.length > 0 && checked === inputs.length;
    $('batchSelectAll').indeterminate = checked > 0 && checked < inputs.length;
    $('batchSelectAll').disabled = Boolean(state.batch?.batchId) || inputs.length === 0;
  }

  async function openBatchDialog() {
    const pending = batchScopedOrders().filter((order) => order.pending_batch_id);
    let batchId = '';
    let orders = batchEligibleOrders();
    if (pending.length) {
      batchId = pending[0].pending_batch_id;
      orders = pending.filter((order) => order.pending_batch_id === batchId);
    }
    if (!orders.length) { showToast('注文確定分はありません。'); return; }
    const groups = batchGroups(orders);
    const currentDate = $('dateFilter').value;
    const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Seoul' }).format(new Date());
    const preferred = batchId ? groups[0] : groups.find((group) => currentDate !== 'all' && dateOf(group.rows[0]) === currentDate) || groups.find((group) => dateOf(group.rows[0]) === today) || groups[0];
    state.batch = { batchId, orders: preferred.rows, groups, selectedGroupKey: preferred.key };
    const multipleEvents = new Set(groups.map((group) => eventIdOf(group.rows[0]))).size > 1;
    $('batchDateSelect').innerHTML = groups.map((group) => `<option value="${escapeHtml(group.key)}">${multipleEvents ? `${escapeHtml(eventNameOf(group.rows[0]))}｜` : ''}${escapeHtml(batchDateText(group.rows[0]))} — ${group.rows.length}件</option>`).join('');
    $('batchDateSelect').value = preferred.key;
    $('batchDateSelect').disabled = Boolean(batchId);
    $('recipientEmail').value = String(config.distributorEmail || '');
    $('pdfSavedCheck').checked = false;
    $('mailSentCheck').checked = false;
    $('openBatchMailButton').disabled = !batchId;
    $('markBatchSentButton').disabled = true;
    $('batchMessage').textContent = batchId ? `作業中の ${batchId} を再開しました。` : `${batchDateText(preferred.rows[0])} の注文確定分を表示しています。対象を確認してPDFを作成してください。`;
    renderBatchOrderList();
    $('batchDialog').showModal();
  }

  async function createBatchPdf() {
    const rows = selectedBatchOrders();
    if (!rows.length) throw new Error('送信対象を選択してください。');
    if (new Set(rows.map(batchGroupKey)).size !== 1) throw new Error('同じ展示会日の注文だけを選択してください。');
    if (!state.batch.batchId) {
      const eventId = eventIdOf(rows[0]), eventName = eventNameOf(rows[0]), eventDate = dateOf(rows[0]);
      const result = await rpc('create_exhibition_order_batch', { p_event_id: eventId, p_event_name: eventName, p_event_date: eventDate, p_order_ids: rows.map((order) => order.id), p_recipient_email: $('recipientEmail').value.trim(), p_created_by_name: staffName() });
      const record = Array.isArray(result) ? result[0] : result;
      if (!record?.batch_id) throw new Error('Batch IDを作成できませんでした。');
      state.batch = { ...state.batch, batchId: record.batch_id, orders: rows };
      $('batchDateSelect').disabled = true;
      $('batchSelectAll').disabled = true;
      document.querySelectorAll('[data-batch-order]').forEach((input) => { input.disabled = true; });
    }
    const urls = await Promise.all(rows.map(signedBusinessCardUrl));
    const qty = rows.reduce((sum, order) => sum + totalQty(order), 0), amount = rows.reduce((sum, order) => sum + orderTotal(order), 0);
    const cover = `<section class="batchCover"><img src="assets/sun_nishimura_logo.jpg" alt="SAN NISHIMURA" style="width:220px"><h1>Korea Exhibition Confirmed Orders</h1><h2>韓国展示会 確定注文明細</h2><table class="batchCoverTable"><tr><th>展示会</th><td>${escapeHtml(eventNameOf(rows[0]))}</td></tr><tr><th>対象日</th><td>${escapeHtml(dateOf(rows[0]))}</td></tr><tr><th>送信グループ番号</th><td>${escapeHtml(state.batch.batchId)}</td></tr><tr><th>作成日時</th><td>${escapeHtml(new Date().toLocaleString('ja-JP'))}</td></tr><tr><th>注文件数</th><td>${rows.length}件</td></tr><tr><th>合計数量</th><td>${qty}点</td></tr><tr><th>合計金額</th><td>${formatMoney(amount)}</td></tr><tr><th>作成担当</th><td>${escapeHtml(staffName())}</td></tr><tr><th>韓国代理店</th><td>KY-S Corporation</td></tr></table></section>`;
    $('printArea').innerHTML = cover + rows.map((order, index) => buildPrint(order, urls[index])).join('');
    $('openBatchMailButton').disabled = false;
    $('batchMessage').textContent = `${state.batch.batchId} の印刷画面を開きます。保存先でPDFを選択してください。`;
    updateBatchDialogSummary();
    await openPrintWhenImagesReady();
  }

  function openBatchMail() {
    if (!state.batch?.batchId) return;
    const rows = state.batch.orders;
    const qty = rows.reduce((sum, order) => sum + totalQty(order), 0), amount = rows.reduce((sum, order) => sum + orderTotal(order), 0), revised = rows.some((order) => order.status === 'resend_required');
    const email = $('recipientEmail').value.trim();
    const subject = `${revised ? 'Revised ' : ''}Korea Exhibition Orders - ${state.batch.batchId}`;
    const body = `Dear KY-S Corporation,\n\nPlease find attached the confirmed order PDF received at the exhibition.\n\nExhibition: ${eventNameOf(rows[0])}\nOrder date: ${dateOf(rows[0])}\nBatch ID: ${state.batch.batchId}\nNumber of orders: ${rows.length}\nTotal quantity: ${qty} pieces\nTotal amount: KRW ${Math.round(amount).toLocaleString('en-US')}\n\nThe attached PDF includes the confirmed order details.\nPlease check the attached order PDF and let us know if you have any questions.\n\nBest regards,\nSAN NISHIMURA CO., LTD.`;
    location.href = `mailto:${encodeURIComponent(email)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    $('batchMessage').textContent = 'メールソフトを開きました。PDFを添付して送信してください。';
  }

  function updateBatchSendEnabled() {
    $('markBatchSentButton').disabled = !($('pdfSavedCheck').checked && $('mailSentCheck').checked && state.batch?.batchId);
  }

  async function markBatchSent() {
    if (!state.batch?.batchId) throw new Error('Batch IDがありません。');
    if (!$('pdfSavedCheck').checked || !$('mailSentCheck').checked) throw new Error('PDF保存とメール送信の両方を確認してください。');
    if (!window.confirm(`${state.batch.orders.length}件を代理店送付済みにしますか？\n実際にメール送信が完了していることを確認してください。`)) return;
    await rpc('mark_exhibition_order_batch_sent', { p_batch_id: state.batch.batchId, p_sent_by_name: staffName() });
    const id = state.batch.batchId;
    state.batch = null;
    $('batchDialog').close();
    await loadOrders();
    showToast(`${id} を代理店送付済みにしました。`);
  }

  async function closeBatchDialog() {
    if (state.batch?.batchId) {
      if (!window.confirm(`${state.batch.batchId} の送付作業を中止しますか？\nPDFを作り直す場合は再度バッチを作成します。`)) return;
      try { await rpc('cancel_exhibition_order_batch', { p_batch_id: state.batch.batchId }); } catch (error) { showToast(`バッチ中止失敗：${humanError(error)}`); return; }
      await loadOrders();
    }
    state.batch = null;
    $('batchDialog').close();
  }

  async function openBatchHistory() {
    $('batchHistoryList').innerHTML = '<div class="empty">読み込み中…</div>';
    $('batchHistoryDialog').showModal();
    try {
      const eventFilter = $('eventFilter').value, dateFilter = $('dateFilter').value;
      const filters = `${eventFilter !== 'all' ? `&event_id=eq.${encodeURIComponent(eventFilter)}` : ''}${dateFilter !== 'all' ? `&event_date=eq.${encodeURIComponent(dateFilter)}` : ''}`;
      const rows = await apiJson(`/rest/v1/order_batches?select=batch_id,event_name,event_date,created_at,created_by_name,sent_at,sent_by_name,recipient_email,order_count,total_quantity,total_amount,status&order=created_at.desc&limit=100${filters}`, { headers: { Accept: 'application/json' } });
      $('batchHistoryList').innerHTML = rows.length ? rows.map((batch) => `<article class="historyRow"><div><div class="historyNo">${escapeHtml(batch.batch_id)}</div><div class="historyCompany">${escapeHtml(batch.event_name || '')} / ${escapeHtml(batch.event_date || '')}</div><div class="historyMeta">${escapeHtml(batch.status === 'sent' ? '送付済み' : batch.status === 'cancelled' ? '中止' : '作業中')} / ${batch.order_count}件 / ${batch.total_quantity}点 / ${formatMoney(batch.total_amount)}<br>送付：${escapeHtml(batch.sent_at ? new Date(batch.sent_at).toLocaleString('ja-JP') : '-')} / ${escapeHtml(batch.sent_by_name || '-')}</div></div></article>`).join('') : '<div class="empty">送信履歴はありません。</div>';
    } catch (error) {
      $('batchHistoryList').innerHTML = `<div class="empty">送信履歴を読み込めません。<br>${escapeHtml(humanError(error))}</div>`;
    }
  }

  function beep() {
    if (!state.soundEnabled) return;
    try {
      const Context = window.AudioContext || window.webkitAudioContext;
      state.audioContext ||= new Context();
      const oscillator = state.audioContext.createOscillator(), gain = state.audioContext.createGain();
      oscillator.frequency.value = 880;
      gain.gain.setValueAtTime(0.0001, state.audioContext.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.18, state.audioContext.currentTime + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, state.audioContext.currentTime + 0.28);
      oscillator.connect(gain).connect(state.audioContext.destination);
      oscillator.start(); oscillator.stop(state.audioContext.currentTime + 0.3);
    } catch {}
  }

  function notifyNewOrder(order) {
    beep();
    showToast(`新しい注文 ${order.order_no}`);
    document.title = `🔴 ${order.order_no} 新規注文`;
    setTimeout(() => { document.title = '韓国展示会 スタッフ注文管理 | SAN NISHIMURA'; }, 6000);
    document.querySelector(`[data-order-id="${CSS.escape(order.id)}"]`)?.classList.add('newFlash');
  }

  function stopRealtime() {
    if (state.realtimeChannel && state.realtimeClient) state.realtimeClient.removeChannel(state.realtimeChannel).catch(() => {});
    state.realtimeChannel = null; state.realtimeClient = null; clearInterval(state.pollTimer);
  }

  async function startRealtime() {
    stopRealtime();
    state.pollTimer = setInterval(() => loadOrders({ silent: true }).catch((error) => { console.warn(error); setSync('error', '自動更新エラー'); }), 10000);
    try {
      const module = await import('https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.105.4/+esm');
      const client = module.createClient(SUPABASE_URL, ANON_KEY, { auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false } });
      client.realtime.setAuth(state.session.access_token);
      const channel = client.channel('korea-exhibition-orders').on('postgres_changes', { event: '*', schema: 'public', table: 'exhibition_orders' }, (payload) => loadOrders({ notify: payload.eventType === 'INSERT', silent: true }).catch(console.error)).subscribe((status) => {
        if (status === 'SUBSCRIBED') setSync('live', 'リアルタイム接続中');
        else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT' || status === 'CLOSED') setSync('error', '10秒ごとの自動更新へ切替');
      });
      state.realtimeClient = client; state.realtimeChannel = channel;
    } catch (error) {
      console.warn('Realtime unavailable', error);
      setSync('', '10秒ごとに自動更新');
    }
  }

  function switchTab(tab) {
    if (!['open', 'progress'].includes(tab)) return;
    state.activeTab = tab;
    document.querySelectorAll('[data-tab]').forEach((button) => button.classList.toggle('active', button.dataset.tab === tab));
    document.querySelectorAll('.primaryColumns .statusColumn').forEach((column) => column.classList.toggle('mobileHidden', column.id !== `column-${tab}`));
  }

  function attachEvents() {
    $('loginForm').addEventListener('submit', async (event) => {
      event.preventDefault();
      const button = $('loginButton'); button.disabled = true; $('loginMessage').textContent = 'ログイン中…';
      try {
        await signIn($('email').value.trim(), $('password').value);
        await loadStaffProfile();
        $('password').value = '';
        showDashboard(); await loadOrders(); await startRealtime();
      } catch (error) {
        saveSession(null); state.staff = null;
        $('loginMessage').textContent = error.message.includes('Invalid login') ? 'メールアドレスまたはパスワードが違います。' : `ログインできませんでした：${humanError(error)}`;
      } finally { button.disabled = false; }
    });
    $('logoutButton').addEventListener('click', signOut);
    $('refreshButton').addEventListener('click', () => withBusy(['refreshButton'], () => loadOrders()).catch((error) => showToast(`更新失敗：${humanError(error)}`)));
    $('historyButton').addEventListener('click', openHistory);
    $('historyTopClose').addEventListener('click', () => $('historyDialog').close());
    $('sentOrdersButton').addEventListener('click', () => { document.querySelector('.utilityMenu')?.removeAttribute('open'); $('sentOrdersDialog').showModal(); });
    $('sentOrdersTopClose').addEventListener('click', () => $('sentOrdersDialog').close());
    $('historyList').addEventListener('click', (event) => { const restore = event.target.closest('[data-restore-id]'); if (restore) withBusy([], () => restoreDeleted(restore.dataset.restoreId)).catch((error) => showToast(`復元失敗：${humanError(error)}`)); });
    $('batchButton').addEventListener('click', () => openBatchDialog().catch((error) => showToast(`送信準備失敗：${humanError(error)}`)));
    $('batchHistoryButton').addEventListener('click', () => openBatchHistory().catch((error) => showToast(`履歴表示失敗：${humanError(error)}`)));
    $('batchHistoryTopClose').addEventListener('click', () => $('batchHistoryDialog').close());
    $('batchTopClose').addEventListener('click', () => closeBatchDialog().catch((error) => showToast(humanError(error))));
    $('cancelBatchButton').addEventListener('click', () => closeBatchDialog().catch((error) => showToast(humanError(error))));
    $('batchDateSelect').addEventListener('change', () => selectBatchDateGroup($('batchDateSelect').value));
    $('batchSelectAll').addEventListener('change', () => {
      document.querySelectorAll('[data-batch-order]').forEach((input) => { if (!input.disabled) input.checked = $('batchSelectAll').checked; });
      updateBatchDialogSummary();
    });
    $('createBatchPdfButton').addEventListener('click', () => withBusy(['createBatchPdfButton'], createBatchPdf).catch((error) => showToast(`PDF準備失敗：${humanError(error)}`, 6000)));
    $('openBatchMailButton').addEventListener('click', openBatchMail);
    $('pdfSavedCheck').addEventListener('change', updateBatchSendEnabled);
    $('mailSentCheck').addEventListener('change', updateBatchSendEnabled);
    $('markBatchSentButton').addEventListener('click', () => withBusy(['markBatchSentButton'], markBatchSent).catch((error) => showToast(`送付済み登録失敗：${humanError(error)}`, 6000)));
    $('searchInput').addEventListener('input', render);
    $('eventFilter').addEventListener('change', () => { populateFilters(); render(); });
    $('dateFilter').addEventListener('change', render);
    $('showUnsentButton').addEventListener('click', () => { $('dateFilter').value = 'all'; render(); requestAnimationFrame(() => $('column-completed').scrollIntoView({ behavior: 'smooth', block: 'start' })); });
    $('soundButton').addEventListener('click', () => { state.soundEnabled = !state.soundEnabled; if (state.soundEnabled) { beep(); $('soundButton').textContent = '🔔 通知音ON'; } else $('soundButton').textContent = '🔕 通知音OFF'; });
    document.querySelectorAll('[data-tab]').forEach((button) => button.addEventListener('click', () => switchTab(button.dataset.tab)));
    $('detailTopClose').addEventListener('click', closeDetailSafely);
    $('closeDetail').addEventListener('click', closeDetailSafely);
    $('detailDialog').addEventListener('cancel', (event) => { event.preventDefault(); closeDetailSafely(); });
    $('startButton').addEventListener('click', () => withBusy(['startButton'], startOrder).catch((error) => showToast(`更新失敗：${humanError(error)}`)));
    $('completeButton').addEventListener('click', () => withBusy(['completeButton'], completeOrder).catch((error) => showToast(`確定失敗：${humanError(error)}`)));
    $('reopenButton').addEventListener('click', () => withBusy(['reopenButton'], reopenOrder).catch((error) => showToast(`更新失敗：${humanError(error)}`)));
    $('customerQrButton').addEventListener('click', openCustomerQr);
    $('customerQrTopClose').addEventListener('click', () => $('customerQrDialog').close());
    $('copyCustomerQrButton').addEventListener('click', () => copyCustomerQrUrl().catch((error) => showToast(`コピー失敗：${humanError(error)}`)));
    $('deleteButton').addEventListener('click', openDeleteDialog);
    $('printButton').addEventListener('click', () => withBusy(['printButton'], printCurrent).catch((error) => showToast(`印刷準備失敗：${humanError(error)}`)));
    $('deleteTopClose').addEventListener('click', () => $('deleteDialog').close());
    $('cancelDeleteButton').addEventListener('click', () => $('deleteDialog').close());
    $('deleteReason').addEventListener('change', () => $('deleteReasonOtherWrap').classList.toggle('hidden', $('deleteReason').value !== 'その他'));
    $('confirmDeleteButton').addEventListener('click', () => withBusy(['confirmDeleteButton'], confirmSoftDelete).catch((error) => showToast(`削除失敗：${humanError(error)}`, 6000)));
  }

  async function init() {
    attachEvents();
    if (!SUPABASE_URL || !ANON_KEY || !config.enabled) { showLogin('Supabase本番設定が未完了です。online-config.jsを確認してください。'); return; }
    loadStoredSession();
    if (!state.session) { showLogin(''); return; }
    try {
      await ensureToken(); await loadStaffProfile(); showDashboard(); await loadOrders(); await startRealtime();
    } catch (error) {
      console.warn(error); saveSession(null); state.staff = null; showLogin(`ログインできませんでした：${humanError(error)}`);
    }
  }

  window.addEventListener('DOMContentLoaded', init);
})();
