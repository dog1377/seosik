"""빌드된 화면 파일 안의 자바스크립트 문법 검사 (node --check).

    python3 tools/test/syntax.py

<script> 안 코드(바깥 파일을 부르는 것 · JSON 제외)를 하나씩 꺼내 node 로 검사. 하나라도 틀리면 종료 코드 1.
"""
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAGES = ['forms/index.html', 'forms/funeral.html', 'forms/admin.html', 'jangrye/index.html', 'admin/index.html', 'index.html',
         'forms/sw.js', 'sw.js', 'jangrye/sw.js', 'admin/sw.js']
TAG = re.compile(r'<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>', re.S | re.I)


def main():
    bad = 0
    with tempfile.TemporaryDirectory() as td:
        for rel in PAGES:
            f = ROOT / rel
            if not f.exists():
                continue
            text = f.read_text(encoding='utf-8')
            chunks = [text] if rel.endswith('.js') else [
                m.group('body') for m in TAG.finditer(text)
                if 'src=' not in m.group('attrs') and not re.search(r'type=["\'](application/(ld\+)?json|module|text/template)', m.group('attrs'))]
            for i, code in enumerate(chunks):
                if not code.strip():
                    continue
                tmp = pathlib.Path(td) / f'c{i}.js'
                tmp.write_text(code, encoding='utf-8')
                r = subprocess.run(['node', '--check', str(tmp)], capture_output=True, text=True)
                if r.returncode:
                    bad += 1
                    print(f'문법 오류: {rel} (스크립트 {i + 1}번째)\n{r.stderr.strip()[:800]}')
    if bad:
        sys.exit(1)
    print('자바스크립트 문법 검사 통과')


if __name__ == '__main__':
    main()
