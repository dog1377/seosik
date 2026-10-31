"""테스트용 가짜 수파베이스 서버 — tools/supabase-part.sql 의 함수와 같은 규칙 (실제 서버에 연결하지 않음).
tools/test/smoke.py 가 씀. 서버 함수를 바꾸면 여기도 같이 바꾼다."""
import copy, itertools, datetime, uuid
CNT=itertools.count()
def case_month(d):
    """행사 달 = 접수한 달 (2026.10.31, 앱 caseMonth · 서버 dw_member_records 와 같은 계산)"""
    import re
    f=d.get('f') or {}; rv=str(f.get('recv') or '')[:7]
    if re.match(r'^\d{4}-(0[1-9]|1[0-2])$',rv): return rv
    cr=d.get('created'); dep=str(f.get('depart') or '')[:10]
    if isinstance(cr,(int,float)) and 1e12<=cr<1e13:
        cd=(datetime.datetime.utcfromtimestamp(cr/1000)+datetime.timedelta(hours=9)).strftime('%Y-%m-%d')
        if not re.match(r'^\d{4}-\d{2}-\d{2}$',dep) or cd<=dep: return cd[:7]
    return next((str(f.get(x)) for x in ['depart','cremDate','hagwanDate','death'] if f.get(x)),'')[:7]
