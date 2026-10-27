-- DW장례업무 · 파트 · 파트 게시판 · 권한 준비 (2026.10.23, -6: 한 사람은 한 파트에만 · 파트장은 다른 파트를 못 봄, -7: 앱에서 파트장 정하기,
--   2026.10.26: 총괄실장 — 관리자가 앱에서 정함, 서식 · 회사 서류만 쓰고 파트장들의 서식 기록을 볼 수만 있음,
--   2026.10.27: 물품 수령 · 불출 장부 — 파트장끼리 같이 쓰는 장부 (부산 · 울산 · 창원 입고 · 불출 · 남은 수량))
-- 수파베이스 화면 왼쪽 「SQL Editor」 → 「New query」 → 이 글 전체를 붙여 넣고 → 「Run」.
-- 먼저 tools/supabase-setup.sql 을 실행해 둔 상태여야 합니다. 여러 번 실행해도 괜찮습니다.
--
-- 하는 일
--   · 직원 명단(아이디 · 이름): 가입하면 자동으로 생기고, 이미 있는 계정도 넣어 둠
--   · 파트: 파트장이 파트를 만들고 직원 아이디를 넣고 뺌
--   · 파트 게시판: 같은 파트 사람끼리만 보임. 파트장은 공지, 파트원도 글 · 댓글
--   · 한 직원은 한 파트에만 들어감. 파트장 계정은 다른 파트에 못 들어감 → 파트장은 자기 파트 게시판 · 파트원만 봄
--   · 파트장은 자기 파트원의 장례일정 · 봉투를 볼 수만 있음 (고치기 안 됨)
--   · 관리자(처음 실행할 때의 파트장)는 앱 설정 「직원 권한」에서 직원을 파트장 · 총괄실장으로 정하거나 직원으로 바꿀 수 있음
--   · 총괄실장은 파트장들이 올린 주간보고 · 회의록 · 후기 · 탁송을 볼 수만 있음 (고치기 안 됨, 장례 기록 · 게시판은 안 보임)
--   · 물품 수령 · 불출 장부: 파트장 모두가 같은 장부를 봄. 넣은 사람(과 관리자)만 고치고 지움, 지운 기록도 서버에 남음
-- 표는 앱에서 바로 건드릴 수 없고, 아래 함수(누가 무엇을 할 수 있는지 검사함)로만 읽고 씁니다.

-- ---------- 표 ----------
create table if not exists public.dw_profiles (
  user_id    uuid primary key references auth.users(id) on delete cascade,
  login_id   text not null unique,              -- 아이디 (아이디@dwfuneral.com 의 앞부분)
  name       text not null default '',
  created_at timestamptz not null default now()
);

create table if not exists public.dw_parts (
  id         uuid primary key default gen_random_uuid(),
  name       text not null,
  leader_id  uuid not null references public.dw_profiles(user_id) on delete cascade,
  created_at timestamptz not null default now()
);

create table if not exists public.dw_part_members (
  part_id  uuid not null references public.dw_parts(id) on delete cascade,
  user_id  uuid not null references public.dw_profiles(user_id) on delete cascade,
  added_at timestamptz not null default now(),
  primary key (part_id, user_id)
);
create index if not exists dw_part_members_user on public.dw_part_members (user_id);

create table if not exists public.dw_posts (
  id         uuid primary key default gen_random_uuid(),
  part_id    uuid not null references public.dw_parts(id) on delete cascade,
  author_id  uuid not null references public.dw_profiles(user_id) on delete cascade,
  notice     boolean not null default false,
  title      text not null default '',
  body       text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists dw_posts_part on public.dw_posts (part_id, created_at desc);

create table if not exists public.dw_comments (
  id         uuid primary key default gen_random_uuid(),
  post_id    uuid not null references public.dw_posts(id) on delete cascade,
  author_id  uuid not null references public.dw_profiles(user_id) on delete cascade,
  body       text not null,
  created_at timestamptz not null default now()
);
create index if not exists dw_comments_post on public.dw_comments (post_id, created_at);

-- 앱에서 표를 바로 못 건드리게 (함수로만)
alter table public.dw_profiles     enable row level security;
alter table public.dw_parts        enable row level security;
alter table public.dw_part_members enable row level security;
alter table public.dw_posts        enable row level security;
alter table public.dw_comments     enable row level security;
revoke all on public.dw_profiles, public.dw_parts, public.dw_part_members, public.dw_posts, public.dw_comments from anon, authenticated;

-- ---------- 도움 함수 (앱에서는 직접 못 부름) ----------
create or replace function public.dw_login_of(p_email text, p_id uuid) returns text
language sql immutable set search_path = '' as $$
  select case
    when lower(coalesce(p_email, '')) like '%@dwfuneral.com' then split_part(lower(p_email), '@', 1)
    when coalesce(p_email, '') <> '' then lower(p_email)
    else p_id::text end
$$;

create or replace function public.dw_profile_ensure(p_user uuid) returns void
language plpgsql security definer set search_path = '' as $$
begin
  insert into public.dw_profiles (user_id, login_id, name)
  select u.id, public.dw_login_of(u.email, u.id), left(btrim(coalesce(u.raw_user_meta_data ->> 'name', '')), 20)
  from auth.users u where u.id = p_user
  on conflict do nothing;
end $$;

create or replace function public.dw_is_leader(p_user uuid) returns boolean
language sql stable security definer set search_path = '' as $$
  select coalesce((select (u.raw_app_meta_data ->> 'dw_role') = 'leader' from auth.users u where u.id = p_user), false)
$$;

create or replace function public.dw_is_admin(p_user uuid) returns boolean
language sql stable security definer set search_path = '' as $$
  select coalesce((select (u.raw_app_meta_data ->> 'dw_admin') = 'true' from auth.users u where u.id = p_user), false)
$$;

create or replace function public.dw_is_chief(p_user uuid) returns boolean
language sql stable security definer set search_path = '' as $$
  select coalesce((select (u.raw_app_meta_data ->> 'dw_role') = 'chief' from auth.users u where u.id = p_user), false)
$$;

create or replace function public.dw_leads(p_part uuid, p_user uuid) returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.dw_parts t where t.id = p_part and t.leader_id = p_user) and public.dw_is_leader(p_user)
$$;

