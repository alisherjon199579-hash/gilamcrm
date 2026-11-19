#!/usr/bin/env python3
"""Oylik: smenada ishlagan soat × soatlik haq avtomat hisoblanib, oylikka qo'shiladi.
Avval install-pul.py va install-smena.py o'rnatilgan bo'lishi kerak.
Ishlatish:  python3 install-soatlik.py /opt/gilam-crm /opt/fayz-crm"""
import os, shutil, sys

MARK = '/* soatlik-v1 */'


def rep(s, old, new, n=1):
    c = s.count(old)
    if c != n:
        raise SystemExit('XATO: kutilgan joy topilmadi (%d marta): %r' % (c, old[:70]))
    return s.replace(old, new)


def patch(s):
    s = rep(s, "paid:0,area:0,rev:0,w:{new:0", "paid:0,area:0,rev:0,hrate:+sv.hrate||0,w:{new:0")
    s = rep(s, "Object.values(st).forEach(s=>{s.area=r2(s.area);s.auto=Math.round(s.area*s.rate)+Math.round(s.rev*s.pct/100);s.earn=s.salary+s.auto});",
            "/* soatlik-v1 */const nowT=Date.now();Object.values(st).forEach(s=>{s.area=r2(s.area);s.ms=S.shift.filter(h=>h.sid===s.x.id&&(h.in||0)>=r.ma&&(h.in||0)<r.mb).reduce((a,h)=>a+Math.max(0,(h.out||nowT)-h.in),0);s.hours=r2(s.ms/3600000);s.hpay=Math.round(s.hours*s.hrate);s.auto=Math.round(s.area*s.rate)+Math.round(s.rev*s.pct/100)+s.hpay;s.earn=s.salary+s.auto});")
    s = rep(s, "+finKV('Belgilangan oylik',money(s.salary))",
            "+((s.hours||s.hrate)?finKV(`Ishlagan ${s.hours} soat × ${money(s.hrate)}`,money(s.hpay)):'')+finKV('Belgilangan oylik',money(s.salary))")
    s = rep(s, "${rateF}${pctF}<label",
            "${rateF}${pctF}<label class=\"f\">Soatlik haq, 1 soat uchun so'm<input id=\"sl-hr\" inputmode=\"numeric\" value=\"${s.hrate||''}\"></label><label")
    s = rep(s, "set({salary:v,rate:rt,pct:pc})", "set({salary:v,rate:rt,pct:pc,hrate:$('#sl-hr')?amt('#sl-hr'):0})")
    s = rep(s, "+(s&&s.rev?' · yetkazilgan tushum '+money(s.rev):'');", "+(s&&s.rev?' · yetkazilgan tushum '+money(s.rev):'')+(s&&s.hours?' · ishlagan '+s.hours+' soat':'');")
    return s


def main(dirs):
    for d in dirs:
        hp = os.path.join(d, 'index.html')
        h = open(hp, encoding='utf-8').read()
        if '/* smena-v1 */' not in h or 'sl-rate' not in h:
            raise SystemExit("XATO: %s da avval install-pul.py va install-smena.py ni o'rnating." % d)
        if MARK in h:
            print(d, ": allaqachon o'rnatilgan, o'tkazib yuborildi")
            continue
        nh = patch(h)
        shutil.copy2(hp, hp + '.bak-soatlik')
        open(hp, 'w', encoding='utf-8').write(nh)
        print(d, ': yangilandi')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit("Papka yo'lini bering: python3 install-soatlik.py /opt/gilam-crm /opt/fayz-crm")
    main(sys.argv[1:])
