"""화면 점검 — 빌드된 앱을 휴대폰 · 태블릿 · PC 크기, 밝은/어두운 화면으로 열어 본다.

    python3 tools/test/smoke.py            (tools/test/run.sh 가 웹서버를 띄우고 부름)

가짜 로그인 서버(mock_server.py · mock_supabase.js)로 파트장 · 직원 · 총괄실장 모두 들어가 본다. 실제 서버 · 인터넷에 연결하지 않음.
확인: 페이지 오류 0건 · 옆으로 밀리는 화면(가로 스크롤) 없음 · 위 막대 글씨 잘림 없음 · 새로 가입한 계정은 빈 화면(계정마다 이 기기 기록 따로).
화면 캡처는 tools/test/out/ 에 저장 (저장소에 올리지 않음) → 눈으로 확인.
하나라도 문제가 있으면 실패(종료 코드 1).
"""
import os
import pathlib
import sys

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from mock_server import Srv, wire  # noqa: E402

BASE = os.environ.get('DW_BASE', 'http://127.0.0.1:8765/')
OUT = HERE / 'out'
OUT.mkdir(exist_ok=True)
MOCK = (HERE / 'mock_supabase.js').read_text(encoding='utf-8')
QUICK = os.environ.get('DW_QUICK') == '1'   # 1이면 휴대폰 · PC 밝은 화면만

SIZES = [(390, 844, 'light'), (1440, 900, 'light')] if QUICK else [
    (390, 844, 'light'), (390, 844, 'dark'), (820, 1180, 'light'), (1180, 820, 'dark'), (1440, 900, 'light'), (1440, 900, 'dark')]

SEED = r"""(()=>{
 const co=n=>db.companies.find(x=>x.name===n).id; rules().mgrName='이승구실장'; me().name='김철수'; me().rank='팀장';
 startCase(co('현진시닝')); let c=curCase(), s=S(c);
 Object.assign(c.f,{eventNo:'1',place:'부산착한 VIP2호',name:'홍길동',death:'2026-10-08T05:30',casket:'2026-10-09T09:00',depart:'2026-10-10T07:00',collect:'257.5',chief:'홍민수',product:'삼성전기 270 일반형',burial:'창원상복-부산추모(벽식)'});
 Object.assign(s,{pay:'현금',altarAmt:'100',altarPay:'현금',urnAsk:'yes',urnCollect:'90',urnCost:'25',urnPay:'현금',hall:'10',burialAmt:'300',burialSea:'no',chodo:'5',kit:'3',lunch:'6'});
 startCase(co('디더블유')); c=curCase(); s=S(c);
 Object.assign(c.f,{eventNo:'3',place:'창원한마음',name:'김영자',depart:'2026-10-12T07:00',collect:'389'});
 Object.assign(s,{pay:'카드',altarAmt:'30',altarPay:'현금',urnAsk:'yes',urnCollect:'120',urnCost:'36',urnPay:'카드',hall:'5'});
 save(); })()"""

# 위 막대(화면 맨 위 90px 안)에서 글씨가 잘린 것 찾기
CLIPPED = r"""(()=>{ const out=[];
 document.querySelectorAll('body *').forEach(el=>{
   if(!el.offsetParent && getComputedStyle(el).position!=='fixed') return;
   const r=el.getBoundingClientRect(); if(r.top>90||r.bottom<0||!r.width) return;
   if(![...el.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())) return;
   const cs=getComputedStyle(el); if(!/hidden|clip/.test(cs.overflowX+cs.overflow)) return;
   if(el.scrollWidth>el.clientWidth+1) out.push(el.textContent.trim().slice(0,24));
 }); return out; })()"""
HSCROLL = 'document.documentElement.scrollWidth > innerWidth + 1'


