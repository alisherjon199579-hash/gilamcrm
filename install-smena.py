#!/usr/bin/env python3
"""Smenalar: «Keldim» / «Ishdan chiqdim» tugmalari, kelgan-ketgan vaqt va ishlagan soat.
Ishlatish:  python3 install-smena.py /opt/gilam-crm /opt/fayz-crm
index.html va server.py zaxiralanadi (.bak-smena)."""
import os, shutil, sys

MARK = '/* smena-v1 */'


def rep(s, old, new, n=1):
    c = s.count(old)
    if c != n:
        raise SystemExit('XATO: kutilgan joy topilmadi (%d marta): %r' % (c, old[:70]))
    return s.replace(old, new)


GUARD = r'''# ---- smena-v1: xodim o'z smenasini ochadi/yopadi; vaqtni server qo'yadi ----
def _shift_geo(data, k):
    import math
    r = DB.execute("SELECT data FROM docs WHERE path='shiftloc/main'").fetchone()
    for x in ('lat', 'lng', 'acc'):
        v = data.pop(k + x, None)
        if x == 'lat': la = v
        elif x == 'lng': ln = v
        else: ac = v
    if not r:
        return
    L = json.loads(r[0])
    rad = float(L.get('r') or 5)
    try:
        la, ln, ac = float(la), float(ln), float(ac or 0)
        A, B = math.radians(la), math.radians(float(L['lat']))
        h = math.sin((B - A) / 2) ** 2 + math.cos(A) * math.cos(B) * math.sin(math.radians(float(L['lng']) - ln) / 2) ** 2
        d = 12742000 * math.asin(math.sqrt(h))
    except Exception:
        raise Err(400, "Joylashuv aniqlanmadi. Telefonda lokatsiyani yoqing va ruxsat bering.")
    if ac > max(30, rad * 3):
        raise Err(400, "GPS aniqligi past (%d m). Ochiq joyga chiqib, qayta urining." % ac)
    if d > rad:
        raise Err(400, "Siz sexdan %d m uzoqdasiz. Faqat sexda (%g m ichida) bosish mumkin." % (d, rad))
    data[k + 'dist'] = round(d, 1)


def _shift_guard(me, op, path, data, old):
    did = path.partition('/')[2]
    if not did.startswith(me + '-'):
        raise Err(403, "Ruxsat yo'q.")
    now = int(time.time() * 1000)
    if op == 'set' and old is None and isinstance(data, dict):
        _shift_geo(data, '')
        for p, d in DB.execute('SELECT path,data FROM docs WHERE path LIKE ? ORDER BY ver DESC LIMIT 30', ('shift/' + me + '-%',)):
            if json.loads(d).get('out') == 0:
                raise Err(400, 'Smena allaqachon ochiq.')
        st = staff_all().get(me) or {}
        geo = {k: data[k] for k in ('dist',) if k in data}
        data.clear()
        data.update({'sid': me, 'name': st.get('name', ''), 'role': st.get('role', ''), 'in': now, 'out': 0})
        data.update(geo)
        return
    if op == 'update' and old is not None and old.get('out') == 0 and isinstance(data, dict) and 'out' in data and set(data) <= {'out', 'olat', 'olng', 'oacc'}:
        _shift_geo(data, 'o')
        data['out'] = now
        return
    raise Err(403, "Ruxsat yo'q.")


'''

SYNC_OLD = "                        d = json.loads(d)\n                        if role != 'admin' and p.startswith('staff/'):"
SYNC_NEW = ("                        d = json.loads(d)\n"
            "                        if role != 'admin' and p.startswith('shift/') and d.get('sid') != me:\n"
            "                            continue\n"
            "                        if role != 'admin' and p.startswith('staff/'):")


def patch_server(s):
    s = rep(s, "SERVER_ONLY = ('tg', 'cfg')", "COLLS = COLLS + ('shift', 'shiftloc')\nSERVER_ONLY = ('tg', 'cfg')")
    s = rep(s, "FLOW = {'washer'", "for _r in ('courier', 'washer', 'packer'):\n    READ[_r] = READ[_r] + ('shift', 'shiftloc')\nFLOW = {'washer'")
    s = rep(s, SYNC_OLD, SYNC_NEW)
    s = rep(s, "def check_write(me, role, op, path, data, old):\n",
            GUARD + "def check_write(me, role, op, path, data, old):\n"
            "    if path.startswith('shiftloc/') and role != 'admin':\n        raise Err(403, \"Ruxsat yo'q.\")\n"
            "    if path.startswith('shift/') and role != 'admin':\n"
            "        return _shift_guard(me, op, path, data, old)\n")
    return s


