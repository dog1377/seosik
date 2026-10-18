/**
 * DW 클라우드 자동 저장 — 구글 앱스 스크립트 (2026.10.18)
 *
 * 쓰는 법: script.google.com → 새 프로젝트 → 이 코드를 전부 붙여 넣기 → 저장
 *        → 배포 → 새 배포 → 유형: 웹 앱 → 실행: 나 / 액세스 권한: 모든 사용자 → 배포 → 권한 허용
 *        → 나오는 「웹 앱 URL」(https://script.google.com/macros/s/…/exec)을 앱 설정 「클라우드 자동 저장」에 붙여 넣기
 *
 * 기록은 내 구글 드라이브 「DW 자동저장」 폴더에 저장됩니다.
 *  - <코드>_funeral.json : 장례업무(행사 · 정산 · 봉투) · 휴무
 *  - <코드>_forms.json   : 관리자 서식(주간보고 · 회의록 · 후기 · 탁송 · 설정)
 *  - 날짜별 사본(<코드>_funeral_20261018.json 등)은 최근 30일치만 남깁니다.
 * 기기마다 앱이 만든 긴 「클라우드 코드」가 있어야만 읽고 쓸 수 있습니다.
 */
var FOLDER = 'DW 자동저장';
var KEEP_DAYS = 30;

function folder_() {
  var it = DriveApp.getFoldersByName(FOLDER);
  return it.hasNext() ? it.next() : DriveApp.createFolder(FOLDER);
}

function out_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}

function valid_(key, slot) {
  return /^[A-Za-z0-9]{24,64}$/.test(String(key || '')) && /^[a-z]{3,16}$/.test(String(slot || ''));
}

// 같은 이름 파일이 있으면 내용만 바꾸고, 없으면 새로 만듦. 새로 만들었으면 true
function put_(dir, name, text) {
  var it = dir.getFilesByName(name);
  if (it.hasNext()) { it.next().setContent(text); return false; }
  dir.createFile(name, text, 'application/json');
  return true;
}

function doGet(e) {
  var p = (e && e.parameter) || {};
  if (p.ping) return out_({ ok: true, app: 'dw-cloud' });
  if (!valid_(p.key, p.slot)) return out_({ ok: false, err: 'key' });
  var it = folder_().getFilesByName(p.key + '_' + p.slot + '.json');
  if (!it.hasNext()) return out_({ ok: true, data: null });
  var f = it.next();
  return out_({ ok: true, data: f.getBlob().getDataAsString('UTF-8'), at: f.getLastUpdated().toISOString() });
}

function doPost(e) {
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(25000)) return out_({ ok: false, err: 'busy' });
  try {
    var b = JSON.parse(e.postData.contents);
    if (!valid_(b.key, b.slot) || typeof b.data !== 'string') return out_({ ok: false, err: 'key' });
    if (b.data.length > 9 * 1024 * 1024) return out_({ ok: false, err: 'big' });
    var dir = folder_();
    var base = b.key + '_' + b.slot;
    put_(dir, base + '.json', b.data);
    var day = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyyMMdd');
    if (put_(dir, base + '_' + day + '.json', b.data)) {
      // 새 날짜 사본을 만든 날에만 오래된 사본 정리 (최근 KEEP_DAYS개만)
      var olds = [], it = dir.searchFiles("title contains '" + base + "_'");
      while (it.hasNext()) { var f = it.next(); if (/_\d{8}\.json$/.test(f.getName())) olds.push(f); }
      olds.sort(function (x, y) { return x.getName() < y.getName() ? 1 : -1; });
      for (var i = KEEP_DAYS; i < olds.length; i++) olds[i].setTrashed(true);
    }
    return out_({ ok: true, at: new Date().toISOString() });
  } catch (err) {
    return out_({ ok: false, err: String(err) });
  } finally {
    lock.releaseLock();
  }
}
