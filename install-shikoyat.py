#!/usr/bin/env python3
"""Shikoyatlar: har kim shikoyat yozadi, rahbar holatini yuritadi (yangi / ko'rilmoqda / hal bo'ldi / rad), tovon summasi, Telegramga xabar.
Ishlatish:  python3 install-shikoyat.py /opt/gilam-crm /opt/fayz-crm
index.html, server.py, bot.py zaxiralanadi (.bak-shikoyat)."""
import os, shutil, sys

MARK = '/* shikoyat-v1 */'


def rep(s, old, new, n=1):
    c = s.count(old)
    if c != n:
        raise SystemExit('XATO: kutilgan joy topilmadi (%d marta): %r' % (c, old[:70]))
    return s.replace(old, new)


GUARD = r'''# ---- shikoyat-v1: xodim faqat yangi shikoyat yozadi (vaqt va ism serverdan) ----
def _comp_guard(me, role, op, path, data, old):
    if op != 'set' or old is not None or not isinstance(data, dict) or not path.partition('/')[2].startswith(me + '-'):
        raise Err(403, "Ruxsat yo'q.")
    text = str(data.get('text', '')).strip()[:1000]
    if not text:
        raise Err(400, 'Shikoyat matnini yozing.')
    st = staff_all().get(me) or {}
    clean = {k: str(data.get(k, '')).strip()[:l] for k, l in (('clientName', 80), ('phone', 30), ('orderNo', 20), ('orderId', 80), ('type', 30))}
    data.clear()
    data.update(clean, text=text, status='new', byId=me, byName=st.get('name', ''), t=int(time.time() * 1000))


'''

BOT = r'''    def complaint(self, c):
        """Yangi shikoyat: rahbarlarga Telegramdan xabar."""
        if not self.token():
            return
        txt = '⚠️ Yangi shikoyat\n%s%s\n%s\n\nYozdi: %s' % (
            c.get('clientName') or 'Mijoz ko\'rsatilmagan', (' · ' + c['phone']) if c.get('phone') else '',
            ('Zakaz №%s · ' % c['orderNo'] if c.get('orderNo') else '') + (c.get('type') or '') + '\n' + (c.get('text') or ''), c.get('byName') or '')
        for ch in self.admins():
            self.say(ch, txt)

    def send_loop(self):'''

