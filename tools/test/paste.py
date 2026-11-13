"""복사한 글로 새 행사 점검 (2026.11.13) — 업체마다 행사를 채워 밴드 일정표 · 제공내역 · 회사 양식을 만들고,
그 글을 그대로 붙여 넣어 만든 행사가 같은 양식을 다시 만드는지 본다(줄마다 비교). 날짜에 달이 없는 밴드 일정표만 붙여도,
일정표 · 제공내역을 따로 붙여도, 매장(하관)이어도 같은지.

    python3 tools/test/paste.py            (tools/test/run.sh 가 웹서버를 띄우고 부름)
"""
import os
import pathlib
import sys

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from mock_server import Srv, wire  # noqa: E402

BASE = os.environ.get('DW_BASE', 'http://127.0.0.1:8765/')
MOCK = (HERE / 'mock_supabase.js').read_text(encoding='utf-8')

RUN = r"""(()=>{
 window.__todayYMD='2026-11-11';
 const out=[], line=t=>String(t||'').split('\n');
 const fill=(c,burial)=>{
  Object.assign(c.f,{eventNo:'12',place:'부산착한 VIP2호',recv:'2026-11-10T08:20',callAt:'2026-11-10T07:50',leaveAt:'2026-11-10T08:30',arrive:'2026-11-10T09:10',consultAt:'2026-11-10T10:00',
   death:'2026-11-10T06:30',casket:'2026-11-11T09:00',depart:'2026-11-12T07:00',company:'넥센타이어',customer:'서재원',custRel:'자',custTel:'010-1234-5678',name:'홍길동',mourn:'부친상',gender:'남자',age:'82',origin:'김해',
   religion:'기독교',cause:'병사',addr:'부산 동래구 명륜동',chief:'홍민수',chiefRel:'장남',chiefTel:'010-2222-3333',method:burial?'매장':'화장',burial1:'부산추모',burial2:'창원상복',burial:'창원상복-부산추모(벽식)',
   product:'삼성전기 270 일반형',productShort:'일반형',support:'66',paid:'120',balance:'30',collect:'277.5',extraAmt:'20',totalAmt:'300',staffOrg:'부산본부',staff:'서영우',staffTel:'010-9999-8888',note:'유족 요청 많음\n영정 크게 준비',
   helper:'김정단',helperHours:'50',mournM:'6',mournW:'4',mournBrand:'한맥',vehType:'버스 리무진',vehCo:'한맥장의차',altar:'20',shroud:'저마수의',transport:'제공',provNote:'영정 가족 준비',coupon:'O',cardBack:'X',
   affiliate:'농협은행 다대포지점',rank:'과장',altarSup:'100만원 공제',cremName:'부산영락',cremDate:'2026-11-12',cremTime:'09:00',cremRound:'4',preJoin:'10만원',certDone:'하단 첨부'});
  if(burial) Object.assign(c.f,{hagwanDate:'2026-11-12',hagwanSi:'사시',hagwanFrom:'09',hagwanTo:'11'});
  c.mgr=[{id:'m1',date:'2026-11-10',sh:'14',sm:'00',eh:'22',em:'00',n:'2'},{id:'m2',date:'2026-11-11',sh:'09',sm:'00',eh:'18',em:'00',n:'1'}];
  c.deductions=[{id:'d1',text:'헌화30송이 5만원공제'},{id:'d2',text:'도우미 6시간 추가 120,000원'}];
  c.items=[{id:'i1',text:'현진저마수의',on:true},{id:'i2',text:'장의차량 70km(실제운행거리)\n장의차량 거리추가시',on:true},{id:'i3',text:'빼 둔 항목',on:false},{id:'i4',text:'09시 입실예정',on:true}];
 };
 const forms=c=>{ const co=coById(c.companyId); return [['밴드',bandOut(c)],...activeReports(co).filter(r=>r.name!=='장례 종료 보고').map(r=>[r.name,fillTpl(r.body,c)])]; };
 const remake=text=>{ const R=psParse(text), co=psCompany(R), n=makeCase(co); if(n.companyId===ETC&&R.coName&&!psFindCo(R.coName)) n.f.coName=R.coName; n.mgr=[]; psApply(n,R,false); return n; };
 const diff=(a,b)=>{ const A=line(a), B=line(b), d=[]; for(let i=0;i<Math.max(A.length,B.length);i++) if((A[i]||'')!==(B[i]||'')) d.push(`  원래: ${A[i]||''}\n  다시: ${B[i]||''}`); return d; };
 db.companies.forEach(co=>{ [false,true].forEach(burial=>{
   const c=makeCase(co.id); fill(c,burial); const F=forms(c), all=F.map(x=>x[1]).join('\n\n');
   const n=remake(all), G=forms(n);
   if(n.companyId!==c.companyId) out.push(`${co.name}: 업체를 ${coById(n.companyId).name}(으)로 읽음`);
   F.forEach(([nm,t],i)=>{ const d=diff(t,(G[i]||[])[1]); if(d.length) out.push(`${co.name}${burial?' (매장)':''} · ${nm}:\n${d.join('\n')}`); });
   if(!burial){
     /* 밴드만 (일정표 · 제공내역 따로 붙임 — 날짜에 달이 없음) */
     const b=bandOut(c), sp=splitBand(b), nb=remake(sp.sched+'\n\n\n'+sp.prov), d=diff(b,bandOut(nb)); if(d.length) out.push(`${co.name} · 밴드만:\n${d.join('\n')}`);
     /* 제공내역만 붙였을 때 일정표 특이사항으로 잘못 가지 않음 */
     if(sp.prov){ const R=psParse(sp.prov); if(R.f.note||R.f.provNote!==c.f.provNote) out.push(`${co.name} · 제공내역만: 특이사항 ${JSON.stringify([R.f.note,R.f.provNote])}`); }
     /* 밴드 앱처럼 줄 사이에 빈 줄이 하나씩 · 앞뒤 띄어쓰기 · 카톡 머리 줄 */
     const loose='[서영우] [오후 2:03] '+all.split('\n').map(l=>'  '+l+' ').join('\n\n'), nl=remake(loose), G2=forms(nl);
     F.forEach(([nm,t],i)=>{ const d=diff(t,(G2[i]||[])[1]); if(d.length) out.push(`${co.name} · 빈 줄 섞인 글 · ${nm}:\n${d.join('\n')}`); });
   }
 }); });
 /* 양식이 아닌 글(이름 : 값) — 글 안의 업체 이름 */
 { const R=psParse('[고이장례연구소 접수]\n고인 : 김영희 (여, 85세)\n빈소 : 해운대백병원 3호\n상주 : 박철수 010-1111-2222\n입관 : 11월 12일 10시\n발인 : 11월 13일 07시 30분\n장지 : 영락공원\n담당 : 서영우 팀장 010-9999-8888');
   const want={name:'김영희',gender:'여자',age:'85',place:'해운대백병원 3호',chief:'박철수',chiefTel:'010-1111-2222',casket:'2026-11-12T10:00',depart:'2026-11-13T07:30',burial:'영락공원',staff:'서영우',staffTel:'010-9999-8888'};
   Object.entries(want).forEach(([k,v])=>{ if(R.f[k]!==v) out.push(`이름 : 값 글 · ${k} ${JSON.stringify(R.f[k])} (기대 ${v})`); });
   if(coById(psCompany(R)).name!=='고이장례연구소') out.push('이름 : 값 글 · 업체 '+coById(psCompany(R)).name); }
 /* 달이 넘어가는 행사 (30일 임종 → 02일 발인) */
 { window.__todayYMD='2026-11-01'; const R=psParse('장례행사 일정표\n장   소 : 동래봉생 2호\n기   간 : 30일-02일 4일\n회사명 : 디더블유\n회원명 : 이순자\n관    계 : 녀\n연락처 :\n고인명 : 김말순 여자 91세\n상주명 : 김철수\n연락처 :\n종    교 : 불교\n임    종 : 30일 23시 10분\n입    관 : 01일 11시\n발    인 : 02일 06시 30분');
   const got=[R.f.death,R.f.casket,R.f.depart].join(' '), want='2026-10-30T23:10 2026-11-01T11:00 2026-11-02T06:30'; if(got!==want) out.push(`달 넘김: ${got}`); window.__todayYMD='2026-11-11'; }
 /* 같은 행사가 있으면 빈 칸만 채우기 */
 const co=db.companies.find(x=>x.name==='현진시닝'), c=makeCase(co.id); fill(c,false); const sp=splitBand(bandOut(c));
 const a=remake(sp.sched); db.cases.push(a); const R=psParse(fillTpl(co.reports[0].body,c)), dup=psDup(R);
 if(!dup||dup.id!==a.id) out.push('같은 행사 찾기 실패');
 else { const before=a.f.customer; a.f.customer='직접 고친 이름'; psApply(a,R,true); if(a.f.customer!=='직접 고친 이름') out.push('빈 칸만 채우기: 넣어 둔 칸을 덮어씀'); if(!a.f.mourn) out.push('빈 칸만 채우기: 빈 칸(상 구분)을 못 채움'); a.f.customer=before; }
 db.cases=db.cases.filter(x=>x.id!==a.id);
 return out;
})()"""