create or replace function public.dw_in_part(p_part uuid, p_user uuid) returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.dw_parts t where t.id = p_part and t.leader_id = p_user)
      or (exists (select 1 from public.dw_part_members m where m.part_id = p_part and m.user_id = p_user)
          and not public.dw_is_leader(p_user) and not public.dw_is_chief(p_user))   -- 파트장 · 총괄실장 계정은 파트 게시판을 못 봄
$$;

create or replace function public.dw_name(p_user uuid) returns text
language sql stable security definer set search_path = '' as $$
  select coalesce((select coalesce(nullif(p.name, ''), p.login_id) from public.dw_profiles p where p.user_id = p_user), '나간 직원')
$$;

-- 가입하면 명단에 자동으로
create or replace function public.dw_profile_new() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  begin
    perform public.dw_profile_ensure(new.id);
  exception when others then
    null;   -- 명단에 못 넣어도 가입은 막지 않음 (나중에 앱이 다시 넣음)
  end;
  return new;
end $$;
drop trigger if exists dw_profile_new on auth.users;
create trigger dw_profile_new after insert on auth.users for each row execute function public.dw_profile_new();

-- 이미 있는 계정도 명단에
insert into public.dw_profiles (user_id, login_id, name)
select u.id, public.dw_login_of(u.email, u.id), left(btrim(coalesce(u.raw_user_meta_data ->> 'name', '')), 20)
from auth.users u
on conflict do nothing;

-- 한 사람은 한 파트에만 · 파트장 계정은 파트원이 될 수 없음 (예전에 넣은 것도 정리: 파트장은 빼고, 두 파트에 있으면 먼저 넣은 파트만 남김)
delete from public.dw_part_members m
where public.dw_is_leader(m.user_id) or public.dw_is_chief(m.user_id) or exists (select 1 from public.dw_parts t where t.leader_id = m.user_id);
delete from public.dw_part_members a using public.dw_part_members b
where a.user_id = b.user_id and (a.added_at, a.part_id::text) > (b.added_at, b.part_id::text);
create unique index if not exists dw_part_members_one on public.dw_part_members (user_id);

-- 관리자(직원을 파트장으로 정할 수 있는 사람): 아직 아무도 없으면 지금 파트장을 관리자로 (처음 한 번)
update auth.users set raw_app_meta_data = coalesce(raw_app_meta_data, '{}'::jsonb) || '{"dw_admin": true}'::jsonb
where raw_app_meta_data ->> 'dw_role' = 'leader'
  and not exists (select 1 from auth.users x where x.raw_app_meta_data ->> 'dw_admin' = 'true');

-- ---------- 앱에서 부르는 함수 ----------
-- 내 정보 + 내가 속한 파트
create or replace function public.dw_me() returns jsonb
language plpgsql security definer set search_path = '' as $$
declare me uuid := auth.uid(); p public.dw_profiles;
begin
  if me is null then return jsonb_build_object('ok', false, 'why', 'login'); end if;
  perform public.dw_profile_ensure(me);
  select * into p from public.dw_profiles where user_id = me;
  return jsonb_build_object(
    'ok', true, 'user_id', me, 'login_id', p.login_id, 'name', p.name, 'leader', public.dw_is_leader(me), 'admin', public.dw_is_admin(me), 'chief', public.dw_is_chief(me),
    'parts', coalesce((
      select jsonb_agg(jsonb_build_object(
               'id', t.id, 'name', t.name, 'leader_id', t.leader_id, 'leader_name', public.dw_name(t.leader_id),
               'mine', t.leader_id = me,
               'members', (select count(*) from public.dw_part_members m where m.part_id = t.id))
             order by t.created_at)
      from public.dw_parts t
      where t.leader_id = me or exists (select 1 from public.dw_part_members m where m.part_id = t.id and m.user_id = me)
    ), '[]'::jsonb));
end $$;

-- 내 이름 바꾸기 (게시판에 보이는 이름)
create or replace function public.dw_set_name(p_name text) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare me uuid := auth.uid(); n text := left(btrim(coalesce(p_name, '')), 20);
begin
  if me is null then return jsonb_build_object('ok', false, 'why', 'login'); end if;
  perform public.dw_profile_ensure(me);
  update public.dw_profiles set name = n where user_id = me;
  return jsonb_build_object('ok', true, 'name', n);
