-- DW 업무 앱 · 실시간 저장 (수파베이스) 준비
-- 수파베이스 화면 왼쪽 「SQL Editor」 → 「New query」 → 이 글 전체를 붙여 넣고 → 「Run」.
-- 여러 번 실행해도 괜찮습니다 (이미 있으면 그대로 둠).
--
-- 규칙: 각자 아이디로 로그인 → 내 기록은 나만 보고 고침 (다른 직원은 못 봄).
--       기록을 지워도 서버에는 「지움」 표시만 하고 내용은 남김 (실수로 지운 것 되살릴 수 있게).
--       더 오래된 내용이 새 내용을 덮어쓰지 못하게 서버에서 막음.

create table if not exists public.dw_records (
  user_id    uuid        not null default auth.uid() references auth.users(id) on delete cascade,
  app        text        not null,               -- 'funeral' = 장례일정 (관리자 서식 안 장례업무도 같음)
  kind       text        not null,               -- 'case' 행사 · 'env' 봉투 · 'state' 설정/휴무
  id         text        not null,
  data       jsonb,
  deleted    boolean     not null default false,
  updated_at bigint      not null default 0,     -- 앱에서 고친 시각 (밀리초)
  device     text,
  server_at  timestamptz not null default now(), -- 서버에 들어온 시각
  primary key (user_id, app, kind, id)
);

create index if not exists dw_records_pull on public.dw_records (user_id, app, server_at);

-- 더 오래된 내용은 덮어쓰지 않음 + 서버 시각 기록
create or replace function public.dw_records_guard() returns trigger
language plpgsql set search_path = '' as $$
begin
  if new.updated_at < old.updated_at then
    return null;            -- 오래된 내용이면 그대로 둠
  end if;
  if new.data is null then
    new.data := old.data;   -- 「지움」 표시만 올 때 내용은 남김
  end if;
  new.server_at := now();
  return new;
end $$;

drop trigger if exists dw_records_guard on public.dw_records;
create trigger dw_records_guard before update on public.dw_records
  for each row execute function public.dw_records_guard();

-- 내 기록만 (서버 규칙)
alter table public.dw_records enable row level security;

drop policy if exists "dw own select" on public.dw_records;
drop policy if exists "dw own insert" on public.dw_records;
drop policy if exists "dw own update" on public.dw_records;
create policy "dw own select" on public.dw_records for select to authenticated using ((select auth.uid()) = user_id);
create policy "dw own insert" on public.dw_records for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "dw own update" on public.dw_records for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
-- 지우기(delete) 규칙은 일부러 만들지 않음 → 앱에서는 기록을 완전히 지울 수 없음

revoke all on public.dw_records from anon;
grant select, insert, update on public.dw_records to authenticated;

-- 실시간 (다른 기기에서 고치면 바로 바뀌게)
do $$
begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'dw_records'
  ) then
    alter publication supabase_realtime add table public.dw_records;
  end if;
end $$;

select 'DW 준비 끝' as result;

-- ---------- 회원 탈퇴 (2026.10.23 추가) ----------
-- 로그인한 본인 계정만 지움. 서버에 있던 내 기록(dw_records)도 같이 지워짐. 이 기기(휴대폰) 기록은 남음.
create or replace function public.dw_delete_me() returns void
language plpgsql security definer set search_path = '' as $$
begin
  if auth.uid() is null then
    raise exception 'not signed in';
  end if;
  delete from auth.users where id = auth.uid();
end $$;
revoke all on function public.dw_delete_me() from public, anon;
grant execute on function public.dw_delete_me() to authenticated;

select 'DW 탈퇴 준비 끝' as result;
