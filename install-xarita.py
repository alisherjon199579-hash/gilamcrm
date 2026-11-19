#!/usr/bin/env python3
"""Xarita: bugungi zakazlar manzili bo'yicha xaritada belgilanadi (rahbar bosh sahifasi).
Ishlatish:  python3 install-xarita.py /opt/gilam-crm /opt/fayz-crm
index.html va server.py zaxiralanadi (.bak-xarita)."""
import os, shutil, sys

MARK = '/* xarita-v1 */'


def rep(s, old, new, n=1):
    c = s.count(old)
    if c != n:
        raise SystemExit('XATO: kutilgan joy topilmadi (%d marta): %r' % (c, old[:70]))
    return s.replace(old, new)


SERVER_CODE = r'''# ---- xarita-v1: manzilni xaritadagi nuqtaga aylantirish ----
import re as _re
GEO_URL = os.environ.get('GEO_URL', 'https://nominatim.openstreetmap.org/search')
GEO_BOX = '62.0,41.9,65.8,38.9'  # Buxoro viloyati (chap, yuqori, o'ng, past)
GEO_LOCK = threading.Lock()
GEO_LAST = [0.0]
GEO_STOP = ('tumani', 'tuman', 'shahri', 'shahar', 'viloyati', 'mahallasi', 'mahalla', 'mfy', 'qishlogi', 'qishloq',
            'kochasi', 'kocha', 'uy', 'dom', 'xonadon', 'mavze', 'mikrorayon', 'kvartal', 'qavat')


def _geo_conn():
    c = sqlite3.connect(os.path.join(DATA, 'crm.db'), timeout=10)
    c.execute('CREATE TABLE IF NOT EXISTS geo_cache(q TEXT PRIMARY KEY, lat REAL, lng REAL, name TEXT, t INTEGER)')
    return c


def _geo_norm(s):
    s = str(s or '').lower()
    for ch in "ʻʼ’‘`´":
        s = s.replace(ch, "'")
    return ' '.join(s.split())[:160]


def _geo_cands(q):
    """Manzildan qidiriladigan bo'laklar: butun matn va vergul bilan ajratilgan qismlar."""
    q = _geo_norm(q)
    out = []
    for p in [q] + _re.split(r'[,;\n]', q):
        w = [x for x in _re.sub(r"[^\w' -]", ' ', p).split() if x.replace("'", '') not in GEO_STOP and not _re.match(r'^\d', x)]
        t = ' '.join(w).strip()
        if len(t) >= 3 and t not in out:
            out.append(t)
    return out[:5]


def _geo_variants(c):
    base = c.replace("'", '')
    out = [base]
    if "'" in c:
        out.append(c.replace("'", 'ʻ'))
    sw = {'a': 'o', 'o': 'a'}
    for i, ch in enumerate(base):
        if ch in sw:
            v = base[:i] + sw[ch] + base[i + 1:]
            if v not in out:
                out.append(v)
        if len(out) >= 8:
            break
    return out


def _geo_fetch(q):
    import urllib.request, urllib.parse
    with GEO_LOCK:
        wait = 1.1 - (time.time() - GEO_LAST[0])
        if wait > 0:
            time.sleep(wait)
        GEO_LAST[0] = time.time()
        url = GEO_URL + '?' + urllib.parse.urlencode({'format': 'jsonv2', 'limit': 1, 'countrycodes': 'uz', 'viewbox': GEO_BOX,
                                                      'bounded': 1, 'accept-language': 'uz', 'q': q})
        req = urllib.request.Request(url, headers={'User-Agent': 'GilamCRM/1.0 (gilam yuvish CRM)'})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode('utf-8'))


def _geo_find(q):
    """(lat, lng, nom) | None | 'net'. Eng aniq (kichik) joy tanlanadi: qishloq tumandan ustun."""
    best, neterr, used = None, False, 0
    for cand in _geo_cands(q):
        for v in _geo_variants(cand):
            if used >= 16:
                break
            used += 1
            try:
                data = _geo_fetch(v)
            except Exception:
                neterr = True
                break
            if data:
                it = data[0]
                rank = int(it.get('place_rank') or 0)
                if best is None or rank > best[0]:
                    best = (rank, float(it['lat']), float(it['lon']), str(it.get('display_name') or '')[:120])
                break
    if best:
        return best[1], best[2], best[3]
    return 'net' if neterr else None


def _geo(h, u):
    import urllib.parse
    q = _geo_norm(urllib.parse.parse_qs(u.query).get('q', [''])[0])
    if len(q) < 2:
        return h.send(400, {'error': "Manzil yo'q."})
    c = _geo_conn()
    try:
        r = c.execute('SELECT lat,lng,name,t FROM geo_cache WHERE q=?', (q,)).fetchone()
    finally:
        c.close()
    now = int(time.time())
    if r and (r[0] is not None or now - r[3] < 43200):
        return h.send(200, {'ok': True, 'lat': r[0], 'lng': r[1], 'name': r[2]} if r[0] is not None else {'ok': False, 'none': True})
    res = _geo_find(q)
    if res == 'net':
        return h.send(200, {'ok': False, 'err': 'net'})
    c = _geo_conn()
    try:
        if res:
            c.execute('INSERT OR REPLACE INTO geo_cache(q,lat,lng,name,t) VALUES(?,?,?,?,?)', (q, res[0], res[1], res[2], now))
        else:
            c.execute('INSERT OR REPLACE INTO geo_cache(q,lat,lng,name,t) VALUES(?,NULL,NULL,NULL,?)', (q, now))
        c.commit()
    finally:
        c.close()
    return h.send(200, {'ok': True, 'lat': res[0], 'lng': res[1], 'name': res[2]} if res else {'ok': False, 'none': True})


'''

