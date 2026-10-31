#!/usr/bin/env python3
"""Build ICTPB glass site: merges backup JSON into index.html, adds glass theme + back buttons."""
import json, os, re, sys

SRC_HTML = sys.argv[1]
SRC_JSON = sys.argv[2]
OUT_DIR = sys.argv[3]
os.makedirs(OUT_DIR, exist_ok=True)

html = open(SRC_HTML, encoding="utf-8").read()
backup = json.load(open(SRC_JSON, encoding="utf-8"))


def sub_once(text, old, new, label):
    if old not in text:
        sys.exit(f"PATTERN NOT FOUND: {label}")
    return text.replace(old, new, 1)


# ---------------------------------------------------------------- 1. seed data
KEEP = ["CLASSES", "students", "staff", "notices", "exams", "txns",
        "attendanceRecords", "receiptSeq"]
seed = {k: backup[k] for k in KEEP if k in backup}
for s in seed["students"]:          # make sure every field the app reads exists
    for f in ("prevRoll", "studentPhone", "email", "photo", "guardian", "phone"):
        s.setdefault(f, "")
    s["att"] = int(s.get("att") or 0)
    s["total"] = int(s.get("total") or 0)
    s["paid"] = int(s.get("paid") or 0)
for p in seed["staff"]:
    if p.get("role") == "Instractor":
        p["role"] = "Instructor"    # typo in backup

seed_json = json.dumps(seed, ensure_ascii=False).replace("</", "<\\/")
seed_tag = f'<script id="ictpb-seed" type="application/json">{seed_json}</script>\n'

html = sub_once(html, "<!-- ====================== ADMIN SUITE ====================== -->",
                seed_tag + "<!-- ====================== ADMIN SUITE ====================== -->", "admin marker")

html = sub_once(html, "function defaultData(){", "function defaultDataBase(){", "defaultData")
html = sub_once(
    html,
    "    var CLASSES=[],students=[],staff=[],notices=[],exams=[],txns=[];",
    """    function defaultData(){
      var base = defaultDataBase();
      try{
        var seed = JSON.parse(document.getElementById('ictpb-seed').textContent);
        for(var k in seed){ base[k] = seed[k]; }
      }catch(e){}
      return base;
    }
    var CLASSES=[],students=[],staff=[],notices=[],exams=[],txns=[];""",
    "var CLASSES")

# new storage key so the merged data loads fresh (old sample data is ignored)
html = html.replace("ictpb_school_data_v4", "ictpb_school_data_v5")

# ---------------------------------------------------------------- 2. back buttons
# 2a landing: floating back button + aurora background
html = sub_once(
    html,
    '<div class="fixed inset-0 z-[-1] bg-grid-pattern"></div>',
    '<div class="aurora"></div>\n  <div class="fixed inset-0 z-[-1] bg-grid-pattern"></div>',
    "grid pattern")
html = sub_once(
    html,
    '<a href="https://wa.me/8801797982323" target="_blank" class="float-whatsapp no-print"',
    '<button id="backBtn" class="back-fab no-print" onclick="goBack()" title="Back"><i class="fas fa-arrow-left"></i><span>Back</span></button>\n  '
    '<a href="https://wa.me/8801797982323" target="_blank" class="float-whatsapp no-print"',
    "whatsapp float")

# instructor photo fallback
html = sub_once(
    html,
    'class="w-full h-full object-cover mix-blend-luminosity hover:mix-blend-normal transition duration-700" loading="lazy">',
    'class="w-full h-full object-cover mix-blend-luminosity hover:mix-blend-normal transition duration-700" loading="lazy" '
    "onerror=\"this.style.display='none';this.parentNode.insertAdjacentHTML('beforeend','<span style=&quot;font-size:64px;font-weight:800;color:#818cf8&quot;>PKR</span>')\">",
    "instructor img")

# 2b admin: back + website buttons in the top bar
html = sub_once(
    html,
    '<button class="hamburger" id="hamburger"><i class="fas fa-bars"></i></button>',
    '<button class="hamburger" id="hamburger"><i class="fas fa-bars"></i></button>\n'
    '        <button class="icon-btn" id="adminBackBtn" title="Back"><i class="fas fa-arrow-left" style="font-size:14px;color:#4f46e5"></i></button>',
    "hamburger")
html = sub_once(
    html,
    '<button class="icon-btn" title="Notifications">',
    '<button class="btn btn-ghost btn-sm" id="toWebsiteBtn" title="Back to website"><i class="fas fa-globe"></i> <span class="site-label">Website</span></button>\n        '
    '<button class="icon-btn" title="Notifications">',
    "notifications btn")

# 2c admin JS: view history stack
html = sub_once(
    html,
    "    function setView(name){\n      if(!VIEW_TITLES[name]) return;",
    """    var viewStack=[], currentView='home', goingBack=false;
    function adminBack(){
      var prev = viewStack.pop();
      if(!prev){
        if(currentView!=='home') prev='home';
        else { if(window.goToWebsite) window.goToWebsite(); return; }
      }
      goingBack=true; setView(prev); goingBack=false;
    }
    function setView(name){
      if(!VIEW_TITLES[name]) return;
      if(!goingBack && name!==currentView){ viewStack.push(currentView); if(viewStack.length>30) viewStack.shift(); }
      currentView=name;""",
    "setView")
html = sub_once(
    html,
    "var hb=$('#hamburger');",
    "var abb=$('#adminBackBtn'); if(abb) abb.addEventListener('click',adminBack);\n"
    "      var twb=$('#toWebsiteBtn'); if(twb) twb.addEventListener('click',function(){ if(window.goToWebsite) window.goToWebsite(); });\n"
    "      var hb=$('#hamburger');",
    "hb init")

# 2d public JS: goToWebsite / goBack / logged-in shortcut
html = sub_once(
    html,
    "window.showLoginModal = function(){",
    "window.showLoginModal = function(){if(isLoggedIn()){showApp();return;}",
    "showLoginModal")
html = sub_once(
    html,
    "  function init(){renderCalendar();",
    """  window.goToWebsite = function(){ showLandingPage(); window.scrollTo({top:0}); };
  window.goBack = function(){
    if(location.hash && history.length>1){ history.back(); }
    else { window.scrollTo({top:0,behavior:'smooth'}); }
  };
  (function(){
    var fab=document.getElementById('backBtn');
    function upd(){ if(fab) fab.classList.toggle('show', window.scrollY>300 || !!location.hash); }
    window.addEventListener('scroll',upd,{passive:true});
    window.addEventListener('hashchange',upd);
    upd();
  })();

  function init(){renderCalendar();""",
    "init")

# ---------------------------------------------------------------- 3. glass theme
glass_css = open(os.path.join(os.path.dirname(__file__), "glass.css"), encoding="utf-8").read()
html = sub_once(html, "</head>", f"<style id=\"glass-theme\">\n{glass_css}\n</style>\n</head>", "</head>")

out = os.path.join(OUT_DIR, "index.html")
open(out, "w", encoding="utf-8").write(html)
print("students:", len(seed["students"]), "| attendance days:", len(seed["attendanceRecords"]),
      "| notices:", len(seed["notices"]), "| exams:", len(seed["exams"]))
print("written", out, len(html), "bytes")
