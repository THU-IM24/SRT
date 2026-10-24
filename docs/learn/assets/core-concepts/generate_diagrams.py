"""Generate four original teaching diagrams; no research data are read."""
from pathlib import Path
import os
os.environ.setdefault("MPLCONFIGDIR", str(Path(os.environ.get("TEMP", ".")) / "srt-core-0500-mpl"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
from matplotlib.font_manager import FontProperties
import json

OUT = Path(__file__).parent
FONT = FontProperties(fname="C:/Windows/Fonts/msyh.ttc")
plt.rcParams.update({"font.family": FONT.get_name(), "axes.unicode_minus": False,
                     "font.size": 12, "savefig.facecolor": "white"})
INK, BLUE, GREEN, GRAY, RED = "#203044", "#2263a5", "#24765a", "#657285", "#b44b42"

def canvas(title, width=12, height=5):
    fig, ax = plt.subplots(figsize=(width, height))
    fig.subplots_adjust(left=.025, right=.975, bottom=.06, top=.84)
    fig.suptitle(title, fontsize=19, color=INK, y=.96, fontproperties=FONT)
    ax.set(xlim=(0,12), ylim=(0,5))
    ax.axis("off")
    return fig, ax

def text(ax, x, y, s, size=12, color=INK, **kwargs):
    return ax.text(x,y,s,ha="center",va="center",fontsize=size,
                   color=color,fontproperties=FONT,**kwargs)

def node(ax, x, y, s, color=BLUE, radius=.3):
    ax.add_patch(Circle((x,y),radius,facecolor="#f0f5fa",edgecolor=color,lw=1.6,zorder=3))
    text(ax,x,y,s,13,color,zorder=4)

def arrow(ax, start, end, color=BLUE, both=False, shrink=21):
    ax.add_patch(FancyArrowPatch(start,end,arrowstyle="<->" if both else "-|>",
                                mutation_scale=17,shrinkA=shrink,shrinkB=shrink,
                                color=color,lw=2,zorder=2))

def box(ax,x,y,w,h,s,color=BLUE,size=12):
    ax.add_patch(FancyBboxPatch((x-w/2,y-h/2),w,h,boxstyle="round,pad=.07",
                               facecolor="#f5f8fb",edgecolor=color,lw=1.3,zorder=3))
    text(ax,x,y,s,size,color,zorder=4)

def save(fig, name):
    fig.savefig(OUT/name,dpi=180)
    plt.close(fig)

fig, ax = canvas("同一组评论，三种关系表示",12,5)
for x, label in [(2,"线程树：父消息 → 子回复"),(6,"主网络：评论者 → 帖作者"),(10,"直接回复网络：评论者 → 父作者")]:
    text(ax,x,4.65,label,12)
for y,s in [(3.9,"P：A发帖"),(2.9,"c1：B"),(1.9,"c2：C"),(.9,"c3：A")]:
    box(ax,2,y,2,.5,s)
for y1,y2 in [(3.9,2.9),(2.9,1.9),(1.9,.9)]:
    arrow(ax,(2,y1),(2,y2),shrink=18)
for center in [6,10]:
    node(ax,center,3.65,"A")
    node(ax,center-1,1.65,"B")
    node(ax,center+1,1.65,"C")
arrow(ax,(5,1.65),(6,3.65))
arrow(ax,(7,1.65),(6,3.65))
text(ax,6,.65,"A在自己帖内的评论去掉\n保留 B→A、C→A",11,GRAY)
arrow(ax,(9,1.65),(10,3.65))
arrow(ax,(11,1.65),(9,1.65))
arrow(ax,(10,3.65),(11,1.65))
text(ax,10,.65,"保留 B→A、C→B、A→C",11,GRAY)
text(ax,2,.1,"虚构事件；不是研究结果",10,GRAY)
save(fig,"edge-definitions.png")

fig, ax = canvas("互惠率：先说清数的是边，还是账号对",12,4.8)
for x,s in [(1.3,"A"),(3.2,"B"),(6.5,"C"),(8.4,"D")]:
    node(ax,x,3.6,s)
arrow(ax,(1.3,3.6),(3.2,3.6),both=True)
arrow(ax,(6.5,3.6),(8.4,3.6))
text(ax,2.25,2.85,"互惠账号对：M = 1",13)
text(ax,7.45,2.85,"单向账号对：U = 1",13)
box(ax,3,1.75,4.6,.9,"有向边：2条有反向 / 共3条\n边互惠率 = 2/3",GREEN,14)
box(ax,9,1.75,4.6,.9,"无序账号对：1对双向 / 共2对\n账号对互惠率 = 1/2",BLUE,14)
text(ax,6,.55,"同一张图，两个不同分母；完全无关系的账号对不计入。",12,GRAY)
save(fig,"reciprocity.png")

fig, ax = canvas("帖主出现 ≠ 直接回应 ≠ 三步往返",12,5.8)
positions={"P":(1.4,3.1),"c1":(4,3.8),"c2":(6.9,3.8),"c3":(9.8,3.8),"c4":(4,1.6)}
for a,b in [("P","c1"),("c1","c2"),("c2","c3"),("P","c4")]:
    arrow(ax,positions[a],positions[b],shrink=70)
for key,label in [("P","P：A发帖"),("c1","c1：B\n09:00"),("c2","c2：A\n10:00"),("c3","c3：B\n11:00"),("c4","c4：C\n未获帖主回应")]:
    x,y=positions[key]
    box(ax,x,y,1.8,.8,label,GREEN if key=="c2" else BLUE,12)
text(ax,8,2.45,"c1获得直接回应，并发起 B、A、B 链",12,GREEN)
text(ax,8,1.55,"起始机会是 c1、c3、c4，共3条\nc3既完成上一段往返，也是新的等待机会",11)
text(ax,6,.35,"假设3条起始评论均可完整观察24小时：出现率1/1；严格回应率1/3；三步往返率1/3。",11,GRAY)
save(fig,"op-return.png")

fig, ax = canvas("完整固定窗口：随访不足不能直接记为未回应",12,5.4)
ax.set(xlim=(-7,50),ylim=(0,5))
for y in [3.65,1.8]:
    ax.plot([0,48],[y,y],color="#ccd5df",lw=2)
ax.axvline(24,ymin=.16,ymax=.88,color=RED,lw=1.8,ls="--")
text(ax,24,4.65,"可靠观察终点 C（虚构）",13,RED)
for y,label in [(3.65,"较早评论"),(1.8,"较晚评论")]:
    ax.text(-1,y,label,ha="right",va="center",fontproperties=FONT,fontsize=12,color=INK)
ax.plot([0,24],[3.65,3.65],color=GREEN,lw=6,solid_capstyle="round")
ax.plot([12,24],[1.8,1.8],color=BLUE,lw=6,solid_capstyle="round")
ax.plot([24,36],[1.8,1.8],color=BLUE,lw=3,ls="--")
for x,y in [(0,3.65),(12,1.8)]:
    ax.plot(x,y,"o",color=INK,ms=7,zorder=5)
text(ax,10,4.1,"完整24小时；满足时间资格",12,GREEN)
text(ax,16,2.4,"只观察12小时",12,BLUE)
text(ax,36,2.4,"尚缺12小时",12,BLUE)
for x,s in [(0,"起点 0h"),(12,"12h"),(24,"24h"),(36,"36h"),(48,"48h")]:
    text(ax,x,.95,s,10,GRAY)
text(ax,22,.25,"未见回复时：较早评论可判断24小时结果；较晚评论记随访不足。时间够长仍需检查覆盖。",11,GRAY)
save(fig,"right-censoring.png")

from PIL import Image
for name in ["edge-definitions.png","reciprocity.png","op-return.png","right-censoring.png"]:
    with Image.open(OUT/name) as im:
        im.verify()
print(json.dumps({"generated":4,"matplotlib":matplotlib.__version__}))
