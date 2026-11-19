#!/usr/bin/env python3
"""Sex lokatsiyasi: qisqa Google Maps havolasini (maps.app.goo.gl/...) qabul qiladi.
Avval install-smena-gps.py o'rnatilgan bo'lishi kerak.
Ishlatish:  python3 install-smena-link.py /opt/gilam-crm /opt/fayz-crm"""
import os, shutil, sys

MARK = '# smena-link-v1'


def rep(s, old, new, n=1):
    c = s.count(old)
    if c != n:
        raise SystemExit('XATO: kutilgan joy topilmadi (%d marta): %r' % (c, old[:70]))
    return s.replace(old, new)


FUNC = r'''# smena-link-v1: Google Maps havolasidan koordinata olish (faqat rahbar)
def _resolve_loc(h, u):
    import re, urllib.request, urllib.parse
    q = urllib.parse.parse_qs(u.query).get('u', [''])[0].strip()
    ok_host = lambda x: x in ('maps.app.goo.gl', 'goo.gl', 'g.co', 'maps.google.com', 'google.com', 'www.google.com') or x.endswith('.google.com')
    try:
        pu = urllib.parse.urlparse(q)
        if pu.scheme not in ('http', 'https') or not ok_host(pu.hostname or ''):
            return h.send(200, {'ok': False})
        req = urllib.request.Request(q, headers={'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36'})
        with urllib.request.urlopen(req, timeout=10) as r:
            fin = r.geturl()
            body = r.read(400000).decode('utf-8', 'ignore')
    except Exception:
        return h.send(200, {'ok': False})
    for txt in (urllib.parse.unquote(fin), body):
        for rx in (r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', r'@(-?\d+\.\d+),(-?\d+\.\d+)', r'[?&](?:q|ll|center|query)=(-?\d+\.\d+)[,%2C]+(-?\d+\.\d+)'):
            m = re.search(rx, txt)
            if m:
                return h.send(200, {'ok': True, 'lat': float(m.group(1)), 'lng': float(m.group(2))})
    return h.send(200, {'ok': False})


'''

ROUTE = '''            if u.path == '/api/resolveloc':
                with LOCK:
                    _me, _s = self.auth()
                if not _me or (_s or {}).get('role') != 'admin':
                    return self.send(403, {'error': "Ruxsat yo'q."})
                return _resolve_loc(self, u)
            with LOCK:
                if u.path == '/api/app/loc':'''

OLD_JS = "else if(a==='slset'){const c=coordOf($('#sl-v').value),r=+$('#sl-r').value;if(!c||!(r>=3)){"
NEW_JS = ("else if(a==='slset'){const v=$('#sl-v').value.trim(),r=+$('#sl-r').value;let c=coordOf(v);\n"
          "    if(!c&&/^https?:\\/\\//i.test(v)){b.disabled=true;b.textContent='Havola tekshirilmoqda…';try{const j=await(await fetch('/api/resolveloc?u='+encodeURIComponent(v),{credentials:'same-origin'})).json();if(j.ok)c=[j.lat,j.lng]}catch(e){}b.disabled=false;b.textContent='Saqlash'}\n"
          "    if(!c||!(r>=3)){")


def main(dirs):
    for d in dirs:
        hp, sp = os.path.join(d, 'index.html'), os.path.join(d, 'server.py')
        h, sv = open(hp, encoding='utf-8').read(), open(sp, encoding='utf-8').read()
        if 'shiftloc' not in h:
            raise SystemExit("XATO: %s da avval install-smena-gps.py ni o'rnating." % d)
        if MARK in sv:
            print(d, ": allaqachon o'rnatilgan, o'tkazib yuborildi")
            continue
        sv = rep(sv, "def check_write(me, role, op, path, data, old):\n", FUNC + "def check_write(me, role, op, path, data, old):\n")
        sv = rep(sv, "            with LOCK:\n                if u.path == '/api/app/loc':", ROUTE)
        h = rep(h, OLD_JS, NEW_JS)
        for p in (hp, sp):
            shutil.copy2(p, p + '.bak-smenalink')
        open(hp, 'w', encoding='utf-8').write(h)
        open(sp, 'w', encoding='utf-8').write(sv)
        print(d, ': yangilandi')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit("Papka yo'lini bering: python3 install-smena-link.py /opt/gilam-crm /opt/fayz-crm")
    main(sys.argv[1:])
