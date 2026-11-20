#!/usr/bin/env python3
"""Joylar lug'ati: qishloq/mahalla nomi -> xaritadagi nuqta. Manzilda shu nom bo'lsa, zakaz xaritada va marshrutda o'sha nuqtada ko'rinadi.
Ishlatish:  python3 install-joylar.py /opt/gilam-crm /opt/fayz-crm   (avval install-xarita va install-marshrut o'rnatilgan bo'lsin)
index.html va server.py zaxiralanadi (.bak-joylar)."""
import os, shutil, sys

MARK = '/* joylar-v1 */'


def rep(s, old, new, n=1):
    c = s.count(old)
    if c != n:
        raise SystemExit('XATO: kutilgan joy topilmadi (%d marta): %r' % (c, old[:70]))
    return s.replace(old, new)


JS = r'''
/* joylar-v1 */
function pnrm(s){return String(s||'').toLowerCase().replace(/[ʻʼ’‘`´']/g,"'").replace(/\s+/g,' ').trim()}
function placePos(o){const k=pnrm(o&&o.address);if(!k||!S.place.length)return null;let b=null;
  S.place.forEach(p=>{const n=pnrm(p.name);if(n.length>=2&&p.lat&&k.includes(n)&&(!b||n.length>pnrm(b.name).length))b=p});return b?[b.lat,b.lng]:null}
function placeLL(v){v=String(v||'');const m=v.match(/!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)/)||v.match(/@(-?\d+\.\d+),(-?\d+\.\d+)/)||v.match(/(-?\d{1,2}\.\d{3,})\s*[,;\s]\s*(-?\d{1,3}\.\d{3,})/);
  if(m){const a=+m[1],b=+m[2];if(a>35&&a<46&&b>54&&b<75)return[a,b]}return null}
FV.place={n:"Joylar lug'ati",s:"Qishloq nomi bo'yicha xaritadagi nuqta",c:'info',i:'<path d="M12 21s7-5.6 7-11a7 7 0 10-14 0c0 5.4 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/>'};
FVH.place=()=>{const l=[...S.place].sort((a,b)=>String(a.name).localeCompare(String(b.name)));
  return `<button class="btn pri wide" data-act="placeadd">+ Joy qo'shish</button><p class="sub" style="margin-top:12px">Manzilda shu nom bo'lsa (masalan, «Tavariyon»), zakaz xaritada va dostavchi marshrutida shu nuqtada ko'rinadi.</p>
  ${l.length?`<div class="stack">${l.map(p=>`<button class="card" data-act="placeedit" data-id="${esc(p.id)}"><div class="row"><b class="grow">${esc(p.name)}</b><span class="meta">${r2(p.lat)}, ${r2(p.lng)}</span></div></button>`).join('')}</div>`:finEmpty("Hali joy qo'shilmagan.")}`};
function openPlace(id,name){const p=id?S.place.find(x=>x.id===id):null;F={pid:id||''};
  showSheet('place',p?esc(p.name):"Yangi joy",`<label class="f">Joy nomi (manzilda shunday yozilgan bo'lsin)<input id="pl-n" value="${esc(p?p.name:(name||''))}"></label>
   <label class="f">Google Maps havolasi yoki koordinata<input id="pl-v" value="${p?p.lat+', '+p.lng:''}" placeholder="41.123456, 64.123456"></label>
   <button class="btn wide" data-act="placegps">Turgan joyimni olish</button><div class="err" id="pl-err"></div>`,
   `<button class="btn pri grow" data-act="placesave">Saqlash</button>${p?`<button class="btn bad" data-act="placedel" data-sure="0">O'chirish</button>`:''}`)}
'''

