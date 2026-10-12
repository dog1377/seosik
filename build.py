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
<meta name="apple-mobile-web-app-title" content="서식함">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" type="image/png" sizes="32x32" href="icons/favicon-32.png">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<script>window.__PWA__ = true; window.__APP_VERSION__ = "{version}";</script>
<style>:root{{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}body{{margin:0}}img{{max-width:100%}}[hidden]{{display:none!important}}</style>
{head_part}
</head>
<body>
{body_part}
</body>
</html>
"""

(ROOT / 'index.html').write_text(html, encoding='utf-8')
sw = (ROOT / 'sw.template.js').read_text(encoding='utf-8').replace('__VERSION__', version)
(ROOT / 'sw.js').write_text(sw, encoding='utf-8')
(ROOT / 'version.json').write_text(json.dumps({'version': version}) + '\n', encoding='utf-8')
print('built version', version)