JS = r'''
/* smena-v1 */
const hhmm=t=>{const d=new Date(t);return p2(d.getHours())+':'+p2(d.getMinutes())};
const dur=ms=>{const m=Math.max(0,Math.round(ms/60000));return Math.floor(m/60)+' soat '+p2(m%60)+' daq'};
const dtl=t=>{const d=new Date(t);return d.getFullYear()+'-'+p2(d.getMonth()+1)+'-'+p2(d.getDate())+'T'+p2(d.getHours())+':'+p2(d.getMinutes())};
const myOpen=()=>S.me&&S.shift.find(s=>s.sid===S.me.id&&!s.out);
const getPos=()=>new Promise((ok,no)=>{if(!navigator.geolocation)return no('Brauzer lokatsiyani qo\'llamaydi.');navigator.geolocation.getCurrentPosition(p=>ok(p.coords),e=>no(e.code===1?"Lokatsiyaga ruxsat bering (telefon sozlamalari).":"Joylashuv aniqlanmadi. Ochiq joyda qayta urining."),{enableHighAccuracy:true,timeout:20000,maximumAge:0})});
const geoOf=async()=>{if(!S.shiftloc)return{};const c=await getPos();return{lat:c.latitude,lng:c.longitude,acc:c.accuracy}};
function shiftBox(){
  if(!S.me||S.tab!==tabsFor()[0])return'';
  const o=myOpen(),d0=dayStart(),done=S.shift.filter(s=>s.sid===S.me.id&&s.out&&(s.in||0)>=d0).sort((a,b)=>a.in-b.in),tot=done.reduce((a,s)=>a+s.out-s.in,0);
  return `<div class="card stack" style="margin-bottom:12px"><div class="row"><b class="grow">Smena</b><span class="pill ${o?'p-yes':'p-wait'}">${o?'Ishda':'Ishda emas'}</span></div>
    ${o?`<div class="meta">Keldi: <b>${hhmm(o.in)}</b> · Ishlayapti: <b id="shift-t">${dur(Date.now()-o.in)}</b></div>`:`<div class="meta">Sexga kelganingizda «Keldim» tugmasini bosing.</div>`}
    ${done.map(s=>`<div class="meta">${hhmm(s.in)} – ${hhmm(s.out)} · ${dur(s.out-s.in)}</div>`).join('')}${done.length?`<div class="meta">Bugun jami: <b>${dur(tot)}</b></div>`:''}
    <button class="btn ${o?'bad':'pri'} wide" data-act="${o?'shiftout':'shiftin'}">${o?'Ishdan chiqdim':'Keldim'}</button></div>`;
}
setInterval(()=>{const e=document.getElementById('shift-t'),o=myOpen();if(e&&o)e.textContent=dur(Date.now()-o.in)},20000);
FV.shift={n:'Smenalar',s:'Kelgan va ketgan vaqt, ishlagan soat',c:'info',m:['day','month'],i:'<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>'};
FVH.shift=r=>{
  const now=Date.now(),L=S.shift.filter(s=>(s.in||0)>=r.a&&(s.in||0)<r.b).sort((x,y)=>y.in-x.in),by={},on=S.shift.filter(s=>!s.out);
  L.forEach(s=>{const x=by[s.sid]=by[s.sid]||{name:s.name,n:0,ms:0};x.n++;x.ms+=(s.out||now)-s.in});
  const L0=S.shiftloc;
  return `<div class="card stack" style="margin-bottom:12px"><div class="row"><b class="grow">Sex lokatsiyasi</b><span class="pill ${L0?'p-yes':'p-wait'}">${L0?'Belgilangan':'Belgilanmagan'}</span></div>
    <div class="meta">${L0?`${L0.lat.toFixed(5)}, ${L0.lng.toFixed(5)} · ruxsat: ${L0.r} m ichida`:"Belgilanmaguncha «Keldim/Ishdan chiqdim» istalgan joyda bosiladi."}</div>
    <label class="f">Xarita havolasi yoki koordinata<input id="sl-v" placeholder="39.77123, 64.42345 yoki Google Maps havolasi"></label>
    <label class="f">Ruxsat etilgan masofa (metr)<input id="sl-r" type="number" min="3" value="${L0?L0.r:5}"></label><div class="err" id="sl-err"></div>
    <div class="row"><button class="btn pri grow" data-act="slset">Saqlash</button><button class="btn grow" data-act="slhere">Hozirgi joyim</button></div></div>
  ${on.length?`<div class="card stack" style="margin-bottom:12px"><b>Hozir ishda · ${on.length} ta</b>${on.map(s=>`<div class="row"><span class="grow">${esc(s.name)}</span><span class="meta">${hhmm(s.in)} dan · ${dur(now-s.in)}</span></div>`).join('')}</div>`:''}
  <h2 style="margin-top:0">Jami ishlagan vaqt</h2>${Object.keys(by).length?`<div class="card stack">${Object.values(by).sort((x,y)=>String(x.name).localeCompare(String(y.name))).map(x=>finKV(`${esc(x.name)} <span class="meta">${x.n} ta smena</span>`,dur(x.ms)+' · '+r2(x.ms/3600000)+' s')).join('')}</div>`:finEmpty("Bu davrda smena yo'q.")}
  <h2>Smenalar</h2>${L.length?`<div class="stack">${L.map(s=>`<button class="card" data-act="shiftedit" data-id="${esc(s.id)}"><div class="row"><b class="grow">${esc(s.name)}</b><span class="pill r-${esc(s.role)}">${ROLE[s.role]||''}</span></div><div class="meta">${dstr(s.in)} · Keldi ${hhmm(s.in)} · Ketdi ${s.out?hhmm(s.out):'<b>hali ishda</b>'}</div><div class="row"><span class="meta grow">Ishlagan vaqt</span><b>${dur((s.out||now)-s.in)}</b></div></button>`).join('')}</div>`:finEmpty("Bu davrda smena yo'q.")}
  <p class="sub" style="margin-top:12px">Smenani bossangiz, vaqtini to'g'rilash yoki o'chirish mumkin (masalan, xodim «Ishdan chiqdim» ni bosishni unutgan bo'lsa).</p>`};
function openShift(id){
  const s=S.shift.find(x=>x.id===id);if(!s)return;F={shid:id};
  showSheet('shift',esc(s.name)+' · smena',`<label class="f">Keldi<input type="datetime-local" id="sh-in" value="${dtl(s.in)}"></label><label class="f">Ketdi (bo'sh qoldirsangiz, hali ishda)<input type="datetime-local" id="sh-out" value="${s.out?dtl(s.out):''}"></label><div class="err" id="sh-err"></div>`,
    `<button class="btn pri grow" data-act="saveshift">Saqlash</button><button class="btn bad" data-act="delshift" data-sure="0">O'chirish</button>`);
}
'''

