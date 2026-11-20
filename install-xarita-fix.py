#!/usr/bin/env python3
"""Xarita: OpenStreetMap «Access blocked / 403» xatosini tuzatadi (brauzer Referer yubormayotgan edi).
Ishlatish:  python3 install-xarita-fix.py /opt/gilam-crm /opt/fayz-crm"""
import os, shutil, sys

OLD = "self.send_header('Referrer-Policy', 'same-origin')"
NEW = "self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')"


def main(dirs):
    for d in dirs:
        sp = os.path.join(d, 'server.py')
        s = open(sp, encoding='utf-8').read()
        if NEW in s:
            print(d, ": allaqachon tuzatilgan, o'tkazib yuborildi")
            continue
        if s.count(OLD) != 1:
            raise SystemExit('XATO: %s da kutilgan joy topilmadi (%d marta)' % (d, s.count(OLD)))
        shutil.copy2(sp, sp + '.bak-xaritafix')
        open(sp, 'w', encoding='utf-8').write(s.replace(OLD, NEW))
        print(d, ': yangilandi')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit("Papka yo'lini bering: python3 install-xarita-fix.py /opt/gilam-crm /opt/fayz-crm")
    main(sys.argv[1:])