JS = r'''
/* shikoyat-v1 */
const CST={new:['Yangi','p-no'],progress:["Ko'rilmoqda",'p-wait'],solved:["Hal bo'ldi",'p-yes'],rejected:['Rad etildi','']},CTYPES=['Sifat','Dog\' qoldi','Shikastlanish','Kechikish','Dostavchi','Boshqa'];let CF='';
function rerenderComp(){if(S.shown==='app'&&!sheetKind&&(S.tab==='fin'&&S.fin.v==='complaint'||S.tab===tabsFor()[0]))renderBody()}
FV.complaint={n:'Shikoyatlar',s:"Mijoz shikoyatlari va ularni hal qilish",c:'madder',i:'<path d="M12 4l9 16H3zM12 10v4M12 17h.01"/>'};
FVH.complaint=()=>{
  const all=[...S.complaint].sort((a,b)=>b.t-a.t),cnt=k=>all.filter(x=>x.status===k).length,list=CF?all.filter(x=>x.status===CF):all;
  return `<div class="tiles"><div class="tile"><small>Yangi</small><b class="${cnt('new')?'neg':''}">${cnt('new')}</b></div><div class="tile"><small>Ko'rilmoqda</small><b>${cnt('progress')}</b></div><div class="tile"><small>Hal bo'ldi</small><b class="pos">${cnt('solved')}</b></div><div class="tile"><small>Tovon (jami)</small><b>${money(all.reduce((s,x)=>s+(+x.comp||0),0))}</b></div></div>
  <button class="btn pri wide" style="margin-top:12px" data-act="compnew">+ Shikoyat qo'shish</button>
  <div class="row" style="margin:12px 0;flex-wrap:wrap"><button class="chip" data-act="compf" data-f="" aria-pressed="${!CF}">Hammasi</button>${Object.keys(CST).map(k=>`<button class="chip" data-act="compf" data-f="${k}" aria-pressed="${CF===k}">${CST[k][0]}</button>`).join('')}</div>
  ${list.length?`<div class="stack">${list.map(x=>`<button class="card" data-act="compopen" data-id="${esc(x.id)}"><div class="row"><b class="grow">${esc(x.clientName||'Mijoz ko\'rsatilmagan')}</b><span class="pill ${CST[x.status]?CST[x.status][1]:''}">${CST[x.status]?CST[x.status][0]:''}</span></div><div class="meta">${x.orderNo?'№'+esc(x.orderNo)+' · ':''}${esc(x.type||'')} · ${mfmt2(x.t)} · ${esc(x.byName||'')}</div><div>${esc(x.text.length>110?x.text.slice(0,110)+'…':x.text)}</div></button>`).join('')}</div>`:finEmpty("Shikoyat yo'q.")}`};
const mfmt2=t=>{const d=new Date(t);return dstr(t)+' '+p2(d.getHours())+':'+p2(d.getMinutes())};
function openCompNew(){F={};
  showSheet('compnew','Shikoyat yozish',`<label class="f">Zakaz raqami (agar bo'lsa)<input id="cp-o" inputmode="numeric"></label><label class="f">Mijoz ismi<input id="cp-n"></label><label class="f">Telefon<input id="cp-p" inputmode="tel"></label>
   <label class="f">Turi<select id="cp-t">${CTYPES.map(x=>`<option>${esc(x)}</option>`).join('')}</select></label><label class="f">Nima bo'ldi?<textarea id="cp-x" rows="4"></textarea></label><div class="err" id="cp-err"></div>`,
   `<button class="btn pri grow" data-act="compsave">Yuborish</button>`);
}
function openComp(id){
  const c=S.complaint.find(x=>x.id===id);if(!c)return;F={cid:id,st:c.status};
  showSheet('comp',esc(c.clientName||'Shikoyat'),`<div class="meta">${c.orderNo?'Zakaz №'+esc(c.orderNo)+' · ':''}${esc(c.type||'')} · ${mfmt2(c.t)} · ${esc(c.byName||'')}</div>${c.phone?`<a class="btn wide" style="margin:8px 0" href="tel:${esc(c.phone)}">${esc(c.phone)}</a>`:''}
   <div class="card" style="white-space:pre-wrap">${esc(c.text)}</div>
   <div class="row" style="margin:12px 0;flex-wrap:wrap">${Object.keys(CST).map(k=>`<button class="chip" data-act="compst" data-s="${k}" aria-pressed="${c.status===k}">${CST[k][0]}</button>`).join('')}</div>
   <label class="f">Qanday hal qilindi<textarea id="cp-r" rows="3">${esc(c.resolution||'')}</textarea></label><label class="f">Tovon summasi, so'm<input id="cp-c" inputmode="numeric" value="${c.comp||''}"></label>`,
   `<button class="btn pri grow" data-act="compupd">Saqlash</button>${c.orderId&&S.orders.some(o=>o.id===c.orderId)?`<button class="btn grow" data-act="order" data-id="${esc(c.orderId)}">Zakaz</button>`:''}<button class="btn bad" data-act="compdel" data-sure="0">O'chirish</button>`);
}
function compBox(){
  if(!S.me||S.me.role==='admin'||S.tab!==tabsFor()[0])return'';
  const n=S.complaint.filter(x=>x.status==='new'||x.status==='progress').length;
  return `<div class="card stack" style="margin-bottom:12px"><div class="row"><b class="grow">Shikoyat</b>${n?`<span class="meta">Ochiq: ${n} ta</span>`:''}</div><button class="btn wide" data-act="compnew">Shikoyat yozish</button></div>`;
}
'''