end $$;

-- 파트 만들기 · 이름 바꾸기 · 없애기 (파트장만)
create or replace function public.dw_part_create(p_name text) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare me uuid := auth.uid(); n text := left(btrim(coalesce(p_name, '')), 30); v uuid;
begin
  if me is null then return jsonb_build_object('ok', false, 'why', 'login'); end if;
  if not public.dw_is_leader(me) then return jsonb_build_object('ok', false, 'why', 'notleader'); end if;
  if n = '' then return jsonb_build_object('ok', false, 'why', 'name'); end if;
  perform public.dw_profile_ensure(me);
  delete from public.dw_part_members where user_id = me;   -- 파트원이었다가 파트장이 되면 예전 파트에서 빠짐
  insert into public.dw_parts (name, leader_id) values (n, me) returning id into v;
  return jsonb_build_object('ok', true, 'id', v);
end $$;

create or replace function public.dw_part_rename(p_part uuid, p_name text) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare me uuid := auth.uid(); n text := left(btrim(coalesce(p_name, '')), 30);
begin
  if not public.dw_leads(p_part, me) then return jsonb_build_object('ok', false, 'why', 'notleader'); end if;
  if n = '' then return jsonb_build_object('ok', false, 'why', 'name'); end if;
  update public.dw_parts set name = n where id = p_part;
  return jsonb_build_object('ok', true);
end $$;

create or replace function public.dw_part_delete(p_part uuid) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare me uuid := auth.uid();
begin
  if not public.dw_leads(p_part, me) then return jsonb_build_object('ok', false, 'why', 'notleader'); end if;
  delete from public.dw_parts where id = p_part;   -- 파트원 명단 · 게시판 글 · 댓글도 같이 지워짐 (직원 계정과 장례 기록은 그대로)
  return jsonb_build_object('ok', true);
end $$;

-- 파트원 넣기 (아이디로) · 빼기 (파트장만)
create or replace function public.dw_part_add(p_part uuid, p_login text) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare me uuid := auth.uid(); l text := lower(btrim(coalesce(p_login, ''))); v uuid; n int;
begin
  if not public.dw_leads(p_part, me) then return jsonb_build_object('ok', false, 'why', 'notleader'); end if;
  if l like '%@dwfuneral.com' then l := split_part(l, '@', 1); end if;
  if l = '' then return jsonb_build_object('ok', false, 'why', 'nouser'); end if;
  select p.user_id into v from public.dw_profiles p where p.login_id = l;
  if v is null then
    select u.id into v from auth.users u where lower(u.email) in (l || '@dwfuneral.com', l) limit 1;
    if v is not null then perform public.dw_profile_ensure(v); end if;
  end if;
  if v is null or not exists (select 1 from public.dw_profiles p where p.user_id = v) then
    return jsonb_build_object('ok', false, 'why', 'nouser');
  end if;
  if v = me then return jsonb_build_object('ok', false, 'why', 'self'); end if;
  if public.dw_is_leader(v) or exists (select 1 from public.dw_parts t where t.leader_id = v) then
    return jsonb_build_object('ok', false, 'why', 'leader');   -- 파트장 계정은 파트원으로 못 넣음
  end if;
  if public.dw_is_chief(v) then return jsonb_build_object('ok', false, 'why', 'chief'); end if;   -- 총괄실장도 파트원으로 못 넣음
  if exists (select 1 from public.dw_part_members m where m.user_id = v and m.part_id <> p_part) then
    return jsonb_build_object('ok', false, 'why', 'otherpart');   -- 한 직원은 한 파트에만
  end if;
  insert into public.dw_part_members (part_id, user_id) values (p_part, v) on conflict do nothing;
  get diagnostics n = row_count;
  if n = 0 then return jsonb_build_object('ok', false, 'why', 'already'); end if;
  return jsonb_build_object('ok', true, 'user_id', v, 'name', public.dw_name(v));
end $$;

create or replace function public.dw_part_remove(p_part uuid, p_user uuid) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare me uuid := auth.uid();
begin
  if not public.dw_leads(p_part, me) then return jsonb_build_object('ok', false, 'why', 'notleader'); end if;
  delete from public.dw_part_members where part_id = p_part and user_id = p_user;
  return jsonb_build_object('ok', true);
end $$;

-- 파트 사람 명단 (파트장 + 파트원)
create or replace function public.dw_part_people(p_part uuid) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare me uuid := auth.uid();
begin
  if not public.dw_in_part(p_part, me) then return jsonb_build_object('ok', false, 'why', 'notmember'); end if;
  return jsonb_build_object('ok', true, 'people', coalesce((
    select jsonb_agg(x.o order by x.lead desc, x.nm)
    from (
      select true as lead, public.dw_name(t.leader_id) as nm,
             jsonb_build_object('user_id', p.user_id, 'login_id', p.login_id, 'name', p.name, 'leader', true, 'me', p.user_id = me) as o
      from public.dw_parts t join public.dw_profiles p on p.user_id = t.leader_id where t.id = p_part
      union all
      select false, public.dw_name(m.user_id),
             jsonb_build_object('user_id', p.user_id, 'login_id', p.login_id, 'name', p.name, 'leader', false, 'me', p.user_id = me, 'added_at', m.added_at)
      from public.dw_part_members m join public.dw_profiles p on p.user_id = m.user_id where m.part_id = p_part
    ) x), '[]'::jsonb));