def main():
    srv = Srv()
    srv.add_user('seo', 'pw1111', leader=True, name='서영우')
    srv.add_user('kim', 'pw2222', name='김철수')
    srv.add_user('boss', 'pw5555', chief=True, name='박총괄')   # 총괄실장 (2026.10.26)
    seo = 'uid-seo'
    srv.upsert(None, seo, [{'user_id': seo, 'app': 'forms', 'kind': 'state', 'id': 'settings', 'data': {'author': '서영우', 'part': '장례지원 1파트', 'roster': []}, 'deleted': False, 'updated_at': 0}])
    problems, errs = [], []

    with sync_playwright() as pw:
        b = pw.chromium.launch()

        def page(w, h, sc):
            ctx = b.new_context(viewport={'width': w, 'height': h}, service_workers='block', color_scheme=sc)
            ctx.add_init_script("try{localStorage.setItem('mf.installDismissed','1');localStorage.setItem('funeral-installDismissed','1')}catch(e){}")
            ctx.route('https://**/*', lambda r: r.abort())
            wire(ctx, srv, MOCK)
            p = ctx.new_page()
            p.on('pageerror', lambda e, t=f'{w}x{h} {sc}': errs.append(f'{t}: {e}'))
            return ctx, p

        def login(p, who, pw_):
            p.wait_for_selector('#gtId', timeout=10000)
            p.fill('#gtId', who); p.fill('#gtPw', pw_); p.click('#gtGo'); p.wait_for_timeout(1800)

        def look(p, name):
            p.wait_for_timeout(350)
            if p.evaluate(HSCROLL):
                problems.append(f'{name}: 화면이 옆으로 밀림(가로 스크롤)')
            cut = p.evaluate(CLIPPED)
            if cut:
                problems.append(f'{name}: 위 막대 글씨 잘림 {cut}')
            p.screenshot(path=str(OUT / f'{name}.png'))

        # 직원 기록 준비: 김철수가 장례업무에서 로그인 → 행사 2건 → 서버로
        ctx, p = page(390, 844, 'light')
        p.goto(BASE + 'forms/funeral.html'); login(p, 'kim', 'pw2222')
        p.evaluate(SEED); p.wait_for_timeout(2500)
        ctx.close()

        # 계정마다 이 기기 기록 따로 (2026.10.28-20): 파트장 기록 → 위 막대 로그아웃 → 새로 가입 → 빈 화면 · 서버에도 안 올라감 → 다시 파트장 → 기록 그대로
        NCASES = "(JSON.parse(localStorage.getItem('funeral-band-v2')||'null')||{cases:[]}).cases.length"
        READY = "typeof setTab==='function' && !document.documentElement.classList.contains('dw-gated')"
        ctx, p = page(390, 844, 'light')
        p.goto(BASE + 'forms/funeral.html'); login(p, 'seo', 'pw1111'); p.wait_for_function(READY, timeout=15000)
        p.evaluate(SEED); p.wait_for_timeout(1500)
        n0 = p.evaluate(NCASES)
        p.click('#dwOut'); p.click('.dwc-ok'); p.wait_for_selector('#gtId', timeout=10000)
        p.click('#gtSwap'); p.fill('#gtId', 'newbie'); p.fill('#gtPw', 'pw3333'); p.fill('#gtPw2', 'pw3333'); p.click('#gtGo')
        p.wait_for_function(READY, timeout=15000); p.wait_for_timeout(1500)
        if p.evaluate(NCASES) != 0:
            problems.append('계정: 새로 가입한 계정에 이 기기의 다른 사람 기록이 보임')
        if [k for k in srv.ROWS if k[0] == 'uid-newbie' and k[2] == 'case']:
            problems.append('계정: 새로 가입한 계정으로 다른 사람 기록이 올라감')
        p.click('#dwOut'); p.click('.dwc-ok'); login(p, 'seo', 'pw1111'); p.wait_for_function(READY, timeout=15000); p.wait_for_timeout(800)
        if not n0 or p.evaluate(NCASES) != n0 or p.evaluate("localStorage.getItem('dw-owner')") != seo:
            problems.append('계정: 원래 계정으로 다시 들어왔는데 이 기기 기록이 돌아오지 않음')
        ctx.close()

        for (w, h, sc) in SIZES:
            tag = f'{w}x{h}_{sc}'
            # 파트장: 게시판 · 자료실(행사 칸) · 서식 · 설정(서식 칸) — 2026.10.29 행사 칸 · 서식 칸 나눔 (예전 홈 없음)
            ctx, p = page(w, h, sc)
            p.goto(BASE + 'forms/#board'); login(p, 'seo', 'pw1111')
            p.wait_for_function("typeof showTab==='function' && typeof S!=='undefined'", timeout=15000)
            for t in ['board', 'docs', 'weekly', 'minutes', 'review', 'ship', 'stock', 'consult', 'settings']:
                p.evaluate(f"showTab('{t}')"); p.wait_for_timeout(500); look(p, f'forms_{t}_{tag}')
                want = 'event' if t in ('board', 'docs') else 'forms'
                got = p.evaluate("[document.body.dataset.mode, (document.querySelector('#dwMode [aria-pressed=\"true\"]')||{getAttribute:()=>''}).getAttribute('data-dwmode')]")
                if got[0] != want or got[1] != want:
                    problems.append(f'{tag} {t}: 행사 · 서식 칸 표시가 다름 {got}')
            # 내 정보 (위 막대 아이디를 누르면, 2026.10.29)
            p.click('.appbar .local'); p.wait_for_selector('#dwMe:not([hidden])', timeout=5000); look(p, f'forms_me_{tag}')
            if p.input_value('#dwMeName') != '서영우':
                problems.append(f'{tag}: 내 정보 이름이 안 채워짐')
            p.keyboard.press('Escape'); p.wait_for_timeout(200)
            # 장례업무 (같은 기기 · 로그인 유지)
            p.goto(BASE + 'forms/funeral.html'); p.wait_for_function("typeof setTab==='function'", timeout=15000)
            p.evaluate(SEED)
            if w < 700 and p.evaluate("document.querySelectorAll('#mobileNav button').length") != 5:
                problems.append(f'{tag}: 장례업무 아래 메뉴가 5칸(행사 · 정산 · 휴무 · 게시판 · 설정)이 아님')
            for t in ['list', 'input', 'out', 'poster', 'deliv', 'settle', 'envelopes', 'duty', 'admin']:
                if t == 'deliv':   # 배송 (2026.10.30): 인력+대체 한 건을 넣고 양식 줄 확인
                    p.evaluate("db.ships=[{id:'t1',kind:'sub',co:'삼성SDS',place:'부산대동 VIP실',mgr:[{id:'m1',date:'2026-10-13',sh:'10',sm:'00',eh:'20',em:'00',n:'1'}],veh:{type:'리무진',km:'200',burial:'김해추모',depart:'2026-10-14T06:30',co:'한맥장의차'},subs:[{id:'s1',n:'4',what:'veh'},{id:'s2',n:'3',what:'mourn',m:'5',w:'1'}],updated:1}]; db.shipCur='t1'")
                p.evaluate(f"setTab('{t}')"); look(p, f'funeral_{t}_{tag}')
                if t == 'deliv':
                    got = p.evaluate("document.getElementById('dvText').value")
                    want = '회사명 : 현진시닝\n업체명 : 삼성SDS\n부산대동 VIP실\n13일 : 10시-20시 1명\n관리사 배치완료.\n\n관리사 4명 대체\n리무진 200km 장지(김해추모)\n14일 06시 배차\n14일 06시 30분 발인\n차량배차완료(한맥장의차)\n\n관리사 3명 대체\n남상복 5세트 여상복 1벌 제공'
                    if got != want:
                        problems.append(f'{tag}: 배송 양식이 다름: {got!r}')
                    p.evaluate("db.ships=[]; db.shipCur=null; save()")
            # 회사 서류
            p.goto(BASE + 'forms/admin.html'); p.wait_for_function("typeof showTab==='function'", timeout=15000)
            for t in ['docs', 'staff', 'settings']:
                p.evaluate(f"showTab('{t}')"); look(p, f'admin_{t}_{tag}')
            ctx.close()
            # 직원: 서식 · 회사 서류는 못 들어감
            ctx, p = page(w, h, sc)
            p.goto(BASE + 'forms/'); login(p, 'kim', 'pw2222')   # 앱을 열면 행사 목록 (2026.10.29)
            p.wait_for_function("typeof setTab==='function' && !document.documentElement.classList.contains('dw-gated')", timeout=15000); look(p, f'member_list_{tag}')
            if 'funeral.html' not in p.url:
                problems.append(f'member {tag}: 앱을 열었는데 행사 목록이 아님')
            if p.evaluate("!!(document.getElementById('dwMode')||{}).offsetParent"):
                problems.append(f'member {tag}: 직원에게 행사 · 서식 바꾸기가 보임')
            p.goto(BASE + 'forms/#board'); p.wait_for_function("typeof showTab==='function' && typeof S!=='undefined' && S.tab==='board'", timeout=15000); look(p, f'member_board_{tag}')
            p.goto(BASE + 'forms/admin.html'); p.wait_for_timeout(1500)
            if 'admin.html' in p.url:
                problems.append(f'member {tag}: 직원이 회사 서류에 들어감')
            ctx.close()
            # 총괄실장: 취합 · 서식 · 설정만, 장례업무는 못 들어감
            ctx, p = page(w, h, sc)
            p.goto(BASE + 'forms/'); login(p, 'boss', 'pw5555')
            try:
                p.wait_for_function("typeof S!=='undefined' && S.tab==='gather'", timeout=15000)
            except Exception:
                pass
            if p.evaluate("typeof S!=='undefined' ? S.tab : ''") != 'gather':
                problems.append(f'chief {tag}: 첫 화면이 취합이 아님')
            for v in ['weekly', 'minutes', 'review', 'ship']:
                p.click(f"#gtTabs [data-gv='{v}']"); p.wait_for_timeout(500); look(p, f'chief_{v}_{tag}')
            p.evaluate("showTab('docs')"); p.wait_for_timeout(500); look(p, f'chief_docs_{tag}')
            p.evaluate("showTab('settings')"); look(p, f'chief_settings_{tag}')
            p.evaluate("showTab('stock')"); p.wait_for_timeout(300)
            if p.evaluate('S.tab') != 'gather':
                problems.append(f'chief {tag}: 총괄실장이 물품 장부에 들어감')
            p.goto(BASE + 'forms/funeral.html'); p.wait_for_timeout(1500)
            if 'funeral.html' in p.url:
                problems.append(f'chief {tag}: 총괄실장이 장례업무에 들어감')
            ctx.close()
        b.close()

    for e in errs:
        print('페이지 오류:', e)
    for x in problems:
        print('문제:', x)
    print(f'화면 캡처: {OUT}')
    if errs or problems:
        print('화면 점검 실패')
        sys.exit(1)
    print('화면 점검 통과')


if __name__ == '__main__':
    main()
