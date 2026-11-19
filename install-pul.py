#!/usr/bin/env python3
"""Pul nazorati: yetkazishda naqd/karta, dastavchi qo'lidagi pul, oylik (yuvuvchi m2, dastavchi tushum).
Ishlatish:  python3 install-pul.py /opt/gilam-crm /opt/fayz-crm
Har bir papkada index.html va server.py zaxiralanadi (.bak-pul), keyin yangilanadi."""
import os, re, shutil, sys

MARK = '/* pul-v1 */'


def rep(s, old, new, n=1):
    c = s.count(old)
    if c != n:
        raise SystemExit('XATO: kutilgan joy topilmadi (%d marta uchradi): %r' % (c, old[:70]))
    return s.replace(old, new)


# ------------------------------------------------------------------ server.py
def patch_server(s):
    s = rep(s, "COLLS = ('staff', 'services', 'orders', 'clients', 'locs', 'cash', 'sal', 'tg', 'cfg')",
            "COLLS = ('staff', 'services', 'orders', 'clients', 'locs', 'cash', 'sal', 'hand', 'tg', 'cfg')")
    s = rep(s, "'courier': ('staff', 'services', 'orders', 'clients', 'locs', 'tg', 'cfg'),",
            "'courier': ('staff', 'services', 'orders', 'clients', 'locs', 'hand', 'tg', 'cfg'),")
    guard = '''
# ---- pul nazorati (pul-v1): yetkazishda to'lov yozuvi ----
PAY_KEYS = {'pays', 'col', 'paid', 'paidAt', 'paidSum', 'kassa', 'collectedBy', 'collectedByName'}


def _pay_guard(me, role, op, path, data, old):
    """Dostavchi to'lov maydonlarini faqat «Qadoqlandi -> Yetkazildi» o'tishida va o'z nomidan yoza oladi."""
    if role == 'admin' or not path.startswith('orders/') or not isinstance(data, dict) or not (set(data) & PAY_KEYS):
        return
    if (role != 'courier' or op != 'update' or old is None or old.get('status') != 'packed'
            or data.get('status') != 'delivered'):
        raise Err(403, "Ruxsat yo'q.")
    if set(data) - PAY_KEYS - {'status', 'log', 'msgSt'}:
        raise Err(403, "Ruxsat yo'q.")
    try:
        col = {k: float(v) for k, v in (data.get('col') or {}).items()}
        pays = {k: float(v) for k, v in (data.get('pays') or {}).items()}
    except Exception:
        raise Err(400, "Summa noto'g'ri.")
    if any(v < 0 for v in list(col.values()) + list(pays.values())):
        raise Err(400, "Summa noto'g'ri.")
    total = float(old.get('total') or 0)
    got = float(old.get('paidSum') or 0)
    if data.get('collectedBy') not in (None, me):
        raise Err(403, "Ruxsat yo'q.")
    if sum(col.values()) > max(total - got, 0) + 0.5 or sum(pays.values()) > total + 0.5:
        raise Err(400, "Summa zakaz summasidan ko'p.")
    if data.get('paid') is True and not (total > 0 and sum(pays.values()) + 0.5 >= total):
        raise Err(400, "Summa to'liq emas.")

'''
    s = rep(s, "def check_write(me, role, op, path, data, old):\n    if role != 'admin':",
            guard + "def check_write(me, role, op, path, data, old):\n    _pay_guard(me, role, op, path, data, old)\n    if role != 'admin':")
    return s


