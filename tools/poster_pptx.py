"""주요 장례일정(빈소 게시용) PPT 양식 → assets/poster.pptx (2026.10.28)

    python3 tools/poster_pptx.py 사용자가_보낸_양식.pptx

- 사용자가 보낸 PPT(세로 4:3)에서 이름 · 일정 · 아래 문구를 빈 자리({{NAME}} {{BODY}} {{FOOT}})로 바꾸고,
  개인 정보가 남지 않게 미리보기 그림(docProps/thumbnail) · 그림 파일 경로(descr) · 작성자 정보를 지운다.
- 배경 그림은 줄여서(가로 1100px) 다시 저장 → 앱이 받는 파일이 작아짐.
- 압축 없이(ZIP_STORED) 묶는다 → 앱이 라이브러리 없이 바로 읽고(zipRead) 다시 묶을 수 있음(zipStore).
- 앱(src/funeral.html posterAssets)은 이 파일 하나로 미리보기 그림과 PPT 저장을 같이 한다. build.py 가 forms/assets/ 로 복사.
"""
import io
import re
import sys
import zipfile
import pathlib

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'assets' / 'poster.pptx'


def main(src):
    zin = zipfile.ZipFile(src)
    files = {n: zin.read(n) for n in zin.namelist()}
    # 1. 미리보기 그림(이름 · 전화번호가 그대로 찍혀 있음) 지우기
    files.pop('docProps/thumbnail.jpeg', None)
    rels = files['_rels/.rels'].decode('utf-8')
    rels = re.sub(r'<Relationship [^>]*Target="docProps/thumbnail\.jpeg"/>', '', rels)
    files['_rels/.rels'] = rels.encode('utf-8')
    ct = files['[Content_Types].xml'].decode('utf-8')
    files['[Content_Types].xml'] = ct.encode('utf-8')
    # 2. 작성자 정보 비우기
    core = files['docProps/core.xml'].decode('utf-8')
    core = re.sub(r'<dc:creator>.*?</dc:creator>', '<dc:creator></dc:creator>', core)
    core = re.sub(r'<cp:lastModifiedBy>.*?</cp:lastModifiedBy>', '<cp:lastModifiedBy></cp:lastModifiedBy>', core)
    core = re.sub(r'<cp:lastPrinted>.*?</cp:lastPrinted>', '', core)
    core = core.replace('<dc:title>PowerPoint 프레젠테이션</dc:title>', '<dc:title>주요 장례일정</dc:title>')
    files['docProps/core.xml'] = core.encode('utf-8')
    # 3. 슬라이드: 그림 경로 지우고, 이름 · 일정 · 아래 문구를 빈 자리로
    x = files['ppt/slides/slide1.xml'].decode('utf-8')
    x = re.sub(r' descr="[^"]*"', '', x)

    def body_of(name):
        i = x.index(f'name="{name}"')
        a = x.index('<p:txBody>', i)
        b = x.index('</p:txBody>', a)
        return a, b

    def set_paras(name, inner):
        nonlocal x
        a, b = body_of(name)
        tb = x[a:b]
        head = tb[:tb.index('<a:p>')]
        x = x[:a] + head + inner + x[b:]

    set_paras('TextBox 2', '<a:p><a:pPr lvl="0" algn="ctr"/><a:r><a:rPr lang="ko-KR" altLang="en-US" sz="3200" b="1" dirty="0"><a:latin typeface="HY견명조"/><a:ea typeface="HY견명조"/></a:rPr><a:t>{{NAME}}</a:t></a:r></a:p>')
    set_paras('직사각형 8', '{{BODY}}')
    set_paras('직사각형 16', '{{FOOT}}')
    assert '장영조' not in x and '서영우' not in x and '7799' not in x and '매일유업' not in x
    files['ppt/slides/slide1.xml'] = x.encode('utf-8')
    # 4. 배경 그림 줄이기 (가로 1100px, 자르는 비율은 PPT 쪽 srcRect 그대로라 비율만 같으면 됨)
    im = Image.open(io.BytesIO(files['ppt/media/image1.jpeg'])).convert('RGB')
    w = 1100
    im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=80, optimize=True, progressive=False)
    files['ppt/media/image1.jpeg'] = buf.getvalue()
    for n, v in files.items():
        if n.endswith('.xml') or n.endswith('.rels'):
            t = v.decode('utf-8')
            for bad in ('장영조', '서영우', '7799', '이광수'):
                assert bad not in t, (n, bad)
    # 5. 압축 없이 묶기 ([Content_Types].xml 이 맨 앞)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    order = ['[Content_Types].xml'] + [n for n in files if n != '[Content_Types].xml']
    with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_STORED) as z:
        for n in order:
            z.writestr(zipfile.ZipInfo(n, date_time=(2026, 10, 28, 0, 0, 0)), files[n])
    print(OUT, OUT.stat().st_size, 'bytes')


if __name__ == '__main__':
    main(sys.argv[1])
