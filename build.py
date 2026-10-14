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
<meta name="theme-color" content="#f1f2ef" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#111518" media="(prefers-color-scheme: dark)">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="관리자 서식">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" type="image/png" sizes="32x32" href="icons/gukhwa-32.png">
<link rel="apple-touch-icon" href="icons/gukhwa-apple-180.png">
<script>window.__PWA__ = true; window.__APP_VERSION__ = "{version}";
try {{ if (!location.hash && localStorage.getItem('mf.lastApp') === 'funeral') location.replace('funeral.html'); }} catch (e) {{}}</script>
<style>:root{{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}body{{margin:0}}img{{max-width:100%}}[hidden]{{display:none!important}}</style>
{head_part}
{lock_html({'hash': LOCKS.get('forms', ''), 'key': 'mf', 'title': '관리자 서식', 'who': '파트장', 'remember': True, 'relockMin': 0, 'alt': '장례일정만 쓰실 분은 <a href="jangrye/">장례일정 열기</a>'})}
</head>
<body>
{body_part}
</body>
</html>
"""

(ROOT / 'index.html').write_text(html, encoding='utf-8')

# ---------- 장례 일정 작성기: 서식함 안의 장례업무(funeral.html)와 따로 쓰는 장례일정 앱(jangrye/) ----------
import re
FUNERAL_SRC = (ROOT / 'src' / 'funeral.html').read_text(encoding='utf-8')
THEME = (ROOT / 'src' / 'funeral-theme.html').read_text(encoding='utf-8')


def make_funeral(title, extras, share_title=None, page_title=None):
    fsrc = FUNERAL_SRC
    if page_title:
        fsrc = fsrc.replace('<title>장례 일정 작성기</title>', '<title>' + page_title + '</title>', 1)
    head = (
        '<link rel="manifest" href="manifest.webmanifest">\n'
        '<link rel="icon" type="image/png" sizes="32x32" href="icons/gukhwa-32.png">\n'
        '<link rel="apple-touch-icon" href="icons/gukhwa-apple-180.png">\n'
        '<meta name="mobile-web-app-capable" content="yes">\n'
        '<meta name="apple-mobile-web-app-capable" content="yes">\n'
        '<meta name="app-version" content="' + version + '">\n'
    )
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
(ROOT / 'funeral.html').write_text(
    make_funeral('관리자 서식', [(ROOT / 'src' / 'funeral-bridge.html').read_text(encoding='utf-8')], share_title='관리자 서식', page_title='장례업무 · 관리자 서식'),
    encoding='utf-8')
(ROOT / 'sw.js').write_text(make_sw('seosik-app-', [
    './', './index.html', './funeral.html', './manifest.webmanifest', './vendor/jspdf.umd.min.js',
    './icons/gukhwa-192.png', './icons/gukhwa-512.png', './icons/gukhwa-apple-180.png',
]), encoding='utf-8')
(ROOT / 'version.json').write_text(json.dumps({'version': version}) + '\n', encoding='utf-8')

# 따로 쓰는 장례일정 앱 (서식 없음)
JR = ROOT / 'jangrye'
JR.mkdir(exist_ok=True)
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
<meta name="theme-color" content="#f1f2ef" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#111518" media="(prefers-color-scheme: dark)">
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