# ------------------------------------------------------------------ index.html
HELPERS = r'''
/* pul-v1 */
const due=o=>o.paid?0:Math.max(0,(o.total||0)-(o.paidSum||0));
function courierCash(id){
  let c=0,k=0,last=0;
  S.orders.forEach(o=>{if(o.collectedBy===id&&o.col){c+=+o.col.cash||0;k+=+o.col.card||0}});
  (S.hand||[]).forEach(h=>{if(h.cid===id){c-=+h.cash||0;k-=+h.card||0;last=Math.max(last,h.t||0)}});
  c=Math.max(0,c);k=Math.max(0,k);return {cash:c,card:k,total:c+k,last};
}
function cashCard(id,who){
  const c=courierCash(id),L=S.orders.filter(o=>o.collectedBy===id&&o.col&&(o.paidAt||0)>c.last).sort((a,b)=>(b.paidAt||0)-(a.paidAt||0)).slice(0,20);
  return `<div class="card stack"><div class="row"><span class="grow meta">${who?esc(who)+' · ':''}QO'LIMDA</span><span class="pill ${c.total?'p-no':'p-yes'}">${c.total?'Topshirish kerak':"Qo'lda pul yo'q"}</span></div>
    <b style="font-size:26px">${money(c.total)}</b><div class="meta">Naqd: ${money(c.cash)} · Karta: ${money(c.card)}</div><div class="meta">Oxirgi topshirish: ${c.last?when(c.last):'hali yo\'q'}</div>
    ${L.length?`<div class="meta" style="margin-top:6px">Topshirilmagan to'lovlar:</div>`+L.map(o=>`<div style="padding:6px 0;border-top:1px solid var(--line)"><div class="meta">№${esc(o.no)} · ${esc(o.name)} · ${when(o.paidAt)}</div><b>${[+o.col.cash?'Naqd '+money(o.col.cash):'',+o.col.card?'Karta '+money(o.col.card):''].filter(Boolean).join(' · ')}</b></div>`).join(''):''}</div>`;
}
function courierBox(){return S.me&&S.me.role==='courier'&&S.filter!=='route'?`<div style="margin-bottom:12px">${cashCard(S.me.id)}</div>`:''}
function handHtml(){
  const cs=S.staff.filter(x=>x.role==='courier'&&x.active!==false);if(!cs.length)return'';
  return `<h2>Dostavchilar qo'lidagi pul</h2><div class="stack">${cs.map(x=>{const c=courierCash(x.id);return `<div class="card stack"><div class="row"><b class="grow">${esc(x.name)}</b><b class="sum ${c.total?'neg':''}">${money(c.total)}</b></div><div class="meta">Naqd: ${money(c.cash)} · Karta: ${money(c.card)} · Oxirgi topshirish: ${c.last?when(c.last):"yo'q"}</div><button class="btn ${c.total?'pri':''}" data-act="hand" data-id="${esc(x.id)}">Pulni qabul qilish</button></div>`}).join('')}</div>`;
}
function openHand(id){
  const x=S.staff.find(z=>z.id===id);if(!x)return;const c=courierCash(id);F={hid:id};
  showSheet('hand',esc(x.name)+" · pul topshirdi",`<div class="meta">Qo'lida: ${money(c.total)} (Naqd ${money(c.cash)} · Karta ${money(c.card)})</div>
    <label class="f">Naqd topshirdi, so'm<input id="hd-cash" inputmode="numeric" value="${c.cash||''}"></label>
    <label class="f">Karta bo'yicha hisob-kitob qildi, so'm<input id="hd-card" inputmode="numeric" value="${c.card||''}"></label><div class="err" id="hd-err"></div>`,
    `<button class="btn pri wide" data-act="savehand">Qabul qilindi</button>`);
}
function openPay(o){
  F={id:o.id};const d=due(o);
  showSheet('pay',`№${esc(o.no)} · to'lov`,`<div class="meta">Mijoz to'lashi kerak: <b>${money(d)}</b></div>
    <div class="row" style="gap:8px;margin:10px 0"><button class="btn grow" data-act="payq" data-m="cash">Hammasi naqd</button><button class="btn grow" data-act="payq" data-m="card">Hammasi karta</button></div>
    <label class="f">Naqd olindi, so'm<input id="py-cash" inputmode="numeric" value="${d||''}"></label>
    <label class="f">Karta orqali olindi, so'm<input id="py-card" inputmode="numeric" value=""></label>
    <div class="err" id="py-err"></div>`,`<button class="btn pri wide" data-act="deliverpay">Yetkazildi</button>`);
}
'''

