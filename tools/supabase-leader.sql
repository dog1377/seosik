-- 관리자 서식을 쓸 파트장 정하기 (수파베이스 SQL Editor 에서 실행)
-- 아래 이메일을 바꿔서 실행하세요. 여러 명이면 쉼표로 이어서.

-- 1) 파트장으로 정하기
update auth.users
set raw_app_meta_data = coalesce(raw_app_meta_data, '{}'::jsonb) || '{"dw_role":"leader"}'::jsonb
where email in ('seo@dwfuneral.com');

-- 2) 파트장에서 빼기
-- update auth.users set raw_app_meta_data = raw_app_meta_data - 'dw_role' where email in ('kim@dwfuneral.com');

-- 3) 누가 파트장인지 보기
select email, coalesce(raw_app_meta_data->>'dw_role', '') as role from auth.users order by email;
