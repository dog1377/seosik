"""휴무 · 당직 앱(src/funeral.html 안 base64) 꺼내기 / 다시 넣기.

  python3 tools/duty_edit.py out duty.html   # 꺼내서 duty.html 로 저장
  python3 tools/duty_edit.py in  duty.html   # 고친 duty.html 을 다시 넣기
"""
import base64, re, sys

SRC = 'src/funeral.html'
PAT = re.compile(r"(const DUTY_B64=/\*DUTY_START\*/')([^']*)('/\*DUTY_END\*/;)")

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ('out', 'in'):
        print(__doc__); sys.exit(1)
    mode, path = sys.argv[1], sys.argv[2]
    s = open(SRC, encoding='utf-8').read()
    m = PAT.search(s)
    assert m and len(PAT.findall(s)) == 1, 'DUTY_B64 줄을 찾지 못했습니다'
    if mode == 'out':
        open(path, 'w', encoding='utf-8').write(base64.b64decode(m.group(2)).decode('utf-8'))
        print('꺼냄 →', path)
    else:
        b = base64.b64encode(open(path, encoding='utf-8').read().encode('utf-8')).decode('ascii')
        s = s[:m.start(2)] + b + s[m.end(2):]
        open(SRC, 'w', encoding='utf-8').write(s)
        print('넣음 ←', path, f'({len(b)}자)')

if __name__ == '__main__':
    main()