UI = r"""(async()=>{
 window.__todayYMD='2026-11-11';
 const co=db.companies.find(x=>x.name==='고이장례연구소'), c=makeCase(co.id);
 Object.assign(c.f,{eventNo:'7',place:'부산온 201호',name:'정남영',death:'2026-11-10T05:00',casket:'2026-11-11T10:00',depart:'2026-11-12T08:00',customer:'정말순',collect:'298',altar:'20',staff:'서영우'});
 c.deductions=[{id:'d',text:'헌화30송이 5만원공제'}];
 return [bandOut(c), fillTpl(co.reports[0].body,c), collectNetWon(c)];
})()"""


def main():
    srv = Srv()
    srv.add_user('seo', 'pw1111', leader=True, name='서영우')
    bad = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, service_workers='block')
        ctx.add_init_script("try{localStorage.setItem('mf.installDismissed','1');localStorage.setItem('funeral-installDismissed','1')}catch(e){}")
        ctx.route('https://**/*', lambda r: r.abort())
        wire(ctx, srv, MOCK)
        p = ctx.new_page()
        errs = []
        p.on('pageerror', lambda e: errs.append(str(e)))
        p.goto(BASE + 'forms/funeral.html')
        p.wait_for_selector('#gtId')
        p.fill('#gtId', 'seo'); p.fill('#gtPw', 'pw1111'); p.click('#gtGo')
        p.wait_for_function("typeof psParse==='function' && !document.documentElement.classList.contains('dw-gated')", timeout=15000)
        p.wait_for_timeout(1200)
        bad += p.evaluate(RUN)
        # 화면: 새 행사 창 → 복사한 글로 새 행사 → 붙여 넣기 → 새 행사 만들기
        band, rep, net = p.evaluate(UI)
        p.evaluate("openPicker('new')")
        p.click('#pickPaste')
        p.wait_for_selector('#psText')
        p.fill('#psText', band + '\n\n' + rep)
        p.wait_for_selector('[data-ps-go="new"]', timeout=3000)
        co = p.evaluate("document.querySelector('#psCoSel').selectedOptions[0].textContent")
        if co != '고이장례연구소':
            bad.append(f'화면: 업체 {co}')
        n0 = p.evaluate('db.cases.length')
        p.click('[data-ps-go="new"]')
        p.wait_for_timeout(500)
        got = p.evaluate("[db.cases.length, db.tab, curCase().f.name, collectNetWon(curCase()), curCase().f.collect, curCase().deductions.length, $('#psBg').hidden]")
        if got[:3] != [n0 + 1, 'input', '정남영'] or got[3] != net or got[5] != 1 or not got[6]:
            bad.append(f'화면: 새 행사 {got} (수금액 {net})')
        # 같은 글을 한 번 더 → 같은 행사 알림 · 빈 칸만 채우기
        p.evaluate("openPicker('new')")
        p.click('#pickPaste')
        p.fill('#psText', band)
        p.wait_for_selector('[data-ps-go="fill"]', timeout=3000)
        p.click('[data-ps-go="fill"]')
        p.wait_for_timeout(400)
        if p.evaluate('db.cases.length') != n0 + 1:
            bad.append('화면: 빈 칸 채우기가 새 행사를 만듦')
        # 알아볼 수 없는 글
        p.evaluate("openPicker('new')")
        p.click('#pickPaste')
        p.fill('#psText', '안녕하세요\n오늘 날씨가 좋네요')
        p.wait_for_timeout(500)
        if not p.locator('.pz-empty').is_visible():
            bad.append('화면: 알아볼 수 없는 글 안내가 안 보임')
        p.screenshot(path=str(HERE / 'out' / 'paste_empty_390.png'))
        p.fill('#psText', band + '\n\n' + rep)
        p.wait_for_timeout(500)
        p.screenshot(path=str(HERE / 'out' / 'paste_390.png'))
        for vw, vh, theme in [(1440, 900, 'light'), (390, 844, 'dark')]:
            p.set_viewport_size({'width': vw, 'height': vh})
            p.evaluate(f"document.documentElement.dataset.theme='{theme}'")
            p.wait_for_timeout(300)
            p.screenshot(path=str(HERE / 'out' / f'paste_{vw}_{theme}.png'))
            if p.evaluate('document.documentElement.scrollWidth>innerWidth+1'):
                bad.append(f'화면: 가로 밀림 {vw}')
        if errs:
            bad.append('페이지 오류: ' + ' / '.join(errs))
        b.close()
    if bad:
        print('복사한 글로 새 행사 점검 실패:')
        for x in bad:
            print('-', x)
        sys.exit(1)
    print('복사한 글로 새 행사 점검 통과')


if __name__ == '__main__':
    main()