end $$;

-- 게시판 글 목록 (공지 먼저, 새 글 먼저)
create or replace function public.dw_posts_list(p_part uuid, p_limit int default 100) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare me uuid := auth.uid(); lead boolean;
begin
  if not public.dw_in_part(p_part, me) then return jsonb_build_object('ok', false, 'why', 'notmember'); end if;
  lead := public.dw_leads(p_part, me);
  return jsonb_build_object('ok', true, 'posts', coalesce((
    select jsonb_agg(jsonb_build_object(
             'id', q.id, 'notice', q.notice, 'title', q.title, 'body', left(q.body, 300),
             'created_at', q.created_at, 'updated_at', q.updated_at,
             'author', public.dw_name(q.author_id), 'mine', q.author_id = me, 'can_delete', q.author_id = me or lead,
             'comments', (select count(*) from public.dw_comments c where c.post_id = q.id))
           order by q.notice desc, q.created_at desc)
    from (select * from public.dw_posts where part_id = p_part order by notice desc, created_at desc limit greatest(1, least(coalesce(p_limit, 100), 300))) q
  ), '[]'::jsonb));
end $$;

-- 글 하나 + 댓글
create or replace function public.dw_post_get(p_id uuid) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare me uuid := auth.uid(); q public.dw_posts; lead boolean;
begin
  select * into q from public.dw_posts where id = p_id;
  if q.id is null then return jsonb_build_object('ok', false, 'why', 'gone'); end if;
  if not public.dw_in_part(q.part_id, me) then return jsonb_build_object('ok', false, 'why', 'notmember'); end if;
  lead := public.dw_leads(q.part_id, me);
  return jsonb_build_object('ok', true, 'post', jsonb_build_object(
    'id', q.id, 'part_id', q.part_id, 'notice', q.notice, 'title', q.title, 'body', q.body,
    'created_at', q.created_at, 'updated_at', q.updated_at,
    'author', public.dw_name(q.author_id), 'mine', q.author_id = me, 'can_delete', q.author_id = me or lead,
    'comments', coalesce((
      select jsonb_agg(jsonb_build_object('id', c.id, 'body', c.body, 'created_at', c.created_at,
               'author', public.dw_name(c.author_id), 'mine', c.author_id = me, 'can_delete', c.author_id = me or lead)
             order by c.created_at)
      from public.dw_comments c where c.post_id = q.id), '[]'::jsonb)));
end $$;

-- 글 쓰기 · 고치기 (공지는 파트장만, 고치기는 쓴 사람만)
create or replace function public.dw_post_save(p_part uuid, p_id uuid, p_title text, p_body text, p_notice boolean) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare me uuid := auth.uid(); t text := left(btrim(coalesce(p_title, '')), 100); b text := left(coalesce(p_body, ''), 5000); v uuid; n int;
begin
  if not public.dw_in_part(p_part, me) then return jsonb_build_object('ok', false, 'why', 'notmember'); end if;
  if t = '' and btrim(b) = '' then return jsonb_build_object('ok', false, 'why', 'empty'); end if;
  if coalesce(p_notice, false) and not public.dw_leads(p_part, me) then return jsonb_build_object('ok', false, 'why', 'notleader'); end if;
  perform public.dw_profile_ensure(me);
  if p_id is null then
    insert into public.dw_posts (part_id, author_id, notice, title, body) values (p_part, me, coalesce(p_notice, false), t, b) returning id into v;
  else
    update public.dw_posts set title = t, body = b, notice = coalesce(p_notice, false), updated_at = now()
    where id = p_id and part_id = p_part and author_id = me returning id into v;
    if v is null then return jsonb_build_object('ok', false, 'why', 'denied'); end if;
  end if;
  return jsonb_build_object('ok', true, 'id', v);
end $$;

-- 글 지우기 (쓴 사람 또는 파트장)
create or replace function public.dw_post_delete(p_id uuid) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare me uuid := auth.uid(); q public.dw_posts;
begin
  select * into q from public.dw_posts where id = p_id;
  if q.id is null then return jsonb_build_object('ok', true); end if;
  if not (q.author_id = me or public.dw_leads(q.part_id, me)) then return jsonb_build_object('ok', false, 'why', 'denied'); end if;
  delete from public.dw_posts where id = p_id;
  return jsonb_build_object('ok', true);
end $$;

-- 댓글 달기 · 지우기 (지우기는 쓴 사람 또는 파트장)
create or replace function public.dw_comment_add(p_post uuid, p_body text) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare me uuid := auth.uid(); q public.dw_posts; b text := left(btrim(coalesce(p_body, '')), 1000); v uuid;
begin
  select * into q from public.dw_posts where id = p_post;
  if q.id is null then return jsonb_build_object('ok', false, 'why', 'gone'); end if;
  if not public.dw_in_part(q.part_id, me) then return jsonb_build_object('ok', false, 'why', 'notmember'); end if;
  if b = '' then return jsonb_build_object('ok', false, 'why', 'empty'); end if;
  perform public.dw_profile_ensure(me);
  insert into public.dw_comments (post_id, author_id, body) values (p_post, me, b) returning id into v;
  return jsonb_build_object('ok', true, 'id', v);
