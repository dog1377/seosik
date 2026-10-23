"""Build the installable app from src/app.html.

Usage:  python3 build.py            (version = current date-time)
        python3 build.py 2026.10.13-1

Writes index.html, sw.js and version.json next to this file.
Edit only src/app.html (and sw.template.js); never edit the generated files.
"""
import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
CDN_JSPDF = '<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>'
LOCAL_JSPDF = '<script src="vendor/jspdf.umd.min.js"></script>'

version = sys.argv[1] if len(sys.argv) > 1 else datetime.datetime.now().strftime('%Y.%m.%d-%H%M')

# 앱 잠금: locks.json 에 비밀번호 해시(코드)만 들어 있음. 비어 있으면 잠그지 않음
LOCKS = json.loads((ROOT / 'locks.json').read_text(encoding='utf-8'))
LOCK_SNIPPET = (ROOT / 'src' / 'lock.html').read_text(encoding='utf-8')
# 관리자 서식은 파트장 계정만 (수파베이스 로그인 · app_metadata.dw_role='leader')
GATE_HEAD = (ROOT / 'src' / 'leader-gate-head.html').read_text(encoding='utf-8')
GATE_BODY = (ROOT / 'src' / 'leader-gate.html').read_text(encoding='utf-8')


def lock_html(cfg):
    return LOCK_SNIPPET.replace('__LOCK_CFG__', json.dumps(cfg, ensure_ascii=False))
src = (ROOT / 'src' / 'app.html').read_text(encoding='utf-8')

split = src.index('<header class="appbar">')
head_part, body_part = src[:split].strip(), src[split:].strip()
if CDN_JSPDF not in body_part:
    raise SystemExit('jsPDF script tag not found in src/app.html')
body_part = body_part.replace(CDN_JSPDF, LOCAL_JSPDF)

html = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="description" content="파트장용 주간보고·탁송 보고서 앱. 기록은 각자 휴대폰에만 저장됩니다.">
<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#121314" media="(prefers-color-scheme: dark)">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="관리자 서식">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="manifest" href="../manifest.webmanifest">
<link rel="icon" type="image/png" sizes="32x32" href="icons/gukhwa-32.png">
<link rel="apple-touch-icon" href="icons/gukhwa-apple-180.png">
<script>window.__PWA__ = true; window.__APP_VERSION__ = "{version}";
try {{ if (!location.hash && localStorage.getItem('mf.lastApp') === 'funeral') location.replace('funeral.html'); }} catch (e) {{}}</script>
<style>:root{{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}body{{margin:0}}img{{max-width:100%}}[hidden]{{display:none!important}}</style>
{head_part}
{lock_html({'hash': LOCKS.get('forms', ''), 'key': 'mf', 'title': '관리자 서식', 'who': '파트장', 'remember': True, 'relockMin': 0, 'alt': '장례일정만 쓰실 분은 <a href="../jangrye/">장례일정 열기</a>'})}
{GATE_HEAD}
</head>
<body>
{body_part}
{GATE_BODY}
</body>
</html>
"""

# 관리자 서식은 forms/ 폴더에 둔다. 맨 앞 주소(/)에 있으면 안드로이드 크롬이 그 아래 장례일정(/jangrye/) · DW관리(/admin/)까지
# 관리자 서식 앱 안으로 봐서 "이미 설치됨"이 뜬다. 앱 신분증(manifest id "/")과 manifest 주소(/manifest.webmanifest)는 그대로라
# 이미 깔린 관리자 서식은 같은 앱으로 이어서 업데이트된다. 맨 앞 주소(/, /funeral.html)는 forms/ 로 넘겨 주는 안내 페이지.
import shutil
FM = ROOT / 'forms'
(FM / 'vendor').mkdir(parents=True, exist_ok=True)
(FM / 'icons').mkdir(parents=True, exist_ok=True)
shutil.copyfile(ROOT / 'vendor' / 'jspdf.umd.min.js', FM / 'vendor' / 'jspdf.umd.min.js')
shutil.copyfile(ROOT / 'vendor' / 'supabase.js', FM / 'vendor' / 'supabase.js')   # 실시간 저장 (장례업무)
for ic in (ROOT / 'icons').glob('*.png'):
    shutil.copyfile(ic, FM / 'icons' / ic.name)
(FM / 'index.html').write_text(html, encoding='utf-8')


def redirect_page(target, title):
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{title}</title>
<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#121314" media="(prefers-color-scheme: dark)">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="관리자 서식">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" type="image/png" sizes="32x32" href="icons/gukhwa-32.png">
<link rel="apple-touch-icon" href="icons/gukhwa-apple-180.png">
<script>location.replace('{target}' + location.search + location.hash);</script>
<noscript><meta http-equiv="refresh" content="0;url={target}"></noscript>
<style>body{{margin:0;padding:32px 20px;font:16px/1.6 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;color:#1c1d1f;background:#fff}}a{{color:inherit}}@media (prefers-color-scheme:dark){{body{{color:#ecebe8;background:#121314}}}}</style>
</head>
<body><p>관리자 서식으로 이동합니다. 넘어가지 않으면 <a href="{target}">여기를 누르세요</a>.</p>
<script>if ('serviceWorker' in navigator) navigator.serviceWorker.register('./sw.js').catch(function () {{}});</script>
</body>
</html>
"""


(ROOT / 'index.html').write_text(redirect_page('forms/', '관리자 서식'), encoding='utf-8')
(ROOT / 'funeral.html').write_text(redirect_page('forms/funeral.html', '장례업무 · 관리자 서식'), encoding='utf-8')

# ---------- 장례 일정 작성기: 서식함 안의 장례업무(funeral.html)와 따로 쓰는 장례일정 앱(jangrye/) ----------
import re
FUNERAL_SRC = (ROOT / 'src' / 'funeral.html').read_text(encoding='utf-8')
THEME = (ROOT / 'src' / 'funeral-theme.html').read_text(encoding='utf-8')


def make_funeral(title, extras, share_title=None, page_title=None, manifest_href='manifest.webmanifest', head_extra=''):
    fsrc = FUNERAL_SRC
    if page_title:
        fsrc = fsrc.replace('<title>장례 일정 작성기</title>', '<title>' + page_title + '</title>', 1)
    head = (
        '<link rel="manifest" href="' + manifest_href + '">\n'
        '<link rel="icon" type="image/png" sizes="32x32" href="icons/gukhwa-32.png">\n'
        '<link rel="apple-touch-icon" href="icons/gukhwa-apple-180.png">\n'
        '<meta name="mobile-web-app-capable" content="yes">\n'
        '<meta name="apple-mobile-web-app-capable" content="yes">\n'
        '<meta name="app-version" content="' + version + '">\n'
    ) + head_extra
    fsrc = re.sub(r'<link rel="(?:icon|apple-touch-icon)"[^>]*>\s*', '', fsrc)
    fsrc = re.sub(r'<meta name="apple-mobile-web-app-title"[^>]*>', '<meta name="apple-mobile-web-app-title" content="' + title + '">', fsrc)
    fsrc = re.sub(r'(<meta name="viewport"[^>]*>\s*)', lambda m: m.group(1) + head, fsrc, count=1)
    # share the app's own main address rather than this page's file name
    fsrc = fsrc.replace("location.pathname.replace(/index\\.html$/,'')", "location.pathname.replace(/(index|funeral)\\.html$/,'')")
    if share_title:
        fsrc = fsrc.replace("navigator.share({title:'장례 일정 작성기',url})", "navigator.share({title:'" + share_title + "',url})")
    cut = fsrc.rfind('</body>')
    if cut < 0:
        raise SystemExit('</body> not found in src/funeral.html')
    return fsrc[:cut] + THEME + ''.join(extras) + '\n' + fsrc[cut:]


def make_sw(prefix, core):
    tpl = (ROOT / 'sw.template.js').read_text(encoding='utf-8')
    return (tpl.replace('__VERSION__', version)
               .replace("'seosik-app-'", "'" + prefix + "'")
               .replace('__CORE__', json.dumps(core, ensure_ascii=False, indent=2)))


# 서식함 안의 장례업무
(FM / 'funeral.html').write_text(
    make_funeral('관리자 서식', [(ROOT / 'src' / 'funeral-bridge.html').read_text(encoding='utf-8'), GATE_BODY], share_title='관리자 서식', page_title='장례업무 · 관리자 서식', manifest_href='../manifest.webmanifest', head_extra=GATE_HEAD),
    encoding='utf-8')
(FM / 'sw.js').write_text(make_sw('forms-app-', [
    './', './index.html', './funeral.html', './vendor/jspdf.umd.min.js',
    './icons/gukhwa-192.png', './icons/gukhwa-512.png', './icons/gukhwa-apple-180.png',
]), encoding='utf-8')
(FM / 'version.json').write_text(json.dumps({'version': version}) + '\n', encoding='utf-8')
# 맨 앞 주소(/)의 서비스워커: 안내 페이지 두 개와 manifest만 맡고, 나머지(forms · jangrye · admin)는 손대지 않음
ROOT_ONLY = ['/', '/index.html', '/funeral.html', '/manifest.webmanifest']
root_sw = make_sw('seosik-app-', ['./', './index.html', './funeral.html', './manifest.webmanifest',
                                  './icons/gukhwa-192.png', './icons/gukhwa-512.png', './icons/gukhwa-apple-180.png'])
scope_line = "if (!url.pathname.startsWith(new URL(self.registration.scope).pathname)) return;"
if scope_line not in root_sw:
    raise SystemExit('scope check line not found in sw.template.js')
root_sw = root_sw.replace(scope_line, 'if (!' + json.dumps(ROOT_ONLY) + '.includes(url.pathname)) return;')
(ROOT / 'sw.js').write_text(root_sw, encoding='utf-8')
(ROOT / 'version.json').write_text(json.dumps({'version': version}) + '\n', encoding='utf-8')

# 따로 쓰는 장례일정 앱 (서식 없음)
JR = ROOT / 'jangrye'
JR.mkdir(exist_ok=True)
(JR / 'vendor').mkdir(exist_ok=True)
shutil.copyfile(ROOT / 'vendor' / 'supabase.js', JR / 'vendor' / 'supabase.js')   # 실시간 저장 (수파베이스 연결 도구, 로그인할 때만 불러옴)
(JR / 'index.html').write_text(
    make_funeral('장례일정', [(ROOT / 'src' / 'jangrye-bridge.html').read_text(encoding='utf-8')], page_title='장례일정'),
    encoding='utf-8')
(JR / 'sw.js').write_text(make_sw('jangrye-app-', [
    './', './index.html', './manifest.webmanifest',
    './icons/gukhwa-192.png', './icons/gukhwa-512.png', './icons/gukhwa-apple-180.png',
]), encoding='utf-8')

# 회사 관리 앱 (admin/): 공지사항·인사발령·재직증명서·시말서·사직서·인사기록카드
import shutil
AD = ROOT / 'admin'
(AD / 'vendor').mkdir(parents=True, exist_ok=True)
shutil.copyfile(ROOT / 'vendor' / 'jspdf.umd.min.js', AD / 'vendor' / 'jspdf.umd.min.js')
asrc = (ROOT / 'src' / 'admin.html').read_text(encoding='utf-8')
asplit = asrc.index('<header class="appbar">')
ahead, abody = asrc[:asplit].strip(), asrc[asplit:].strip()
if CDN_JSPDF not in abody:
    raise SystemExit('jsPDF script tag not found in src/admin.html')
abody = abody.replace(CDN_JSPDF, LOCAL_JSPDF)
admin_html = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="description" content="DW관리 · 회사 관리자용 공지사항·인사발령·재직증명서·시말서·사직서·인사기록카드. 기록은 이 휴대폰에만 저장됩니다.">
<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#121314" media="(prefers-color-scheme: dark)">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="DW관리">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="robots" content="noindex">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" type="image/png" sizes="32x32" href="icons/gukhwa-32.png">
<link rel="apple-touch-icon" href="icons/gukhwa-apple-180.png">
<script>window.__PWA__ = true; window.__APP_VERSION__ = "{version}";</script>
<style>:root{{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}body{{margin:0}}img{{max-width:100%}}[hidden]{{display:none!important}}</style>
<script>window.__LOCK_STATE__ = {json.dumps({k: bool(v) for k, v in LOCKS.items()})};</script>
{ahead}
{lock_html({'hash': LOCKS.get('admin', ''), 'key': 'ca', 'title': 'DW관리', 'who': '관리자', 'remember': False, 'relockMin': 10, 'alt': ''})}
</head>
<body>
{abody}
</body>
</html>
"""
(AD / 'index.html').write_text(admin_html, encoding='utf-8')
(AD / 'sw.js').write_text(make_sw('admin-app-', [
    './', './index.html', './manifest.webmanifest', './vendor/jspdf.umd.min.js',
    './icons/gukhwa-192.png', './icons/gukhwa-512.png', './icons/gukhwa-apple-180.png',
]), encoding='utf-8')
(AD / 'version.json').write_text(json.dumps({'version': version}) + '\n', encoding='utf-8')
print('built version', version)