HANDLERS = r'''else if(a==='shiftin'){if(myOpen())return;b.disabled=true;const t=Date.now(),tx=b.textContent;b.textContent='Joylashuv tekshirilmoqda…';
    let g;try{g=await geoOf()}catch(e){toast(e);b.disabled=false;b.textContent=tx;return}
    if(await save(db.doc('shift/'+S.me.id+'-'+t).set({sid:S.me.id,name:S.me.name,role:S.me.role,in:t,out:0,...g}),'Ish boshlandi'))renderBody();else{b.disabled=false;b.textContent=tx}}
  else if(a==='shiftout'){const o=myOpen();if(!o)return;
    if(b.dataset.c!=='1'){b.dataset.c='1';b.textContent='Tasdiqlash uchun yana bosing';setTimeout(()=>{if(b.isConnected){b.dataset.c='0';b.textContent='Ishdan chiqdim'}},3500);return}
    b.disabled=true;b.textContent='Joylashuv tekshirilmoqda…';let g;try{g=await geoOf()}catch(e){toast(e);b.disabled=false;b.textContent='Ishdan chiqdim';return}
    const o2=g.lat!=null?{olat:g.lat,olng:g.lng,oacc:g.acc}:{};
    if(await save(db.doc('shift/'+o.id).update({out:Date.now(),...o2}),'Ish tugadi'))renderBody();else{b.disabled=false;b.textContent='Ishdan chiqdim'}}
  else if(a==='slset'){const c=coordOf($('#sl-v').value),r=+$('#sl-r').value;if(!c||!(r>=3)){$('#sl-err').textContent="Koordinata (masalan 39.77123, 64.42345) va masofa (kamida 3 m) kiriting.";return}
    if(await save(db.doc('shiftloc/main').set({lat:c[0],lng:c[1],r}),'Sex lokatsiyasi saqlandi'))renderBody()}
  else if(a==='slhere'){const r=+$('#sl-r').value||5;let g;try{g=await getPos()}catch(e){toast(e);return}
    if(await save(db.doc('shiftloc/main').set({lat:g.latitude,lng:g.longitude,r}),'Hozirgi joy sex sifatida saqlandi'))renderBody()}
  else if(a==='shiftedit')openShift(d.id);
  else if(a==='saveshift'){const i=new Date($('#sh-in').value).getTime(),ov=$('#sh-out').value,o=ov?new Date(ov).getTime():0;
    if(!isFinite(i)||(ov&&(!isFinite(o)||o<=i))){$('#sh-err').textContent="Vaqtni to'g'ri kiriting (ketish kelishdan keyin bo'lsin).";return}
    if(await save(db.doc('shift/'+F.shid).update({in:i,out:o}),'Smena saqlandi'))closeSheet()}
  else if(a==='delshift'){if(!sure(b))return;if(await save(db.doc('shift/'+F.shid).delete(),"Smena o'chirildi"))closeSheet()}
  '''


