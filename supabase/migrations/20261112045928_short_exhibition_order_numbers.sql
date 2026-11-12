begin;

create sequence public.exhibition_staff_order_number_seq
  as bigint
  start with 1
  no cycle;

-- Reserve existing short numbers without changing either stored order number.
with used_numbers as (
  select substring(order_no from '^K-([0-9]+)$')::numeric as number
  from public.exhibition_orders
  where order_no ~ '^K-[0-9]+$'
), last_number as (
  select max(number) as number
  from used_numbers
  where number between 1 and 9223372036854775807
)
select setval('public.exhibition_staff_order_number_seq',
              coalesce(number, 1)::bigint, number is not null)
from last_number;

revoke all on sequence public.exhibition_staff_order_number_seq from public, anon, authenticated;
grant usage on sequence public.exhibition_staff_order_number_seq to service_role;

create function public.next_korea_staff_order_no()
returns text
language sql
volatile
security invoker
set search_path = ''
as $$
  select 'K-' || lpad(number, greatest(4, length(number)), '0')
  from (
    select nextval('public.exhibition_staff_order_number_seq'::regclass)::text as number
  ) as allocated;
$$;

revoke all on function public.next_korea_staff_order_no() from public, anon, authenticated;
grant execute on function public.next_korea_staff_order_no() to service_role;

commit;
