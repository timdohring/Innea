# -*- coding: utf-8 -*-
"""Generate 06_pops.txt: area targets distributed over locations by dev/terrain/jitter,
with optional per-location pins."""
import csv, io, re, os, json, collections, hashlib, math

GAMMA, BETA, JITTER = 1.9, 0.25, 0.18
SEED = "innea-pops-v1"

# MINIMUM per-location sizes, in thousands. A location takes the larger of its natural
# share of the area target and this floor - so a floor never caps a location.
PIN_FLOORS = {"fuad": 1000.0}

# Suburb damping: scale these locations' natural share by the factor, and hand the
# surplus to the named primary. Lets a great city outgrow its hinterland.
SUBURBS = [(["zuwar", "bayd", "sire"], 0.85, "fuad")]

# Per-area flattening: raise every weight in the area to this power before distributing
# the target. <1 pulls the top down and the bottom up while keeping the area total exact;
# 1.0 is the default shape. Used where one location was running away with its area.
AREA_FLATTEN = {
    "lower_falfedo_area":   0.85,   # falansyr was 26.6% of the area on its own
    "central_teltran_area": 0.85,   # bergendale was 15.7%
}

MOD  = r"C:\Users\timdo\OneDrive\Documents\Projects\Innea modding\EU5 Innea\wip mod folder"
MAPW = r"C:\Users\timdo\OneDrive\Documents\Projects\Innea modding\map"
REPO = r"C:\Users\timdo\OneDrive\Documents\Projects\Innea modding\EU5 Innea"
SCR  = os.path.dirname(os.path.abspath(__file__))
rd=lambda p,e='utf-8-sig': open(p,encoding=e,errors='replace').read()

_MULT=json.load(open(os.path.join(SCR,"vanilla_multipliers.json")))
_MULT["topo"].update({"deadlands":0.25,"glacial":0.15,"volcanic":0.85})
_MULT["veg"].update({"dead":0.20,"fungal":1.50})
_MULT["rgo"].update({"cloves":3.0,"elephants":3.0,"pepper":2.8,"silk":2.6})

id2hex={}
for row in csv.reader(io.StringIO(rd(os.path.join(MAPW,"location_def.csv"),'latin-1')),delimiter=';'):
    if len(row)>=4 and row[0].strip().isdigit():
        id2hex[int(row[0])]="%02x%02x%02x"%(int(row[1]),int(row[2]),int(row[3]))
hex2name={m.group(2).lower():m.group(1) for m in re.finditer(
    r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([0-9a-fA-F]{6})\s*$',
    rd(os.path.join(MOD,"in_game","map_data","named_locations","00_default.txt")),re.M)}
id2loc={i:hex2name[h] for i,h in id2hex.items() if h in hex2name}

tpl=rd(os.path.join(MOD,"in_game","map_data","location_templates.txt"))
rel={};cul={};terr={}
for m in re.finditer(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{([^}]*)\}',tpl,re.M):
    b=m.group(2); g=lambda k:(re.search(k+r'\s*=\s*(\S+)',b) or [None,None])[1]
    if g("religion"): rel[m.group(1)]=g("religion")
    if g("culture"):  cul[m.group(1)]=g("culture")
    terr[m.group(1)]=dict(topo=g("topography"),veg=g("vegetation"),cli=g("climate"),rgo=g("raw_material"))

toks=re.findall(r'[A-Za-z_][A-Za-z0-9_]*|\{|\}|=',rd(os.path.join(MOD,"in_game","map_data","definitions.txt")))
st=[];path={};i=0
while i<len(toks):
    x=toks[i]
    if x=='{': i+=1; continue
    if x=='}': st and st.pop(); i+=1; continue
    if x=='=': i+=1; continue
    if i+1<len(toks) and toks[i+1]=='=' and i+2<len(toks) and toks[i+2]=='{': st.append(x); i+=3; continue
    path[x]=list(st); i+=1

def terrain_multiplier(loc):
    a=terr.get(loc,{}); m=1.0
    for k in ("topo","veg","cli","rgo"): m*=_MULT[k].get(a.get(k),1.0)
    return m**BETA
def jitter(loc):
    if not JITTER: return 1.0
    d=hashlib.sha256((SEED+"|"+loc).encode()).digest()
    u1=(int.from_bytes(d[0:4],"big")+1)/(2**32+1); u2=(int.from_bytes(d[4:8],"big")+1)/(2**32+1)
    z=math.sqrt(-2.0*math.log(u1))*math.cos(2.0*math.pi*u2)
    return math.exp(JITTER*max(-2.5,min(2.5,z)))