def patch_html(s):
    s = rep(s, "cash:[],sal:[],", "cash:[],sal:[],shift:[],")
    s = rep(s, "  ['cash','sal'].forEach(n=>db.collection(n)",
            "  db.collection('shiftloc').onSnapshot(x=>{S.shiftloc=(x.docs.find(y=>y.id==='main')||{data:()=>null}).data();if(S.shown==='app'&&!sheetKind&&S.tab==='fin'&&S.fin.v==='shift'&&!document.activeElement.matches('input'))renderBody()},()=>{});\n  db.collection('shift').onSnapshot(x=>{S.shift=x.docs.map(y=>({id:y.id,...y.data()}));if(S.shown==='app'&&!sheetKind&&(S.tab===tabsFor()[0]||(S.tab==='fin'&&S.fin.v==='shift')))renderBody()},()=>{});\n  ['cash','sal'].forEach(n=>db.collection(n)")
    s = rep(s, "function openCashForm(type){", JS + "function openCashForm(type){")
    s = rep(s, "b.innerHTML=({dash:dashHtml,orders:ordersHtml,clients:clientsHtml,fin:finHtml,staff:staffHtml,prices:pricesHtml})[S.tab]()}",
            "b.innerHTML=shiftBox()+({dash:dashHtml,orders:ordersHtml,clients:clientsHtml,fin:finHtml,staff:staffHtml,prices:pricesHtml})[S.tab]()}")
    s = rep(s, "else if(a==='sal')openSal(d.id);", "else if(a==='sal')openSal(d.id);\n  " + HANDLERS.rstrip() + "\n  ")
    return s


def main(dirs):
    for d in dirs:
        hp, sp = os.path.join(d, 'index.html'), os.path.join(d, 'server.py')
        h, sv = open(hp, encoding='utf-8').read(), open(sp, encoding='utf-8').read()
        if MARK in h:
            print(d, ": allaqachon o'rnatilgan, o'tkazib yuborildi")
            continue
        nh, ns = patch_html(h), patch_server(sv)
        for p in (hp, sp):
            shutil.copy2(p, p + '.bak-smena')
        open(hp, 'w', encoding='utf-8').write(nh)
        open(sp, 'w', encoding='utf-8').write(ns)
        print(d, ': yangilandi')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit("Papka yo'lini bering: python3 install-smena.py /opt/gilam-crm /opt/fayz-crm")
    main(sys.argv[1:])