end $$;

create or replace function public.dw_comment_delete(p_id uuid) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare me uuid := auth.uid(); c public.dw_comments; part uuid;
begin
  select * into c from public.dw_comments where id = p_id;
  if c.id is null then return jsonb_build_object('ok', true); end if;
  select q.part_id into part from public.dw_posts q where q.id = c.post_id;
  if not (c.author_id = me or public.dw_leads(part, me)) then return jsonb_build_object('ok', false, 'why', 'denied'); end if;
  delete from public.dw_comments where id = p_id;
  return jsonb_build_object('ok', true);
end $$;

-- 홈 화면: 내 파트들의 최근 공지
create or replace function public.dw_notices(p_limit int default 3) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare me uuid := auth.uid();
begin
  if me is null then return jsonb_build_object('ok', false, 'why', 'login'); end if;
  return jsonb_build_object('ok', true, 'posts', coalesce((
    select jsonb_agg(jsonb_build_object('id', x.id, 'part_id', x.part_id, 'part_name', x.part_name, 'title', x.title,
             'body', left(x.body, 120), 'created_at', x.created_at, 'author', public.dw_name(x.author_id)) order by x.created_at desc)
    from (
      select q.*, t.name as part_name from public.dw_posts q join public.dw_parts t on t.id = q.part_id
      where q.notice and public.dw_in_part(q.part_id, me)
      order by q.created_at desc limit greatest(1, least(coalesce(p_limit, 3), 20))
    ) x), '[]'::jsonb));
end $$;