def now_iso(): return (datetime.datetime(2026,10,23,9)+datetime.timedelta(seconds=next(CNT))).isoformat()+'+00:00'
class Srv:
    def __init__(s):
        s.USERS={}; s.ROWS={}; s.PROF={}; s.PARTS={}; s.MEM=[]; s.POSTS={}; s.CMTS={}; s.STOCK={}; s.OBJ={}; s.DOCS={}; s.MADE={}; s.UNMIX=[]; s.noserver=False; s.calls=[]
    def add_user(s,login,pw,leader=False,name='',chief=False,admin=False):
        email=login if '@' in login else login+'@dwfuneral.com'; lid=login.split('@')[0] if email.endswith('@dwfuneral.com') else email
        am={'dw_role':'leader'} if leader else {'dw_role':'chief'} if chief else {}
        if admin: am['dw_admin']=True
        uid='uid-'+login.split('@')[0]; s.USERS[email]=[pw,uid,am,{'name':name} if name else {}]
        s.PROF[uid]={'login_id':lid,'name':name}; s.MADE[uid]=1792710000000+len(s.MADE)*86400000; return uid
    # auth
    def auth(s,src,email,pw):
        u=s.USERS.get(email)
        if not u or u[0]!=pw: return {'error':'bad'}
        return {'user':{'id':u[1],'email':email,'app_metadata':dict(u[2]),'user_metadata':dict(u[3])}}
    def signup(s,src,email,pw,meta):
        if email in s.USERS: return {'error':'User already registered'}
        uid='uid-'+email.split('@')[0]; s.USERS[email]=[pw,uid,{},meta]; s.MADE[uid]=1792710000000+len(s.MADE)*86400000; s.PROF[uid]={'login_id':email.split('@')[0] if email.endswith('@dwfuneral.com') else email,'name':meta.get('name','')}
        return {'user':{'id':uid,'email':email,'app_metadata':{},'user_metadata':meta}}
    def getuser(s,src,uid):
        for e,u in s.USERS.items():
            if u[1]==uid: return {'user':{'id':uid,'email':e,'app_metadata':dict(u[2]),'user_metadata':dict(u[3])}}
        return {'error':{'message':'User not found','status':403}}
    def select(s,src,uid,app,since,a,b):
        rs=sorted([r for (u,ap,k,i),r in s.ROWS.items() if u==uid and ap==app and (not since or r['server_at']>since)],key=lambda r:r['server_at']); return copy.deepcopy(rs[a:b+1])
    def upsert(s,src,uid,rows):
        for r in rows:
            if r.get('user_id')!=uid: return {'error':{'message':'rls'}}
            k=(r['user_id'],r['app'],r['kind'],r['id']); old=s.ROWS.get(k)
            if old and r['updated_at']<old['updated_at']: continue
            n=dict(old or {}); n.update(r)
            if old and r.get('data') is None: n['data']=old['data']
            n['server_at']=now_iso(); s.ROWS[k]=n
        return {'ok':True}
    # helpers
    def leader(s,uid): return any(u[1]==uid and u[2].get('dw_role')=='leader' for u in s.USERS.values())
    def admin(s,uid): return any(u[1]==uid and u[2].get('dw_admin') is True for u in s.USERS.values())
    def chief(s,uid): return any(u[1]==uid and u[2].get('dw_role')=='chief' for u in s.USERS.values())
    def f_dw_people(s,me):
        if not s.admin(me): return s.no('notadmin')
        out=[]
        for uid,p in s.PROF.items():
            part=next((s.PARTS[a]['name'] for a,b,_ in s.MEM if b==uid and a in s.PARTS),None)
            out.append(dict(user_id=uid,login_id=p['login_id'],name=p['name'],leader=s.leader(uid),chief=s.chief(uid),admin=s.admin(uid),me=uid==me,part=part,leads=sum(1 for t in s.PARTS.values() if t['leader_id']==uid)))
        out.sort(key=lambda x:(0 if x['chief'] else 1 if x['leader'] else 2,x['name'] or x['login_id']))
        return s.ok(people=out)
    def f_dw_set_role(s,me,p_user,p_leader):
        if not s.admin(me): return s.no('notadmin')
        if p_user==me: return s.no('self')
        u=next((u for u in s.USERS.values() if u[1]==p_user),None)
        if not u: return s.no('nouser')
        if p_leader: u[2]['dw_role']='leader'; s.MEM=[m for m in s.MEM if m[1]!=p_user]
        else: u[2].pop('dw_role',None); u[2].pop('dw_admin',None)
        return s.ok()
    def f_dw_set_role_to(s,me,p_user,p_role):
        if not s.admin(me): return s.no('notadmin')
        if p_user==me: return s.no('self')
        r=str(p_role or '').strip().lower()
        if r not in ('leader','chief','member'): return s.no('role')
        u=next((u for u in s.USERS.values() if u[1]==p_user),None)
        if not u: return s.no('nouser')
        if r=='member': u[2].pop('dw_role',None); u[2].pop('dw_admin',None)
        else:
            if r=='chief': u[2].pop('dw_admin',None)
            u[2]['dw_role']=r; s.MEM=[m for m in s.MEM if m[1]!=p_user]
        return s.ok()
    def f_dw_chief_leaders(s,me):
        if not s.chief(me): return s.no('notchief')
        out=[dict(user_id=uid,login_id=p['login_id'],name=p['name'],parts=[t['name'] for t in sorted(s.PARTS.values(),key=lambda t:t['created']) if t['leader_id']==uid]) for uid,p in s.PROF.items() if s.leader(uid)]
        return s.ok(leaders=sorted(out,key=lambda x:x['name'] or x['login_id']))
    def f_dw_chief_records(s,me,p_kind,p_from=None,p_to=None):
        if not s.chief(me) or p_kind not in ('weekly','minute','review','ship'): return []
        lo=p_from or '0000'; hi=p_to or '9999'; out=[]
        for (u,ap,k,i),r in sorted(s.ROWS.items()):
            if ap!='forms' or r.get('deleted') or r.get('data') is None or not s.leader(u): continue
            d=r['data']
            if k=='state' and i in ('settings','reviewTitle'): pass
            elif k==p_kind:
                key=str(d.get('weekStart') or '') if k=='weekly' else i if k=='review' else str(d.get('date') or '')
                if not (lo<=key<=hi): continue
            else: continue
            out.append(dict(owner=u,rkind=k,rid=i,rdata=d,rupdated=r['updated_at']))
        return out
    def leads(s,p,uid): return p in s.PARTS and s.PARTS[p]['leader_id']==uid and s.leader(uid)
    def inpart(s,p,uid): return p in s.PARTS and (s.PARTS[p]['leader_id']==uid or ((p,uid) in [(a,b) for a,b,_ in s.MEM] and not s.leader(uid) and not s.chief(uid)))
    def name(s,uid): p=s.PROF.get(uid); return (p['name'] or p['login_id']) if p else '나간 직원'
    def rpc(s,src,fn,uid,args,rng):
        s.calls.append(fn)
        if fn=='dw_delete_me':
            for e in [e for e,u in s.USERS.items() if u[1]==uid]: del s.USERS[e]
            return {'data':None}
        if s.noserver: return {'error':{'message':'Could not find the function public.'+fn,'code':'PGRST202'}}
        f=getattr(s,'f_'+fn,None)
        if not f: return {'error':{'message':'Could not find the function','code':'PGRST202'}}
        d=f(uid,**args)
        if rng is not None and isinstance(d,list): d=d[rng[0]:rng[1]+1]
        return {'data':copy.deepcopy(d)}
    def ok(s,**k): k['ok']=True; return k
    def no(s,why): return {'ok':False,'why':why}
    def f_dw_me(s,me):
        p=s.PROF[me]; parts=[]
        for pid,t in sorted(s.PARTS.items(),key=lambda x:x[1]['created']):
            if s.inpart(pid,me): parts.append({'id':pid,'name':t['name'],'leader_id':t['leader_id'],'leader_name':s.name(t['leader_id']),'mine':t['leader_id']==me,'members':sum(1 for a,b,_ in s.MEM if a==pid)})
        u=s.user_of(me)
        return s.ok(user_id=me,login_id=p['login_id'],name=p['name'],leader=s.leader(me),admin=s.admin(me),chief=s.chief(me),parts=parts,
                    phone=p.get('phone',''),rank=p.get('rank',''),info_at=p.get('info_at',0),pw_reset=bool(u and u[2].get('dw_pw_reset')))
    def f_dw_set_name(s,me,p_name): s.PROF[me]['name']=p_name.strip()[:20]; s.PROF[me]['info_at']=s.now_ms(); return s.ok(name=s.PROF[me]['name'])
    # 내 정보 · 비밀번호 초기화 (2026.10.29)
    def now_ms(s): import time; return int(time.time()*1000)
    def user_of(s,uid): return next((u for u in s.USERS.values() if u[1]==uid),None)
    def f_dw_set_me(s,me,p):
        if not isinstance(p,dict): return s.no('bad')
        r=s.PROF[me]; t=int(p['at']) if str(p.get('at','')).isdigit() and len(str(p['at']))<=15 else 0; now=s.now_ms()
        if t<=0 or t>now+86400000: t=now
        if t>=r.get('info_at',0):
            for k in ('name','phone','rank'):
                if k in p: r[k]=str(p.get(k) or '').strip()[:20]
            r['info_at']=t; return s.ok(name=r['name'],phone=r.get('phone',''),rank=r.get('rank',''),info_at=t)
        return s.ok(stale=True,name=r['name'],phone=r.get('phone',''),rank=r.get('rank',''),info_at=r.get('info_at',0))
    def f_dw_reset_pw(s,me,p_user):
        if not p_user or p_user==me: return s.no('self')
        u=s.user_of(p_user)
        if not u: return s.no('nouser')
        ok=s.admin(me) or (s.leader(me) and any(b==p_user and s.PARTS.get(a,{}).get('leader_id')==me for a,b,_ in s.MEM) and not s.leader(p_user) and not s.chief(p_user) and not s.admin(p_user))
        if not ok: return s.no('deny')
        u[0]='12345678a'; u[2]['dw_pw_reset']=True
        return s.ok(name=s.name(p_user),pw='12345678a')
    def f_dw_pw_reset_done(s,me):
        u=s.user_of(me)
        if u[0]=='12345678a': return s.no('same')
        u[2].pop('dw_pw_reset',None); return s.ok()
    def updatepw(s,src,uid,pw):
        u=s.user_of(uid)
        if not u: return {'error':{'message':'User not found','status':403}}
        if len(pw)<6: return {'error':{'message':'Password should be at least 6 characters.','code':'weak_password','status':422}}
        if pw==u[0]: return {'error':{'message':'New password should be different from the old password.','code':'same_password','status':422}}
        u[0]=pw; return s.getuser(src,uid)
    def f_dw_part_create(s,me,p_name):
        if not s.leader(me): return s.no('notleader')
        n=p_name.strip()[:30]
        if not n: return s.no('name')
        s.MEM=[m for m in s.MEM if m[1]!=me]
        pid=str(uuid.uuid4()); s.PARTS[pid]={'name':n,'leader_id':me,'created':next(CNT)}; return s.ok(id=pid)
    def f_dw_part_rename(s,me,p_part,p_name):
        if not s.leads(p_part,me): return s.no('notleader')
        if not p_name.strip(): return s.no('name')
        s.PARTS[p_part]['name']=p_name.strip()[:30]; return s.ok()
    def f_dw_part_delete(s,me,p_part):
        if not s.leads(p_part,me): return s.no('notleader')
        del s.PARTS[p_part]; s.MEM=[m for m in s.MEM if m[0]!=p_part]
        for k in [k for k,q in s.POSTS.items() if q['part_id']==p_part]:
            del s.POSTS[k]
            for c in [c for c,v in s.CMTS.items() if v['post_id']==k]: del s.CMTS[c]
        return s.ok()
    def f_dw_part_add(s,me,p_part,p_login):
        if not s.leads(p_part,me): return s.no('notleader')
        l=p_login.strip().lower()
        if l.endswith('@dwfuneral.com'): l=l.split('@')[0]
        v=next((u for u,p in s.PROF.items() if p['login_id']==l),None)
        if not v: return s.no('nouser')
        if v==me: return s.no('self')
        if s.leader(v) or any(t['leader_id']==v for t in s.PARTS.values()): return s.no('leader')
        if s.chief(v): return s.no('chief')
        if any(b==v and a!=p_part for a,b,_ in s.MEM): return s.no('otherpart')
        if any(a==p_part and b==v for a,b,_ in s.MEM): return s.no('already')
        s.MEM.append((p_part,v,now_iso())); return s.ok(user_id=v,name=s.name(v))
    def f_dw_part_remove(s,me,p_part,p_user):
        if not s.leads(p_part,me): return s.no('notleader')
        s.MEM=[m for m in s.MEM if not (m[0]==p_part and m[1]==p_user)]; return s.ok()
    def f_dw_part_people(s,me,p_part):
        if not s.inpart(p_part,me): return s.no('notmember')
        L=s.PARTS[p_part]['leader_id']; out=[dict(user_id=L,login_id=s.PROF[L]['login_id'],name=s.PROF[L]['name'],leader=True,me=L==me)]
        mem=[dict(user_id=b,login_id=s.PROF[b]['login_id'],name=s.PROF[b]['name'],leader=False,me=b==me,added_at=t) for a,b,t in s.MEM if a==p_part]
        return s.ok(people=out+sorted(mem,key=lambda x:x['name'] or x['login_id']))
    def post_json(s,q,me,lead,full=False):
        d=dict(id=q['id'],notice=q['notice'],title=q['title'],body=q['body'] if full else q['body'][:300],created_at=q['created_at'],updated_at=q['updated_at'],author=s.name(q['author_id']),mine=q['author_id']==me,can_delete=q['author_id']==me or lead)
        if full:
            d['part_id']=q['part_id']
            d['comments']=[dict(id=c['id'],body=c['body'],created_at=c['created_at'],author=s.name(c['author_id']),mine=c['author_id']==me,can_delete=c['author_id']==me or lead) for c in sorted(s.CMTS.values(),key=lambda c:c['created_at']) if c['post_id']==q['id']]
        else: d['comments']=sum(1 for c in s.CMTS.values() if c['post_id']==q['id'])
        return d
    def f_dw_posts_list(s,me,p_part,p_limit=100):
        if not s.inpart(p_part,me): return s.no('notmember')
        lead=s.leads(p_part,me); qs=sorted([q for q in s.POSTS.values() if q['part_id']==p_part],key=lambda q:(not q['notice'],[-ord(ch) for ch in q['created_at']]))
        return s.ok(posts=[s.post_json(q,me,lead) for q in qs[:p_limit]])
    def f_dw_post_get(s,me,p_id):
        q=s.POSTS.get(p_id)
        if not q: return s.no('gone')
        if not s.inpart(q['part_id'],me): return s.no('notmember')
        return s.ok(post=s.post_json(q,me,s.leads(q['part_id'],me),True))
    def f_dw_post_save(s,me,p_part,p_id,p_title,p_body,p_notice):
        if not s.inpart(p_part,me): return s.no('notmember')
        t=p_title.strip()[:100]; b=p_body[:5000]
        if not t and not b.strip(): return s.no('empty')
        if p_notice and not s.leads(p_part,me): return s.no('notleader')
        if p_id is None:
            i=str(uuid.uuid4()); ts=now_iso(); s.POSTS[i]=dict(id=i,part_id=p_part,author_id=me,notice=bool(p_notice),title=t,body=b,created_at=ts,updated_at=ts); return s.ok(id=i)
        q=s.POSTS.get(p_id)
        if not q or q['author_id']!=me or q['part_id']!=p_part: return s.no('denied')
        q.update(title=t,body=b,notice=bool(p_notice),updated_at=now_iso()); return s.ok(id=p_id)
    def f_dw_post_delete(s,me,p_id):
        q=s.POSTS.get(p_id)
        if not q: return s.ok()
        if not (q['author_id']==me or s.leads(q['part_id'],me)): return s.no('denied')
        del s.POSTS[p_id]
        for c in [c for c,v in s.CMTS.items() if v['post_id']==p_id]: del s.CMTS[c]
        return s.ok()
    def f_dw_comment_add(s,me,p_post,p_body):
        q=s.POSTS.get(p_post)
        if not q: return s.no('gone')
        if not s.inpart(q['part_id'],me): return s.no('notmember')
        b=p_body.strip()[:1000]
        if not b: return s.no('empty')
        i=str(uuid.uuid4()); s.CMTS[i]=dict(id=i,post_id=p_post,author_id=me,body=b,created_at=now_iso()); return s.ok(id=i)
    def f_dw_comment_delete(s,me,p_id):
        c=s.CMTS.get(p_id)
        if not c: return s.ok()
        q=s.POSTS[c['post_id']]
        if not (c['author_id']==me or s.leads(q['part_id'],me)): return s.no('denied')
        del s.CMTS[p_id]; return s.ok()
    def f_dw_notices(s,me,p_limit=3):
        qs=sorted([q for q in s.POSTS.values() if q['notice'] and s.inpart(q['part_id'],me)],key=lambda q:q['created_at'],reverse=True)[:p_limit]
        return s.ok(posts=[dict(id=q['id'],part_id=q['part_id'],part_name=s.PARTS[q['part_id']]['name'],title=q['title'],body=q['body'][:120],created_at=q['created_at'],author=s.name(q['author_id'])) for q in qs])
    def f_dw_member_records(s,me,p_part,p_user=None,p_month=None):
        import re
        if not s.leads(p_part,me): return []
        mem={b for a,b,_ in s.MEM if a==p_part}; out=[]
        for (u,ap,k,i),r in sorted(s.ROWS.items()):
            if u not in mem or ap!='funeral' or r.get('deleted') or r.get('data') is None: continue
            if p_user and u!=p_user: continue
            if not (k in ('case','env') or (k=='state' and i=='settings')): continue
            d=r['data']
            if k=='case':
                f=d.get('f') or {}; mon=case_month(d)
            elif k=='env':
                mon=str((d.get('edits') or {}).get('month')) if 'month' in (d.get('edits') or {}) else str((d.get('auto') or {}).get('month') or '')
            else: mon=''
            if p_month and k!='state' and mon!=p_month and re.match(r'^\d{4}-(0[1-9]|1[0-2])$',mon): continue
            out.append(dict(owner=u,rkind=k,rid=i,rdata=d,rupdated=r['updated_at']))
        return out
    # 물품 수령 · 불출 장부 (2026.10.27) — 파트장끼리 같이 씀, 고치기 · 지우기는 넣은 사람 또는 관리자
    def stock_json(s,r,me):
        return dict(id=r['id'],kind=r['kind'],loc=r['loc'],item=r['item'],qty=r['qty'],day=r['day'],party=r['party'],memo=r['memo'],deleted=r['deleted'],
                    created_at=r['created_at'],updated_at=r['updated_at'],server_at=r['server_at'],
                    author=s.name(r['author_id']) if r['author_id'] else '나간 직원',editor=s.name(r['editor_id']) if r['editor_id'] and r['editor_id']!=r['author_id'] else '',
                    mine=r['author_id']==me,can_edit=r['author_id']==me or s.admin(me))
    def f_dw_stock_list(s,me,p_since=None):
        if not s.leader(me): return s.no('notleader')
        since=None
        try: since=datetime.datetime.fromisoformat(p_since)-datetime.timedelta(minutes=2) if p_since else None
        except Exception: since=None
        rows=[r for r in sorted(s.STOCK.values(),key=lambda r:r['server_at']) if (since is None and not r['deleted']) or (since is not None and datetime.datetime.fromisoformat(r['server_at'])>since)]
        return s.ok(full=since is None,rows=[s.stock_json(r,me) for r in rows])
    def f_dw_stock_save(s,me,p):
        import re
        if not s.leader(me): return s.no('notleader')
        i=str(p.get('id') or '').strip()
        if not i or len(i)>40 or not re.match(r'^[A-Za-z0-9_-]+$',i): return s.no('bad')
        k=p.get('kind'); l=str(p.get('loc') or '').strip()[:20]; it=re.sub(r'\s+',' ',str(p.get('item') or '')).strip()[:60]
        if k not in ('in','out') or not l or not it: return s.no('empty')
        try:
            q=int(p.get('qty')); d=str(p.get('day')); datetime.date.fromisoformat(d); up=int(p.get('updated_at') or 0); dl=bool(p.get('deleted') or False)
        except Exception: return s.no('bad')
        if q<1 or q>1000000: return s.no('bad')
        old=s.STOCK.get(i); row=dict(kind=k,loc=l,item=it,qty=q,day=d,party=str(p.get('party') or '').strip()[:60],memo=str(p.get('memo') or '')[:500],deleted=dl,updated_at=up,server_at=now_iso(),editor_id=me)
        if not old:
            row.update(id=i,author_id=me,created_at=now_iso()); s.STOCK[i]=row; return s.ok(id=i)
        if not (old['author_id']==me or s.admin(me)): return s.no('denied')
        if up<old['updated_at']: return s.ok(id=i,stale=True)
        old.update(row); return s.ok(id=i)
    # 자료실 (2026.10.28) — 보기: 파트원 · 파트장 · 총괄실장 · 관리자, 올리기: 파트장 · 총괄실장 · 관리자, 고치기 · 지우기: 올린 사람 또는 관리자
    def doc_view(s,uid): return s.leader(uid) or s.chief(uid) or s.admin(uid) or any(b==uid for a,b,_ in s.MEM)
    def doc_up(s,uid): return s.leader(uid) or s.chief(uid) or s.admin(uid)
    def storage(s,src,op,uid,bucket,path,size):
        import json
        if s.noserver or bucket!='dw-docs': return {'error':'Bucket not found','status':404}
        if op=='upload':
            if not s.doc_up(uid) or path.split('/')[0]!=uid: return {'error':'new row violates row-level security policy','status':403}
            if size>50*1024*1024: return {'error':'The object exceeded the maximum allowed size','status':413}
            if path in s.OBJ: return {'error':'The resource already exists','status':409}
            s.OBJ[path]={'owner':uid,'size':size}; return {'ok':True}
        if op=='read':
            if not s.doc_view(uid) or path not in s.OBJ: return {'error':'Object not found','status':400}
            return {'ok':True}
        if op=='remove':
            out=[]
            for p in json.loads(path):
                if p in s.OBJ and ((s.doc_up(uid) and p.split('/')[0]==uid) or s.admin(uid)): del s.OBJ[p]; out.append(p)
            return {'removed':out}
        return {'error':'bad'}
    def f_dw_docs_list(s,me):
        if not s.doc_view(me): return s.no('notstaff')
        up=s.doc_up(me); ds=sorted([d for d in s.DOCS.values() if not d['deleted']],key=lambda d:d['created_at'],reverse=True)
        return s.ok(can_upload=up,used=sum(int(f.get('size') or 0) for d in ds for f in d['files']),
                    docs=[dict(id=d['id'],title=d['title'],body=d['body'],files=d['files'],created_at=d['created_at'],updated_at=d['updated_at'],
                               author=s.name(d['author_id']) if d['author_id'] else '나간 직원',mine=d['author_id']==me,can_edit=(d['author_id']==me and up) or s.admin(me)) for d in ds])
    def f_dw_doc_save(s,me,p):
        import re
        if not s.doc_up(me): return s.no('notup')
        t=re.sub(r'\s+',' ',str(p.get('title') or '')).strip()[:100]; b=str(p.get('body') or '')[:3000]
        if not t: return s.no('title')
        if not isinstance(p.get('files'),list): return s.no('bad')
        isnew=not str(p.get('id') or '').strip(); did=str(p.get('new_id') if isnew else p.get('id') or '')
        if not re.match(r'^[0-9a-f-]{36}$',did): return s.no('bad')
        old=s.DOCS.get(did)
        if isnew and old: return s.no('bad')
        if not isnew:
            if not old or old['deleted']: return s.no('gone')
            if not (old['author_id']==me or s.admin(me)): return s.no('denied')
        oldp={f['path']:f for f in (old['files'] if old else [])}; fs=[]
        for f in p['files']:
            pth=str(f.get('path') or '')
            if len(fs)>=10: return s.no('many')
            if pth in oldp: sz=oldp[pth]['size']
            else:
                if not re.match('^'+re.escape(me)+'/'+did+r'/[A-Za-z0-9._-]{1,80}$',pth): return s.no('bad')
                sz=s.OBJ[pth]['size'] if pth in s.OBJ else int(f.get('size') or 0)
            if any(x['path']==pth for x in fs): return s.no('bad')
            fs.append(dict(path=pth,name=(str(f.get('name') or '').strip() or '파일')[:150],size=sz,type=str(f.get('type') or '')[:100]))
        if not fs: return s.no('nofiles')
        others=sum(int(f['size'] or 0) for d in s.DOCS.values() if not d['deleted'] and d['id']!=did for f in d['files'])
        newsz=sum(int(f['size'] or 0) for f in fs); oldsz=sum(int(f['size'] or 0) for f in (old['files'] if old else []))
        if others+newsz>838860800 and newsz>oldsz: return s.no('full')   # 자료실 800MB (supabase-part.sql 과 같음)
        ts=now_iso()
        if isnew: s.DOCS[did]=dict(id=did,title=t,body=b,files=fs,author_id=me,deleted=False,created_at=ts,updated_at=ts); return s.ok(id=did,removed=[])
        removed=[x for x in oldp if not any(y['path']==x for y in fs)]
        old.update(title=t,body=b,files=fs,updated_at=ts); return s.ok(id=did,removed=removed)
    def f_dw_doc_delete(s,me,p_id):
        d=s.DOCS.get(p_id)
        if not d or d['deleted']: return s.ok(paths=[])
        if not ((d['author_id']==me and s.doc_up(me)) or s.admin(me)): return s.no('denied')
        d['deleted']=True; return s.ok(paths=[f['path'] for f in d['files']])
    # ---- 섞인 기록 정리 (supabase-part.sql dw_unmix_plan · dw_unmix_states · dw_admin_* 와 같은 규칙) ----
    def unmix_plan(s):
        import hashlib, json as _j
        live=[]
        for (u,ap,k,i),r in s.ROWS.items():
            d=r.get('data')
            if r.get('deleted') or k=='state' or d is None: continue
            if k=='review' and not str((d or {}).get('text') or '').strip(): continue
            dk=hashlib.md5(_j.dumps(d,sort_keys=True).encode()).hexdigest() if k in ('review','gnote') else ''
            live.append(dict(u=u,app=ap,kind=k,id=i,dk=dk,dev=r.get('device'),data=d))
        from collections import defaultdict
        g=defaultdict(list)
        for x in live: g[(x['app'],x['kind'],x['id'],x['dk'])].append(x)
        dup={k for k,v in g.items() if len({x['u'] for x in v})>1}
        uniq=defaultdict(set)
        for x in live:
            if x['dev'] and (x['app'],x['kind'],x['id'],x['dk']) not in dup: uniq[x['u']].add(x['dev'])
        devs=defaultdict(set)
        for x in live:
            if x['dev']: (devs[x['u']].update(uniq[x['u']]) if uniq[x['u']] else devs[x['u']].add(x['dev']))
        out=[]
        for k in dup:
            rows=[]
            for x in g[k]:
                d=x['data'] or {}; born=None
                for f in ('created','createdAt'):
                    v=str(d.get(f,'')) if isinstance(d,dict) else ''
                    if v.isdigit() and 12<=len(v)<=14 and born is None: born=int(v)
                made=s.MADE.get(x['u'],0); could=True if born is None else made<=born+3600000
                rows.append((not could, not (x['dev'] in devs[x['u']]), made, x['u'], x))
            rows.sort(key=lambda t:t[:4]); owner=rows[0][4]['u']
            for t in rows[1:]: out.append(dict(copy=t[4]['u'],owner=owner,app=t[4]['app'],kind=t[4]['kind'],id=t[4]['id']))
        return out
    def unmix_states(s):
        import hashlib
        st=[]
        for (u,ap,k,i),r in s.ROWS.items():
            d=r.get('data')
            if r.get('deleted') or k!='state' or not isinstance(d,dict): continue
            if ap=='funeral' and i=='settings': w,key='me',str((d.get('me') or {}).get('name') or '').strip()
            elif ap=='forms' and i=='settings': w,key='author',str(d.get('author') or '').strip()
            elif ap=='forms' and i=='signature':
                if not d.get('data'): continue
                w,key='sig',hashlib.md5(str(d.get('data')).encode()).hexdigest()
            else: continue
            if not key: continue
            st.append(dict(u=u,app=ap,kind=k,id=i,what=w,k=key,data=d,pn=str((s.PROF.get(u) or {}).get('name') or '').strip(),made=s.MADE.get(u,0)))
        from collections import defaultdict
        g=defaultdict(list)
        for x in st: g[(x['what'],x['k'])].append(x)
        out=[]
        for key,v in g.items():
            if len({x['u'] for x in v})<2: continue
            v=sorted(v,key=lambda x:(not (x['what']!='sig' and x['pn'] and x['pn']==x['k']), x['made'], x['u'])); o=v[0]
            for x in v[1:]:
                if x['what']!='sig' and x['pn'] and x['pn']==x['k']: continue
                if x['what']=='me':
                    m=dict(x['data'].get('me') or {}); om=o['data'].get('me') or {}
                    m['name']=x['pn']; m['phone']='' if str(m.get('phone') or '')==str(om.get('phone') or '') else m.get('phone',''); m['rank']='' if str(m.get('rank') or '')==str(om.get('rank') or '') else m.get('rank','')
                    fix=dict(x['data']); fix['me']=m
                elif x['what']=='author': fix=dict(x['data']); fix['author']=x['pn']
                else: fix={'none':True}
                out.append(dict(user=x['u'],what=x['what'],owner=o['u'],app=x['app'],kind=x['kind'],id=x['id'],fix=fix))
        return out
    def f_dw_admin_mixed(s,me):
        if not s.admin(me): return s.no('denied')
        from collections import defaultdict
        pr=defaultdict(list)
        for x in s.unmix_plan(): pr[(x['copy'],x['owner'])].append(x)
        pairs=[dict(copy=c,owner=o,n=len(v),funeral=sum(1 for x in v if x['app']=='funeral'),forms=sum(1 for x in v if x['app']=='forms'),company=sum(1 for x in v if x['app']=='company'),
                    copy_name=s.name(c),owner_name=s.name(o),samples=[x['kind']+' '+x['id'] for x in v][:4]) for (c,o),v in pr.items()]
        pairs.sort(key=lambda x:-x['n'])
        states=[dict(user=x['user'],what=x['what'],owner=x['owner'],user_name=s.name(x['user']),owner_name=s.name(x['owner'])) for x in s.unmix_states()]
        bs=[dict(batch=b['batch'],at=b['at'],n=len(b['rows'])) for b in reversed(s.UNMIX)][:5]
        return s.ok(pairs=pairs,states=states,batches=bs)
    def f_dw_admin_unmix(s,me,p):
        if not s.admin(me): return s.no('denied')
        import uuid as _u, time
        t=int(time.time()*1000); prs={tuple(x) for x in (p.get('pairs') or [])}; sts={tuple(x) for x in (p.get('states') or [])}
        rows=[]; n=ns=0
        for x in s.unmix_plan():
            if (x['copy'],x['owner']) in prs:
                r=s.ROWS[(x['copy'],x['app'],x['kind'],x['id'])]; rows.append(dict(key=(x['copy'],x['app'],x['kind'],x['id']),what='copy',prev=None))
                r.update(deleted=True,updated_at=max(r['updated_at']+1,t),device='unmix',server_at=now_iso()); n+=1
        for x in s.unmix_states():
            if (x['user'],x['what']) in sts:
                r=s.ROWS[(x['user'],x['app'],x['kind'],x['id'])]; rows.append(dict(key=(x['user'],x['app'],x['kind'],x['id']),what=x['what'],prev=copy.deepcopy(r['data'])))
                r.update(data=x['fix'],updated_at=max(r['updated_at']+1,t),device='unmix',server_at=now_iso()); ns+=1
        if not rows: return s.ok(n=0,states=0)
        b=str(_u.uuid4()); s.UNMIX.append(dict(batch=b,at=now_iso(),rows=rows)); return s.ok(batch=b,n=n,states=ns)
    def f_dw_admin_unmix_undo(s,me,p_batch):
        if not s.admin(me): return s.no('denied')
        import time
        t=int(time.time()*1000); n=ns=0
        for b in [b for b in s.UNMIX if b['batch']==p_batch]:
            for x in b['rows']:
                r=s.ROWS.get(x['key'])
                if not r: continue
                if x['what']=='copy': r.update(deleted=False,updated_at=max(r['updated_at']+1,t),device='unmix',server_at=now_iso()); n+=1
                elif x['prev'] is not None: r.update(data=x['prev'],updated_at=max(r['updated_at']+1,t),device='unmix',server_at=now_iso()); ns+=1
        s.UNMIX=[b for b in s.UNMIX if b['batch']!=p_batch]
        return s.ok(n=n,states=ns)
def wire(ctx,srv,mockjs):
    ctx.route('**/vendor/supabase.js', lambda r: r.fulfill(status=200,content_type='application/javascript',body=mockjs))
    for n,f in [('mockUpdatePw',srv.updatepw),('mockAuth',srv.auth),('mockSignUp',srv.signup),('mockGetUser',srv.getuser),('mockRpc',srv.rpc),('mockSelect',srv.select),('mockUpsert',srv.upsert),('mockStorage',srv.storage)]: ctx.expose_binding(n,f)
