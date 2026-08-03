-- 自動削除Cronの確認用SQL（設定は01_schema.sqlで自動作成されます）
select jobid, jobname, schedule, active, command
from cron.job
where jobname = 'cleanup-expired-exhibition-orders';

-- 最近の実行結果
select jobid, status, return_message, start_time, end_time
from cron.job_run_details
where jobid in (select jobid from cron.job where jobname = 'cleanup-expired-exhibition-orders')
order by start_time desc
limit 20;