-- 파트장: 파트원의 장례일정 · 봉투 보기 (보기만 · 고치기 안 됨). p_month(예: '2026-10')를 주면 그 달 것만 (발인일 기준, 앱과 같은 계산)
create or replace function public.dw_member_records(p_part uuid, p_user uuid default null, p_month text default null)
returns table (owner uuid, rkind text, rid text, rdata jsonb, rupdated bigint)
language sql stable security definer set search_path = '' as $$
  select x.user_id, x.kind, x.id, x.data, x.updated_at
  from (
    select r.*,
      case r.kind
        when 'case' then left(coalesce(nullif(r.data #>> '{f,depart}', ''), nullif(r.data #>> '{f,cremDate}', ''), nullif(r.data #>> '{f,hagwanDate}', ''),
                                       nullif(r.data #>> '{f,death}', ''), nullif(r.data #>> '{f,recv}', ''), ''), 7)
        when 'env' then coalesce(case when (r.data -> 'edits') ? 'month' then r.data #>> '{edits,month}' else r.data #>> '{auto,month}' end, '')
        else '' end as mon
    from public.dw_records r
    where public.dw_leads(p_part, auth.uid())
      and exists (select 1 from public.dw_part_members m where m.part_id = p_part and m.user_id = r.user_id)
      and (p_user is null or r.user_id = p_user)
      and r.app = 'funeral' and not r.deleted and r.data is not null
      and (r.kind in ('case', 'env') or (r.kind = 'state' and r.id = 'settings'))
  ) x
  where p_month is null or x.kind = 'state' or x.mon = p_month or x.mon !~ '^[0-9]{4}-(0[1-9]|1[0-2])$'
  order by x.user_id, x.kind, x.id
$$;

-- 관리자: 직원 명단과 권한 보기 · 파트장으로 정하기 / 직원으로 바꾸기
create or replace function public.dw_people() returns jsonb
language plpgsql security definer set search_path = '' as $$
declare me uuid := auth.uid();
begin
  if not public.dw_is_admin(me) then return jsonb_build_object('ok', false, 'why', 'notadmin'); end if;
  insert into public.dw_profiles (user_id, login_id, name)
  select u.id, public.dw_login_of(u.email, u.id), left(btrim(coalesce(u.raw_user_meta_data ->> 'name', '')), 20) from auth.users u
  on conflict do nothing;
  return jsonb_build_object('ok', true, 'people', coalesce((
    select jsonb_agg(x.o order by x.rk, x.nm)
    from (
      select case when public.dw_is_chief(p.user_id) then 0 when public.dw_is_leader(p.user_id) then 1 else 2 end as rk, coalesce(nullif(p.name, ''), p.login_id) as nm,
             jsonb_build_object('user_id', p.user_id, 'login_id', p.login_id, 'name', p.name,
               'leader', public.dw_is_leader(p.user_id), 'chief', public.dw_is_chief(p.user_id), 'admin', public.dw_is_admin(p.user_id), 'me', p.user_id = me,
               'part', (select t.name from public.dw_part_members m join public.dw_parts t on t.id = m.part_id where m.user_id = p.user_id limit 1),
               'leads', (select count(*) from public.dw_parts t where t.leader_id = p.user_id)) as o
      from public.dw_profiles p
    ) x), '[]'::jsonb));
end $$;

create or replace function public.dw_set_role(p_user uuid, p_leader boolean) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare me uuid := auth.uid();
begin
  if not public.dw_is_admin(me) then return jsonb_build_object('ok', false, 'why', 'notadmin'); end if;
  if p_user = me then return jsonb_build_object('ok', false, 'why', 'self'); end if;
  if not exists (select 1 from auth.users u where u.id = p_user) then return jsonb_build_object('ok', false, 'why', 'nouser'); end if;
  if coalesce(p_leader, false) then
    update auth.users set raw_app_meta_data = coalesce(raw_app_meta_data, '{}'::jsonb) || '{"dw_role": "leader"}'::jsonb where id = p_user;
    delete from public.dw_part_members where user_id = p_user;   -- 파트장은 다른 파트의 파트원이 될 수 없음
  else
    update auth.users set raw_app_meta_data = coalesce(raw_app_meta_data, '{}'::jsonb) - 'dw_role' - 'dw_admin' where id = p_user;
  end if;
  return jsonb_build_object('ok', true);
end $$;

-- 관리자: 권한 정하기 (2026.10.26~ 앱은 이것을 씀) — p_role: 'leader'(파트장) · 'chief'(총괄실장) · 'member'(직원)
create or replace function public.dw_set_role_to(p_user uuid, p_role text) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare me uuid := auth.uid(); r text := lower(btrim(coalesce(p_role, '')));
begin
  if not public.dw_is_admin(me) then return jsonb_build_object('ok', false, 'why', 'notadmin'); end if;
  if p_user = me then return jsonb_build_object('ok', false, 'why', 'self'); end if;
  if r not in ('leader', 'chief', 'member') then return jsonb_build_object('ok', false, 'why', 'role'); end if;
  if not exists (select 1 from auth.users u where u.id = p_user) then return jsonb_build_object('ok', false, 'why', 'nouser'); end if;
  if r = 'member' then
    update auth.users set raw_app_meta_data = coalesce(raw_app_meta_data, '{}'::jsonb) - 'dw_role' - 'dw_admin' where id = p_user;
  elsif r = 'chief' then
    update auth.users set raw_app_meta_data = (coalesce(raw_app_meta_data, '{}'::jsonb) - 'dw_admin') || '{"dw_role": "chief"}'::jsonb where id = p_user;
    delete from public.dw_part_members where user_id = p_user;   -- 총괄실장은 파트원이 아님
  else
    update auth.users set raw_app_meta_data = coalesce(raw_app_meta_data, '{}'::jsonb) || '{"dw_role": "leader"}'::jsonb where id = p_user;
    delete from public.dw_part_members where user_id = p_user;   -- 파트장은 다른 파트의 파트원이 될 수 없음
  end if;
  return jsonb_build_object('ok', true);
end $$;

-- 총괄실장: 파트장 명단 (제출 현황을 보려고)
create or replace function public.dw_chief_leaders() returns jsonb
language plpgsql security definer set search_path = '' as $$
declare me uuid := auth.uid();
begin
  if not public.dw_is_chief(me) then return jsonb_build_object('ok', false, 'why', 'notchief'); end if;
  insert into public.dw_profiles (user_id, login_id, name)
  select u.id, public.dw_login_of(u.email, u.id), left(btrim(coalesce(u.raw_user_meta_data ->> 'name', '')), 20)
  from auth.users u where u.raw_app_meta_data ->> 'dw_role' = 'leader'
  on conflict do nothing;
  return jsonb_build_object('ok', true, 'leaders', coalesce((
    select jsonb_agg(jsonb_build_object('user_id', p.user_id, 'login_id', p.login_id, 'name', p.name,
             'parts', coalesce((select jsonb_agg(t.name order by t.created_at) from public.dw_parts t where t.leader_id = p.user_id), '[]'::jsonb))
           order by coalesce(nullif(p.name, ''), p.login_id))
    from public.dw_profiles p where public.dw_is_leader(p.user_id)
  ), '[]'::jsonb));
end $$;

-- 총괄실장: 파트장들이 올린 서식 기록 보기 (보기만). p_kind: weekly(주간보고, 주 시작일) · minute(회의록, 회의일) · review(후기, 출상일) · ship(탁송, 탁송일)
-- p_from ~ p_to (예: '2026-10-01' ~ '2026-10-31') 안의 것 + 각 파트장의 설정(파트명 · 작성자 · 회사명) · 후기 제목
create or replace function public.dw_chief_records(p_kind text, p_from text default null, p_to text default null)
returns table (owner uuid, rkind text, rid text, rdata jsonb, rupdated bigint)
language sql stable security definer set search_path = '' as $$
  select r.user_id, r.kind, r.id, r.data, r.updated_at
  from public.dw_records r
  where public.dw_is_chief(auth.uid())
    and p_kind in ('weekly', 'minute', 'review', 'ship')
    and r.app = 'forms' and not r.deleted and r.data is not null
    and public.dw_is_leader(r.user_id)
    and ((r.kind = 'state' and r.id in ('settings', 'reviewTitle'))
      or (r.kind = p_kind
          and (case r.kind when 'weekly' then coalesce(r.data ->> 'weekStart', '') when 'review' then r.id else coalesce(r.data ->> 'date', '') end)
              between coalesce(nullif(p_from, ''), '0000') and coalesce(nullif(p_to, ''), '9999')))
  order by r.user_id, r.kind, r.id
$$;

-- ---------- 물품 수령 · 불출 장부 (2026.10.27) ----------
-- 파트장끼리 같이 쓰는 장부. 부산 · 울산 · 창원에 들어온(입고) · 내보낸(불출) 자잘한 물품을 적고, 남은 수량은 앱이 셈.
-- 지우기는 「지움」 표시만 (내용은 남음, 되돌리기 됨). 앱에서 고친 시각(updated_at, ms)이 더 오래된 내용은 무시.
create table if not exists public.dw_stock (
  id         text primary key,                 -- 앱이 만든 번호 (인터넷이 끊겨도 먼저 적어 둘 수 있게)
  kind       text not null check (kind in ('in', 'out')),   -- in = 입고(받음) · out = 불출(내보냄)
  loc        text not null,                    -- 부산 · 울산 · 창원
  item       text not null,                    -- 품목
  qty        integer not null check (qty > 0),
  day        date not null,                    -- 받은 날 · 내보낸 날
  party      text not null default '',         -- 입고: 보낸 곳 · 불출: 받는 곳(사람)
  memo       text not null default '',
  author_id  uuid references public.dw_profiles(user_id) on delete set null,   -- 넣은 사람 (탈퇴해도 기록은 남음)
  editor_id  uuid references public.dw_profiles(user_id) on delete set null,   -- 마지막으로 고친 사람
  deleted    boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at bigint not null default 0,
  server_at  timestamptz not null default clock_timestamp()
);
create index if not exists dw_stock_server_at on public.dw_stock (server_at);
alter table public.dw_stock enable row level security;
revoke all on public.dw_stock from anon, authenticated;

-- 장부 받기 (파트장만). p_since 를 주면 그 뒤에 바뀐 것만 (지운 것 포함), 안 주면 지금 살아 있는 것 전부
create or replace function public.dw_stock_list(p_since text default null) returns jsonb
language plpgsql stable security definer set search_path = '' as $$
declare me uuid := auth.uid(); adm boolean; since timestamptz;
begin
  if not public.dw_is_leader(me) then return jsonb_build_object('ok', false, 'why', 'notleader'); end if;
  adm := public.dw_is_admin(me);
  begin since := nullif(btrim(coalesce(p_since, '')), '')::timestamptz; exception when others then since := null; end;
  return jsonb_build_object('ok', true, 'full', since is null, 'rows', coalesce((
    select jsonb_agg(jsonb_build_object(
             'id', s.id, 'kind', s.kind, 'loc', s.loc, 'item', s.item, 'qty', s.qty, 'day', to_char(s.day, 'YYYY-MM-DD'),
             'party', s.party, 'memo', s.memo, 'deleted', s.deleted, 'created_at', s.created_at, 'updated_at', s.updated_at, 'server_at', s.server_at,
             'author', case when s.author_id is null then '나간 직원' else public.dw_name(s.author_id) end,
             'editor', case when s.editor_id is null or s.editor_id = s.author_id then '' else public.dw_name(s.editor_id) end,
             'mine', coalesce(s.author_id = me, false), 'can_edit', coalesce(s.author_id = me, false) or adm)
           order by s.server_at)
    from public.dw_stock s
    where (since is null and not s.deleted) or s.server_at > since - interval '2 minutes'   -- 2분 겹쳐서 받음 (동시에 저장된 것을 놓치지 않게)
  ), '[]'::jsonb));
end $$;

-- 장부 한 줄 넣기 · 고치기 · 지우기(deleted true) · 되돌리기(deleted false). 고치기 · 지우기는 넣은 사람 또는 관리자만
create or replace function public.dw_stock_save(p jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare me uuid := auth.uid(); old public.dw_stock;
  v_id text := btrim(coalesce(p ->> 'id', ''));
  k text := coalesce(p ->> 'kind', '');
  l text := left(btrim(coalesce(p ->> 'loc', '')), 20);
  it text := left(btrim(regexp_replace(coalesce(p ->> 'item', ''), '\s+', ' ', 'g')), 60);
  pa text := left(btrim(coalesce(p ->> 'party', '')), 60);
  mm text := left(coalesce(p ->> 'memo', ''), 500);
  q integer; d date; up bigint; del boolean;
begin
  if not public.dw_is_leader(me) then return jsonb_build_object('ok', false, 'why', 'notleader'); end if;
  if v_id = '' or length(v_id) > 40 or v_id !~ '^[A-Za-z0-9_-]+$' then return jsonb_build_object('ok', false, 'why', 'bad'); end if;
  if k not in ('in', 'out') or l = '' or it = '' then return jsonb_build_object('ok', false, 'why', 'empty'); end if;
  begin
    q := (p ->> 'qty')::integer; d := (p ->> 'day')::date;
    up := coalesce((p ->> 'updated_at')::bigint, 0); del := coalesce((p ->> 'deleted')::boolean, false);
  exception when others then return jsonb_build_object('ok', false, 'why', 'bad'); end;
  if q is null or q < 1 or q > 1000000 or d is null then return jsonb_build_object('ok', false, 'why', 'bad'); end if;
  perform public.dw_profile_ensure(me);
  select * into old from public.dw_stock where id = v_id for update;
  if old.id is null then
    insert into public.dw_stock (id, kind, loc, item, qty, day, party, memo, author_id, editor_id, deleted, updated_at, server_at)
    values (v_id, k, l, it, q, d, pa, mm, me, me, del, up, clock_timestamp());
    return jsonb_build_object('ok', true, 'id', v_id);
  end if;
  if not (coalesce(old.author_id = me, false) or public.dw_is_admin(me)) then return jsonb_build_object('ok', false, 'why', 'denied'); end if;
  if up < old.updated_at then return jsonb_build_object('ok', true, 'id', v_id, 'stale', true); end if;   -- 더 나중에 고친 것이 이미 있음
  update public.dw_stock set kind = k, loc = l, item = it, qty = q, day = d, party = pa, memo = mm,
         editor_id = me, deleted = del, updated_at = up, server_at = clock_timestamp()
   where id = v_id;
  return jsonb_build_object('ok', true, 'id', v_id);
end $$;

-- ---------- 누가 부를 수 있는지 ----------
revoke all on function public.dw_login_of(text, uuid)          from public, anon, authenticated;
revoke all on function public.dw_profile_ensure(uuid)          from public, anon, authenticated;
revoke all on function public.dw_is_leader(uuid)               from public, anon, authenticated;
revoke all on function public.dw_is_admin(uuid)                from public, anon, authenticated;
revoke all on function public.dw_is_chief(uuid)                from public, anon, authenticated;
revoke all on function public.dw_leads(uuid, uuid)             from public, anon, authenticated;
revoke all on function public.dw_in_part(uuid, uuid)           from public, anon, authenticated;
revoke all on function public.dw_name(uuid)                    from public, anon, authenticated;
revoke all on function public.dw_profile_new()                 from public, anon, authenticated;

revoke all on function public.dw_me()                                        from public, anon;
revoke all on function public.dw_people()                                    from public, anon;
revoke all on function public.dw_set_role(uuid, boolean)                     from public, anon;
revoke all on function public.dw_set_name(text)                              from public, anon;
revoke all on function public.dw_part_create(text)                           from public, anon;
revoke all on function public.dw_part_rename(uuid, text)                     from public, anon;
revoke all on function public.dw_part_delete(uuid)                           from public, anon;
revoke all on function public.dw_part_add(uuid, text)                        from public, anon;
revoke all on function public.dw_part_remove(uuid, uuid)                     from public, anon;
revoke all on function public.dw_part_people(uuid)                           from public, anon;
revoke all on function public.dw_posts_list(uuid, int)                       from public, anon;
revoke all on function public.dw_post_get(uuid)                              from public, anon;
revoke all on function public.dw_post_save(uuid, uuid, text, text, boolean)  from public, anon;
revoke all on function public.dw_post_delete(uuid)                           from public, anon;
revoke all on function public.dw_comment_add(uuid, text)                     from public, anon;
revoke all on function public.dw_comment_delete(uuid)                        from public, anon;
revoke all on function public.dw_notices(int)                                from public, anon;
revoke all on function public.dw_member_records(uuid, uuid, text)            from public, anon;
revoke all on function public.dw_set_role_to(uuid, text)                     from public, anon;
revoke all on function public.dw_chief_leaders()                             from public, anon;
revoke all on function public.dw_chief_records(text, text, text)             from public, anon;
revoke all on function public.dw_stock_list(text)                         from public, anon;
revoke all on function public.dw_stock_save(jsonb)                        from public, anon;

grant execute on function public.dw_me()                                        to authenticated;
grant execute on function public.dw_people()                                    to authenticated;
grant execute on function public.dw_set_role(uuid, boolean)                     to authenticated;
grant execute on function public.dw_set_name(text)                              to authenticated;
grant execute on function public.dw_part_create(text)                           to authenticated;
grant execute on function public.dw_part_rename(uuid, text)                     to authenticated;
grant execute on function public.dw_part_delete(uuid)                           to authenticated;
grant execute on function public.dw_part_add(uuid, text)                        to authenticated;
grant execute on function public.dw_part_remove(uuid, uuid)                     to authenticated;
grant execute on function public.dw_part_people(uuid)                           to authenticated;
grant execute on function public.dw_posts_list(uuid, int)                       to authenticated;
grant execute on function public.dw_post_get(uuid)                              to authenticated;
grant execute on function public.dw_post_save(uuid, uuid, text, text, boolean)  to authenticated;
grant execute on function public.dw_post_delete(uuid)                           to authenticated;
grant execute on function public.dw_comment_add(uuid, text)                     to authenticated;
grant execute on function public.dw_comment_delete(uuid)                        to authenticated;
grant execute on function public.dw_notices(int)                                to authenticated;
grant execute on function public.dw_member_records(uuid, uuid, text)            to authenticated;
grant execute on function public.dw_set_role_to(uuid, text)                     to authenticated;
grant execute on function public.dw_chief_leaders()                             to authenticated;
grant execute on function public.dw_chief_records(text, text, text)             to authenticated;
grant execute on function public.dw_stock_list(text)                         to authenticated;
grant execute on function public.dw_stock_save(jsonb)                        to authenticated;

select 'DW 파트 · 게시판 · 물품 장부 준비 끝' as result;
