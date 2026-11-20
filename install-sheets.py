#!/usr/bin/env python3
"""Google Sheets: zakazlar, mijozlar bazasi, kassa, smenalar va oylik hisobot jadvalga avtomat yuboriladi.
Ishlatish:  python3 install-sheets.py /opt/gilam-crm /opt/fayz-crm
index.html va server.py zaxiralanadi (.bak-sheets)."""
import os, shutil, sys

MARK = '/* sheets-v1 */'


def rep(s, old, new, n=1):
    c = s.count(old)
    if c != n:
        raise SystemExit('XATO: kutilgan joy topilmadi (%d marta): %r' % (c, old[:70]))
    return s.replace(old, new)


SERVER = r'''# ---- sheets-v1: CRM ma'lumotlarini Google Sheets (Apps Script) ga yuborish ----
GS_ST = {'new': 'Yangi', 'washing': 'Yuvishda', 'washed': 'Yuvildi', 'packed': 'Qadoqlandi', 'delivered': 'Yetkazildi', 'cancelled': 'Bekor qilindi'}
GS_ROLE = {'admin': 'Rahbar', 'courier': 'Dostavchik', 'washer': 'Yuvuvchi', 'packer': 'Qadoqlovchi'}
GS_SCRIPT = r"""var SECRET='__SECRET__';
function doPost(e){
  var out=function(o){return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON)};
  try{
    var d=JSON.parse(e.postData.contents);
    if(d.secret!==SECRET)return out({ok:false,error:'Maxfiy kalit mos emas'});
    var ss=SpreadsheetApp.getActiveSpreadsheet();
    Object.keys(d.sheets).forEach(function(n){
      var t=d.sheets[n],sh=ss.getSheetByName(n)||ss.insertSheet(n),rows=[t.head].concat(t.rows),w=t.head.length;
      sh.clear();
      (t.text||[]).forEach(function(c){sh.getRange(1,c+1,rows.length,1).setNumberFormat('@')});
      sh.getRange(1,1,rows.length,w).setValues(rows);
      sh.setFrozenRows(1);
      sh.getRange(1,1,1,w).setFontWeight('bold').setBackground('#dff3ef');
      sh.autoResizeColumns(1,w);
    });
    var f=ss.getSheets()[0];
    if(ss.getSheets().length>1&&f.getLastRow()==0&&/^(Sheet1|Varaq1|Лист1|Sheet 1)$/.test(f.getName()))ss.deleteSheet(f);
    return out({ok:true});
  }catch(err){return out({ok:false,error:String(err)})}
}"""


def _gs_fmt(ms):
    import datetime
    try:
        return datetime.datetime.fromtimestamp(float(ms) / 1000, datetime.timezone(datetime.timedelta(hours=5))).strftime('%Y-%m-%d %H:%M')
    except Exception:
        return ''


def _gs_num(v):
    try:
        return float(v or 0)
    except Exception:
        return 0.0


def _gs_key(ph):
    return ''.join(c for c in str(ph or '') if c.isdigit())[-9:]


def _gs_build():
    G = {}
    for coll in ('orders', 'clients', 'cash', 'shift', 'staff'):
        G[coll] = [json.loads(d) for (d,) in DB.execute('SELECT data FROM docs WHERE coll=?', (coll,))]
    now = int(time.time() * 1000)
    orders = sorted(G['orders'], key=lambda o: -_gs_num(o.get('createdAt')))
    zr, cl, months = [], {}, {}
    for c in G['clients']:
        k = _gs_key(c.get('phone')) or str(c.get('name', ''))
        cl[k] = {'name': c.get('name', ''), 'phone': c.get('phone', ''), 'addr': c.get('address', ''), 'n': 0, 'sum': 0.0, 'debt': 0.0, 'last': 0}
    for o in orders:
        total = _gs_num(o.get('total'))
        cancelled = o.get('status') == 'cancelled'
        p = o.get('pays')
        cash = card = 0.0
        if isinstance(p, dict):
            cash, card = _gs_num(p.get('cash')), _gs_num(p.get('card'))
        elif o.get('paid'):
            if o.get('kassa') == 'card':
                card = total
            else:
                cash = total
        paid = cash + card
        debt = 0.0 if cancelled else max(0.0, total - paid)
        its = o.get('items') or []
        area = sum(_gs_num(i.get('qty')) for i in its if i.get('unit') == 'm2')
        cnt = sum(_gs_num(i.get('count')) for i in its)
        zr.append([o.get('no', ''), _gs_fmt(o.get('createdAt')), o.get('name', ''), o.get('phone', ''), o.get('address', ''), GS_ST.get(o.get('status'), o.get('status', '')),
                   cnt, round(area, 2), ', '.join(str(i.get('name', '')) for i in its), total, cash, card, debt, o.get('assignedName', ''), o.get('byName', ''), o.get('note', '')])
        k = _gs_key(o.get('phone')) or str(o.get('name', ''))
        c = cl.setdefault(k, {'name': o.get('name', ''), 'phone': o.get('phone', ''), 'addr': o.get('address', ''), 'n': 0, 'sum': 0.0, 'debt': 0.0, 'last': 0})
        if not cancelled:
            c['n'] += 1
            c['sum'] += total
            c['debt'] += debt
            c['last'] = max(c['last'], _gs_num(o.get('createdAt')))
            m = months.setdefault(_gs_fmt(o.get('createdAt'))[:7], {'n': 0, 'sum': 0.0, 'paid': 0.0, 'debt': 0.0, 'in': 0.0, 'out': 0.0})
            m['n'] += 1
            m['sum'] += total
            m['paid'] += paid
            m['debt'] += debt
    kr = []
    for x in sorted(G['cash'], key=lambda x: -_gs_num(x.get('t'))):
        kr.append([_gs_fmt(x.get('t')), 'Kirim' if x.get('type') == 'in' else 'Chiqim', _gs_num(x.get('amount')), x.get('cat', ''), x.get('kassa', ''), x.get('staffName', ''), x.get('note', ''), x.get('byName', '')])
        m = months.setdefault(_gs_fmt(x.get('t'))[:7], {'n': 0, 'sum': 0.0, 'paid': 0.0, 'debt': 0.0, 'in': 0.0, 'out': 0.0})
        m['in' if x.get('type') == 'in' else 'out'] += _gs_num(x.get('amount'))
    sr, hrs = [], {}
    for s in sorted(G['shift'], key=lambda s: -_gs_num(s.get('in'))):
        h = round(max(0.0, (_gs_num(s.get('out')) or now) - _gs_num(s.get('in'))) / 3600000.0, 2)
        sr.append([s.get('name', ''), GS_ROLE.get(s.get('role'), ''), _gs_fmt(s.get('in'))[:10], _gs_fmt(s.get('in'))[11:], _gs_fmt(s.get('out'))[11:] if s.get('out') else 'hali ishda', h, 'ha' if s.get('auto') else ''])
        key = (_gs_fmt(s.get('in'))[:7], s.get('name', ''), GS_ROLE.get(s.get('role'), ''))
        v = hrs.setdefault(key, [0, 0.0])
        v[0] += 1
        v[1] += h
    mr = [[k, v['n'], v['sum'], v['paid'], v['debt'], v['in'], v['out'], v['paid'] + v['in'] - v['out']] for k, v in sorted(months.items(), reverse=True)]
    hr = [[k[0], k[1], k[2], v[0], round(v[1], 2)] for k, v in sorted(hrs.items(), key=lambda kv: (kv[0][0], kv[0][1]), reverse=True)]
    cr = [[v['name'], v['phone'], v['addr'], v['n'], v['sum'], v['debt'], _gs_fmt(v['last'])[:10] if v['last'] else ''] for v in sorted(cl.values(), key=lambda v: -v['sum'])]
    return {
        'Zakazlar': {'head': ['№', 'Sana', 'Mijoz', 'Telefon', 'Manzil', 'Holat', 'Gilam soni', 'Maydon m²', 'Xizmatlar', 'Jami', 'Naqd', 'Karta', 'Qarz', 'Dostavchi', 'Qabul qildi', 'Izoh'], 'rows': zr, 'text': [3]},
        'Mijozlar': {'head': ['Mijoz', 'Telefon', 'Manzil', 'Zakazlar soni', 'Jami summa', 'Qarz', 'Oxirgi zakaz'], 'rows': cr, 'text': [1]},
        'Kassa': {'head': ['Sana', 'Tur', 'Summa', 'Kategoriya', 'Kassa', 'Xodim', 'Izoh', 'Kiritdi'], 'rows': kr, 'text': []},
        'Oylar': {'head': ['Oy', 'Zakazlar soni', 'Zakazlar summasi', "To'langan", 'Qarz', 'Boshqa kirim', 'Chiqim', "Sof (to'langan + kirim - chiqim)"], 'rows': mr, 'text': [0]},
        'Smenalar': {'head': ['Xodim', 'Lavozim', 'Sana', 'Keldi', 'Ketdi', 'Soat', 'Avtomat'], 'rows': sr, 'text': [2, 3, 4]},
        'Soat (oylik)': {'head': ['Oy', 'Xodim', 'Lavozim', 'Smenalar soni', 'Ishlagan soat'], 'rows': hr, 'text': [0]},
    }


def _gs_push(force):
    import urllib.request
    with LOCK:
        url, sec = meta('gs_url'), meta('gs_secret')
        if not url:
            return {'ok': False, 'error': 'Ulanmagan'}
        sheets = _gs_build()
        h = hashlib.sha1(json.dumps(sheets, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
        if not force and meta('gs_hash') == h:
            return {'ok': True, 'same': True}
    body = json.dumps({'secret': sec, 'sheets': sheets}, ensure_ascii=False).encode('utf-8')
    ok, err = False, ''
    try:
        req = urllib.request.Request(url, data=body, headers={'Content-Type': 'text/plain;charset=utf-8'})
        with urllib.request.urlopen(req, timeout=90) as r:
            txt = r.read().decode('utf-8', 'ignore')
        try:
            res = json.loads(txt)
            ok, err = bool(res.get('ok')), str(res.get('error', ''))[:160]
        except Exception:
            err = "Google javobi tushunarsiz. Joylashtirishda «Kim kirishi mumkin» = «Hamma» ekanini tekshiring."
    except Exception as e:
        err = str(e)[:160]
    with LOCK:
        set_meta('gs_last', int(time.time() * 1000))
        set_meta('gs_status', 'ok' if ok else (err or 'xato'))
        if ok:
            set_meta('gs_hash', h)
    return {'ok': ok, 'error': err}


def _gs_api(d):
    act = d.get('act')
    with LOCK:
        if not meta('gs_secret'):
            set_meta('gs_secret', secrets.token_urlsafe(18))
        if act == 'set':
            url = str(d.get('url', '')).strip()
            if not (url.startswith('https://script.google.com/') or (os.environ.get('GS_TEST') and url.startswith('http://127.0.0.1'))):
                raise Err(400, "Havola https://script.google.com/ bilan boshlanishi kerak.")
            set_meta('gs_url', url)
            set_meta('gs_hash', '')
        elif act == 'off':
            set_meta('gs_url', '')
            set_meta('gs_status', '')
    if act in ('set', 'push'):
        r = _gs_push(True)
        if not r.get('ok'):
            raise Err(400, r.get('error') or 'Yuborib bo\'lmadi.')
    with LOCK:
        return {'ok': True, 'url': bool(meta('gs_url')), 'last': int(meta('gs_last') or 0), 'status': meta('gs_status') or '', 'script': GS_SCRIPT.replace('__SECRET__', meta('gs_secret'))}


def _gs_loop():
    time.sleep(60)
    while True:
        try:
            with LOCK:
                on = bool(meta('gs_url'))
            if on:
                _gs_push(False)
        except Exception as e:
            sys.stderr.write('gsheet: %r\n' % (e,))
        time.sleep(600)


'''

