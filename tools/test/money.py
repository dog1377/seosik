"""돈 계산 검산 — 고친 뒤 반드시 이 값이 그대로 나와야 함 (03_정산_봉투_수당_규칙.md 의 검산 예시).

    python3 tools/test/money.py            (tools/test/run.sh 가 웹서버를 띄우고 부름)

빌드된 forms/funeral.html 을 브라우저로 열어 실제 계산 함수(settleCalc · caseEnvelope · commText · rcptForms)를 부른다.
하나라도 다르면 실패(종료 코드 1).
"""
import os
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get('DW_BASE', 'http://127.0.0.1:8765/')

SETUP = r"""(()=>{
 const co=n=>db.companies.find(x=>x.name===n).id; rules().mgrName='이승구실장';
 startCase(co('현진시닝')); let c=curCase(), s=S(c);
 Object.assign(c.f,{eventNo:'1',place:'부산착한 VIP2호',name:'홍길동',depart:'2026-10-10T07:00',collect:'257.5',customer:'서재원',company:'넥센타이어',helper:'김정단',helperHours:'50',vehType:'버스 리무진',vehCo:'한맥장의차',mournBrand:'한맥',burial:'창원상복-부산추모(벽식)'});
 Object.assign(s,{pay:'현금',altarAmt:'100',altarPay:'현금',urnAsk:'yes',urnCollect:'90',urnCost:'25',urnDisc:'5',urnPay:'현금',urnType:'봉분골드천향',
   extras:[{id:'e1',text:'남상복 6세트 추가',amt:'30',pay:'현금'},{id:'e2',text:'여상복 4벌 추가',amt:'12',pay:'현금'}],flower:'경북 5만원',flowerPay:'월말 법카결제',flowerSale:'30',flowerSalePay:'현금',trib:'영호 5만원',tribPay:'월말 법카결제',
   hall:'10',burialAmt:'300',burialSea:'no',chodo:'5',kit:'3',lunch:'6'});
 const c1=c;
 startCase(co('디더블유')); c=curCase(); s=S(c);
 Object.assign(c.f,{eventNo:'3',place:'창원한마음',depart:'2026-10-12T07:00',collect:'389'});
 Object.assign(s,{pay:'카드',altarAmt:'30',altarPay:'현금',urnAsk:'yes',urnCollect:'120',urnCost:'36',urnPay:'카드',extras:[{id:'e3',text:'도우미 6시간 추가',amt:'12',pay:'카드'}],flower:'삼미 5만원',flowerPay:'월말 법카결제'});
 const c2=c;
 startCase(co('디더블유')); c=curCase(); s=S(c);
 Object.assign(c.f,{eventNo:'5',place:'김해복음',depart:'2026-10-14T07:00',collect:'300'}); Object.assign(s,{pay:'현금',altarAmt:'24',altarPay:'현금'});
 const before3=settleCalc(c).sendWon;
 s.carry=[{id:'r1',from:c2.id,label:caseTag(c2),won:settleCalc(c2).sendWon}];
 save();
 const v=caseEnvelope(c1);   // 원 단위
 S(c1).burialSea='yes'; const sea=caseEnvelope(c1); S(c1).burialSea='no'; caseEnvelope(c1);
 return {ex1:settleCalc(c1).sendWon, ex2:settleCalc(c2).sendWon, tag2:caseTag(c2), ex3before:before3, ex3:settleCalc(c).sendWon,
   part:v.part, mgr:v.manager, seaBur:[sea.partBurial,sea.managerBurial],
   comm:(commText(c1).match(/총계 : .*/)||[''])[0], rc:rcptForms(c1).map(f=>f.text).join('\n'), t1:settleText(c1),
   altar:(()=>{ startCase(co('디더블유')); const a=curCase(); Object.assign(a.f,{collect:'300',altar:'20'}); Object.assign(S(a),{pay:'현금'});   // 제단공제 20 · 2026.10.29 법인카드결제
     const ded=settleCalc(a).sendWon; a.f.altarCard=true; const card=settleCalc(a).sendWon, txt=vals(a)['제단공제']; a.f.altarCard=false; return [ded,card,txt]; })()};
})()"""

EXPECT = [
    ('제단공제 20 · 수금 300 현금 → 공제 / 법인카드결제(공제 안 함)', 'altar', [2800000, 3000000, '20만원 법인카드결제']),
    ('예시1 보내는금액', 'ex1', 3955000),
    ('예시2 보내는금액', 'ex2', -180000),
    ('예시2 마이너스 이름', 'tag2', '10월3번행사'),
    ('예시3 빼기 전', 'ex3before', 3240000),
    ('예시3 빼고 난 뒤', 'ex3', 3060000),
    ('예시4 본부장 봉투', 'part', 1660000),
    ('예시4 실장 봉투', 'mgr', 2820000),
    ('해양장 장지 (본부장 · 실장)', 'seaBur', [1500000, 1500000]),
    ('수당 총계', 'comm', '총계 : 134만원'),
]


def main():
    bad = []
    errs = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        ctx = b.new_context(viewport={'width': 1440, 'height': 900}, service_workers='block')
        ctx.route('https://**/*', lambda r: r.abort())
        p = ctx.new_page()
        p.on('pageerror', lambda e: errs.append(str(e)))
        p.goto(BASE + 'forms/funeral.html')
        p.wait_for_function("typeof settleCalc==='function' && typeof db==='object'", timeout=15000)
        r = p.evaluate(SETUP)
        for name, key, want in EXPECT:
            got = r[key]
            ok = got == want
            print(('  OK  ' if ok else '  틀림 ') + f'{name}: {got}' + ('' if ok else f'  (나와야 할 값: {want})'))
            if not ok:
                bad.append(name)
        ok = '4,195,000원' in r['rc']
        print(('  OK  ' if ok else '  틀림 ') + '영수증 발행금액 4,195,000원')
        if not ok:
            bad.append('영수증')
        ok = r['t1'].rstrip().endswith('보내는금액 : 3,955,000원')
        print(('  OK  ' if ok else '  틀림 ') + '정산 카톡 마지막 줄 「보내는금액 : 3,955,000원」')
        if not ok:
            bad.append('정산 카톡')
        b.close()
    if errs:
        print('페이지 오류:', errs)
    if bad or errs:
        print('돈 계산 검산 실패:', ', '.join(bad) or '페이지 오류')
        sys.exit(1)
    print('돈 계산 검산 통과')


if __name__ == '__main__':
    main()
