#!/usr/bin/env python3
"""Mashina va yoqilg'i: mashinalar ro'yxati, dostavchi yoqilg'i quyganini yozadi, rahbar masofa, sarf (l/100 km) va 1 km narxini ko'radi.
Ishlatish:  python3 install-mashina.py /opt/gilam-crm /opt/fayz-crm
index.html va server.py zaxiralanadi (.bak-mashina)."""
import os, shutil, sys

MARK = '/* mashina-v1 */'


def rep(s, old, new, n=1):
    c = s.count(old)
    if c != n:
        raise SystemExit('XATO: kutilgan joy topilmadi (%d marta): %r' % (c, old[:70]))
    return s.replace(old, new)


GUARD = r'''# ---- mashina-v1: yoqilg'i yozuvlari (dostavchi faqat o'ziga yozadi, vaqtni server qo'yadi) ----
def _car_guard(me, role, op, path, data, old):
    did = path.partition('/')[2]
    if path.startswith('car/') or role != 'courier' or op != 'set' or old is not None or not did.startswith(me + '-') or not isinstance(data, dict):
        raise Err(403, "Ruxsat yo'q.")
    try:
        liters, amount, odo = float(data.get('liters')), float(data.get('amount') or 0), float(data.get('odo') or 0)
    except Exception:
        raise Err(400, "Qiymatlar noto'g'ri.")
    if not (0 < liters <= 500) or not (0 <= amount <= 1e8) or not (0 <= odo <= 5e6):
        raise Err(400, "Qiymatlar noto'g'ri.")
    cid = str(data.get('carId', ''))[:80]
    car = get_doc('car/' + cid)
    if not car:
        raise Err(400, 'Mashina topilmadi.')
    st = staff_all().get(me) or {}
    data.clear()
    data.update({'sid': me, 'name': st.get('name', ''), 'carId': cid, 'carName': car.get('name', ''), 'liters': liters, 'amount': amount, 'odo': odo, 't': int(time.time() * 1000)})


'''