ROUTE = '''            if u.path == '/api/gsheet':
                with LOCK:
                    _me, _s = self.auth()
                if not _me:
                    return self.send(401, {'error': 'login'})
                if (_s or {}).get('role') != 'admin':
                    raise Err(403, "Ruxsat yo'q.")
                return self.send(200, _gs_api(d))
            with LOCK:
                if u.path == '/api/login':'''

JS = r'''
/* sheets-v1 */
const GS={loaded:false,busy:false,d:{}};
const gsApi=(act,x)=>fetch('/api/gsheet',{method:'POST',headers:{'X-CRM':'1','Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({act,...(x||{})})}).then(r=>r.json().then(j=>{if(!r.ok)throw new Error(j.error||'Xato');return j}));
async function gsLoad(){if(GS.busy)return;GS.busy=true;try{GS.d=await gsApi('get');GS.loaded=true}catch(e){GS.d={err:String(e.message||e)};GS.loaded=true}GS.busy=false;if(S.shown==='app'&&S.tab==='fin'&&S.fin.v==='gsheet'&&!document.activeElement.matches('input'))renderBody()}
FV.gsheet={n:'Google Sheets',s:'Zakazlar, mijozlar va hisobotlar jadvalga avtomat yuboriladi',c:'info',i:'<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M4 10h16M4 15h16M10 4v16"/>'};
FVH.gsheet=r=>{
  if(!GS.loaded){gsLoad();return '<div class="empty">Yuklanmoqda…</div>'}
  const d=GS.d;if(d.err)return `<div class="card stack"><div class="err">${esc(d.err)}</div><button class="btn" data-act="gsreload">Qayta urinish</button></div>`;
  const st=d.status&&d.status!=='ok'?`<div class="err">${esc(d.status)}</div>`:'';
  return `<div class="card stack"><div class="row"><b class="grow">Holat</b><span class="pill ${d.url&&d.status==='ok'?'p-yes':'p-wait'}">${d.url?(d.status==='ok'?'Ulangan':'Xato'):'Ulanmagan'}</span></div>
    ${d.url?`<div class="meta">Oxirgi yuborish: ${d.last?hhmm(d.last)+' · '+dstr(d.last):'—'}. Har 10 daqiqada o'zgarish bo'lsa avtomat yuboriladi.</div>${st}<button class="btn pri wide" data-act="gspush">Hozir yuborish</button><button class="btn wide" data-act="gsoff" data-sure="0">Uzish</button>`:`<div class="meta">Quyidagi qadamlarni bajaring.</div>`}</div>
  <h2>${d.url?'Qayta ulash':'Ulash'}</h2><div class="card stack">
    <div class="meta"><b>1.</b> Google Sheets'da yangi bo'sh jadval oching (sheets.new).</div>
    <div class="meta"><b>2.</b> Yuqorida «Kengaytmalar» → «Apps Script» ni bosing.</div>
    <div class="meta"><b>3.</b> U yerdagi hamma kodni o'chirib, quyidagini joylang:</div>
    <textarea id="gs-code" readonly rows="6" style="width:100%;font:12px/1.3 monospace">${esc(d.script||'')}</textarea><button class="btn" data-act="gscopy">Kodni nusxalash</button>
    <div class="meta"><b>4.</b> «Joylashtirish» → «Yangi joylashtirish» → turi «Veb-ilova». «Kim kirishi mumkin» = <b>Hamma</b>. Ruxsat bering (Advanced → Go to ... ).</div>
    <div class="meta"><b>5.</b> Chiqqan «Veb-ilova URL» havolasini shu yerga qo'ying:</div>
    <input id="gs-url" placeholder="https://script.google.com/macros/s/.../exec"><div class="err" id="gs-err"></div><button class="btn pri wide" data-act="gssave">Ulash va yuborish</button></div>
  <h2>Jadvalda nimalar bo'ladi</h2><div class="card stack"><div class="meta">Zakazlar · Mijozlar (jami summa va qarz bilan) · Kassa (kirim/chiqim) · Oylar (oylik hisobot) · Smenalar · Soat (oylik).</div></div>`};
'''