f=lambda s: float(s) if s.strip().replace('.','',1).isdigit() else None
entries=[]; skipped=collections.Counter()
for r in list(csv.reader(io.StringIO(rd(os.path.join(MAPW,"sheet_columns","sheet_gid0.csv"),'utf-8'))))[2:]:
    i=r[0].strip() if r else ""
    if not i.isdigit(): skipped["no id"]+=1; continue
    dev=f(r[7])
    if not dev or dev<=0: skipped["no development"]+=1; continue
    loc=id2loc.get(int(i))
    if not loc: skipped["id not on map"]+=1; continue
    c,rg=cul.get(loc),rel.get(loc)
    if not c or not rg or c=="swedish" or rg=="catholic": skipped["placeholder/unauthored"]+=1; continue
    if loc not in path or len(path[loc])<4: skipped["no area in definitions"]+=1; continue
    entries.append((loc,dev,c,rg,path[loc][3]))

targets={}
for line in rd(os.path.join(REPO,"map","area_population_targets.txt")).split("\n"):
    s=line.strip()
    if s and not s.startswith("#"):
        t=s.split()
        if len(t)>=2:
            try: targets[t[0]]=float(t[1])
            except ValueError: pass

byarea=collections.defaultdict(list)
for loc,dev,c,rg,area in entries: byarea[area].append((loc,dev,c,rg))
weight={loc: dev**GAMMA*terrain_multiplier(loc)*jitter(loc) for loc,dev,_,_,_ in entries}

size={}; notes=[]
for area,rows in byarea.items():
    tgt=targets.get(area)
    if tgt is None: notes.append("area %s has no target - left unscaled"%area); tgt=sum(weight[l] for l,_,_,_ in rows)
    names=[l for l,_,_,_ in rows]
    w={l:weight[l] for l in names}

    # 1. suburb damping - move weight from the hinterland to its primary city
    for grp,factor,primary in SUBURBS:
        g=[l for l in grp if l in w]
        if not g or primary not in w: continue
        freed=sum(w[l]*(1.0-factor) for l in g)
        for l in g: w[l]*=factor
        w[primary]+=freed

    # 2. optional flattening - compress the spread within this area
    k=AREA_FLATTEN.get(area)
    if k and k!=1.0:
        for l in names: w[l]=w[l]**k

    # 3. distribute the area target by weight
    wsum=sum(w.values()) or 1.0
    out={l: tgt*w[l]/wsum for l in names}

    # 4. apply floors, taking the shortfall from everyone else pro rata
    for l,floor in PIN_FLOORS.items():
        if l not in out or out[l]>=floor: continue
        short=floor-out[l]; out[l]=floor
        others=[o for o in names if o!=l]
        osum=sum(out[o] for o in others) or 1.0
        if osum<=short:
            notes.append("area %s: floor for %s exceeds the area target"%(area,l)); continue
        for o in others: out[o]-=short*out[o]/osum
    size.update(out)

L=["# Innea starting population.",
   "# Per-area totals come from map/area_population_targets.txt (hand-authored).",
   "# Within each area they are split by:  dev^%.2f * (topography*vegetation*climate*rgo)^%.2f * jitter"%(GAMMA,BETA),
   "#   jitter = seeded lognormal, sigma %.2f, seed '%s' (deterministic per location)"%(JITTER,SEED),
   "# size is in THOUSANDS of people (vanilla Earth totals 393,896 = ~394 million).",
   "#",
   "# FIRST PASS: the whole population of a location is a single peasants pop.",
   "# Splitting it into tribesmen / burghers / clergy / nobles / slaves comes later.",""]
if PIN_FLOORS or SUBURBS or AREA_FLATTEN:
    L.append("# Hand adjustments:")
    for k,v in PIN_FLOORS.items(): L.append("#   %s has a floor of %.0fk (not a cap)"%(k,v))
    for grp,fa,pr in SUBURBS:
        L.append("#   %s damped to %.0f%% of their natural share, surplus to %s"%(" + ".join(grp),100*fa,pr))
    for a,k in AREA_FLATTEN.items():
        L.append("#   %s flattened: weights ^ %.2f before distributing the area target"%(a,k))
    L.append("")
L+=["locations={",""]
tot=0.0
for loc,dev,c,rg,area in sorted(entries,key=lambda x:x[0]):
    s=round(size[loc],3)
    if s<0.001: s=0.001
    tot+=s
    L.append("%s = {"%loc)
    L.append("\tdefine_pop = {\ttype = peasants\tsize = %.3f\tculture = %s\treligion = %s }"%(s,c,rg))
    L.append("}")
L.append("}")
out=os.path.join(MOD,"main_menu","setup","start","06_pops.txt")
open(out,"w",encoding="utf-8",newline="\r\n").write("\n".join(L)+"\n")
print("wrote",out)
print("locations %d | world %.0fk (%.1f million) | areas %d"%(len(entries),tot,tot/1000,len(byarea)))
print("skipped:",dict(skipped))
for n in notes[:10]: print("  NOTE:",n)
print("\npins:")
for l in ["fuad","zuwar","bayd","sire"]:
    if l in size: print("   %-8s %8.1fk"%(l,size[l]))
print("   trio total %.1fk"%sum(size[l] for l in ("zuwar","bayd","sire") if l in size))