JS = r'''
/* mashina-v1 */
const mfmt=t=>{const d=new Date(t);return dstr(t)+' '+p2(d.getHours())+':'+p2(d.getMinutes())};
const carName=c=>c?esc(c.name)+(c.plate?' · '+esc(c.plate):''):'—';
function rerenderCar(){if(S.shown==='app'&&!sheetKind&&(S.tab===tabsFor()[0]||(S.tab==='fin'&&S.fin.v==='car')))renderBody()}
function carStat(c,a,b){
  const all=S.fuel.filter(f=>f.carId===c.id).sort((x,y)=>x.t-y.t),inP=all.filter(f=>f.t>=a&&f.t<b),base=[...all].reverse().find(f=>f.t<a),seq=base?[base,...inP]:inP;
  const L=inP.reduce((s,f)=>s+(+f.liters||0),0),A=inP.reduce((s,f)=>s+(+f.amount||0),0);let km=0,cons=0,cpk=0,A2=0;
  if(seq.length>=2){const d=(+seq[seq.length-1].odo||0)-(+seq[0].odo||0);if(d>0){km=d;const lit=seq.slice(1).reduce((s,f)=>s+(+f.liters||0),0),amt=seq.slice(1).reduce((s,f)=>s+(+f.amount||0),0);cons=r2(lit/d*100);cpk=Math.round(amt/d);A2=amt}}
  return {n:inP.length,L:r2(L),A,km,cons,cpk,A2};
}
FV.car={n:"Mashinalar va yoqilg'i",s:"Yoqilg'i, yurgan masofa va sarfi",c:'accent',m:['month'],i:'<path d="M5 16V8l2-3h10l2 3v8"/><circle cx="8" cy="17" r="1.5"/><circle cx="16" cy="17" r="1.5"/><path d="M5 11h14"/>'};
FVH.car=r=>{
  const rows=S.car.filter(c=>c.active!==false).map(c=>({c,s:carStat(c,r.a,r.b)})).sort((x,y)=>String(x.c.name).localeCompare(String(y.c.name))),
    T=rows.reduce((o,x)=>({L:o.L+x.s.L,A:o.A+x.s.A,km:o.km+x.s.km,A2:o.A2+x.s.A2}),{L:0,A:0,km:0,A2:0}),logs=S.fuel.filter(f=>f.t>=r.a&&f.t<r.b).sort((x,y)=>y.t-x.t);
  return `<div class="tiles"><div class="tile"><small>Yoqilg'i</small><b>${r2(T.L)} l</b></div><div class="tile"><small>Xarajat</small><b class="neg">${money(T.A)}</b></div><div class="tile"><small>Yurgan masofa</small><b>${T.km} km</b></div><div class="tile"><small>1 km narxi</small><b>${T.km?money(Math.round(T.A2/T.km)):'—'}</b></div></div>
  <div class="row" style="margin-top:12px"><button class="btn pri grow" data-act="fuelnew">+ Yoqilg'i</button><button class="btn grow" data-act="caradd">+ Mashina</button></div>
  <h2>Mashinalar</h2>${rows.length?`<div class="stack">${rows.map(x=>`<button class="card" data-act="carman" data-id="${esc(x.c.id)}"><div class="row"><b class="grow">${carName(x.c)}</b><span class="meta">${esc(x.c.driverName||'')}</span></div><div class="row"><span class="meta grow">${x.s.n} marta · ${x.s.L} l</span><b>${money(x.s.A)}</b></div><div class="meta">${x.s.km?`${x.s.km} km · ${x.s.cons} l/100 km · 1 km = ${money(x.s.cpk)}`:"Masofa uchun kamida 2 ta quyish va spidometr kerak"}</div></button>`).join('')}</div>`:finEmpty("Hali mashina qo'shilmagan.")}
  <h2>Quyishlar</h2>${logs.length?`<div class="stack">${logs.map(f=>`<button class="card" data-act="fueledit" data-id="${esc(f.id)}"><div class="row"><b class="grow">${esc(f.carName||'')}</b><b>${money(f.amount)}</b></div><div class="meta">${mfmt(f.t)} · ${r2(f.liters)} l${f.odo?' · '+f.odo+' km':''} · ${esc(f.name||'')}</div></button>`).join('')}</div>`:finEmpty("Bu oyda quyish yozilmagan.")}
  <p class="sub" style="margin-top:12px">Sarf va 1 km narxi spidometr ko'rsatkichlari orasidagi farqdan hisoblanadi (to'liq bak usuli).</p>`};
function openCar(id){
  const c=id?S.car.find(x=>x.id===id):null,dr=S.staff.filter(x=>x.role==='courier'&&x.active!==false);F={carid:id||''};
  showSheet('car',c?esc(c.name):'Yangi mashina',`<label class="f">Nomi (masalan: Damas)<input id="cr-n" value="${c?esc(c.name):''}"></label><label class="f">Davlat raqami<input id="cr-p" value="${c?esc(c.plate||''):''}"></label>
    <label class="f">Haydovchi<select id="cr-d"><option value="">Biriktirilmagan</option>${dr.map(x=>`<option value="${esc(x.id)}" ${c&&c.driverId===x.id?'selected':''}>${esc(x.name)}</option>`).join('')}</select></label><div class="err" id="cr-err"></div>`,
    `<button class="btn pri grow" data-act="carsave">Saqlash</button>${c?`<button class="btn bad" data-act="cardel" data-sure="0">O'chirish</button>`:''}`);
}
function openCarMan(id){
  const c=S.car.find(x=>x.id===id);if(!c)return;const r=finRange(),s=carStat(c,r.ma,r.mb),logs=S.fuel.filter(f=>f.carId===id).sort((x,y)=>y.t-x.t).slice(0,30);
  showSheet('carman',esc(c.name),`<div class="card stack">${finKV(r.mlabel+": quyildi",s.L+' l · '+s.n+' marta')}${finKV('Xarajat',money(s.A))}${finKV('Yurgan masofa',s.km?s.km+' km':'—')}${finKV('Sarf',s.km?s.cons+' l/100 km':'—')}${finKV('1 km narxi',s.km?money(s.cpk):'—')}</div>
    <div class="meta" style="margin-top:6px">${c.plate?esc(c.plate)+' · ':''}${c.driverName?'Haydovchi: '+esc(c.driverName):'Haydovchi biriktirilmagan'}</div>
    <h2>Oxirgi quyishlar</h2>${logs.length?`<div class="stack">${logs.map(f=>`<button class="card" data-act="fueledit" data-id="${esc(f.id)}"><div class="row"><span class="grow meta">${mfmt(f.t)} · ${r2(f.liters)} l${f.odo?' · '+f.odo+' km':''}</span><b>${money(f.amount)}</b></div></button>`).join('')}</div>`:'<div class="empty">Hali quyilmagan.</div>'}`,
    `<button class="btn pri grow" data-act="fuelnew" data-car="${esc(id)}">+ Yoqilg'i</button><button class="btn grow" data-act="caredit" data-id="${esc(id)}">Tahrirlash</button>`);
}
function lastOdo(cid,exId){const l=S.fuel.filter(x=>x.carId===cid&&x.id!==exId).sort((a,b)=>b.t-a.t)[0];return l?+l.odo||0:0}
function openFuel(id,carId){
  const f=id?S.fuel.find(x=>x.id===id):null,adm=S.me.role==='admin',cars=S.car.filter(c=>c.active!==false);
  if(!cars.length){toast(adm?"Avval mashina qo'shing.":"Mashina qo'shilmagan. Rahbarga ayting.");return}
  const def=f?f.carId:(carId||(cars.find(c=>c.driverId===S.me.id)||cars[0]).id),td=new Date(f?f.t:Date.now()),iso=td.getFullYear()+'-'+p2(td.getMonth()+1)+'-'+p2(td.getDate());F={fid:id||''};
  showSheet('fuel',f?'Quyishni tahrirlash':"Yoqilg'i quydim",`<label class="f">Mashina<select id="fu-c">${cars.map(c=>`<option value="${esc(c.id)}" ${c.id===def?'selected':''}>${esc(c.name)}${c.plate?' · '+esc(c.plate):''}</option>`).join('')}</select></label>
    <label class="f">Necha litr<input id="fu-l" inputmode="decimal" value="${f?f.liters:''}"></label><label class="f">Summasi, so'm<input id="fu-a" inputmode="numeric" value="${f?f.amount:''}"></label>
    <label class="f">Spidometr ko'rsatkichi, km<input id="fu-o" inputmode="numeric" value="${f?f.odo:''}" placeholder="oxirgisi: ${lastOdo(def,id)} km"></label>
    ${adm?`<label class="f">Sana<input id="fu-d" type="date" value="${iso}" max="${iso}"></label>${f?'':`<label class="f" style="flex-direction:row;gap:8px;align-items:center"><input type="checkbox" id="fu-k" checked style="width:auto">Kassadan chiqim sifatida yozish</label>`}`:''}<div class="err" id="fu-err"></div>`,
    `<button class="btn pri grow" data-act="fuelsave">Saqlash</button>${f&&adm?`<button class="btn bad" data-act="fueldel" data-sure="0">O'chirish</button>`:''}`);
}
function carBox(){
  if(!S.me||S.me.role!=='courier'||S.tab!==tabsFor()[0]||!S.car.length)return'';
  const m=S.fuel.filter(f=>f.sid===S.me.id).sort((a,b)=>b.t-a.t)[0];
  return `<div class="card stack" style="margin-bottom:12px"><div class="row"><b class="grow">Mashina</b>${m?`<span class="meta">Oxirgi quyish: ${mfmt(m.t)} · ${r2(m.liters)} l</span>`:''}</div><button class="btn wide" data-act="fuelnew">Yoqilg'i quydim</button></div>`;
}
'''

