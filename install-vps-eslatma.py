#!/usr/bin/env python3
"""Server to'lovi eslatmasi: har oyning 10-sanasidan boshlab rahbarga CRM ichida chiqadi va Telegramga xabar keladi ("To'ladim" bosilguncha, 20-sanagacha).
Ishlatish:  python3 install-vps-eslatma.py /opt/gilam-crm /opt/fayz-crm"""
import os, shutil, sys

MARK = '/* vps-eslatma-v1 */'
MARK2 = '/* vps-eslatma-v2 */'


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


def upgrade_v2(h, b):
    """v1 -> v2: to'lov sahifasi havolasi (CRM ichidan kiritiladi, Telegram xabariga qo'shiladi)."""
    h = rep(h, "/* vps-eslatma-v1 */", "/* vps-eslatma-v1 */ /* vps-eslatma-v2 */")
    h = rep(h, "function vpsDue(){", """const vpsDoc=x=>{const r={...(S.remind.find(y=>y.id==='vps')||{})};delete r.id;return {...r,...x}};
function openVpsUrl(){const r=S.remind.find(y=>y.id==='vps')||{};showSheet('vpsurl',"To'lov sahifasi havolasi",`<label class="f">Server ta'minotchisining to'lov (billing) sahifasi<input id="vu-u" inputmode="url" value="${esc(r.url||'')}" placeholder="https://..."></label><p class="sub">Telegramdagi eslatmaga va bosh sahifadagi kartaga shu havola qo'shiladi. Parolni bu yerga yozmang.</p><div class="err" id="vu-err"></div>`,`<button class="btn pri grow" data-act="vpsurlsave">Saqlash</button>`)}
function vpsDue(){""")
    vu = "(S.remind.find(x=>x.id==='vps')||{}).url"
    h = rep(h, '<button class="btn pri wide" data-act="vpspaid"',
            '${' + vu + '?`<a class="btn wide" href="${esc(' + vu + ')}" target="_blank" rel="noopener">To\'lov sahifasini ochish</a>`:\'\'}'
            '<button class="btn sm" data-act="vpsurl">${' + vu + '?"Havolani o\'zgartirish":"Havola qo\'shish"}</button><button class="btn pri wide" data-act="vpspaid"')
    h = rep(h, "set({paid:d.ym,by:S.me.name,t:Date.now()})", "set(vpsDoc({paid:d.ym,by:S.me.name,t:Date.now()}))")
    h = rep(h, "else if(a==='vpspaid'){", """else if(a==='vpsurl')openVpsUrl();
  else if(a==='vpsurlsave'){const u=$('#vu-u').value.trim();if(u&&!/^https:\\/\\/[^\\s]+$/i.test(u)){$('#vu-err').textContent="Havola https:// bilan boshlansin.";return}
    if(await save(db.doc('remind/vps').set(vpsDoc({url:u})),'Saqlandi')){closeSheet();if(S.shown==='app')renderBody()}}
  else if(a==='vpspaid'){""")
    b = rep(b, "            pd = (self.s.get_doc('remind/vps') or {}).get('paid')\n", "            rv = self.s.get_doc('remind/vps') or {}\n            pd = rv.get('paid')\n")
    b = rep(b, "CRM'ning bosh sahifasida «To'ladim» tugmasini bosing, shunda eslatma to'xtaydi.\")",
            "CRM'ning bosh sahifasida «To'ladim» tugmasini bosing, shunda eslatma to'xtaydi.\" + (\"\\n\\nTo'lov sahifasi: \" + rv['url'] if rv.get('url') else ''))")
    return h, b


def main(dirs):
    for d in dirs:
        ps = [os.path.join(d, n) for n in ('index.html', 'server.py', 'bot.py')]
        h, sv, bt = [open(p, encoding='utf-8').read() for p in ps]
        if MARK2 in h:
            print(d, ": allaqachon o'rnatilgan, o'tkazib yuborildi")
            continue
        if MARK in h:  # v1 o'rnatilgan: faqat havola qismi qo'shiladi
            nh, nb = upgrade_v2(h, bt)
            new = [nh, sv, nb]
        else:
            nh, nb = upgrade_v2(patch_html(h), patch_bot(bt))
            new = [nh, patch_server(sv), nb]
        for p, t in zip(ps, new):
            shutil.copy2(p, p + '.bak-vps')
            open(p, 'w', encoding='utf-8').write(t)
        print(d, ': yangilandi')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit("Papka yo'lini bering: python3 install-vps-eslatma.py /opt/gilam-crm /opt/fayz-crm")
    main(sys.argv[1:])
