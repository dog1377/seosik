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
   hall:'10',burialAmt:'300',burialType:'tree',burialSea:'no',chodo:'5',kit:'3',lunch:'6'});
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
 setBType(S(c1),'sea'); const sea=caseEnvelope(c1); setBType(S(c1),'tree'); caseEnvelope(c1);
 const line=(k)=>(commText(c1).split('\n').find(l=>l.startsWith(k+' :'))||''), tot=()=>(commText(c1).match(/총계 : .*/)||[''])[0];
 const bt={tree:[line('수목장'),tot()]}; setBType(S(c1),'sea'); bt.sea=[line('바다장'),tot()]; setBType(S(c1),'ossuary'); bt.oss=[line('납골'),tot()];
 delete S(c1).burialType; S(c1).burialSea='no'; bt.oldNo=[line('수목장'),line('바다장'),line('납골'),tot()]; S(c1).burialSea='yes'; bt.oldYes=[line('바다장'),tot()];
 setBType(S(c1),'tree'); caseEnvelope(c1);
 return {ex1:settleCalc(c1).sendWon, ex2:settleCalc(c2).sendWon, tag2:caseTag(c2), ex3before:before3, ex3:settleCalc(c).sendWon,
   part:v.part, mgr:v.manager, seaBur:[sea.partBurial,sea.managerBurial],
   comm:(commText(c1).match(/총계 : .*/)||[''])[0], bt, rc:rcptForms(c1).map(f=>f.text).join('\n'), t1:settleText(c1),
   altar:(()=>{ startCase(co('디더블유')); const a=curCase(); Object.assign(a.f,{collect:'300',altar:'20'}); Object.assign(S(a),{pay:'현금'});   // 제단공제 20 · 2026.10.29 법인카드결제
     const ded=settleCalc(a).sendWon; a.f.altarCard=true; const card=settleCalc(a).sendWon, txt=vals(a)['제단공제'], band=(bandOut(a).match(/제단공제 : .*/)||[''])[0]; a.f.altarCard=false; return [ded,card,txt,band]; })(),
   goiDed:(()=>{ startCase(co('고이장례연구소')); const g=curCase(); g.f.collect='300'; S(g).pay='현금';   // 2026.11.14 고이 공제 · 추가 항목 「할인」도 뺌
     g.deductions=[{id:'d1',text:'헌화30송이 5만원공제'},{id:'d2',text:'장례식장 할인 10만원'},{id:'d3',text:'도우미 6시간 추가 120,000원'}];
     return [collectNetWon(g), settleCalc(g).sendWon, dedAmtText(g,g.deductions[1])]; })(),
   goiCert:(()=>{ startCase(co('고이장례연구소')); const g=curCase(); g.f.collect='300'; S(g).pay='현금';   // 2026.11.14 이행완료확인서 = 기존 납입금 + 할인 금액 공제
     Object.assign(g.f,{paidAsk:'yes',paid:'1',discAsk:'yes',certDisc:'10'}); g.deductions=[{id:'d1',text:'헌화30송이 5만원공제'}];
     const r=[vals(g)['공제항목'], collectNetWon(g)];
     g.f.discAsk='no'; r.push(vals(g)['공제항목'].split('\n')[0], collectNetWon(g)); g.f.discAsk='yes';
     g.deductions.push({id:'d2',text:'이행완료확인서 11만원 공제'}); r.push(collectNetWon(g)); return r; })(),
   goiBand:(()=>{ startCase(co('고이장례연구소')); const g=curCase();   // 2026.11.24 상품 289 자동 · 이행완료확인서(기납입 1 + 할인 10) · 밴드 납입 · 잔액 · 수금액
     g.f.product='2026 가족장 289'; goiAutoCollect(g); S(g).pay='현금'; Object.assign(g.f,{certAsk:'yes',paid:'1',certDisc:'10'}); g.deductions=[{id:'d1',text:'헌화30송이 5만원공제'}];
     const v=vals(g), r=[g.f.collect, v['납입'], v['잔액'], v['수금액'], vals(g)['공제항목'], settleCalc(g).sendWon];
     g.f.certAsk='no'; g.f.paid=''; g.f.certDisc=''; const v2=vals(g); r.push(v2['납입'], v2['잔액'], v2['수금액']);
     r.push(prodWon('289 4일장'), prodWon('2026 가족장'), prodWon('삼성전기 270 일반형'));
     g.f.collect='300'; delete g.f.collectAuto; g.f.product='2026 가족장 320'; r.push(goiAutoCollect(g), g.f.collect); return r; })(),
   basket:(()=>{ startCase(co('디더블유')); const b=curCase();   // 2026.11.24 꽃바구니 줄 · 입관꽃장식 제공
     Object.assign(b.f,{eventNo:'9',place:'양산농협 VIP1호',depart:'2026-11-20T07:00',collect:'250',helper:'김정단',helperHours:'20',vehType:'버스 리무진',vehCo:'한맥장의차',mournBrand:'한맥',burial:'진주화장-양산선영(평장)'});
     Object.assign(S(b),{pay:'현금',altarAmt:'38',altarPay:'현금',extras:[{id:'x1',text:'여상복 1벌',amt:'3',pay:'현금'}],flower:'경북 5만원',flowerPay:'월말 법카결제',basket:'영호 2만원',basketPay:'월말 법카결제'});
     const t1=settleText(b).split('\n').slice(-6).join('\n'), w1=settleCalc(b).sendWon;
     S(b).basketPay='현장결제'; const w2=settleCalc(b).sendWon;
     S(b).basket=''; S(b).basketPay=''; const t3=settleText(b), none=!/꽃바구니/.test(t3);
     S(b).basket='영호 2만원'; S(b).basketPay='월말 법카결제'; const ck=checkSettleKakao(settleText(b)); const ckOk=!ck.money.length&&!ck.form.length;
     S(b).flowerFree='yes'; const skip=!scrOn(b,SCR[SCR_I('fsAsk')]); S(b).flowerFree=''; const ask=scrOn(b,SCR[SCR_I('fsAsk')]);
     return [t1,w1,w2,none,ckOk,skip,ask]; })(),
   crem:(()=>{ startCase(co('디더블유')); const c=curCase(), r=[];   // 2026.11.24 화장장 이름: 회사 보고 = 정식 이름, 밴드 · 배차 = 짧은 이름
     for(const n of ['부산영락','김해추모의공원','창원','마산화장장']){ Object.assign(c.f,{method:'화장',cremName:n,cremDate:'2026-11-25',cremTime:'09:00',cremRound:'3',burial:'창원상복-부산추모(벽식)'});
       r.push(reportFill('화장 : {화장}\n장법 : {장법화장장}\n장지 : {장지}',c), fillTpl('화장 : {화장}',c), cremOrHagwan(c.f)); }
     return r; })(),
   bmark:(()=>{ startCase(co('현진시닝')); const c=curCase();   // 2026.11.24 밴드 장법 괄호 (부산추모(봉안)) · 회사 보고에는 안 들어감
     Object.assign(c.f,{burial1:'부산영락',burial2:'부산추모',burialMark:'봉안'}); const r=[bandBurial(c.f), reportFill('장지 : {장지}\n2차 : {2차장지}',c), (bandOut(c).match(/장\s*지 : .*/)||[''])[0]];
     c.f.burial='창원상복-부산추모(벽식)'; c.f.burialMark='자차'; r.push(bandBurial(c.f), reportFill('장지 : {장지}',c));
     c.f.burial=''; c.f.burial1='안동선영'; c.f.burial2=''; c.f.burialMark='산골,자차'; r.push(bandBurial(c.f), reportFill('장지 : {장지}',c), settleText(c).split('\n').find(l=>/^장지 :/.test(l))||'');
     return r; })(),
   etc:(()=>{ const e=coById(ETC), g=db.companies.find(x=>x.name==='고이장례연구소'), r=[activeReports(e).length, activeReports(g).length>0];   // 2026.11.24 기타 업체 = 고이 양식 없음
     const keep=e.reports; e.reports=[{id:'a',name:'보고 양식',body:GOI_REPORT},{id:'b',name:'내 양식',body:'장소 : {장소}'}]; e.reportsEnabled=true; etcNoGoi(); r.push(e.reports.map(x=>x.name).join(',')); e.reports=keep; delete e.reportsEnabled;
     startCase(ETC); r.push(outViews(curCase()).some(([k])=>/^rep/.test(k))); return r; })(),
   goiBal:(()=>{ const goi=co('고이장례연구소'), r=[];   // 2026.11.24 사용자 실제 행사: 잔액 2,781,100원 · 공제 1만원 → 수금액 2,771,100원 (이행완료확인서 두 번 빠지던 것)
     startCase(goi); let g=curCase(); psApply(g,psParse('장례행사 일정표\n장   소 : 부산메리놀 특2호\n기   간 : 23일-25일 3일\n회사명 : 고이장례연구소\n회원명 : 한봉재\n관    계 : 자\n연락처 : 010-9990-7287\n고인명 : 김정자 여자 86세(본관/안동)\n상주명 : 한봉재\n연락처 : 010-9990-7287\n종    교 : 불교\n임    종 : 23일 06시 20분\n입    관 : 24일 14시\n발    인 : 25일 08시 30분\n장    지 : 부산영락-부산추모공원(봉안)\n상    품 : 2026 가족장 289\n납    입 : 108,900원\n잔    액 : 2,781,100원\n수금액 : 2,781,100원\n담    당 : 서영우\n연락처 : 010-7799-7720\n특이사항 :'),false); g.deductions.push({id:'x',text:'헌화 1만원 공제'});
     r.push(bandCollect(g), g.f.certAsk, g.f.collect, settleCalc(g).sendWon);
     startCase(goi); g=curCase(); Object.assign(g.f,{product:'2026 가족장 289',paid:'108900',balance:'2781100',collect:'278.11'}); g.dedNet=true; certFromOld(g,'yes'); g.deductions=[{id:'y',text:'헌화 1만원 공제'}]; r.push(bandCollect(g));
     startCase(goi); g=curCase(); Object.assign(g.f,{product:'2026 가족장 289',collect:'289',collectAuto:'289',certAsk:'yes',paid:'8900',certDisc:'10'}); g.deductions=[{id:'b',text:'1.이행완료확인서 108,900원 공제'},{id:'a',text:'헌화 1만원 공제'}]; r.push(bandCollect(g), goiSumVals(g).bal);
     g.deductions=[{id:'a',text:'헌화 1만원 공제'},{id:'d',text:'상복 추가 5만원'}]; g.f.altar='20'; r.push(bandCollect(g), altarNotes(g).collect);
     return r; })(),
   live:(()=>{ const r=[];   // 2026.11.25 금액을 고치면 정산 카톡도 바로: 고이 붙여넣은 잔액 고정 풀기 · 지난 마이너스 금액 따라가기
     startCase(co('고이장례연구소')); const g=curCase(); Object.assign(g.f,{product:'2026 가족장 289',paid:'108900',balance:'2781100',collect:'278.11',certAsk:'yes'}); g.dedNet=true; g.deductions=[{id:'y',text:'헌화 1만원 공제'}];
     r.push(goiNorm(g), g.f.collect, g.f.balance, bandCollect(g)); g.f.certDisc='3'; r.push(bandCollect(g), settleCalc(g).sendWon); g.f.collect='300'; r.push(bandCollect(g));
     startCase(co('디더블유')); const a=curCase(); Object.assign(a.f,{eventNo:'3',place:'창원한마음',depart:'2026-10-12T08:00',collect:'389'}); Object.assign(S(a),{pay:'카드',altarAmt:'30',altarPay:'현금',urnCollect:'120',urnCost:'36',urnPay:'카드'});
     startCase(co('디더블유')); const b=curCase(); Object.assign(b.f,{eventNo:'5',place:'김해복음',depart:'2026-10-14T08:00',collect:'300'}); Object.assign(S(b),{pay:'현금',altarAmt:'24',altarPay:'현금'}); S(b).carry=[{id:'k1',from:a.id,label:caseTag(a),won:settleCalc(a).sendWon}];
     const tail=()=>settleText(b).split('\n').slice(-2).join(' / ');
     r.push(tail()); S(a).urnCollect='100'; r.push(tail()); S(a).pay='현금'; r.push(tail());
     S(a).carry=[{id:'k2',from:b.id,label:'돌기',won:-10000}]; r.push(settleCalc(a).sendWon>0);   // 서로 빼 줘도 계산이 돌지 않음
     return r; })(),
   urnHq:(()=>{ startCase(co('현진시닝')); const h=curCase(), s=S(h);   // 2026.11.25 현진시닝 유골함 본사송금: 카드처럼 우리 몫 실장 줄 · 카톡 유골함 끝 (본사송금)
     Object.assign(h.f,{place:'부산착한 VIP2호',collect:'257.5'}); Object.assign(s,{pay:'현금',altarAmt:'100',altarPay:'현금',urnAsk:'yes',urnCollect:'90',urnCost:'25',urnDisc:'5',urnType:'봉분골드천향',urnPay:'본사송금'}); s.extras=[];
     const t=settleText(h).split('\n'), rs=rcptSums(h);
     const P=parseSettleKakao(settleText(h));
     return [t.find(l=>/^유골함 :/.test(l)), t.find(l=>/: -33만원$/.test(l))||'', settleCalc(h).sendWon, rs.cash, P&&P.s?P.s.urnPay:'', P&&P.s?P.s.urnType:'']; })(),
   hq:(()=>{ const p0=S(c1).pay; S(c1).pay='본사송금'; const t=settleText(c1), r=[settleCalc(c1).sendWon, t.split('\n').find(l=>/^수금 :/.test(l)), rcptSums(c1).cash]; S(c1).pay=p0; return r; })()};   // 2026.11.13 상품 수금 본사송금
})()"""

EXPECT = [
    ('제단공제 20 · 수금 300 현금 → 공제 / 법인카드결제(공제 안 함, 밴드 양식은 「20만원 공제」)', 'altar', [2800000, 3000000, '20만원 법인카드결제', '제단공제 : 20만원 공제']),
    ('고이 공제 · 추가 항목 (5만원공제 · 할인 10만원 · 추가 12만원, 수금 300 현금)', 'goiDed', [2970000, 2970000, '수금액에서 10만원 뺍니다']),
    ('고이 이행완료확인서 (납입 1 + 할인 10 → 1번 「이행완료확인서 11만원 공제」, 할인 없음 → 1만원, 직접 적은 줄이 있으면 두 번 안 뺌)', 'goiCert', ['1.이행완료확인서 11만원 공제\n2.헌화30송이 5만원공제', 2840000, '1.이행완료확인서 1만원 공제', 2940000, 2840000]),
    ('꽃바구니 줄 (헌화 다음, 법카 · 현장결제는 안 더함, 없으면 줄 없음, 카톡 검사 통과) · 입관꽃장식 제공이면 추가 판매 안 물음', 'basket', ['기타추가 : 여상복 1벌 3만원(현금)\n이송 :\n입관꽃장식 : 경북 5만원(월말 법카결제)\n헌화 :\n꽃바구니 : 영호 2만원(월말 법카결제)\n보내는금액 : 277만원', 2770000, 2770000, True, True, True, True]),
    ('고이 상품 「2026 가족장 289」 → 수금액 289 자동 · 이행완료확인서 있음(1+10) → 밴드 납입 11 · 잔액 278 · 수금액 273 / 없음 → 납입 그대로 · 잔액 289 · 수금액 284 · 직접 고친 수금액은 그대로', 'goiBand', ['289', '11만원', '278만원', '273만원', '1.이행완료확인서 11만원 공제\n2.헌화30송이 5만원공제', 2730000, '', '289만원', '284만원', 2890000, 0, 2700000, False, '300']),
    ('화장장 이름 (회사 보고 = 정식 이름 · 밴드 · 배차 = 짧은 이름)', 'crem', [
        '화장 : 11월 25일 09시 (부산영락공원 03회차)\n장법 : 화장(부산영락공원)\n장지 : 창원상복공원-부산추모', '화장 : 11월 25일 09시 (부산영락 03회차)', '화장 : 부산영락 (03회차)',
        '화장 : 11월 25일 09시 (김해추모의공원 03회차)\n장법 : 화장(김해추모의공원)\n장지 : 창원상복공원-부산추모', '화장 : 11월 25일 09시 (김해추모 03회차)', '화장 : 김해추모 (03회차)',
        '화장 : 11월 25일 09시 (창원상복공원 03회차)\n장법 : 화장(창원상복공원)\n장지 : 창원상복공원-부산추모', '화장 : 11월 25일 09시 (창원상복 03회차)', '화장 : 창원상복 (03회차)',
        '화장 : 11월 25일 09시 (마산화장장 03회차)\n장법 : 화장(마산화장장)\n장지 : 창원상복공원-부산추모', '화장 : 11월 25일 09시 (마산화장 03회차)', '화장 : 마산화장 (03회차)']),
    ('밴드 장법 괄호 (밴드만 · 회사 보고 · 정산 카톡에는 없음)', 'bmark', ['부산영락-부산추모(봉안)', '장지 : 부산영락공원-부산추모\n2차 : 부산추모', '장    지 : 부산영락-부산추모(봉안)', '창원상복-부산추모(벽식,자차)', '장지 : 창원상복공원-부산추모', '안동선영(산골,자차)', '장지 : 안동선영', '장지 : 안동선영']),
    ('기타 업체 = 회사 보고 양식 없음 (고이 양식만 빠지고 직접 만든 양식은 남음, 고이는 그대로)', 'etc', [0, True, '내 양식', False]),
    ('고이 수금액 = 잔액 − 공제 + 추가 (이행완료확인서 한 번만: 붙여넣기 · 붙여넣은 뒤 있음 · 직접 적은 줄)', 'goiBal', ['2,771,100원', None, '2781100', 2771100, '2,771,100원', '2,771,100원', '2,781,100원', '2,621,100원', '잔액 2,781,100원에서 제단공제 20만원 빼고 · 공제 · 추가 +4만원 → 2,621,100원']),
    ('금액 고치면 바로 (고이 붙여넣은 잔액 → 상품금액 기준, 할인 · 상품금액 고치면 수금액 · 지난 마이너스 따라감)', 'live', [True, '289', '', '2,771,100원', '2,741,100원', 2741100, '2,851,100원', '10월3번행사 -18만원 / 보내는금액 : 306만원', '10월3번행사 -8만원 / 보내는금액 : 316만원', '헌화 : / 보내는금액 : 324만원', True]),
    ('현진시닝 유골함 본사송금 (카드처럼 실장 몫 줄 · 카톡 끝 (본사송금) · 현금영수증에 안 넣음 · 받은 카톡에서 읽음)', 'urnHq', ['유골함 : 32만원(65만원)수금(90만원)할인(5만원)봉분골드천향(본사송금)', '이승구실장 : -33만원', 2485000, 2575000, '본사송금', '봉분골드천향']),
    ('예시1 보내는금액', 'ex1', 3955000),
    ('예시1 상품 수금 본사송금 → 보내는금액 · 현금영수증에서 빠짐', 'hq', [1380000, '수금 : 2,575,000원(본사송금)', 1620000]),
    ('예시2 보내는금액', 'ex2', -180000),
    ('예시2 마이너스 이름', 'tag2', '10월3번행사'),
    ('예시3 빼기 전', 'ex3before', 3240000),
    ('예시3 빼고 난 뒤', 'ex3', 3060000),
    ('예시4 본부장 봉투', 'part', 1660000),
    ('예시4 실장 봉투', 'mgr', 2820000),
    ('해양장 장지 (본부장 · 실장)', 'seaBur', [1500000, 1500000]),
    ('수당 총계 (수목장 실장 몫 포함, 2026.11.09)', 'comm', '총계 : 282만원'),
    ('장지 종류 → 수당 줄 (수목장 · 해양장=바다장 · 납골당=납골 · 예전 일반 · 예전 해양장)', 'bt', {'tree': ['수목장 : 148만원(300)', '총계 : 282만원'], 'sea': ['바다장 : 150만원(300)', '총계 : 284만원'], 'oss': ['납골 : 148만원(300)', '총계 : 282만원'], 'oldNo': ['수목장 :', '바다장 :', '납골 :', '총계 : 134만원'], 'oldYes': ['바다장 : 150만원(300)', '총계 : 284만원']}),
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