HANDLERS = r'''else if(a==='caradd')openCar('');
  else if(a==='caredit')openCar(d.id);
  else if(a==='carman')openCarMan(d.id);
  else if(a==='carsave'){const n=$('#cr-n').value.trim(),p=$('#cr-p').value.trim(),dv=$('#cr-d').value,st=S.staff.find(x=>x.id===dv);
    if(!n){$('#cr-err').textContent='Mashina nomini kiriting.';return}
    if(await save(db.doc('car/'+(F.carid||('car'+Date.now().toString(36)))).set({name:n,plate:p,driverId:dv,driverName:st?st.name:'',active:true}),'Saqlandi'))(closeSheet(),rerenderCar())}
  else if(a==='cardel'){if(!sure(b))return;if(await save(db.doc('car/'+F.carid).delete(),"Mashina o'chirildi"))(closeSheet(),rerenderCar())}
  else if(a==='fuelnew')openFuel('',d.car);
  else if(a==='fueledit'){if(S.me.role==='admin')openFuel(d.id)}
  else if(a==='fuelsave'){const cid=$('#fu-c').value,c=S.car.find(x=>x.id===cid),lt=num($('#fu-l').value),am=amt('#fu-a'),od=amt('#fu-o'),adm=S.me.role==='admin',E=$('#fu-err');
    if(!c){E.textContent='Mashinani tanlang.';return}
    if(!(lt>0)){E.textContent='Necha litr quyilganini kiriting.';return}
    if(!(od>0)){E.textContent="Spidometr ko'rsatkichini (km) kiriting.";return}
    if(!F.fid&&od<lastOdo(cid)){E.textContent="Spidometr oldingisidan ("+lastOdo(cid)+" km) kam bo'lmasin.";return}
    const dv=adm&&$('#fu-d')?$('#fu-d').value:'',now=new Date(),isT=!dv||dv===now.getFullYear()+'-'+p2(now.getMonth()+1)+'-'+p2(now.getDate()),t=isT?Date.now():new Date(dv+'T12:00:00').getTime();b.disabled=true;
    if(F.fid){if(await save(db.doc('fuel/'+F.fid).update({carId:cid,carName:c.name,liters:lt,amount:am,odo:od,t:isT?S.fuel.find(x=>x.id===F.fid).t:t}),'Saqlandi'))(closeSheet(),rerenderCar());else b.disabled=false;return}
    const k=adm&&$('#fu-k')&&$('#fu-k').checked&&am>0,cid2=k?'fuel-'+t:'';
    if(await save(db.doc('fuel/'+S.me.id+'-'+t).set({sid:S.me.id,name:S.me.name,carId:cid,carName:c.name,liters:lt,amount:am,odo:od,t,cashId:cid2}),"Yoqilg'i yozildi")){
      if(k)await save(db.doc('cash/'+cid2).set({type:'out',amount:am,cat:"Yoqilg'i",kassa:'cash',note:c.name+' '+lt+' l',t,staffId:'',staffName:'',byName:S.me.name}));(closeSheet(),rerenderCar())}else b.disabled=false}
  else if(a==='fueldel'){if(!sure(b))return;const f=S.fuel.find(x=>x.id===F.fid);if(await save(db.doc('fuel/'+F.fid).delete(),"Yozuv o'chirildi")){if(f&&f.cashId)await save(db.doc('cash/'+f.cashId).delete());(closeSheet(),rerenderCar())}}
  else if(a==='delcash'){'''