HANDLERS = r'''else if(a==='compnew')openCompNew();
  else if(a==='compopen'){if(S.me.role==='admin')openComp(d.id)}
  else if(a==='compf'){CF=d.f||'';renderBody()}
  else if(a==='compst'){F.st=d.s;document.querySelectorAll('[data-act=compst]').forEach(x=>x.setAttribute('aria-pressed',x.dataset.s===d.s))}
  else if(a==='compupd'){b.disabled=true;if(await save(db.doc('complaint/'+F.cid).update({status:F.st,resolution:$('#cp-r').value.trim(),comp:amt('#cp-c'),doneBy:S.me.name,doneAt:Date.now()}),'Saqlandi'))(closeSheet(),rerenderComp());else b.disabled=false}
  else if(a==='compdel'){if(!sure(b))return;if(await save(db.doc('complaint/'+F.cid).delete(),"Shikoyat o'chirildi"))(closeSheet(),rerenderComp())}
  else if(a==='compsave'){const tx=$('#cp-x').value.trim(),no=$('#cp-o').value.trim(),o=no?S.orders.find(x=>String(x.no)===no):null;let nm=$('#cp-n').value.trim(),ph=$('#cp-p').value.trim();
    if(!tx){$('#cp-err').textContent='Nima bo\'lganini yozing.';return}
    if(o){nm=nm||o.name||'';ph=ph||o.phone||''}
    if(!nm&&!ph&&!no){$('#cp-err').textContent='Zakaz raqami yoki mijoz ismini kiriting.';return}
    b.disabled=true;const t=Date.now();
    if(await save(db.doc('complaint/'+S.me.id+'-'+t).set({clientName:nm,phone:ph,orderNo:no,orderId:o?o.id:'',type:$('#cp-t').value,text:tx,status:'new',byId:S.me.id,byName:S.me.name,t}),'Shikoyat yuborildi'))(closeSheet(),rerenderComp());else b.disabled=false}
  else if(a==='delcash'){'''


def patch_server(s):
    s = rep(s, "SERVER_ONLY = ('tg', 'cfg')", "COLLS = COLLS + ('complaint',)\nSERVER_ONLY = ('tg', 'cfg')")
    s = rep(s, "FLOW = {'washer'", "for _r in ('courier', 'washer', 'packer'):\n    READ[_r] = READ[_r] + ('complaint',)\nFLOW = {'washer'")
    s = rep(s, "                        if role != 'admin' and p.startswith('staff/'):",
            "                        if role != 'admin' and p.startswith('complaint/') and d.get('byId') != me:\n                            continue\n                        if role != 'admin' and p.startswith('staff/'):")
    s = rep(s, "def check_write(me, role, op, path, data, old):\n",
            GUARD + "def check_write(me, role, op, path, data, old):\n"
            "    if path.startswith('complaint/') and role != 'admin':\n"
            "        return _comp_guard(me, role, op, path, data, old)\n")
    s = rep(s, "                        BOT.staff_event(old, new, me)\n",
            "                        BOT.staff_event(old, new, me)\n"
            "                    if seg[0] == 'complaint' and op == 'set' and old is None:\n"
            "                        BOT.complaint(new)\n")
    return s


def patch_html(s):
    s = rep(s, "cash:[],sal:[],", "cash:[],sal:[],complaint:[],")
    s = rep(s, "  ['cash','sal'].forEach(n=>db.collection(n)",
            "  db.collection('complaint').onSnapshot(x=>{S.complaint=x.docs.map(y=>({id:y.id,...y.data()}));rerenderComp()},()=>{});\n"
            "  ['cash','sal'].forEach(n=>db.collection(n)")
    s = rep(s, "function openCashForm(type){", JS.lstrip('\n') + "function openCashForm(type){")
    s = rep(s, "({dash:dashHtml,orders:ordersHtml", "compBox()+({dash:dashHtml,orders:ordersHtml")
    s = rep(s, "else if(a==='delcash'){", HANDLERS)
    return s


def patch_bot(s):
    return rep(s, "    def send_loop(self):", BOT)


def main(dirs):
    for d in dirs:
        ps = [os.path.join(d, n) for n in ('index.html', 'server.py', 'bot.py')]
        h, sv, bt = [open(p, encoding='utf-8').read() for p in ps]
        if MARK in h:
            print(d, ": allaqachon o'rnatilgan, o'tkazib yuborildi")
            continue
        new = [patch_html(h), patch_server(sv), patch_bot(bt)]
        for p, t in zip(ps, new):
            shutil.copy2(p, p + '.bak-shikoyat')
            open(p, 'w', encoding='utf-8').write(t)
        print(d, ': yangilandi')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit("Papka yo'lini bering: python3 install-shikoyat.py /opt/gilam-crm /opt/fayz-crm")
    main(sys.argv[1:])
