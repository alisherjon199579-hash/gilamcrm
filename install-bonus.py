#!/usr/bin/env python3
"""Qaytish bonusi: uzoq vaqt kelmagan mijozga chegirma. Rahbar yoqadi (Mijozlar -> Faolligi pasaygan), yangi zakazda avtomat taklif qilinadi,
Telegram eslatmasiga bonus qatori qo'shiladi.
Ishlatish:  python3 install-bonus.py /opt/gilam-crm /opt/fayz-crm
index.html, server.py, bot.py zaxiralanadi (.bak-bonus)."""
import os, shutil, sys

MARK = '/* bonus-v1 */'


def rep(s, old, new, n=1):
    c = s.count(old)
    if c != n:
        raise SystemExit('XATO: kutilgan joy topilmadi (%d marta): %r' % (c, old[:70]))
    return s.replace(old, new)


BOT = r'''    def bonus_msg(self, text, months):
        """Qaytish bonusi yoqilgan va mijoz shuncha vaqt kelmagan bo'lsa, eslatmaga bonus qatori qo'shiladi."""
        try:
            with self.s.LOCK:
                b = self.s.get_doc('bonus/cfg') or {}
            if b.get('on') and months * 30 >= int(b.get('days') or 90):
                head, _, tail = text.partition('\n\n')
                return head + "\n\n🎁 Qaytganingiz uchun %s%% chegirma! Zakaz berganingizda ayting." % int(b.get('pct') or 0) + ('\n\n' + tail if tail else '')
        except Exception:  # noqa
            pass
        return text

    def remind(self, now=None):'''

JS = r'''
/* bonus-v1 */
const bcfg=()=>{const b=S.bonus.find(x=>x.id==='cfg')||{};return {on:!!b.on,pct:+b.pct||10,days:+b.days||90}};
function bonusFor(key){const c=bcfg();if(!c.on||!key)return 0;const r=clientRows().find(x=>x.key===key);return r&&r.last&&Date.now()-r.last>=c.days*86400000?c.pct:0}
function bonusTxt(){const c=bcfg();return c.on?` Qaytganingiz uchun ${c.pct}% chegirma bor!`:''}
function bonPct(){if(F&&F.id){const eo=S.orders.find(x=>x.id===F.id);return eo&&eo.disc||0}const k=$('#of-bon-c');return k&&k.checked?F.bon||0:0}
const applyDisc=(s,p)=>p?Math.round(s*(1-p/100)):s;
function updBonus(){const el=$('#of-bon');if(!el||(F&&F.id))return;const p=bonusFor(phoneKey($('#of-phone')?$('#of-phone').value:''));
  if(p===(F.bon||0)&&F.bonShown)return;F.bon=p;F.bonShown=true;
  el.innerHTML=p?`<label class="card" style="display:flex;gap:10px;align-items:center;font-weight:600;border-color:var(--ok)"><input type="checkbox" id="of-bon-c" checked style="width:24px;height:24px;min-height:0;flex:none;padding:0"> Qaytish bonusi: −${p}% chegirma</label>`:'';updTotal()}
document.addEventListener('input',e=>{if(e.target.id==='of-phone')updBonus()});document.addEventListener('change',e=>{if(e.target.id==='of-bon-c')updTotal()});
const _ocB=orderCard;orderCard=function(o){const h=_ocB(o);if(!o.disc)return h;const i=h.lastIndexOf('</button>');return h.slice(0,i)+`<div class="row" style="margin-top:6px;gap:6px"><span class="pill p-yes">Bonus −${o.disc}%</span></div>`+h.slice(i)};
const _chB=clientsHtml;clientsHtml=function(){const h=_chB();if(S.cv!=='lapsed'||!isAdmin())return h;const c=bcfg();
  return `<button class="card" data-act="bonuscfg" style="margin-bottom:12px"><div class="row"><b class="grow">Qaytish bonusi</b><span class="pill ${c.on?'p-yes':'p-wait'}">${c.on?'Yoqilgan':"O'chiq"}</span></div><div class="meta">${c.on?`${c.days} kundan beri kelmagan mijozga −${c.pct}% chegirma`:'Yoqsangiz, uzoq kelmagan mijozga chegirma taklif qilinadi'}</div></button>`+h};
function openBonusCfg(){const c=bcfg();showSheet('bonus','Qaytish bonusi',`<label class="f" style="flex-direction:row;gap:8px;align-items:center"><input type="checkbox" id="bn-on" ${c.on?'checked':''} style="width:auto">Yoqish</label>
  <label class="f">Chegirma, %<input id="bn-p" inputmode="numeric" value="${c.pct}"></label><label class="f">Necha kun kelmagan mijozga (kun)<input id="bn-d" inputmode="numeric" value="${c.days}"></label>
  <p class="sub">Yangi zakaz yozishda mijoz shuncha kundan beri kelmagan bo'lsa, chegirma avtomat taklif qilinadi. Telegram eslatmasiga ham yoziladi.</p><div class="err" id="bn-err"></div>`,
  `<button class="btn pri grow" data-act="bonussave">Saqlash</button>`)}
'''