HANDLERS = r'''else if(a==='placeadd')openPlace('',d.n||'');
  else if(a==='placeedit')openPlace(d.id);
  else if(a==='placegps'){if(!navigator.geolocation){$('#pl-err').textContent='Telefon joylashuvni bermadi.';return}b.disabled=true;
    navigator.geolocation.getCurrentPosition(p=>{b.disabled=false;$('#pl-v').value=p.coords.latitude.toFixed(6)+', '+p.coords.longitude.toFixed(6)},()=>{b.disabled=false;$('#pl-err').textContent='Joylashuvni olib bo\'lmadi. Ruxsat bering.'},{enableHighAccuracy:true,timeout:15000})}
  else if(a==='placesave'){const n=$('#pl-n').value.trim(),v=$('#pl-v').value.trim(),E=$('#pl-err');let c=placeLL(v);
    if(n.length<2){E.textContent='Joy nomini kiriting.';return}
    if(!c&&/^https?:\/\//i.test(v)){b.disabled=true;b.textContent='Havola tekshirilmoqda…';try{const j=await(await fetch('/api/resolveloc?u='+encodeURIComponent(v),{credentials:'same-origin'})).json();if(j.ok)c=[j.lat,j.lng]}catch(e){}b.disabled=false;b.textContent='Saqlash'}
    if(!c){E.textContent="Koordinata topilmadi. Havolani yoki «41.12, 64.12» ko'rinishida yozing.";return}
    if(S.place.some(x=>x.id!==F.pid&&pnrm(x.name)===pnrm(n))){E.textContent='Bu nom allaqachon bor.';return}
    b.disabled=true;if(await save(db.doc('place/'+(F.pid||('p'+Date.now().toString(36)))).set({name:n,lat:c[0],lng:c[1]}),'Saqlandi')){closeSheet();if(S.shown==='app')renderBody()}else b.disabled=false}
  else if(a==='placedel'){if(!sure(b))return;if(await save(db.doc('place/'+F.pid).delete(),"Joy o'chirildi")){closeSheet();if(S.shown==='app')renderBody()}}
  else if(a==='delcash'){'''


def patch_server(s):
    s = rep(s, "SERVER_ONLY = ('tg', 'cfg')", "COLLS = COLLS + ('place',)\nSERVER_ONLY = ('tg', 'cfg')")
    s = rep(s, "FLOW = {'washer'", "for _r in ('courier', 'washer', 'packer'):\n    READ[_r] = READ[_r] + ('place',)\nFLOW = {'washer'")
    return s


def patch_html(s):
    s = rep(s, "cash:[],sal:[],", "cash:[],sal:[],place:[],")
    s = rep(s, "  ['cash','sal'].forEach(n=>db.collection(n)",
            "  db.collection('place').onSnapshot(x=>{S.place=x.docs.map(y=>({id:y.id,...y.data()}));if(S.shown==='app'&&!sheetKind&&(S.tab==='dash'||S.tab==='fin'&&S.fin.v==='place'))renderBody()},()=>{});\n"
            "  ['cash','sal'].forEach(n=>db.collection(n)")
    s = rep(s, "function openCashForm(type){", JS.lstrip('\n') + "function openCashForm(type){")
    s = rep(s, "else if(a==='delcash'){", HANDLERS)
    # xarita: lug'at birinchi, geokoder faqat lug'atda topilmasa
    s = rep(s, "var k=nrm(o.address);if(!k)return null;var g=G[k];return g&&g.lat?[g.lat,g.lng]:null}",
            "var pp=placePos(o);if(pp)return pp;var k=nrm(o.address);if(!k)return null;var g=G[k];return g&&g.lat?[g.lat,g.lng]:null}")
    s = rep(s, "function geoAsk(o){var k=nrm(o.address);if(!k||(k in G))return;", "function geoAsk(o){var k=nrm(o.address);if(!k||(k in G)||placePos(o))return;")
    s = rep(s, "o.address?' ('+esc(o.address)+')':' (manzil yo‘q)')",
            "o.address?' ('+esc(o.address)+') <button class=\"btn sm\" data-act=\"placeadd\" data-n=\"'+esc(o.address)+'\">+ joy</button>':' (manzil yo‘q)')")
    # marshrut
    s = rep(s, "if(!c&&o.address){c=GEOX.get(o.address);ap=!!c}", "if(!c){c=placePos(o);ap=!!c}if(!c&&o.address){c=GEOX.get(o.address);ap=!!c}")
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
            shutil.copy2(p, p + '.bak-joylar')
        open(hp, 'w', encoding='utf-8').write(nh)
        open(sp, 'w', encoding='utf-8').write(ns)
        print(d, ': yangilandi')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit("Papka yo'lini bering: python3 install-joylar.py /opt/gilam-crm /opt/fayz-crm")
    main(sys.argv[1:])
