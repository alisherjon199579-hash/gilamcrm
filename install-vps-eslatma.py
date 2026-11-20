#!/usr/bin/env python3
"""Server to'lovi eslatmasi: har oyning 10-sanasidan boshlab rahbarga CRM ichida chiqadi va Telegramga xabar keladi ("To'ladim" bosilguncha, 20-sanagacha).
Ishlatish:  python3 install-vps-eslatma.py /opt/gilam-crm /opt/fayz-crm"""
import os, shutil, sys

MARK = '/* vps-eslatma-v1 */'


def rep(s, old, new, n=1):
    c = s.count(old)
    if c != n:
        raise SystemExit('XATO: kutilgan joy topilmadi (%d marta): %r' % (c, old[:70]))
    return s.replace(old, new)


BOT = r'''        with self.s.LOCK:
            vp = self.s.meta('tg_vps', '')
            pd = (self.s.get_doc('remind/vps') or {}).get('paid')
        if adm and 10 <= t.tm_mday <= 20 and t.tm_hour >= 10 and vp != day and pd != '%d-%02d' % (t.tm_year, t.tm_mon):
            with self.s.LOCK:
                self.s.set_meta('tg_vps', day)
            for c in adm:
                self.say(c, "💳 Server to'lovi vaqti keldi. VPS ta'minotchi hisobiga kirib to'lovni qiling, aks holda CRM va bot to'xtab qolishi mumkin.\n\nTo'lagach, CRM'ning bosh sahifasida «To'ladim» tugmasini bosing, shunda eslatma to'xtaydi.")
        with self.s.LOCK:
            dly = self.s.meta('tg_daily', '')'''

JS = r'''
/* vps-eslatma-v1 */
function vpsDue(){const d=new Date(),ym=d.getFullYear()+'-'+p2(d.getMonth()+1),r=S.remind.find(x=>x.id==='vps');return isAdmin()&&d.getDate()>=10&&!(r&&r.paid===ym)?ym:''}
const _dhV=dashHtml;dashHtml=function(){const ym=vpsDue();return (ym?`<div class="card stack" style="margin-bottom:12px;border-color:var(--warn)"><b>Server to'lovi vaqti keldi</b><div class="meta">VPS ta'minotchi hisobiga kirib to'lovni qiling, aks holda CRM to'xtab qolishi mumkin.</div><button class="btn pri wide" data-act="vpspaid" data-ym="${ym}">To'ladim</button></div>`:'')+_dhV()};
'''

HANDLER = r'''else if(a==='vpspaid'){if(await save(db.doc('remind/vps').set({paid:d.ym,by:S.me.name,t:Date.now()}),"Rahmat, eslatma o'chirildi")&&S.shown==='app')renderBody()}
  else if(a==='delcash'){'''


def patch_server(s):
    s = rep(s, "SERVER_ONLY = ('tg', 'cfg')", "COLLS = COLLS + ('remind',)\nSERVER_ONLY = ('tg', 'cfg')")
    return s


def patch_bot(s):
    return rep(s, "        with self.s.LOCK:\n            dly = self.s.meta('tg_daily', '')", BOT)


def patch_html(s):
    s = rep(s, "cash:[],sal:[],", "cash:[],sal:[],remind:[],")
    s = rep(s, "  ['cash','sal'].forEach(n=>db.collection(n)",
            "  db.collection('remind').onSnapshot(x=>{S.remind=x.docs.map(y=>({id:y.id,...y.data()}));if(S.shown==='app'&&!sheetKind&&S.tab==='dash')renderBody()},()=>{});\n"
            "  ['cash','sal'].forEach(n=>db.collection(n)")
    s = rep(s, "function openCashForm(type){", JS.lstrip('\n') + "function openCashForm(type){")
    s = rep(s, "else if(a==='delcash'){", HANDLER)
    return s


def main(dirs):
    for d in dirs:
        ps = [os.path.join(d, n) for n in ('index.html', 'server.py', 'bot.py')]
        h, sv, bt = [open(p, encoding='utf-8').read() for p in ps]
        if MARK in h:
            print(d, ": allaqachon o'rnatilgan, o'tkazib yuborildi")
            continue
        new = [patch_html(h), patch_server(sv), patch_bot(bt)]
        for p, t in zip(ps, new):
            shutil.copy2(p, p + '.bak-vps')
            open(p, 'w', encoding='utf-8').write(t)
        print(d, ': yangilandi')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit("Papka yo'lini bering: python3 install-vps-eslatma.py /opt/gilam-crm /opt/fayz-crm")
    main(sys.argv[1:])
