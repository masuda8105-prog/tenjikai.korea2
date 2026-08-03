-- Authentication > Users でスタッフを作成した後に実行します。
-- メールアドレスと表示名を変更してください。
insert into public.exhibition_staff (user_id, display_name)
select id, '増田'
from auth.users
where email = 'staff@example.com'
on conflict (user_id)
do update set
  display_name = excluded.display_name,
  active = true;
