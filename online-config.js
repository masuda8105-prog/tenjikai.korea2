/*
 * 韓国展示会 注文ツール 本番設定
 * Publishable key はブラウザ公開用です。Secret key / service_role は絶対に記載しないでください。
 */
window.ORDER_ONLINE_CONFIG = Object.freeze({
  enabled: true,
  supabaseUrl: 'https://qdexhwgzawisiklekfzm.supabase.co',
  anonKey: 'sb_publishable__mWzF7WQI5BimtlT4Rmglg_9IRh25LV',
  publicAppUrl: 'https://masuda8105-prog.github.io/korea-exibition-sannishimura/',
  functionName: 'exhibition-order',
  staffPage: 'staff.html',
  orderRetentionDays: 14
});