HANDLERS = r'''else if(a==='hand')openHand(d.id);
  else if(a==='savehand'){const x=S.staff.find(z=>z.id===F.hid),ca=amt('#hd-cash'),ka=amt('#hd-card');if(!x||ca<0||ka<0||(ca<=0&&ka<=0)){$('#hd-err').textContent="Summani kiriting.";return}b.disabled=true;
    if(await save(db.collection('hand').doc().set({cid:x.id,cname:x.name,cash:ca,card:ka,t:Date.now(),byName:S.me.name}),'Pul qabul qilindi'))closeSheet();else b.disabled=false}
  else if(a==='payq'){const o=S.orders.find(x=>x.id===F.id);if(!o)return;$('#py-cash').value=d.m==='cash'?(due(o)||''):'';$('#py-card').value=d.m==='card'?(due(o)||''):''}
  else if(a==='deliverpay'){const o=S.orders.find(x=>x.id===F.id);if(!o)return;const dn=due(o),ca=amt('#py-cash'),ka=amt('#py-card'),err=$('#py-err');
    if(ca<0||ka<0){err.textContent="Summani to'g'ri kiriting.";return}
    if(ca+ka>dn){err.textContent="Kiritilgan summa to'lanishi kerak bo'lgan summadan ("+money(dn)+") ko'p.";return}
    if(ca+ka<dn&&b.dataset.ok!=='1'){b.dataset.ok='1';err.textContent=(ca+ka?'Qolgan ':"To'lov olinmadi. ")+money(dn-ca-ka)+" qarz bo'lib qoladi. Tasdiqlash uchun yana bosing.";return}
    b.disabled=true;const id=o.id,t=Date.now(),log=[...(o.log||[]),{t,by:S.me.name,byId:S.me.id,st:'delivered'}],upd={status:'delivered',log};
    if(ca+ka>0){const pc=(+((o.pays||{}).cash)||0)+ca,pk=(+((o.pays||{}).card)||0)+ka,sum=(+o.paidSum||0)+ca+ka;
      Object.assign(upd,{pays:{...(o.pays||{}),cash:pc,card:pk},col:{cash:ca,card:ka},collectedBy:S.me.id,collectedByName:S.me.name,paidSum:sum,paid:(o.total||0)>0&&sum>=(o.total||0),paidAt:t,kassa:ca&&ka?(ca>=ka?'cash':'card'):(ka?'card':'cash')})}
    if(await save(db.doc('orders/'+id).update(upd),`№${o.no}: ${ST.delivered}`)){if(!(await autoChek(id,{status:'delivered',log})))closeSheet()}else b.disabled=false}
  '''

STAFFMONTH = r'''function staffMonth(r){
  const st={};S.staff.forEach(x=>{const sv=S.sal.find(s=>s.id===x.id)||{};st[x.id]={x,salary:+sv.salary||0,rate:+sv.rate||0,pct:+sv.pct||0,paid:0,area:0,rev:0,w:{new:0,washed:0,packed:0,delivered:0}}});
  S.cash.forEach(c=>{if(c.type==='out'&&c.staffId&&st[c.staffId]&&c.t>=r.ma&&c.t<r.mb)st[c.staffId].paid+=+c.amount||0});
  const byName={};S.staff.forEach(x=>byName[x.name]=x.id);
  S.orders.forEach(o=>{const seen={};(o.log||[]).forEach(l=>{const id=l.byId||byName[l.by];if(id&&st[id]&&l.t>=r.ma&&l.t<r.mb&&st[id].w[l.st]!==undefined){st[id].w[l.st]++;
    if(o.status!=='cancelled'&&!seen[id+l.st]){seen[id+l.st]=1;
      if(l.st==='washed')st[id].area+=(o.items||[]).reduce((a,i)=>a+(i.unit==='m2'?(+i.qty||0):0),0);
      if(l.st==='delivered')st[id].rev+=o.total||0}}})});
  Object.values(st).forEach(s=>{s.area=r2(s.area);s.auto=Math.round(s.area*s.rate)+Math.round(s.rev*s.pct/100);s.earn=s.salary+s.auto});
  return Object.values(st).sort((a,b)=>String(a.x.name).localeCompare(String(b.x.name)));
}
'''

