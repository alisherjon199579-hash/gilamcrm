#!/usr/bin/env python3
"""Smena: (1) hisobotda xodim bitta qatorda, ichida oylik soati; (2) sexdan 50 m uzoqlashsa smena avtomat yopiladi.
Avval install-smena.py (yoki install-smena-gps.py) o'rnatilgan bo'lishi kerak.
Ishlatish:  python3 install-smena-auto.py /opt/gilam-crm /opt/fayz-crm"""
import os, shutil, sys

MARK = '/* smena-auto-v1 */'


def rep(s, old, new, n=1):
    c = s.count(old)
    if c != n:
        raise SystemExit('XATO: kutilgan joy topilmadi (%d marta): %r' % (c, old[:70]))
    return s.replace(old, new)


FAR = r'''def _shift_far(data, now, old):
    import math
    r = DB.execute("SELECT data FROM docs WHERE path='shiftloc/main'").fetchone()
    if not r:
        raise Err(400, 'Sex lokatsiyasi belgilanmagan.')
    L = json.loads(r[0])
    try:
        la, ln, ac = float(data.pop('olat')), float(data.pop('olng')), float(data.pop('oacc') or 0)
        A, B = math.radians(la), math.radians(float(L['lat']))
        h = math.sin((B - A) / 2) ** 2 + math.cos(A) * math.cos(B) * math.sin(math.radians(float(L['lng']) - ln) / 2) ** 2
        d = 12742000 * math.asin(math.sqrt(h))
    except Exception:
        raise Err(400, 'Joylashuv aniqlanmadi.')
    if ac > 30 or d <= 50:
        raise Err(400, 'Siz hali sex yaqinidasiz.')
    out = now
    try:
        at = int(data.pop('outAt'))
        if old['in'] <= at <= now:
            out = at
    except Exception:
        pass
    data.clear()
    data.update({'out': out, 'auto': 1, 'odist': round(d, 1)})


'''

OLD_S = """    if op == 'update' and old is not None and old.get('out') == 0 and isinstance(data, dict) and 'out' in data and set(data) <= {'out', 'olat', 'olng', 'oacc'}:
        _shift_geo(data, 'o')
        data['out'] = now
        return"""
NEW_S = """    if op == 'update' and old is not None and old.get('out') == 0 and isinstance(data, dict) and 'out' in data and set(data) <= {'out', 'olat', 'olng', 'oacc', 'auto', 'outAt'}:
        if data.get('auto'):
            data.pop('auto')
            _shift_far(data, now, old)
        else:
            data.pop('auto', None)
            data.pop('outAt', None)
            _shift_geo(data, 'o')
            data['out'] = now
        return"""