ROUTE = '''            if u.path == '/api/geocode':
                with LOCK:
                    _me, _s = self.auth()
                if not _me:
                    return self.send(401, {'error': 'Tizimga kiring.'})
                return _geo(self, u)
            with LOCK:
                if u.path == '/api/app/loc':'''

JS = r'''  /* xarita-v1 */
  var omode='today',olayers=[],osig='',G={},gq=[],gbusy=false,ofit=false;
  function nrm(s){return String(s||'').toLowerCase().replace(/[ʻʼ’‘`´']/g,"'").replace(/\s+/g,' ').trim()}
  function parseLL(v){v=String(v||'');var m=v.match(/!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)/)||v.match(/(-?\d{1,2}\.\d{3,})\s*[,;\s]\s*(-?\d{1,3}\.\d{3,})/);
    if(m){var a=+m[1],b=+m[2];if(a>35&&a<46&&b>54&&b<75)return[a,b]}return null}
  function ordPos(o){
    try{var pts=(typeof allLocs==='function'?allLocs():[]).filter(function(p){return p.oid===o.id});(o.locs||[]).forEach(function(p){pts.push(p)});
      pts.sort(function(x,y){return (y.t||0)-(x.t||0)});for(var i=0;i<pts.length;i++){var ll=parseLL(pts[i].v);if(ll)return ll}}catch(e){}
    var k=nrm(o.address);if(!k)return null;var g=G[k];return g&&g.lat?[g.lat,g.lng]:null}
  function ordList(){var d0=dayStart();
    return S.orders.filter(function(o){if(o.status==='cancelled')return false;return omode==='today'?(o.createdAt||0)>=d0:o.status!=='delivered'})}
  function geoAsk(o){var k=nrm(o.address);if(!k||(k in G))return;G[k]=undefined;gq.push({k:k,raw:o.address});geoNext()}
  function geoDone(k,v){G[k]=v;if(v===0)setTimeout(function(){delete G[k]},v===0?900000:0)}
  function geoNext(){if(gbusy||!gq.length)return;var it=gq.shift();gbusy=true;
    fetch('/api/geocode?q='+encodeURIComponent(it.raw),{credentials:'same-origin'}).then(function(r){return r.ok?r.json():null}).then(function(d){
      if(d&&d.ok)G[it.k]={lat:d.lat,lng:d.lng,name:d.name};else if(d&&d.none)geoDone(it.k,0);else{G[it.k]=0;setTimeout(function(){delete G[it.k]},60000)}
    }).catch(function(){G[it.k]=0;setTimeout(function(){delete G[it.k]},60000)}).then(function(){gbusy=false;osig='';geoNext()})}
  function ordColor(o){return (typeof isPick==='function'&&isPick(o))?'#d97706':o.status==='packed'?'#16a34a':o.status==='delivered'?'#6b7280':'#2563eb'}
  function ordTick(){var l=ordList(),sig=omode;
    l.forEach(function(o){geoAsk(o);var p=ordPos(o);sig+='|'+o.id+':'+o.status+':'+(p?p[0].toFixed(4)+','+p[1].toFixed(4):'-')});
    if(sig===osig)return;osig=sig;drawOrders(l)}
  function drawOrders(list){
    olayers.forEach(function(x){map.removeLayer(x)});olayers=[];
    var seen={},pts=[],miss=[],wait=0;
    list.forEach(function(o){var p=ordPos(o);
      if(!p){var k=nrm(o.address);if(!k||G[k]===0)miss.push(o);else wait++;return}
      var key=p[0].toFixed(3)+','+p[1].toFixed(3),n=seen[key]=(seen[key]||0)+1,ang=n*2.4,r=n>1?0.0012*Math.sqrt(n):0;
      var ll=[p[0]+r*Math.sin(ang),p[1]+r*Math.cos(ang)*1.3];pts.push(ll);
      var col=ordColor(o),ic=L.divIcon({className:'',html:'<div style="width:34px;height:34px;border-radius:50%;background:'+col+';color:#fff;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4);font:700 11px/30px system-ui,sans-serif;text-align:center">'+esc(o.no)+'</div>',iconSize:[34,34],iconAnchor:[17,17]});
      olayers.push(L.marker(ll,{icon:ic}).addTo(map).bindPopup('<b>&#8470;'+esc(o.no)+'</b> &middot; '+esc(o.name||'')+'<br>'+esc(o.phone||'')+'<br>'+esc(o.address||'')+'<br><i>'+esc((typeof ST!=='undefined'&&ST[o.status])||'')+'</i>'))});
    var el=wrap.querySelector('#ordlist');
    if(el)el.innerHTML='<div><span style="color:#d97706">&#9679;</span> olinishi kerak &nbsp;<span style="color:#2563eb">&#9679;</span> jarayonda &nbsp;<span style="color:#16a34a">&#9679;</span> yetkazishga tayyor &nbsp;<span style="color:#6b7280">&#9679;</span> yetkazilgan</div>'
      +'<div><b>'+pts.length+' ta zakaz</b> xaritada'+(wait?' &middot; '+wait+' ta manzil qidirilmoqda&hellip;':'')+'</div>'
      +(miss.length?'<div style="color:#b45309">Joyi topilmadi: '+miss.map(function(o){return '&#8470;'+esc(o.no)+(o.address?' ('+esc(o.address)+')':' (manzil yo‘q)')}).join(', ')+'</div>':'');
    ['today','active'].forEach(function(m){var b=wrap.querySelector('[data-om="'+m+'"]');if(b){b.style.background=omode===m?'#0a6f79':'#e5e7eb';b.style.color=omode===m?'#fff':'#111827'}});
    if(!ofit&&pts.length){ofit=true;if(!fitted){fitted=true;if(pts.length>1)map.fitBounds(pts,{padding:[40,40],maxZoom:14});else map.setView(pts[0],14)}}}
'''