OPENSAL = r'''function openSal(id){
  const s=staffMonth(finRange()).find(z=>z.x.id===id);if(!s)return;F={sid:id};const left=Math.max(0,s.earn-s.paid),role=s.x.role;
  const rateF=role==='washer'?`<label class="f">Yuvish haqi, 1 m² uchun so'm<input id="sl-rate" inputmode="numeric" value="${s.rate||''}"></label>`:'';
  const pctF=role==='courier'?`<label class="f">Dostavchi ulushi: yetkazgan zakazlar tushumidan, %<input id="sl-pct" inputmode="decimal" value="${s.pct||''}"></label>`:'';
  const brk=(role==='washer'?finKV(`Yuvilgan ${s.area} m² × ${money(s.rate)}`,money(Math.round(s.area*s.rate))):'')+(role==='courier'?finKV(`Yetkazilgan tushum ${money(s.rev)} × ${s.pct}%`,money(Math.round(s.rev*s.pct/100))):'')+finKV('Belgilangan oylik',money(s.salary))+finKV("<b>Jami hisoblangan</b>",money(s.earn));
  showSheet('sal',esc(s.x.name)+' · oylik',`<div class="meta">${finRange().mlabel}: ${workLine(s.w,s)}. To'landi ${money(s.paid)}.</div><div class="card stack" style="margin-top:8px">${brk}</div>
    ${rateF}${pctF}<label class="f">Belgilangan oylik (ixtiyoriy), so'm<input id="sl-sal" inputmode="numeric" value="${s.salary||''}"></label><button class="btn" data-act="savesal">Saqlash</button>
    <label class="f">To'lov summasi (avans yoki oylik), so'm<input id="sl-pay" inputmode="numeric" value="${left||''}"></label><button class="btn pri" data-act="paysal">To'lovni chiqimga yozish</button><div class="err" id="sl-err"></div>`,'');
}
'''


