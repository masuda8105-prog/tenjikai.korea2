-- 安全な期限切れ注文cleanup Cronの再登録例です。
-- 1) REPLACE_WITH_LONG_RANDOM_SECRET を32文字以上のランダム値へ置換します。
-- 2) 同じ値を Edge Function の CLEANUP_SECRET に設定します。
-- 3) Supabase SQL Editorでこのファイルを実行します。
-- このファイルへ本物のsecretを保存・commitしないでください。

create extension if not exists pg_cron;
create extension if not exists pg_net;
create extension if not exists supabase_vault;

select vault.create_secret(
  'REPLACE_WITH_LONG_RANDOM_SECRET',
  'korea_exhibition_cleanup_secret',
  'cleanup-orders Cron only'
)
where not exists (
  select 1 from vault.decrypted_secrets where name = 'korea_exhibition_cleanup_secret'
);

do $$
declare
  existing_job_id bigint;
begin
  for existing_job_id in
    select jobid from cron.job where jobname = 'cleanup-expired-exhibition-orders'
  loop
    perform cron.unschedule(existing_job_id);
  end loop;

  perform cron.schedule(
    'cleanup-expired-exhibition-orders',
    '15 18 * * *',
    $job$
    select net.http_post(
      url := 'https://qdexhwgzawisiklekfzm.supabase.co/functions/v1/cleanup-orders',
      headers := jsonb_build_object(
        'Content-Type', 'application/json',
        'x-cleanup-secret', (
          select decrypted_secret
          from vault.decrypted_secrets
          where name = 'korea_exhibition_cleanup_secret'
          limit 1
        )
      ),
      body := '{}'::jsonb,
      timeout_milliseconds := 30000
    );
    $job$
  );
end $$;
