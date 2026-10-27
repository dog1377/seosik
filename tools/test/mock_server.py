"""테스트용 가짜 수파베이스 서버 — tools/supabase-part.sql 의 함수와 같은 규칙 (실제 서버에 연결하지 않음).
tools/test/smoke.py 가 씀. 서버 함수를 바꾸면 여기도 같이 바꾼다."""
import copy, itertools, datetime, uuid
CNT=itertools.count()
def now_iso(): return (datetime.datetime(2026,10,23,9)+datetime.timedelta(seconds=next(CNT))).isoformat()+'+00:00'
class Srv:
    def __init__(s):
        s.USERS={}; s.ROWS={}; s.PROF={}; s.PARTS={}; s.MEM=[]; s.POSTS={}; s.CMTS={}; s.STOCK={}; s.noserver=False; s.calls=[]
    def add_user(s,login,pw,leader=False,name='',chief=False,admin=False):
        email=login if '@' in login else login+'@dwfuneral.com'; lid=login.split('@')[0] if email.endswith('@dwfuneral.com') else email
        am={'dw_role':'leader'} if leader else {'dw_role':'chief'} if chief else {}
        if admin: am['dw_admin']=True
        uid='uid-'+login.split('@')[0]; s.USERS[email]=[pw,uid,am,{'name':name} if name else {}]
        s.PROF[uid]={'login_id':lid,'name':name}; return uid
    # auth
    def auth(s,src,email,pw):
        u=s.USERS.get(email)
        if not u or u[0]!=pw: return {'error':'bad'}
        return {'user':{'id':u[1],'email':email,'app_metadata':dict(u[2]),'user_metadata':dict(u[3])}}
    def signup(s,src,email,pw,meta):
        if email in s.USERS: return {'error':'User already registered'}
        uid='uid-'+email.split('@')[0]; s.USERS[email]=[pw,uid,{},meta]; s.PROF[uid]={'login_id':email.split('@')[0] if email.endswith('@dwfuneral.com') else email,'name':meta.get('name','')}
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
        return s.ok(user_id=me,login_id=p['login_id'],name=p['name'],leader=s.leader(me),admin=s.admin(me),chief=s.chief(me),parts=parts)
    def f_dw_set_name(s,me,p_name): s.PROF[me]['name']=p_name.strip()[:20]; return s.ok(name=s.PROF[me]['name'])
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
                f=d.get('f') or {}; mon=next((str(f.get(x)) for x in ['depart','cremDate','hagwanDate','death','recv'] if f.get(x)),'')[:7]
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
def wire(ctx,srv,mockjs):
    ctx.route('**/vendor/supabase.js', lambda r: r.fulfill(status=200,content_type='application/javascript',body=mockjs))
    for n,f in [('mockAuth',srv.auth),('mockSignUp',srv.signup),('mockGetUser',srv.getuser),('mockRpc',srv.rpc),('mockSelect',srv.select),('mockUpsert',srv.upsert)]: ctx.expose_binding(n,f)