def patch_html(s):
    # holat va yuklash
    s = rep(s, "cash:[],sal:[],", "cash:[],sal:[],hand:[],")
    s = rep(s, "  ['cash','sal'].forEach(n=>db.collection(n)",
            "  db.collection('hand').onSnapshot(x=>{S.hand=x.docs.map(y=>({id:y.id,...y.data()}));if(S.shown==='app'&&(S.tab==='orders'||S.tab==='dash'))renderBody()},()=>{});\n  ['cash','sal'].forEach(n=>db.collection(n)")
    # yordamchi funksiyalar
    s = rep(s, "const payT=o=>o.paidAt||o.createdAt||0;", "const payT=o=>o.paidAt||o.createdAt||0;" + HELPERS)
    # oylik hisobi
    s = re.sub(r"function staffMonth\(r\)\{.*?\n\}\n(?=const workLine)", lambda m: STAFFMONTH, s, count=1, flags=re.S)
    assert 'S.orders.forEach(o=>{const seen' in s, 'staffMonth almashmadi'
    s = re.sub(r"const workLine=w=>.*?\n", lambda m: "const workLine=(w,s)=>([[w.new,'zakaz oldi'],[w.washed,'yuvdi'],[w.packed,'qadoqladi'],[w.delivered,'yetkazdi']].filter(p=>p[0]).map(p=>p[0]+' ta '+p[1]).join(' · ')||'Bu oyda ish yozuvi yoʻq')+(s&&s.area?' · yuvilgan '+s.area+' m²':'')+(s&&s.rev?' · yetkazilgan tushum '+money(s.rev):'');\n", s, count=1)
    assert "(w,s)=>" in s
    s = s.replace("workLine(s.w)", "workLine(s.w,s)")
    s = rep(s, "Oylik ${s.salary?money(s.salary):'belgilanmagan'} · to'landi ${money(s.paid)}</span><b class=\"sum ${s.salary-s.paid>0?'neg':'pos'}\">${s.salary?(s.salary-s.paid>0?'Qoldi '+money(s.salary-s.paid):\"To'liq to'langan\"):''}</b>",
            "Hisoblangan ${s.earn?money(s.earn):'belgilanmagan'} · to'landi ${money(s.paid)}</span><b class=\"sum ${s.earn-s.paid>0?'neg':'pos'}\">${s.earn?(s.earn-s.paid>0?'Qoldi '+money(s.earn-s.paid):\"To'liq to'langan\"):''}</b>", n=2)
    s = re.sub(r"function openSal\(id\)\{.*?\n\}\n(?=const amt=)", lambda m: OPENSAL, s, count=1, flags=re.S)
    assert "sl-rate" in s, 'openSal almashmadi'
    s = rep(s, "if(await save(db.doc('sal/'+F.sid).set({salary:v}),'Oylik saqlandi'))closeSheet()",
            "const rt=$('#sl-rate')?amt('#sl-rate'):0,pc=$('#sl-pct')?Math.max(0,Math.min(100,num($('#sl-pct').value))):0;if(await save(db.doc('sal/'+F.sid).set({salary:v,rate:rt,pct:pc}),'Saqlandi'))closeSheet()")
    # yetkazishda to'lov oynasi
    s = rep(s, "if(!o)return;b.disabled=true;const id=o.id;\n    const log=[...(o.log||[]),{t:Date.now(),by:S.me.name,st:d.st}];",
            "if(!o)return;if(d.st==='delivered'){openPay(o);return}b.disabled=true;const id=o.id;\n    const log=[...(o.log||[]),{t:Date.now(),by:S.me.name,byId:S.me.id,st:d.st}];")
    s = rep(s, "else if(a==='sal')openSal(d.id);", "else if(a==='sal')openSal(d.id);\n  " + HANDLERS.rstrip() + "\n  ")
    # rahbar «To'landi» tugmasi: qolgan summa tanlangan kassaga yoziladi
    s = rep(s, "paid:!o.paid,paidAt:o.paid?0:Date.now(),kassa:o.paid?'':d.k}",
            "...(o.paid?{paid:false,paidAt:0,kassa:'',pays:{cash:0,card:0},paidSum:0,col:{cash:0,card:0}}:(()=>{const p={...(o.pays||{})};p[d.k]=(+p[d.k]||0)+due(o);return {paid:true,paidAt:Date.now(),kassa:d.k,paidSum:o.total||0,pays:p}})())}")
    # kassa va qarzlar
    s = rep(s, "S.orders.forEach(o=>{if(o.status!=='cancelled'&&o.paid)g(o.kassa).i+=o.total||0});",
            "S.orders.forEach(o=>{if(o.status==='cancelled')return;if(o.pays){Object.keys(o.pays).forEach(k=>{g(k).i+=+o.pays[k]||0})}else if(o.paid)g(o.kassa).i+=o.total||0});")
    s = rep(s, "sum(live.filter(o=>!o.paid))", "live.filter(o=>!o.paid).reduce((x,o)=>x+due(o),0)")
    s = rep(s, "if(!o.paid){c.debt+=o.total||0;c.dn++}", "if(!o.paid){c.debt+=due(o);c.dn++}")
    s = rep(s, "x.sum+=o.total", "x.sum+=due(o)")
    s = rep(s, "tot(ord.filter(o=>!o.paid),o=>o.total)", "tot(ord.filter(o=>!o.paid),o=>due(o))")
    s = rep(s, "tot(c.ord.filter(o=>!o.paid),o=>o.total)", "tot(c.ord.filter(o=>!o.paid),o=>due(o))")
    # zakaz tafsilotida to'lov
    s = rep(s, "<dt>Qabul qildi</dt><dd>${esc(o.byName||'')}</dd>",
            "<dt>Qabul qildi</dt><dd>${esc(o.byName||'')}</dd>${seesMoney()&&o.pays&&Object.keys(o.pays).some(k=>+o.pays[k])?`<dt>To'lov</dt><dd>${Object.keys(o.pays).filter(k=>+o.pays[k]).map(k=>(KAS[k]||k)+' '+money(o.pays[k])).join(' · ')}${o.collectedByName?' · '+esc(o.collectedByName):''}</dd>`:''}")
    # dostavchi ro'yxati tepasida «Qo'limda», rahbar bosh sahifasida dostavchilar puli
    s = rep(s, "function ordersHtml(){\n  if(S.filter==='route')return routeHtml();",
            "function ordersHtml(){return courierBox()+ordersHtml0()}\nfunction ordersHtml0(){\n  if(S.filter==='route')return routeHtml();")
    s = rep(s, "<h2>Zakazlar holati</h2>", "${handHtml()}<h2>Zakazlar holati</h2>")
    return s


def main(dirs):
    for d in dirs:
        hp, sp = os.path.join(d, 'index.html'), os.path.join(d, 'server.py')
        h, sv = open(hp, encoding='utf-8').read(), open(sp, encoding='utf-8').read()
        if MARK in h:
            print(d, ': allaqachon o\'rnatilgan, o\'tkazib yuborildi')
            continue
        nh, ns = patch_html(h), patch_server(sv)
        shutil.copy2(hp, hp + '.bak-pul')
        shutil.copy2(sp, sp + '.bak-pul')
        open(hp, 'w', encoding='utf-8').write(nh)
        open(sp, 'w', encoding='utf-8').write(ns)
        print(d, ': yangilandi')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit('Papka yo\'lini bering: python3 install-pul.py /opt/gilam-crm /opt/fayz-crm')
    main(sys.argv[1:])
