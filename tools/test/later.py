"""장지 추후입금 점검 (2026.11.13) — 정산 「장지에서 받은 금액」 추후입금 체크 → 「다음」 · 장지 종류 질문 · 확인 화면 줄 ·
첫 화면 할 일 · 행사 목록(거르기 · 표시) · 봉투 점검 → 「장지 금액 넣기」 → 금액을 넣으면 저절로 풀리고 봉투로 나뉨(300 → 152 / 148).

    python3 tools/test/later.py            (tools/test/run.sh 가 웹서버를 띄우고 부름)
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


def main():
    srv = Srv()
    srv.add_user('seo', 'pw1111', leader=True, name='서영우')
    bad = []

    def want(name, got, exp):
        if got != exp:
            bad.append(f'{name}: {got!r} (기대 {exp!r})')

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
        p.wait_for_function("typeof burialLater==='function' && !document.documentElement.classList.contains('dw-gated')", timeout=15000)
        p.wait_for_timeout(1200)
        p.evaluate("""(()=>{ const co=db.companies.find(x=>x.name==='디더블유'); startCase(co.id); const c=curCase();
          Object.assign(c.f,{eventNo:'4',place:'동래봉생 2호',name:'김말순',depart:seoulToday()+'T07:00'}); S(c).hall='10'; save();
          setSettleMode('wizard'); wzPos.set(c.id,'burial'); setTab('settle'); })()""")
        p.wait_for_timeout(500)
        want('빈 칸 버튼', p.inner_text('#wzGo'), '없음')
        p.check('#p-settle [data-s-later]')
        p.wait_for_timeout(200)
        want('추후입금 버튼', p.inner_text('#wzGo'), '다음')
        p.click('#wzGo')
        p.wait_for_timeout(400)
        want('다음 질문', p.evaluate('wzAt(curCase())'), 'sea')
        p.click('.wz-card [data-wz-pick="burialType"][data-v="tree"]')
        p.wait_for_timeout(300)
        p.evaluate("wzGo('done')")
        p.wait_for_timeout(400)
        want('확인 화면 줄', p.evaluate("document.querySelector('.wz-rv small').textContent"), '식장 10만원 · 장지 추후입금(수목장)')
        want('봉투 안내', p.evaluate("!!document.querySelector('#wzEnv .ep-later [data-later-go]')"), True)
        want('보내는금액 그대로', p.evaluate('settleCalc(curCase()).sendWon'), 0)
        p.evaluate("setTab('home')")
        p.wait_for_timeout(300)
        want('첫 화면 할 일', p.evaluate("[homeT.later.length, document.querySelector('#p-home').innerHTML.includes('장지 추후입금 1건')]"), [1, True])
        p.evaluate("LV.month='';LV.st='later';setTab('list')")
        p.wait_for_timeout(300)
        want('행사 목록 (추후입금만)', p.evaluate("[document.querySelectorAll('.lv-tr:not(.lv-th):not(.lv-tf)').length, !!document.querySelector('.lv-later')]"), [1, True])
        p.evaluate("setTab('envelopes')")
        p.wait_for_timeout(300)
        want('봉투 점검', p.evaluate("envChkItems().filter(x=>x.act==='later').length"), 1)
        p.evaluate("laterGo(curCase())")
        p.wait_for_timeout(400)
        want('장지 금액 넣기', p.evaluate("[db.tab, wzAt(curCase())]"), ['settle', 'burial'])
        p.fill('#p-settle [data-s="burialAmt"]', '300')
        p.wait_for_timeout(300)
        want('금액 넣으면 풀림', p.evaluate("[burialLater(curCase()), document.querySelector('#p-settle [data-s-later]').checked]"), [False, False])
        want('봉투 장지 (수목장)', p.evaluate("(()=>{ const e=caseEnvelope(curCase()); return [e.partBurial,e.managerBurial]; })()"), [1520000, 1480000])
        # 모두 보기: 체크하면 넣어 둔 금액은 비움
        p.evaluate("setSettleMode('all')")
        p.wait_for_timeout(300)
        p.check('#p-settle [data-s-later]')
        p.wait_for_timeout(200)
        want('모두 보기 체크', p.evaluate("[S(curCase()).burialAmt, burialLater(curCase()), document.querySelector('#p-settle [data-s=\"burialAmt\"]').value]"), ['', True, ''])
        p.evaluate("setSettleMode('wizard')")
        if errs:
            bad.append('페이지 오류: ' + ' / '.join(errs))
        b.close()
    if bad:
        print('장지 추후입금 점검 실패:')
        for x in bad:
            print('-', x)
        sys.exit(1)
    print('장지 추후입금 점검 통과')


if __name__ == '__main__':
    main()