def patch_server(s):
    s = rep(s, "SERVER_ONLY = ('tg', 'cfg')", "COLLS = COLLS + ('car', 'fuel')\nSERVER_ONLY = ('tg', 'cfg')")
    s = rep(s, "FLOW = {'washer'", "for _r in ('courier', 'washer', 'packer'):\n    READ[_r] = READ[_r] + ('car', 'fuel')\nFLOW = {'washer'")
    s = rep(s, "                        if role != 'admin' and p.startswith('staff/'):",
            "                        if role != 'admin' and p.startswith('fuel/') and d.get('sid') != me:\n                            continue\n                        if role != 'admin' and p.startswith('staff/'):")
    s = rep(s, "def check_write(me, role, op, path, data, old):\n",
            GUARD + "def check_write(me, role, op, path, data, old):\n"
            "    if (path.startswith('car/') or path.startswith('fuel/')) and role != 'admin':\n"
            "        return _car_guard(me, role, op, path, data, old)\n")
    return s


def patch_html(s):
    s = rep(s, "cash:[],sal:[],", "cash:[],sal:[],car:[],fuel:[],")
    s = rep(s, "  ['cash','sal'].forEach(n=>db.collection(n)",
            "  db.collection('car').onSnapshot(x=>{S.car=x.docs.map(y=>({id:y.id,...y.data()}));rerenderCar()},()=>{});\n"
            "  db.collection('fuel').onSnapshot(x=>{S.fuel=x.docs.map(y=>({id:y.id,...y.data()}));rerenderCar()},()=>{});\n"
            "  ['cash','sal'].forEach(n=>db.collection(n)")
    s = rep(s, "function openCashForm(type){", JS.lstrip('\n') + "function openCashForm(type){")
    s = rep(s, "({dash:dashHtml,orders:ordersHtml", "carBox()+({dash:dashHtml,orders:ordersHtml")
    s = rep(s, "else if(a==='delcash'){", HANDLERS)
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
            shutil.copy2(p, p + '.bak-mashina')
        open(hp, 'w', encoding='utf-8').write(nh)
        open(sp, 'w', encoding='utf-8').write(ns)
        print(d, ': yangilandi')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit("Papka yo'lini bering: python3 install-mashina.py /opt/gilam-crm /opt/fayz-crm")
    main(sys.argv[1:])
