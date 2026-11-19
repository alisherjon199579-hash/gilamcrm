#!/usr/bin/env python3
"""Dostavchi marshruti: dostavchiga «Marshrut» bo'limi qaytariladi; lokatsiyasi yo'q zakazlar manzili bo'yicha xaritaga qo'yiladi.
Avval install-xarita.py o'rnatilgan bo'lishi kerak (manzilni nuqtaga aylantirish shu yerda).
Ishlatish:  python3 install-marshrut.py /opt/gilam-crm /opt/fayz-crm
index.html zaxiralanadi (.bak-marshrut)."""
import os, shutil, sys

MARK = '/* marshrut-v1 */'


def rep(s, old, new, n=1):
    c = s.count(old)
    if c != n:
        raise SystemExit('XATO: kutilgan joy topilmadi (%d marta): %r' % (c, old[:70]))
    return s.replace(old, new)


GEOX = r'''/* marshrut-v1 */
const GEOX={m:{},q:[],busy:false,
  key:a=>String(a||'').toLowerCase().replace(/[ʻʼ’‘`´']/g,"'").replace(/\s+/g,' ').trim(),
  get(a){const k=this.key(a);if(!k)return null;const v=this.m[k];if(v&&v.lat)return[v.lat,v.lng];if(!(k in this.m)){this.m[k]=undefined;this.q.push({k,a});this.next()}return null},
  next(){if(this.busy||!this.q.length)return;const it=this.q.shift();this.busy=true;
    const done=(v,ttl)=>{this.m[it.k]=v;if(v===0)setTimeout(()=>{delete this.m[it.k]},ttl);this.busy=false;if(S.shown==='app'&&S.tab==='orders'&&S.filter==='route'&&!sheetKind)renderBody();this.next()};
    fetch('/api/geocode?q='+encodeURIComponent(it.a),{credentials:'same-origin'}).then(r=>r.ok?r.json():null).then(d=>{if(d&&d.ok)done({lat:d.lat,lng:d.lng});else done(0,d&&d.none?900000:60000)}).catch(()=>done(0,60000))}};
'''


def patch_html(s):
    s = rep(s, "chips.push(['pickup','Olinishi kerak'],['queue','Yetkazilishi kerak']);if(S.filter!=='pickup'&&S.filter!=='queue')S.filter='pickup'}",
            "chips.push(['pickup','Olinishi kerak'],['queue','Yetkazilishi kerak'],['route','Marshrut']);if(S.filter!=='pickup'&&S.filter!=='queue'&&S.filter!=='route')S.filter='pickup'}")
    s = rep(s, "function routeStops(){", GEOX + "function routeStops(){")
    s = rep(s, "let c=null;for(const l of ls){c=coordOf(l.v);if(c)break}return {o,c,pick:isPick(o),d:null}",
            "let c=null,ap=false;for(const l of ls){c=coordOf(l.v);if(c)break}if(!c&&o.address){c=GEOX.get(o.address);ap=!!c}return {o,c,pick:isPick(o),d:null,ap}")
    s = rep(s, "rel=\"noopener\">Xarita</a>", "rel=\"noopener\">${s.ap?'Xarita (taxminiy)':'Xarita'}</a>")
    return s


def main(dirs):
    for d in dirs:
        hp, sp = os.path.join(d, 'index.html'), os.path.join(d, 'server.py')
        h = open(hp, encoding='utf-8').read()
        if '/api/geocode' not in open(sp, encoding='utf-8').read():
            raise SystemExit("XATO: %s da avval install-xarita.py ni o'rnating." % d)
        if MARK in h:
            print(d, ": allaqachon o'rnatilgan, o'tkazib yuborildi")
            continue
        nh = patch_html(h)
        shutil.copy2(hp, hp + '.bak-marshrut')
        open(hp, 'w', encoding='utf-8').write(nh)
        print(d, ': yangilandi')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit("Papka yo'lini bering: python3 install-marshrut.py /opt/gilam-crm /opt/fayz-crm")
    main(sys.argv[1:])
