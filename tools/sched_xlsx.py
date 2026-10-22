"""장례행사 일정표 엑셀 양식 → src/funeral.html 안의 SCHED_XLSX 로 넣기.

빈 양식(tools/sched-template.xlsx, 견본 값은 지운 것)의 각 파일을 글자 그대로 넣는다.
앱은 이 글자에서 칸 값만 바꿔 압축 없이(zip store) 묶어 .xlsx 로 내보낸다.

  python3 tools/sched_xlsx.py          # 양식을 바꾼 뒤 다시 넣기
"""
import json, re, zipfile, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
TPL = ROOT / 'tools' / 'sched-template.xlsx'
SRC = ROOT / 'src' / 'funeral.html'

parts = {}
with zipfile.ZipFile(TPL) as z:
    for n in z.namelist():
        t = z.read(n).decode('utf-8')
        if n == 'xl/worksheets/sheet1.xml':
            t = re.sub(r'(<c r="[A-Z]+\d+"(?: s="\d+")?) t="n"></c>', r'\1/>', t)   # 빈 칸 줄이기
        if n == 'docProps/core.xml':
            t = re.sub(r'<dc:creator[^>]*>.*?</dc:creator>', '<dc:creator xmlns:dc="http://purl.org/dc/elements/1.1/">디더블유 장례의전</dc:creator>', t)
            t = re.sub(r'<cp:lastModifiedBy>.*?</cp:lastModifiedBy>|<cp:lastPrinted>.*?</cp:lastPrinted>', '', t)
        parts[n] = t
data = json.dumps(parts, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
tag = '<script id="schedXlsxData">/* 장례행사 일정표 엑셀 양식 (tools/sched_xlsx.py 로 만듦 · 직접 고치지 말 것) */const SCHED_XLSX=' + data + ';</script>'
h = SRC.read_text(encoding='utf-8')
if 'id="schedXlsxData"' in h:
    h = re.sub(r'<script id="schedXlsxData">.*?</script>', lambda m: tag, h, count=1, flags=re.S)
else:
    cut = h.rfind('</body>')
    h = h[:cut] + tag + '\n' + h[cut:]
SRC.write_text(h, encoding='utf-8')
print('SCHED_XLSX', len(data), 'bytes,', len(parts), 'files')