HANDLERS = r'''else if(a==='bonuscfg')openBonusCfg();
  else if(a==='bonussave'){const p=Math.round(num($('#bn-p').value)),dd=Math.round(num($('#bn-d').value));
    if(!(p>=1&&p<=50)){$('#bn-err').textContent="Chegirma 1 dan 50 gacha bo'lsin.";return}
    if(!(dd>=14&&dd<=730)){$('#bn-err').textContent="Kun 14 dan 730 gacha bo'lsin.";return}
    if(await save(db.doc('bonus/cfg').set({on:$('#bn-on').checked,pct:p,days:dd}),'Saqlandi')){closeSheet();if(S.shown==='app')renderBody()}}
  else if(a==='delcash'){'''


def patch_server(s):
    s = rep(s, "SERVER_ONLY = ('tg', 'cfg')", "COLLS = COLLS + ('bonus',)\nSERVER_ONLY = ('tg', 'cfg')")
    s = rep(s, "FLOW = {'washer'", "for _r in ('courier', 'washer', 'packer'):\n    READ[_r] = READ[_r] + ('bonus',)\nFLOW = {'washer'")
    return s


def patch_bot(s):
    s = rep(s, "    def remind(self, now=None):", BOT)
    s = rep(s, "self.say(chat, REMIND % (os_[0].get('name') or 'hurmatli mijoz', months))",
            "self.say(chat, self.bonus_msg(REMIND % (os_[0].get('name') or 'hurmatli mijoz', months), months))")
    s = rep(s, "        L += [('sep',), ('kv', 'HOZIRCHA JAMI' if pend(o) else 'JAMI', money(o.get('total')), 1, 1)]",
            "        if o.get('disc'):\n            L += [('sep',), ('kv', 'Qaytish bonusi', '-%s%%' % o['disc'], 0, 0)]\n"
            "        L += [('sep',), ('kv', 'HOZIRCHA JAMI' if pend(o) else 'JAMI', money(o.get('total')), 1, 1)]")
    return s


def patch_html(s):
    s = rep(s, "cash:[],sal:[],", "cash:[],sal:[],bonus:[],")
    s = rep(s, "  ['cash','sal'].forEach(n=>db.collection(n)",
            "  db.collection('bonus').onSnapshot(x=>{S.bonus=x.docs.map(y=>({id:y.id,...y.data()}))},()=>{});\n"
            "  ['cash','sal'].forEach(n=>db.collection(n)")
    s = rep(s, "function openCashForm(type){", JS.lstrip('\n') + "function openCashForm(type){")
    s = rep(s, "else if(a==='delcash'){", HANDLERS)
    s = rep(s, '<label class="f">Izoh<textarea id="of-note">', "${o?'':'<div id=\"of-bon\"></div>'}<label class=\"f\">Izoh<textarea id=\"of-note\">")
    s = rep(s, "t.textContent=money(it.reduce((a,i)=>a+i.sum,0));", "t.textContent=money(applyDisc(it.reduce((a,i)=>a+i.sum,0),bonPct()));")
    s = rep(s, "const items=calcItems(),total=items.reduce((a,i)=>a+i.sum,0);",
            "const items=calcItems(),sum0=items.reduce((a,i)=>a+i.sum,0),dpc=bonPct(),total=applyDisc(sum0,dpc);")
    s = rep(s, "items,total,...(F.pick?", "items,total,...(F.pick?")  # tahrirda bonus o'zgarmaydi (total yuqorida hisoblandi)
    s = rep(s, "items,total,status:'new',", "items,total,...(dpc?{disc:dpc,discSum:sum0-total}:{}),status:'new',")
    s = rep(s, "update({items,total:items.reduce((x,i)=>x+i.sum,0)}),\"O'lchamlar saqlandi\"",
            "update({items,total:applyDisc(items.reduce((x,i)=>x+i.sum,0),o.disc||0)}),\"O'lchamlar saqlandi\"")
    s = rep(s, "xizmatimizga tayyormiz!`", "xizmatimizga tayyormiz!${bonusTxt()}`")
    s = rep(s, "    L.push({t:'sep'},{t:'kv',a:pend(o)?'HOZIRCHA JAMI':'JAMI',b:money(o.total),bold:1,big:1});",
            "    if(o.disc)L.push({t:'sep'},{t:'kv',a:'Qaytish bonusi',b:'-'+o.disc+'%'});\n    L.push({t:'sep'},{t:'kv',a:pend(o)?'HOZIRCHA JAMI':'JAMI',b:money(o.total),bold:1,big:1});")
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
            shutil.copy2(p, p + '.bak-bonus')
            open(p, 'w', encoding='utf-8').write(t)
        print(d, ': yangilandi')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit("Papka yo'lini bering: python3 install-bonus.py /opt/gilam-crm /opt/fayz-crm")
    main(sys.argv[1:])