HANDLERS = r'''else if(a==='gsreload'){GS.loaded=false;renderBody()}
  else if(a==='gscopy'){const t=$('#gs-code');try{await navigator.clipboard.writeText(t.value)}catch(e){t.select();document.execCommand('copy')}toast('Kod nusxalandi')}
  else if(a==='gssave'){const u=$('#gs-url').value.trim();if(!u){$('#gs-err').textContent='Havolani qo\'ying.';return}
    b.disabled=true;b.textContent='Yuborilmoqda…';try{GS.d=await gsApi('set',{url:u});toast('Ulandi va ma\'lumot yuborildi');renderBody()}catch(e){$('#gs-err').textContent=String(e.message||e);b.disabled=false;b.textContent='Ulash va yuborish'}}
  else if(a==='gspush'){b.disabled=true;b.textContent='Yuborilmoqda…';try{GS.d=await gsApi('push');toast('Yuborildi')}catch(e){toast(String(e.message||e));GS.loaded=false}renderBody()}
  else if(a==='gsoff'){if(!sure(b))return;try{GS.d=await gsApi('off');toast('Uzildi')}catch(e){toast(String(e.message||e))}renderBody()}
  else if(a==='delcash'){'''


def main(dirs):
    for d in dirs:
        hp, sp = os.path.join(d, 'index.html'), os.path.join(d, 'server.py')
        h, sv = open(hp, encoding='utf-8').read(), open(sp, encoding='utf-8').read()
        if MARK in h:
            print(d, ": allaqachon o'rnatilgan, o'tkazib yuborildi")
            continue
        sv = rep(sv, "def check_write(me, role, op, path, data, old):\n", SERVER + "def check_write(me, role, op, path, data, old):\n")
        sv = rep(sv, "            with LOCK:\n                if u.path == '/api/login':", ROUTE)
        sv = rep(sv, "    BOT.start()\n", "    BOT.start()\n    threading.Thread(target=_gs_loop, daemon=True).start()\n")
        h = rep(h, "function openCashForm(type){", JS.lstrip('\n') + "function openCashForm(type){")
        h = rep(h, "else if(a==='delcash'){", HANDLERS)
        for p in (hp, sp):
            shutil.copy2(p, p + '.bak-sheets')
        open(hp, 'w', encoding='utf-8').write(h)
        open(sp, 'w', encoding='utf-8').write(sv)
        print(d, ': yangilandi')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit("Papka yo'lini bering: python3 install-sheets.py /opt/gilam-crm /opt/fayz-crm")
    main(sys.argv[1:])