JS = r'''
/* smena-auto-v1 */
const _fvh=FVH.shift;
FVH.shift=r=>{
  const head=_fvh(r).split('<h2 style="margin-top:0">Jami ishlagan vaqt</h2>')[0],now=Date.now(),by={};
  S.shift.forEach(s=>{const x=by[s.sid]=by[s.sid]||{sid:s.sid,name:s.name,role:s.role,p:0,pn:0,m:0,on:false},t=Math.max(0,(s.out||now)-s.in);
    if(s.in>=r.a&&s.in<r.b){x.p+=t;x.pn++}if(s.in>=r.ma&&s.in<r.mb)x.m+=t;if(!s.out)x.on=true});
  const L=Object.values(by).filter(x=>x.pn).sort((a,b)=>String(a.name).localeCompare(String(b.name))),same=r.a===r.ma&&r.b===r.mb;
  return head+`<h2 style="margin-top:0">Xodimlar</h2>`+(L.length?`<div class="stack">${L.map(x=>`<button class="card" data-act="shiftman" data-id="${esc(x.sid)}"><div class="row"><b class="grow">${esc(x.name)}</b>${x.on?'<span class="pill p-yes">Ishda</span>':''}<span class="pill r-${esc(x.role)}">${ROLE[x.role]||''}</span></div>
    <div class="row"><span class="meta grow">${r.mlabel}: ishlagan</span><b>${dur(x.m)} · ${r2(x.m/3600000)} s</b></div>${same?'':`<div class="row"><span class="meta grow">Tanlangan davr: ${x.pn} ta smena</span><span>${dur(x.p)}</span></div>`}</button>`).join('')}</div>`:finEmpty("Bu davrda smena yo'q."))
    +`<p class="sub" style="margin-top:12px">Xodimni bossangiz, shu oydagi barcha smenalari chiqadi. Ularning vaqtini to'g'rilash yoki o'chirish mumkin.</p>`};
function openShiftMan(sid){
  const r=finRange(),now=Date.now(),L=S.shift.filter(s=>s.sid===sid&&s.in>=r.ma&&s.in<r.mb).sort((a,b)=>b.in-a.in),ms=L.reduce((a,s)=>a+Math.max(0,(s.out||now)-s.in),0);
  showSheet('shiftman',esc((L[0]||{}).name||'')+' · smenalar',`<div class="card stack"><div class="row"><span class="grow">${r.mlabel}: jami</span><b>${dur(ms)} · ${r2(ms/3600000)} s</b></div><div class="meta">${L.length} ta smena</div></div>
    <div class="stack" style="margin-top:8px">${L.map(s=>`<button class="card" data-act="shiftedit" data-id="${esc(s.id)}"><div class="row"><b class="grow">${dstr(s.in)}</b>${s.auto?'<span class="pill p-wait">avtomat</span>':''}</div><div class="meta">Keldi ${hhmm(s.in)} · Ketdi ${s.out?hhmm(s.out):'<b>hali ishda</b>'}</div><div class="row"><span class="meta grow">Ishlagan vaqt</span><b>${dur(Math.max(0,(s.out||now)-s.in))}</b></div></button>`).join('')}</div>`,'');
}
const mDist=(a,b,c,d)=>{const r=x=>x*Math.PI/180,h=Math.sin(r(c-a)/2)**2+Math.cos(r(a))*Math.cos(r(c))*Math.sin(r(d-b)/2)**2;return 12742000*Math.asin(Math.sqrt(h))};
let wid=null,farN=0,autoBusy=false;
function shiftWatch(){
  const o=myOpen(),L=S.shiftloc;
  if(!o||!L){if(wid!=null){try{navigator.geolocation.clearWatch(wid)}catch(e){}wid=null;farN=0}return}
  if(wid!=null||!navigator.geolocation)return;
  wid=navigator.geolocation.watchPosition(p=>{
    const o=myOpen(),L=S.shiftloc;if(!o||!L||autoBusy)return;
    const c=p.coords,d=mDist(c.latitude,c.longitude,L.lat,L.lng),k='lastin-'+o.id;
    if(d<=50){farN=0;try{localStorage.setItem(k,String(Date.now()))}catch(e){}return}
    if(c.accuracy>30||++farN<2)return;
    autoBusy=true;let li=0;try{li=+localStorage.getItem(k)||0}catch(e){}
    const x={out:Date.now(),auto:1,olat:c.latitude,olng:c.longitude,oacc:c.accuracy};if(li>o.in)x.outAt=li;
    save(db.doc('shift/'+o.id).update(x),'Sexdan uzoqlashdingiz: smena avtomat yopildi').then(ok=>{autoBusy=false;farN=0;if(ok)renderBody()});
  },()=>{},{enableHighAccuracy:true,maximumAge:5000,timeout:30000});
}
setInterval(shiftWatch,5000);
'''


def main(dirs):
    for d in dirs:
        hp, sp = os.path.join(d, 'index.html'), os.path.join(d, 'server.py')
        h, sv = open(hp, encoding='utf-8').read(), open(sp, encoding='utf-8').read()
        if 'shiftloc' not in h:
            raise SystemExit("XATO: %s da avval install-smena.py (yoki install-smena-gps.py) ni o'rnating." % d)
        if MARK in h:
            print(d, ": allaqachon o'rnatilgan, o'tkazib yuborildi")
            continue
        sv = rep(sv, OLD_S, NEW_S)
        sv = rep(sv, "def _shift_guard(me, op, path, data, old):", FAR + "def _shift_guard(me, op, path, data, old):")
        h = rep(h, "function openCashForm(type){", JS.lstrip('\n') + "function openCashForm(type){")
        h = rep(h, "else if(a==='shiftedit')openShift(d.id);", "else if(a==='shiftman')openShiftMan(d.id);\n  else if(a==='shiftedit')openShift(d.id);")
        for p in (hp, sp):
            shutil.copy2(p, p + '.bak-smenaauto')
        open(hp, 'w', encoding='utf-8').write(h)
        open(sp, 'w', encoding='utf-8').write(sv)
        print(d, ': yangilandi')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit("Papka yo'lini bering: python3 install-smena-auto.py /opt/gilam-crm /opt/fayz-crm")
    main(sys.argv[1:])