def patch_server(s):
    s = rep(s, "# ---- ruxsatlar (perms) v1 ----", SERVER_CODE + "# ---- ruxsatlar (perms) v1 ----")
    s = rep(s, "            with LOCK:\n                if u.path == '/api/app/loc':", ROUTE)
    return s


def patch_html(s):
    s = rep(s, "var wrap,map,data,layers=[],fitted=false,lastFetch=0,queue=null;", "var wrap,map,data,layers=[],fitted=false,lastFetch=0,queue=null;")
    s = rep(s, """'<div style="font-weight:700;margin-bottom:8px">Dostavchiklar xaritada</div>'""",
            """'<div style="display:flex;align-items:center;gap:6px;margin-bottom:8px;flex-wrap:wrap"><b style="flex:1;min-width:150px">Dostavchilar va zakazlar xaritada</b><button type="button" data-om="today" style="border:0;border-radius:999px;padding:6px 12px;font-weight:600">Bugungi</button><button type="button" data-om="active" style="border:0;border-radius:999px;padding:6px 12px;font-weight:600">Faol zakazlar</button></div>'""")
    s = rep(s, """+'<div id="applivelist" style="margin-top:8px;font-size:14px;line-height:1.6"></div>'}""",
            """+'<div id="applivelist" style="margin-top:8px;font-size:14px;line-height:1.6"></div>'
      +'<div id="ordlist" style="margin-top:8px;font-size:13.5px;line-height:1.6;border-top:1px solid #e5e7eb;padding-top:8px"></div>';
    wrap.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('[data-om]');if(b){omode=b.getAttribute('data-om');ofit=false;osig='';if(map)ordTick()}})}""")
    s = rep(s, "  function tick(){try{\n    var b=document.getElementById('body');", JS + "  function tick(){try{\n    var b=document.getElementById('body');")
    s = rep(s, "    if(Date.now()-lastFetch>15000){lastFetch=Date.now();", "    if(map)ordTick();\n    if(Date.now()-lastFetch>15000){lastFetch=Date.now();")
    return s


def main(dirs):
    for d in dirs:
        hp, sp = os.path.join(d, 'index.html'), os.path.join(d, 'server.py')
        h, sv = open(hp, encoding='utf-8').read(), open(sp, encoding='utf-8').read()
        if MARK in h:
            print(d, ": allaqachon o'rnatilgan, o'tkazib yuborildi")
            continue
        nh, ns = patch_html(h), patch_server(sv)
        shutil.copy2(hp, hp + '.bak-xarita')
        shutil.copy2(sp, sp + '.bak-xarita')
        open(hp, 'w', encoding='utf-8').write(nh)
        open(sp, 'w', encoding='utf-8').write(ns)
        print(d, ': yangilandi')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit("Papka yo'lini bering: python3 install-xarita.py /opt/gilam-crm /opt/fayz-crm")
    main(sys.argv[1:])
