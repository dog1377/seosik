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
        p.evaluate('DW_HOME_GO()')   # 휴대폰: 로그아웃 버튼은 첫 화면에만 (2026.10.30)
        p.click('#dwOut'); p.click('.dwc-ok'); p.wait_for_selector('#gtId', timeout=10000)
        p.click('#gtSwap'); p.fill('#gtId', 'newbie'); p.fill('#gtPw', 'pw3333'); p.fill('#gtPw2', 'pw3333'); p.click('#gtGo')
        p.wait_for_function(READY, timeout=15000); p.wait_for_timeout(1500)
        if p.evaluate(NCASES) != 0:
            problems.append('계정: 새로 가입한 계정에 이 기기의 다른 사람 기록이 보임')
        if [k for k in srv.ROWS if k[0] == 'uid-newbie' and k[2] == 'case']:
            problems.append('계정: 새로 가입한 계정으로 다른 사람 기록이 올라감')
        p.evaluate('DW_HOME_GO()')
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
            # 서식 설정은 한 가지씩 (2026.11.11 설정 한 곳 — 목록은 장례업무 설정, 서식 첫 화면 fhome 은 총괄실장만)
            for t in ['board', 'docs', 'weekly', 'minutes', 'review', 'ship', 'stock', 'consult', 'settings:info', 'settings:roster', 'settings:sig', 'settings:staff']:
                p.evaluate(f"showTab('{t}')"); p.wait_for_timeout(500); look(p, f'forms_{t.replace(":", "_")}_{tag}')
                want = 'event' if t in ('board', 'docs') else 'forms'
                got = p.evaluate("[document.body.dataset.mode, (document.querySelector('#dwMode [aria-pressed=\"true\"]')||{getAttribute:()=>''}).getAttribute('data-dwmode')]")
                if got[0] != want or got[1] != want:
                    problems.append(f'{tag} {t}: 행사 · 서식 칸 표시가 다름 {got}')
            # 게시판 위 줄 (2026.11.25 사용자 「파트원 관리 글씨가 너무 작아서 안 보임」): 파트 게시판 · 파트 현황 · 파트원 관리 · 자료실
            p.evaluate("showTab('board')"); p.wait_for_timeout(600)
            got = p.evaluate("[...document.querySelectorAll('#boardTabs [data-btab]')].filter(b=>b.offsetParent).map(b=>b.textContent).join(',')")
            if got != '파트 게시판,파트 현황,파트원 관리,자료실':
                problems.append(f'{tag}: 게시판 위 줄이 다름 {got}')
            p.click('#boardTabs [data-btab="board:people"]'); p.wait_for_timeout(500); look(p, f'forms_board_people_{tag}')
            got = p.evaluate("[S.tab, PB.view, (document.querySelector('#bdBody .pg-title')||{}).textContent||'', document.querySelector('#boardTabs [aria-current=page]').dataset.btab, !!document.getElementById('bdAddId')]")
            if got[:2] != ['board', 'people'] or not got[2].startswith('파트원 관리') or got[3] != 'board:people' or not got[4]:
                problems.append(f'{tag}: 「파트원 관리」 칸이 안 열림 {got}')
            p.click('#boardTabs [data-btab="board:status"]'); p.wait_for_timeout(500)
            if p.evaluate("[PB.view, (document.querySelector('#bdBody .pg-title')||{}).textContent||'']")[0] != 'status':
                problems.append(f'{tag}: 「파트 현황」 칸이 안 열림')
            p.click('#boardTabs [data-btab="board"]'); p.wait_for_timeout(400)
            if (w, h, sc) == SIZES[0]:   # 1~4파트 · 파트장 누구든 직원 파트 지정 (2026.11.25)
                got = p.evaluate("""(async()=>{ const L=await window.dwAcct.rpc('dw_staff_list'), kim=(L.people||[]).find(x=>x.login_id==='kim'), p2=(L.parts||[]).find(x=>x.name==='2파트');
                  const S=await window.dwAcct.rpc('dw_staff_set',{p:{user:kim.user_id,part:p2.id}}), M=await window.dwAcct.rpc('dw_me'), D=await window.dwAcct.rpc('dw_part_delete',{p_part:p2.id});
                  return [(L.parts||[]).map(x=>x.name).join(','), !!kim.can_part, S.part, (M.parts||[]).map(x=>x.name+':'+x.mine).join(','), D.why]; })()""")
                if got != ['1파트,2파트,3파트,4파트', True, '2파트', '1파트:true,2파트:true,3파트:true,4파트:true', 'fixed']:
                    problems.append(f'{tag}: 1~4파트 · 파트장 파트 지정이 다름 {got}')
            # 내 정보 (위 막대 아이디를 누르면, 2026.10.29)
            p.click('.appbar .local'); p.wait_for_selector('#dwMe:not([hidden])', timeout=5000); look(p, f'forms_me_{tag}')
            if p.input_value('#dwMeName') != '서영우':
                problems.append(f'{tag}: 내 정보 이름이 안 채워짐')
            p.keyboard.press('Escape'); p.wait_for_timeout(200)
            # 장례업무 (같은 기기 · 로그인 유지)
            p.goto(BASE + 'forms/funeral.html'); p.wait_for_function("typeof setTab==='function'", timeout=15000)
            p.evaluate(SEED)
            # 휴대폰 첫 화면 (2026.11.11 바둑판 3안): 아래 메뉴 없음 · 행사 · 서식 · 배송 묶음 한 장 · 「‹ 홈」은 첫 화면이 아닐 때만
            if p.evaluate("!!document.getElementById('mobileNav').offsetParent"):
                problems.append(f'{tag}: 장례업무 아래 메뉴가 보임 (2026.10.30 에 없앰)')
            if w < 700:
                p.evaluate("setTab('input')")
                if not p.evaluate("!!(document.getElementById('dwHomeBtn')||{}).offsetParent"):
                    problems.append(f'{tag}: 행사 입력 화면에 「‹ 홈」 버튼이 안 보임')
                p.click('#dwHomeBtn'); p.wait_for_timeout(300)
                # 첫 화면 (2026.11.25 B안): 요약 카드 + 묶음 접기 · 펴기(진행 중인 행사 · 정산 남음 · 자주 쓰는 기능 · 서식 · 파트 · 자료 — 예전 이름 함께 쓰기, 2026.11.25) · 맨 아래 설정 · 떠 있는 「+ 새 행사」 · 위 막대 ☰ (아래 탭 바 없음)
                vis = "(id=>{const e=document.getElementById(id);return !!e&&getComputedStyle(e).display!=='none'})"
                p.evaluate("db.homeQuick=[]; save(); renderHome()")   # 같은 계정으로 화면 크기마다 다시 들어오므로 처음 상태로
                got = p.evaluate(f"[db.tab, [...document.querySelectorAll('#p-home .dsh-acc-h b')].map(x=>x.textContent).join(' '), document.querySelectorAll('#p-home .dsh-q').length, (document.querySelector('#p-home .dsh-todo b')||{{}}).textContent||'', !!(document.getElementById('dwHomeBtn')||{{}}).offsetParent, {vis}('dwSideBtn'), {vis}('dwFab'), !!document.getElementById('dwTabbar')]")
                if got != ['home', '진행 중인 행사 정산 남음 자주 쓰는 기능 서식 파트 · 자료', 0, '오늘 할 일 3건', False, True, True, False]:   # 자주 쓰는 기능은 처음엔 비어 있음 (2026.11.19)
                    problems.append(f'{tag}: 첫 화면이 다름 [탭, 묶음, 퀵 카드, 할 일, 홈 버튼 보임, ☰, 새 행사 버튼, 탭 바 있음] = {got}')
                if p.evaluate("document.querySelectorAll('#p-home .dsh-case').length"):   # 시험 행사는 발인일(10월)이 지남 → 진행 중 아님
                    problems.append(f'{tag}: 발인일이 지난 행사가 「진행 중인 행사」에 보임')
                p.click('#p-home [data-hacc="settle"]'); p.wait_for_timeout(200)   # 묶음 접기 → 이 기기에 기억
                if p.evaluate("[document.getElementById('hacc-settle').hidden, JSON.parse(localStorage.getItem('dw-home-acc')||'{}').settle]") != [True, False]:
                    problems.append(f'{tag}: 첫 화면 묶음을 눌러도 접히지 않음')
                p.click('#p-home [data-hacc="settle"]'); p.wait_for_timeout(200)
                p.click('#p-home .dsh-qempty'); p.wait_for_timeout(300)   # 자주 쓰는 기능 고르기 → 화장예약 조회 · 정산
                p.click('#acList [data-qe="crem"]'); p.click('#acList [data-qe="p-settle"]'); p.click('#acFoot [data-qe-done]'); p.wait_for_timeout(300)
                if p.evaluate("[db.homeQuick, 'homeQuick' in sbSettings(), [...document.querySelectorAll('#p-home .dsh-q .dsh-ql')].map(x=>x.textContent)]") != [['crem', 'p-settle'], True, ['화장예약 조회', '정산', '추가']]:
                    problems.append(f'{tag}: 자주 쓰는 기능을 골랐는데 첫 화면 카드가 다름')
                crem = p.evaluate("(a=>a&&[a.getAttribute('href'),a.target,a.rel,a.querySelector('.dsh-ql').textContent])(document.querySelector('#p-home a.dsh-q'))")   # 화장예약 조회 = e하늘 새 창
                if crem != ['https://15774129.go.kr/info/total_search.do', '_blank', 'noopener noreferrer', '화장예약 조회']:
                    problems.append(f'{tag}: 첫 화면 「화장예약 조회」 카드가 다름 {crem}')
                p.click('#p-home .dsh-todo'); p.wait_for_timeout(300)
                if p.evaluate("document.getElementById('acBg').hidden || document.querySelectorAll('#acList .dsh-row').length!==3"):
                    problems.append(f'{tag}: 첫 화면 「오늘 할 일 3건」을 눌러도 할 일 3줄이 안 나옴')
                look(p, f'funeral_home_todo_{tag}')
                p.click('#acClose'); p.wait_for_timeout(300)
                p.locator('#p-home [data-hk="list"]').click(); p.wait_for_timeout(300)   # 행사 목록 전체 보기
                if p.evaluate("[db.tab, document.getElementById('tnSubRow').hidden, !!(document.getElementById('dwHomeBtn')||{}).offsetParent]") != ['list', True, True]:
                    problems.append(f'{tag}: 첫 화면 「행사 목록 전체 보기」 → 행사 목록(「‹ 홈」 있음)이 아님')
                # 왼쪽 메뉴 (2026.11.25 B안): ☰ → 왼쪽에서 열림 · 묶음 · 정산할 행사 → 행사 목록(정산할 것만)
                p.click('#dwSideBtn'); p.wait_for_timeout(350); look(p, f'funeral_side_{tag}')
                got = p.evaluate("[document.documentElement.classList.contains('dsn-open'), [...document.querySelectorAll('#dwSide .dsn-h span')].map(x=>x.textContent).join(' '), document.getElementById('dwSide').inert]")
                if got != [True, '행사 업무 정산 · 봉투 화장예약 서식 배송 파트 · 자료', False]:
                    problems.append(f'{tag}: ☰ 왼쪽 메뉴가 다름 [열림, 묶음, 막힘] = {got}')
                p.click('#dwSide [data-dsn="todo"]'); p.wait_for_timeout(350)
                if p.evaluate("[db.tab, LV.st, document.documentElement.classList.contains('dsn-open')]") != ['list', 'todo', False]:
                    problems.append(f'{tag}: 왼쪽 메뉴 「정산할 행사」 → 행사 목록(정산할 것)이 아님')
                # 행사를 누르면 그 행사의 일 (B안): 행사 화면 위 6칸 · 왼쪽 메뉴 「지금 보는 행사」
                p.evaluate("LV.st=''; listSave(); setTab('input')"); p.wait_for_timeout(300)
                got = p.evaluate("[...document.querySelectorAll('#caseSteps [data-ctab]')].map(b=>b.dataset.ctab).join(',')")
                if got != 'input,out,sched,poster,settle,envelopes':
                    problems.append(f'{tag}: 행사 화면 「이 행사의 일」 칸이 다름 {got}')
                p.click('#caseSteps [data-ctab="sched"]'); p.wait_for_timeout(350)
                p.click('#dwSideBtn'); p.wait_for_timeout(350)
                got = p.evaluate("[db.tab, !document.getElementById('dwSideCase').hidden, (document.querySelector('#dwSideCase [aria-current]')||{}).textContent||'']")
                if got[:2] != ['sched', True] or not got[2].startswith('보고서'):
                    problems.append(f'{tag}: 행사 칸 「보고서」 · 왼쪽 메뉴 지금 보는 행사가 다름 {got}')
                p.click('#dwSide [data-dsn-case="settle"]'); p.wait_for_timeout(350)
                if p.evaluate('db.tab') != 'settle':
                    problems.append(f'{tag}: 왼쪽 메뉴 지금 보는 행사 「정산」을 눌러도 정산이 아님')
                # 1~5단계 (2026.11.13): 자주 쓰는 기능 「행사 보고서」 → 이번 달 행사 고르기 → 그 행사의 행사 보고서
                p.evaluate("setTab('home')"); p.wait_for_timeout(200); p.evaluate("homeGo('p-sched')"); p.wait_for_timeout(400)
                got = p.evaluate("[!document.getElementById('cpBg').hidden, document.getElementById('cpTitle').textContent, cpMonth===seoulToday().slice(0,7)||!db.cases.some(c=>caseMonth(c)===seoulToday().slice(0,7))]")
                if got != [True, '행사 보고서 · 행사 선택', True]:
                    problems.append(f'{tag}: 「행사 보고서」 → 이번 달 행사 고르기가 아님 {got}')
                p.locator('#cpList [data-cp]').first.click(); p.wait_for_timeout(400)
                if p.evaluate("[db.tab, document.getElementById('cpBg').hidden]") != ['sched', True]:
                    problems.append(f'{tag}: 행사를 골랐는데 행사 보고서로 안 감')
                p.evaluate("dwSide.open('ship')"); p.wait_for_timeout(350)   # 접혀 있던 묶음은 열면서 펼침
                p.click('#dwSide [data-dsn="dnew"]'); p.wait_for_timeout(350)
                if p.evaluate("[db.tab, !!dvCur(), window.dwDrawer.key()==='dv:'+db.shipCur]") != ['deliv', True, True]:   # 새 배송 = 서랍이 열림 (2026.11.14)
                    problems.append(f'{tag}: 왼쪽 메뉴 「새 배송」을 눌렀는데 새 배송이 안 됨')
                p.evaluate("window.dwDrawer.close(); db.ships=[]; db.shipCur=null; save()"); p.wait_for_timeout(250)
                # 설정 한 곳 (2026.11.11): 전체 「설정」 → 설정 목록 → 한 가지 → 「‹ 설정」
                p.click('#dwSideBtn'); p.wait_for_timeout(350)
                p.click('#dwSide .dsn-foot [data-dsn="set"]'); p.wait_for_timeout(400)   # 설정 = 메뉴 맨 아래 늘 보이는 한 줄 (2026.11.25)
                got = p.evaluate("[db.tab, db.adminView, [...document.querySelectorAll('#setHub .dws-g h2')].map(x=>x.textContent).join(' '), !!document.querySelector('#setHub .dws-me')]")
                if got != ['admin', 'hub', '직원 행사 업무 서식 · 보고서 회사 서류 화면 · 계정', True]:   # 직원 명단 묶음 (2026.11.14)
                    problems.append(f'{tag}: 설정 목록이 다름 {got}')
                p.locator('#setHub [data-dws="ev-rules"]').click(); p.wait_for_timeout(300)
                if p.evaluate("[db.adminView, document.getElementById('setBack').hidden, !!document.getElementById('rAltar').offsetParent]") != ['rules', False, True]:
                    problems.append(f'{tag}: 설정 목록 「정산 기준」 → 정산 기준 화면이 아님')
                p.locator('#setBack [data-dws-back]').click(); p.wait_for_timeout(300)
                if p.evaluate('db.adminView') != 'hub':
                    problems.append(f'{tag}: 「‹ 설정」을 눌러도 설정 목록으로 안 감')
            if w >= 700:   # 왼쪽 메뉴 (2026.11.25 B안): 1100px 이상 늘 보임, 700~1099px 아이콘 줄 + 누르면 펼침
                p.evaluate("setTab('input')"); p.wait_for_timeout(300)
                got = p.evaluate("[getComputedStyle(document.getElementById('dwSide')).visibility, !!document.querySelector('.dsn-rail')&&getComputedStyle(document.querySelector('.dsn-rail')).display!=='none', !document.getElementById('dwSideCase').hidden, document.querySelectorAll('#caseSteps [data-ctab]').length, getComputedStyle(document.getElementById('topNav').querySelector('.tn-main-row')).display]")
                want = ['visible' if w >= 1100 else 'hidden', w < 1100, True, 6, 'none']
                if got != want:
                    problems.append(f'{tag}: 넓은 화면 왼쪽 메뉴가 다름 [메뉴 보임, 아이콘 줄, 지금 보는 행사, 행사 칸 수, 예전 메뉴 줄] = {got}')
                if w < 1100:
                    p.click('.dsn-rail [data-dsn-open="money"]'); p.wait_for_timeout(350); look(p, f'funeral_rail_open_{tag}')
                    if p.evaluate("[document.documentElement.classList.contains('dsn-open'), document.querySelector('[data-dsn-h=\"money\"]').getAttribute('aria-expanded')]") != [True, 'true']:
                        problems.append(f'{tag}: 아이콘 줄 「정산」을 눌러도 메뉴가 안 펼쳐짐')
                    p.keyboard.press('Escape'); p.wait_for_timeout(300)
                    if p.evaluate("document.documentElement.classList.contains('dsn-open')"):
                        problems.append(f'{tag}: Esc 로 왼쪽 메뉴가 안 닫힘')
            for t in ['home', 'list', 'input', 'out', 'poster', 'deliv', 'settle', 'envelopes', 'duty', 'admin']:
                if t == 'deliv':   # 배송 (2026.10.30): 인력+대체 한 건을 넣고 양식 줄 확인
                    p.evaluate("db.ships=[{id:'t1',kind:'sub',co:'삼성SDS',place:'부산대동 VIP실',mgr:[{id:'m1',date:'2026-10-13',sh:'10',sm:'00',eh:'20',em:'00',n:'1'}],veh:{type:'리무진',km:'200',burial:'김해추모',depart:'2026-10-14T06:30',co:'한맥장의차'},subs:[{id:'s1',n:'4',what:'veh'},{id:'s2',n:'3',what:'mourn',m:'5',w:'1'}],updated:1}]; db.shipCur='t1'")
                p.evaluate(f"setTab('{t}')"); look(p, f'funeral_{t}_{tag}')
                if t == 'deliv':   # 2026.11.14: 배송 기록 목록 → 줄을 누르면 서랍(입력 칸 · 양식)
                    if p.evaluate("[document.querySelectorAll('#p-deliv .lv-tr[data-key]').length, document.querySelectorAll('#p-deliv .kpi-card').length]") != [1, 4]:
                        problems.append(f'{tag}: 배송 기록 목록 · 요약 카드가 다름')
                    p.locator('#p-deliv .lv-tr[data-key] .lv-ico').first.click(); p.wait_for_timeout(350); look(p, f'funeral_deliv_drawer_{tag}')
                    got = p.evaluate("document.getElementById('dvText').value")
                    want = '회사명 : 현진시닝\n업체명 : 삼성SDS\n부산대동 VIP실\n13일 : 10시-20시 1명\n관리사 배치완료.\n\n관리사 4명 대체\n리무진 200km 장지(김해추모)\n14일 06시 배차\n14일 06시 30분 발인\n차량배차완료(한맥장의차)\n\n관리사 3명 대체\n남상복 5세트 여상복 1벌 제공'
                    if got != want:
                        problems.append(f'{tag}: 배송 양식이 다름: {got!r}')
                    # 「버스 리무진」 = 리무진(화장장까지) · 장의버스 따로, 「차량 추가」 = 대체 줄 없이 차량만 (2026.10.30)
                    p.evaluate("db.ships[0].veh={type:'버스 리무진',km:'200',crem:'부산',burial:'부산추모(평장)',depart:'2026-10-14T06:30',co:'한맥장의차'}; db.ships[0].subs=[{id:'s2',n:'3',what:'mourn',m:'5',w:'1'},{id:'s3',what:'car'}]; renderDeliv()")
                    got = p.evaluate("document.getElementById('dvText').value")
                    car = '14일 06시 배차\n14일 06시 30분 발인\n차량배차완료(한맥장의차)'
                    want = '회사명 : 현진시닝\n업체명 : 삼성SDS\n부산대동 VIP실\n13일 : 10시-20시 1명\n관리사 배치완료.\n\n관리사 3명 대체\n남상복 5세트 여상복 1벌 제공\n\n리무진 부산영락\n' + car + '\n\n장의버스 200km 부산영락-부산추모-장례식장\n' + car
                    if got != want:
                        problems.append(f'{tag}: 배송 버스 리무진 양식이 다름: {got!r}')
                    p.evaluate("db.ships[0].veh.burial='부산추모-장례식장'; renderDeliv()")   # 장례식장을 직접 적으면 한 번만
                    if p.evaluate("document.getElementById('dvText').value") != want:
                        problems.append(f'{tag}: 배송 장례식장이 두 번 들어감')
                    if p.evaluate("document.getElementById('dvCremWrap').hidden || !!document.querySelector('[data-dv-car-add]')"):
                        problems.append(f'{tag}: 배송 화장장 칸이 안 보이거나 「차량 추가」가 두 번 됨')
                    p.evaluate("db.ships=[]; db.shipCur=null; save()")
            # 회사 서류
            p.goto(BASE + 'forms/admin.html'); p.wait_for_function("typeof showTab==='function'", timeout=15000)
            for t in ['docs', 'staff', 'settings']:
                p.evaluate(f"showTab('{t}')"); look(p, f'admin_{t}_{tag}')
            if p.evaluate("[document.getElementById('coTabs').hidden, document.getElementById('coSetBack').hidden, document.querySelectorAll('#coTabs [data-ctab]').length]") != [True, False, 2]:
                problems.append(f'{tag}: 회사 정보 화면이 설정 한 가지 모양(「‹ 설정」, 서류 · 직원 탭 숨김)이 아님')
            ctx.close()
            # 직원: 서식 · 회사 서류는 못 들어감
            ctx, p = page(w, h, sc)
            p.goto(BASE + 'forms/'); login(p, 'kim', 'pw2222')   # 앱을 열면 행사 목록 (2026.10.29)
            p.wait_for_function("typeof setTab==='function' && !document.documentElement.classList.contains('dw-gated')", timeout=15000); look(p, f'member_list_{tag}')
            if 'funeral.html' not in p.url:
                problems.append(f'member {tag}: 앱을 열었는데 행사 목록이 아님')
            if p.evaluate("!!(document.querySelector('#dwMode [data-dwmode=\"forms\"]')||{}).offsetParent"):
                problems.append(f'member {tag}: 직원에게 「서식」 칸 바꾸기가 보임')
            if w < 700:
                if p.evaluate('db.tab') != 'home':
                    problems.append(f'member {tag}: 휴대폰에서 앱을 열었는데 첫 화면이 아님')
                elif p.evaluate("[...document.querySelectorAll('#p-home .dsh-acc-h b')].map(x=>x.textContent).join(' ')") != '진행 중인 행사 정산 남음 자주 쓰는 기능 파트 · 자료':
                    problems.append(f'member {tag}: 직원 첫 화면에 서식 묶음이 보이거나 묶음이 다름')
                p.evaluate("setTab('admin')"); look(p, f'member_settings_{tag}')
                if p.evaluate("[...document.querySelectorAll('#setHub [data-dws]')].map(b=>b.dataset.dws).filter(k=>k.startsWith('ev-')||k.startsWith('fm-')||k.startsWith('co-')).join(',')") != 'ev-rules,ev-lists,ev-keep':
                    problems.append(f'member {tag}: 직원 설정 목록에 파트장 설정이 보임')
            p.goto(BASE + 'forms/#board'); p.wait_for_function("typeof showTab==='function' && typeof S!=='undefined' && S.tab==='board'", timeout=15000); look(p, f'member_board_{tag}')
            got = p.evaluate("[...document.querySelectorAll('#boardTabs [data-btab]')].filter(b=>b.offsetParent).map(b=>b.textContent).join(',')")
            if got != '파트 게시판,자료실':   # 직원은 파트 현황 · 파트원 관리 없음
                problems.append(f'member {tag}: 직원 게시판 위 줄이 다름 {got}')
            p.goto(BASE + 'forms/admin.html'); p.wait_for_timeout(1500)
            if 'admin.html' in p.url:
                problems.append(f'member {tag}: 직원이 회사 서류에 들어감')
            ctx.close()
            # 총괄실장: 취합 · 서식 · 설정만, 장례업무는 못 들어감
            ctx, p = page(w, h, sc)
            p.goto(BASE + 'forms/'); login(p, 'boss', 'pw5555')
            try:
                p.wait_for_function("typeof S!=='undefined' && (S.tab==='gather' || S.tab==='fhome')", timeout=15000)
            except Exception:
                pass
            first = 'fhome' if w < 700 else 'gather'   # 휴대폰은 서식 첫 화면 바둑판 (2026.10.30)
            if p.evaluate("typeof S!=='undefined' ? S.tab : ''") != first:
                problems.append(f'chief {tag}: 첫 화면이 {first} 가 아님')
            if w < 700:
                look(p, f'chief_fhome_{tag}'); p.evaluate("showTab('gather')"); p.wait_for_timeout(500)
            for v in ['weekly', 'minutes', 'review', 'ship']:
                p.click(f"#gtTabs [data-gv='{v}']"); p.wait_for_timeout(500); look(p, f'chief_{v}_{tag}')
            p.evaluate("showTab('docs')"); p.wait_for_timeout(500); look(p, f'chief_docs_{tag}')
            p.evaluate("showTab('settings')"); look(p, f'chief_settings_{tag}')
            if p.evaluate("[S.setView, [...document.querySelectorAll('#setHubF [data-dws]')].map(b=>b.dataset.dws).filter(k=>/^(ev|fm|co|duty)/.test(k)).join(',')]") != ['hub', 'fm-info,fm-sig,co-info']:
                problems.append(f'chief {tag}: 총괄실장 설정 목록이 다름')
            p.evaluate("showTab('settings:info')"); look(p, f'chief_settings_info_{tag}')
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
