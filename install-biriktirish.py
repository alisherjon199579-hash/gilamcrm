#!/usr/bin/env python3
"""Zakazni xohlagan dostavchiga biriktirish.
Ishlatish:  python3 install-biriktirish.py /opt/gilam-crm /opt/fayz-crm
index.html, server.py, bot.py zaxiralanadi (.bak-biriktir)."""
import os, shutil, sys

MARK = '/* biriktir-v1 */'


def rep(s, old, new, n=1):
    c = s.count(old)
    if c != n:
        raise SystemExit('XATO: kutilgan joy topilmadi (%d marta): %r' % (c, old[:70]))
    return s.replace(old, new)


def patch_server(s):
    return rep(s, "def check_write(me, role, op, path, data, old):\n",
               "def check_write(me, role, op, path, data, old):\n"
               "    # biriktir-v1: zakazni dostavchiga faqat rahbar biriktiradi\n"
               "    if role != 'admin' and path.startswith('orders/') and isinstance(data, dict) and ({'assignedTo', 'assignedName', 'assignedAt'} & set(data)):\n"
               "        raise Err(403, \"Ruxsat yo'q.\")\n")


def patch_bot(s):
    s = rep(s, "    def staff_chats(self, roles, skip=None):", "    def staff_chats(self, roles, skip=None, courier=None):")
    s = rep(s, "and (staff.get(sid) or {}).get('role') in roles]\n        skip_chats",
            "and (staff.get(sid) or {}).get('role') in roles\n               and not (courier and (staff.get(sid) or {}).get('role') == 'courier' and sid != courier)]\n        skip_chats")
    s = rep(s, "        if not head:\n            return\n        if actor and (self.s.staff_all()",
            "        asg = new.get('assignedTo') or ''\n"
            "        if not head and asg and (old or {}).get('assignedTo') != asg and st not in ('delivered', 'cancelled'):\n"
            "            head, roles = 'Sizga zakaz biriktirildi', ('courier',)\n"
            "        if not head:\n            return\n        if actor and (self.s.staff_all()")
    s = rep(s, "for c in self.staff_chats(roles, actor):\n            self.say(c, '\\n'.join(L))",
            "for c in self.staff_chats(roles, actor, courier=new.get('assignedTo') or None):\n            self.say(c, '\\n'.join(L))")
    return s


GETTER = r'''
/* biriktir-v1 */
(function(){var raw=S.orders,cache=null;Object.defineProperty(S,'orders',{configurable:true,enumerable:true,
  get:function(){var me=S.me;if(!me||me.role!=='courier')return raw;var k=me.id;if(cache&&cache.r===raw&&cache.k===k)return cache.v;
    cache={r:raw,k:k,v:raw.filter(function(o){return !o.assignedTo||o.assignedTo===k||o.collectedBy===k})};return cache.v},
  set:function(v){raw=v}})})();
const couriers=()=>S.staff.filter(x=>x.role==='courier'&&x.active!==false);
'''

ASSIGN_BLOCK = r'''${isAdmin()&&o.status!=='cancelled'&&o.status!=='delivered'?`<div class="card stack" style="margin-top:8px"><label class="f">Dostavchi<select id="as-sel"><option value="">— Hamma dostavchilarga ko'rinadi</option>${couriers().map(x=>`<option value="${esc(x.id)}" ${o.assignedTo===x.id?'selected':''}>${esc(x.name)}</option>`).join('')}</select></label><button class="btn" data-act="assign">Biriktirish</button></div>`:''}
    <table class="items">'''

HANDLER = r'''else if(a==='assign'){const o=S.orders.find(x=>x.id===F.id),v=($('#as-sel')||{}).value||'',st=S.staff.find(x=>x.id===v);if(!o)return;b.disabled=true;
    if(await save(db.doc('orders/'+o.id).update({assignedTo:v,assignedName:st?st.name:'',assignedAt:Date.now()}),v?`№${o.no}: ${st.name}ga biriktirildi`:`№${o.no}: biriktirish bekor qilindi`))closeSheet();else b.disabled=false}
  '''


def patch_html(s):
    s = rep(s, "let db=null,F=null,sheetKind=null,toastT=null;", "let db=null,F=null,sheetKind=null,toastT=null;" + GETTER)
    s = rep(s, "${pend(o)?`<span class=\"pill p-wait\">O'lchanmagan</span>`:''}",
            "${pend(o)?`<span class=\"pill p-wait\">O'lchanmagan</span>`:''}${o.assignedName&&o.status!=='delivered'?`<span class=\"pill p-wait\">→ ${esc(o.assignedName)}</span>`:''}", n=2)
    s = rep(s, '\n    <table class="items">', "\n    " + ASSIGN_BLOCK)
    s = rep(s, "else if(a==='sal')openSal(d.id);", "else if(a==='sal')openSal(d.id);\n  " + HANDLER.rstrip() + "\n  ") if "else if(a==='sal')openSal(d.id);" in s else s
    s = rep(s, "<label class=\"f\">Izoh<textarea id=\"of-note\">${esc(o?o.note:'')}</textarea></label><div class=\"err\" id=\"of-err\"></div>`;",
            "${isAdmin()&&!o?`<label class=\"f\">Dostavchi (ixtiyoriy)<select id=\"of-as\"><option value=\"\">— Hamma dostavchilarga ko'rinadi</option>${couriers().map(x=>`<option value=\"${esc(x.id)}\">${esc(x.name)}</option>`).join('')}</select></label>`:''}"
            "<label class=\"f\">Izoh<textarea id=\"of-note\">${esc(o?o.note:'')}</textarea></label><div class=\"err\" id=\"of-err\"></div>`;")
    s = rep(s, "status:'new',paid:false,pickup:pick,createdAt:t,by:S.me.id,byName:S.me.name,log:[{t,by:S.me.name,st:'new'}]}",
            "status:'new',paid:false,pickup:pick,createdAt:t,by:S.me.id,byName:S.me.name,log:[{t,by:S.me.name,st:'new'}],...(()=>{const v=($('#of-as')||{}).value,x=S.staff.find(z=>z.id===v);return v&&x?{assignedTo:v,assignedName:x.name,assignedAt:t}:{}})()}")
    return s


def main(dirs):
    for d in dirs:
        hp, sp, bp = (os.path.join(d, n) for n in ('index.html', 'server.py', 'bot.py'))
        h, sv, bt = (open(p, encoding='utf-8').read() for p in (hp, sp, bp))
        if MARK in h:
            print(d, ": allaqachon o'rnatilgan, o'tkazib yuborildi")
            continue
        nh, ns, nb = patch_html(h), patch_server(sv), patch_bot(bt)
        for p in (hp, sp, bp):
            shutil.copy2(p, p + '.bak-biriktir')
        for p, t in ((hp, nh), (sp, ns), (bp, nb)):
            open(p, 'w', encoding='utf-8').write(t)
        print(d, ': yangilandi')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit("Papka yo'lini bering: python3 install-biriktirish.py /opt/gilam-crm /opt/fayz-crm")
    main(sys.argv[1:])
