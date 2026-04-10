#!/usr/bin/env python3
"""
CleanDaMacintosh v2.0  —  Free, Open-Source Mac Cleaner
Premium UI inspired by CleanMyMac  |  MIT License  |  No pip installs needed
"""
import tkinter as tk
from tkinter import messagebox
import os, sys, shutil, subprocess, threading, math, time, random
from pathlib import Path
from datetime import datetime
from collections import defaultdict
try:
    import plistlib
except ImportError:
    plistlib = None

# ════════════════════════════════════════════════════════════════
#  DESIGN SYSTEM
# ════════════════════════════════════════════════════════════════
APP    = "CleanDaMacintosh"
VER    = "2.0.0"
HOME   = Path.home()
WIN_W, WIN_H = 1200, 750
SB_W   = 228    # sidebar width

# Deep-space purple palette (CleanMyMac-inspired)
BG       = "#0e0825"   # main bg
BG2      = "#170e38"   # content bg (slightly lighter)
SB_BG    = "#060212"   # sidebar
CARD     = "#1a1048"   # card bg
CARD_H   = "#251865"   # card hover
SEP      = "#1e1450"   # separator / border

PINK     = "#e91e8c"   # primary accent
PINK_L   = "#f06292"   # lighter pink
PURPLE   = "#7c3aed"   # purple
BLUE     = "#38bdf8"   # sky blue
TEAL     = "#2dd4bf"   # teal
GREEN    = "#4ade80"   # success
AMBER    = "#fbbf24"   # warning
RED      = "#f87171"   # danger

WHITE    = "#ffffff"
TEXT2    = "#c4b5f4"   # lavender text
TEXT3    = "#8b7db5"   # muted text (sidebar inactive)
MUTED    = "#5c508a"   # very muted

SB_ABGR  = "#1e1658"    # active sidebar bg  (white@10% on #060212)
SB_HBGR  = "#0f0a2a"    # hover sidebar bg   (white@4% on #060212)
SB_CAT   = "#3d3070"    # category label

def F(size=12, bold=False, italic=False):
    fam = "SF Pro Display" if sys.platform == "darwin" else "Helvetica Neue"
    wt  = "bold"   if bold   else "normal"
    sl  = "italic" if italic else "roman"
    return (fam, size, wt, sl)

def FM(size=12):
    return ("SF Mono" if sys.platform == "darwin" else "Courier New", size, "normal")

def _lerp(a, b, t):
    return int(a + (b - a) * max(0.0, min(1.0, t)))

def hex2rgb(h):
    return int(h[1:3],16), int(h[3:5],16), int(h[5:7],16)

def blend(c1, c2, t):
    r1,g1,b1 = hex2rgb(c1); r2,g2,b2 = hex2rgb(c2)
    return f"#{_lerp(r1,r2,t):02x}{_lerp(g1,g2,t):02x}{_lerp(b1,b2,t):02x}"

def ab(color, alpha, bg=None):
    """Alpha-blend color onto bg — returns solid 6-char hex (tkinter compatible)."""
    if bg is None: bg = BG
    if isinstance(alpha, str): alpha = int(alpha, 16)
    t = alpha / 255.0
    return blend(bg, color, t)

# ════════════════════════════════════════════════════════════════
#  UTILITIES
# ════════════════════════════════════════════════════════════════
def fmt(b):
    if b == 0: return "0 B"
    for unit, dv in [("B",1),("KB",1<<10),("MB",1<<20),("GB",1<<30),("TB",1<<40)]:
        if b < dv * 1024 or unit == "TB":
            return f"{int(b)} B" if unit=="B" else f"{b/dv:.1f} {unit}"

def du(path):
    total = 0
    try:
        p = Path(path)
        if p.is_symlink(): return 0
        if p.is_file(follow_symlinks=False): return p.stat().st_size
        for e in os.scandir(p):
            try:
                if not e.is_symlink():
                    if e.is_file(follow_symlinks=False): total += e.stat().st_size
                    elif e.is_dir(follow_symlinks=False): total += du(e.path)
            except: pass
    except: pass
    return total

def disk():
    s = shutil.disk_usage("/")
    return s.total, s.used, s.free

def to_trash(path):
    try:
        subprocess.run(["osascript","-e",
            f'tell app "Finder" to delete POSIX file "{path}"'],
            capture_output=True, timeout=15)
    except: pass

# ════════════════════════════════════════════════════════════════
#  CANVAS HELPERS
# ════════════════════════════════════════════════════════════════
def grad_v(cv, x1, y1, x2, y2, c1, c2, steps=90, tag=""):
    r1,g1,b1 = hex2rgb(c1); r2,g2,b2 = hex2rgb(c2)
    h = y2 - y1
    kw = {"tags":tag} if tag else {}
    for i in range(steps):
        t = i/steps
        col = f"#{_lerp(r1,r2,t):02x}{_lerp(g1,g2,t):02x}{_lerp(b1,b2,t):02x}"
        ys = y1 + int(h*i/steps)
        ye = y1 + int(h*(i+1)/steps) + 1
        cv.create_rectangle(x1, ys, x2, ye, fill=col, outline="", **kw)

def rr(cv, x1, y1, x2, y2, radius=12, **kw):
    """Rounded rectangle on canvas."""
    r = min(radius, (x2-x1)//2, (y2-y1)//2)
    pts = [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r,
           x2,y2-r, x2,y2, x2-r,y2, x1+r,y2,
           x1,y2, x1,y2-r, x1,y1+r, x1,y1]
    return cv.create_polygon(pts, smooth=True, **kw)

def glow_oval(cv, cx, cy, r, color, tag=""):
    """Draw a soft glowing circle."""
    kw = {"tags":tag} if tag else {}
    for spread, alpha in [(r+24,"11"),(r+14,"22"),(r+6,"44")]:
        cv.create_oval(cx-spread,cy-spread,cx+spread,cy+spread,
                      fill=ab(color,alpha), outline="", **kw)

# ════════════════════════════════════════════════════════════════
#  APP DATA
# ════════════════════════════════════════════════════════════════
JUNK_DEFS = [
    dict(id="caches",  label="User Caches",        icon="◈", color=BLUE,
         desc="Application cache files — safely recreated on next launch",
         paths=[HOME/"Library"/"Caches"]),
    dict(id="logs",    label="System & App Logs",   icon="◉", color=TEAL,
         desc="Log files accumulated by macOS and applications",
         paths=[HOME/"Library"/"Logs", Path("/private/var/log")]),
    dict(id="trash",   label="Trash Bins",          icon="◎", color=RED,
         desc="Files currently waiting in your Trash",
         paths=[HOME/".Trash"]),
    dict(id="derived", label="Xcode Derived Data",  icon="◆", color=PURPLE,
         desc="Xcode build artifacts — regenerated on next build",
         paths=[HOME/"Library"/"Developer"/"Xcode"/"DerivedData"]),
    dict(id="simul",   label="iOS Simulators",      icon="◇", color=AMBER,
         desc="Unused iOS/watchOS simulator data",
         paths=[HOME/"Library"/"Developer"/"CoreSimulator"/"Caches"]),
    dict(id="brew",    label="Homebrew Cache",      icon="◈", color=GREEN,
         desc="Cached Homebrew package downloads",
         paths=[Path("/opt/homebrew/var/cache"),
                Path("/usr/local/var/cache/homebrew")]),
    dict(id="npm",     label="npm Cache",           icon="◉", color=BLUE,
         desc="Node package manager download cache",
         paths=[HOME/".npm"/"_cacache"]),
    dict(id="pip",     label="pip Cache",           icon="◆", color=TEAL,
         desc="Python pip package download cache",
         paths=[HOME/"Library"/"Caches"/"pip"]),
    dict(id="ds",      label=".DS_Store Files",     icon="◇", color=MUTED,
         desc="Hidden macOS metadata files scattered across your drive",
         paths=None),
    dict(id="mail",    label="Mail Downloads",      icon="✉", color=PINK,
         desc="Attachments downloaded through Apple Mail",
         paths=[HOME/"Library"/"Mail Downloads",
                HOME/"Library"/"Containers"/"com.apple.mail"/"Data"/"Library"/"Mail Downloads"]),
]

PRIV_TARGETS = [
    dict(id="safari_h", label="Safari History",      icon="◉", color=BLUE,
         desc="URLs visited in Safari",
         paths=[HOME/"Library"/"Safari"/"History.db",
                HOME/"Library"/"Safari"/"History.db-wal",
                HOME/"Library"/"Safari"/"History.db-shm"]),
    dict(id="safari_c", label="Safari Cache",        icon="◈", color=TEAL,
         desc="Websites cached by Safari",
         paths=[HOME/"Library"/"Caches"/"com.apple.Safari"]),
    dict(id="chrome_h", label="Chrome History",      icon="◉", color=BLUE,
         desc="URLs visited in Google Chrome",
         paths=[HOME/"Library"/"Application Support"/"Google"/"Chrome"/"Default"/"History"]),
    dict(id="chrome_c", label="Chrome Cache",        icon="◈", color=TEAL,
         desc="Websites cached by Chrome",
         paths=[HOME/"Library"/"Caches"/"Google"/"Chrome"]),
    dict(id="ff",       label="Firefox Data",        icon="◉", color=AMBER,
         desc="Firefox browsing history and cache",
         paths=[HOME/"Library"/"Application Support"/"Firefox"/"Profiles"]),
    dict(id="recents",  label="Recent Documents",    icon="◆", color=PURPLE,
         desc="Recently opened documents list",
         paths=[HOME/"Library"/"Application Support"/"com.apple.sharedfilelist"]),
    dict(id="crash",    label="Crash Reports",       icon="◇", color=RED,
         desc="Application crash logs and diagnostics",
         paths=[HOME/"Library"/"Logs"/"DiagnosticReports",
                Path("/Library/Logs/DiagnosticReports")]),
    dict(id="quarant",  label="Quarantine Database", icon="◉", color=AMBER,
         desc="macOS quarantine event log for downloaded files",
         paths=[HOME/"Library"/"Preferences"/"com.apple.LaunchServices.QuarantineEventsV2"]),
]

# ════════════════════════════════════════════════════════════════
#  SIDEBAR
# ════════════════════════════════════════════════════════════════
# NAV: (label, icon, page_key, is_category, locked)
NAV = [
    ("Smart Care",       "✦", "smartcare",   False, False),
    ("CLEANUP",          "",  None,          True,  False),
    ("System Junk",      "◈", "junk",        False, False),
    ("Mail & Downloads", "✉", "mail",        False, False),
    ("Trash Bins",       "◎", "trash",       False, False),
    ("PROTECTION",       "",  None,          True,  False),
    ("Malware Scan",     "⬡", "malware",     False, False),
    ("Privacy",          "◉", "privacy",     False, False),
    ("VPN Guard",        "⊕", "vpnguard",    False, True),
    ("PERFORMANCE",      "",  None,          True,  False),
    ("Optimization",     "⚡","optimize",    False, False),
    ("Maintenance",      "⚙", "maintain",    False, False),
    ("RAM Cleaner",      "◈", "ramcleaner",  False, True),
    ("Battery Monitor",  "◆", "battery",     False, True),
    ("APPLICATIONS",     "",  None,          True,  False),
    ("Uninstaller",      "⊟", "uninstall",   False, False),
    ("Extensions",       "⊞", "extensions",  False, False),
    ("App Updater",      "⟳", "appupdater",  False, True),
    ("FILES",            "",  None,          True,  False),
    ("Space Lens",       "◎", "spacelens",   False, False),
    ("Large & Old",      "◆", "largeold",    False, False),
    ("Shredder",         "✂", "shredder",    False, False),
    ("Duplicate Finder", "⊞", "duplicates",  False, True),
    ("Photo Cleaner",    "◉", "photos",      False, True),
    ("Cloud Cleanup",    "◎", "cloud",       False, True),
    ("EXTRAS",           "",  None,          True,  False),
    ("Network Monitor",  "⬡", "network",     False, True),
    ("Disk Speed Test",  "⚡","diskspeed",   False, True),
    ("Menu Bar Widget",  "✦", "menubar",     False, True),
    ("File Vault",       "⊟", "filevault",   False, True),
    ("Time Machine",     "◇", "timemachine", False, True),
]

# Metadata for locked feature preview pages
LOCKED_INFO = {
    "vpnguard": dict(
        title="VPN Guard", icon="⊕", color=TEAL, version="v3.0",
        tagline="Browse with zero-trust protection",
        desc="Automatically detects unprotected network connections and alerts you. Monitors VPN status in real-time and warns when sensitive apps go online without encryption.",
        benefits=["Real-time VPN connection monitoring","Auto-alerts on unprotected Wi-Fi","Per-app network protection rules","One-click connect to trusted VPNs"],
    ),
    "ramcleaner": dict(
        title="RAM Cleaner", icon="◈", color=BLUE, version="v3.0",
        tagline="Instant memory relief, no restart needed",
        desc="Intelligently reclaims inactive RAM without touching your active apps. See exactly which processes are hoarding memory and free it all in one click.",
        benefits=["Free inactive RAM in one click","Live memory pressure graph","Per-process RAM breakdown","Scheduled auto-clean mode"],
    ),
    "battery": dict(
        title="Battery Monitor", icon="◆", color=GREEN, version="v3.0",
        tagline="Extend your MacBook's lifespan",
        desc="Track battery health, cycle count, and charge history over time. Get notified when a background app is draining power and optimize charge habits with smart recommendations.",
        benefits=["Cycle count & health score","Top battery-draining apps","Charge history timeline","Smart charging recommendations"],
    ),
    "appupdater": dict(
        title="App Updater", icon="⟳", color=PURPLE, version="v3.0",
        tagline="Every app up-to-date, always",
        desc="Scans all installed apps — including those outside the App Store — and shows available updates in one unified list. Update everything in one click.",
        benefits=["Detects updates for non-App Store apps","Batch update in one click","Version changelog previews","Auto-update scheduling"],
    ),
    "duplicates": dict(
        title="Duplicate Finder", icon="⊞", color=AMBER, version="v3.0",
        tagline="Identical files wasting your space",
        desc="Deep byte-level scan finds true duplicates across your entire drive — photos, documents, downloads. Preview side-by-side and keep only what you need.",
        benefits=["Byte-for-byte duplicate detection","Smart photo similarity matching","Side-by-side preview before delete","Keeps originals, removes copies"],
    ),
    "photos": dict(
        title="Photo Cleaner", icon="◉", color=PINK, version="v3.0",
        tagline="Reclaim gigabytes from your photo library",
        desc="Finds blurry shots, near-duplicates, screenshots, and forgotten RAW originals clogging your Photos library. Preview and delete in seconds.",
        benefits=["Blurry & out-of-focus detection","Near-duplicate photo grouping","Screenshot & temp photo sweep","RAW+JPEG pair cleanup"],
    ),
    "cloud": dict(
        title="Cloud Cleanup", icon="◎", color=BLUE, version="v3.0",
        tagline="Stop paying for cloud you don't need",
        desc="Audits your iCloud, Dropbox, and Google Drive local caches. Shows which synced files are safe to offload to the cloud and free up local disk space.",
        benefits=["iCloud Drive cache analysis","Dropbox & Google Drive support","Safe offload suggestions","Sync status per file/folder"],
    ),
    "network": dict(
        title="Network Monitor", icon="⬡", color=TEAL, version="v3.0",
        tagline="See every byte leaving your Mac",
        desc="Real-time bandwidth graph per app. Spot background uploaders, rogue processes, and data-hungry apps at a glance.",
        benefits=["Per-app upload/download stats","Real-time bandwidth graph","Historical usage by day/week","Block app network access"],
    ),
    "diskspeed": dict(
        title="Disk Speed Test", icon="⚡", color=AMBER, version="v3.0",
        tagline="Know if your SSD is performing",
        desc="Benchmark read and write speeds of your internal and external drives. Compare against baseline and get an instant health verdict.",
        benefits=["Sequential read & write benchmark","Compare vs drive baseline","External drive support","Health verdict & recommendations"],
    ),
    "menubar": dict(
        title="Menu Bar Widget", icon="✦", color=PINK, version="v3.0",
        tagline="System health always one click away",
        desc="A lightweight menu bar icon shows live CPU, RAM, and disk status at a glance. Trigger quick cleans without opening the full app.",
        benefits=["Live CPU / RAM / disk in menu bar","One-click quick clean from menu","Customizable metrics display","Low-footprint background mode"],
    ),
    "filevault": dict(
        title="File Vault", icon="⊟", color=PURPLE, version="v3.0",
        tagline="Encrypt and hide sensitive files",
        desc="Create encrypted vaults for your most sensitive documents. Lock and unlock with Touch ID. Files are invisible outside the vault.",
        benefits=["AES-256 encrypted vaults","Touch ID lock/unlock","Drag-and-drop to vault","Decoy vault option"],
    ),
    "timemachine": dict(
        title="Time Machine Helper", icon="◇", color=GREEN, version="v3.0",
        tagline="Smarter backups, less wasted space",
        desc="Analyzes your Time Machine backups to find redundant snapshots eating disk space. Prune safely and schedule smarter backup windows.",
        benefits=["Snapshot size breakdown","Safe selective snapshot pruning","Backup schedule optimizer","Exclude-list manager"],
    ),
    # keep existing placeholders working too
    "maintain": dict(
        title="Maintenance", icon="⚙", color=TEAL, version="v3.0",
        tagline="Keep macOS running at peak condition",
        desc="Rebuilds Spotlight index, flushes DNS cache, repairs disk permissions, and runs periodic maintenance scripts — all in one place.",
        benefits=["Spotlight index rebuild","DNS & caches flush","Disk permissions repair","Scheduled maintenance scripts"],
    ),
    "extensions": dict(
        title="Extensions", icon="⊞", color=PURPLE, version="v3.0",
        tagline="Audit every extension on your Mac",
        desc="Lists all Safari, Chrome, and system extensions with usage stats. Remove unused ones in seconds.",
        benefits=["Safari & Chrome extension audit","System extension manager","Usage statistics per extension","One-click remove & disable"],
    ),
    "shredder": dict(
        title="Shredder", icon="✂", color=RED, version="v3.0",
        tagline="Permanently destroy sensitive files",
        desc="Military-grade overwrite ensures deleted files can never be recovered. Drag files in, choose passes, shred.",
        benefits=["DoD 7-pass overwrite standard","Drag-and-drop shredding","Free space overwrite option","Shred confirmation & log"],
    ),
}

class Sidebar(tk.Canvas):
    def __init__(self, master, on_select, **kw):
        super().__init__(master, bg=SB_BG, width=SB_W,
                         highlightthickness=0, bd=0, **kw)
        self.on_select = on_select
        self.active_label = "Smart Care"
        self._items = []
        self._hover = None
        self._draw_all()
        self.bind("<Motion>",   self._motion)
        self.bind("<Leave>",    self._leave)
        self.bind("<Button-1>", self._click)

    def _draw_all(self):
        self.delete("all")
        self._items.clear()
        self.create_rectangle(0,0,SB_W,4000, fill=SB_BG, outline="")
        self.create_line(SB_W-1,0, SB_W-1,4000, fill=SEP, width=1)

        # Logo
        self.create_text(SB_W//2, 36, text="✦", font=F(22,True),
                         fill=PINK, anchor="center")
        self.create_text(SB_W//2, 60, text=APP, font=F(10,True),
                         fill=WHITE, anchor="center")
        self.create_text(SB_W//2, 76, text=f"v{VER}  ·  Free & Open Source",
                         font=F(8), fill=MUTED, anchor="center")

        y = 100
        for entry in NAV:
            label, icon, page, is_cat, locked = entry
            if is_cat:
                self.create_text(16, y+3, text=label, font=F(8,True),
                                 fill=SB_CAT, anchor="w")
                y += 24
                continue
            item = dict(label=label, icon=icon, page=page, locked=locked,
                        y1=y, y2=y+38,
                        bg_id=None, icon_id=None, text_id=None, lock_id=None)
            item["bg_id"] = self.create_rectangle(
                8, y, SB_W-8, y+38, fill="", outline="")
            txt_color = MUTED if locked else TEXT3
            if icon:
                item["icon_id"] = self.create_text(
                    36, y+19, text=icon, font=F(13),
                    fill=txt_color, anchor="center")
                item["text_id"] = self.create_text(
                    52, y+19, text=label, font=F(12),
                    fill=txt_color, anchor="w")
            else:
                item["text_id"] = self.create_text(
                    36, y+19, text=label, font=F(12),
                    fill=txt_color, anchor="w")
            if locked:
                item["lock_id"] = self.create_text(
                    SB_W-18, y+19, text="v3", font=F(7,True),
                    fill=AMBER, anchor="center")
            self._items.append(item)
            if label == self.active_label:
                self._set_active(item)
            y += 42

    def _set_active(self, item):
        self.itemconfig(item["bg_id"],   fill=SB_ABGR, outline="")
        self.itemconfig(item["text_id"], fill=WHITE)
        if item["icon_id"]: self.itemconfig(item["icon_id"], fill=PINK if not item["locked"] else AMBER)

    def _clear(self, item):
        if item["label"] == self.active_label: return
        self.itemconfig(item["bg_id"],   fill="", outline="")
        base = MUTED if item["locked"] else TEXT3
        self.itemconfig(item["text_id"], fill=base)
        if item["icon_id"]: self.itemconfig(item["icon_id"], fill=base)

    def _hover_on(self, item):
        if item["label"] == self.active_label: return
        self.itemconfig(item["bg_id"], fill=SB_HBGR)

    def _hit(self, y):
        for item in self._items:
            if item["y1"] <= y <= item["y2"]: return item
        return None

    def _motion(self, e):
        hit = self._hit(e.y)
        if hit != self._hover:
            if self._hover: self._clear(self._hover)
            if hit: self._hover_on(hit)
            self._hover = hit

    def _leave(self, e):
        if self._hover:
            self._clear(self._hover)
            self._hover = None

    def _click(self, e):
        hit = self._hit(e.y)
        if not hit or hit["label"] == self.active_label: return
        for item in self._items: self._clear(item)
        self.active_label = hit["label"]
        self._set_active(hit)
        self.on_select(hit["page"] or "smartcare", hit["label"])

    def jump(self, label):
        for item in self._items: self._clear(item)
        self.active_label = label
        for item in self._items:
            if item["label"] == label:
                self._set_active(item); break


# ════════════════════════════════════════════════════════════════
#  BASE PAGE
# ════════════════════════════════════════════════════════════════
class Page(tk.Canvas):
    def __init__(self, master, **kw):
        super().__init__(master, bg=BG, highlightthickness=0, bd=0, **kw)
        self._last_w = self._last_h = 0
        self.bind("<Configure>", self._on_configure)

    def _on_configure(self, e):
        if e.width != self._last_w or e.height != self._last_h:
            self._last_w, self._last_h = e.width, e.height
            self._draw_bg(e.width, e.height)
            self.after(10, lambda: self.on_resize(e.width, e.height))

    def _draw_bg(self, w, h):
        grad_v(self, 0, 0, w, h, BG, BG2, tag="bg_grad")

    def on_resize(self, w, h):
        pass  # override in subclasses


# ════════════════════════════════════════════════════════════════
#  SMART CARE PAGE  (Welcome / Main Scan)
# ════════════════════════════════════════════════════════════════
class SmartCarePage(Page):
    def __init__(self, master, app_ref, **kw):
        super().__init__(master, **kw)
        self.app      = app_ref
        self.scanning = False
        self.angle    = 0
        self.results  = {}
        self._spin_id = None
        self._btn_cx = self._btn_cy = self._btn_r = 0
        self.bind("<Button-1>", self._click)
        self.bind("<Motion>",   self._motion)

    def on_resize(self, w, h):
        self._render(w, h)

    def _render(self, w=None, h=None):
        w = w or self.winfo_width()
        h = h or self.winfo_height()
        if w < 10: return
        self.delete("ui")
        cx = w // 2

        # ── Title ──────────────────────────────────────────────
        self.create_text(cx, 38, text="Smart Care", font=F(26,True),
                         fill=WHITE, anchor="center", tags="ui")
        self.create_text(cx, 66,
            text="A full health check for your Mac — junk, speed, and protection in one scan",
            font=F(12), fill=TEXT2, anchor="center", tags="ui")

        # ── iMac Illustration ──────────────────────────────────
        self._draw_imac(cx, int(h * 0.40))

        # ── Scan Button ────────────────────────────────────────
        btn_y = int(h * 0.72)
        self._draw_scan_btn(cx, btn_y)

        # ── Result Cards ───────────────────────────────────────
        if self.results:
            self._draw_cards(cx, int(h * 0.58), w)

        # ── Disk Bar ───────────────────────────────────────────
        self._draw_disk_bar(cx, h - 34, w)

    # ── iMac drawing ───────────────────────────────────────────
    def _draw_imac(self, cx, cy):
        mw, mh = 210, 148
        mx1, my1 = cx - mw//2, cy - mh//2 - 10
        mx2, my2 = cx + mw//2, cy + mh//2 - 10

        # outer glow
        for spread, alpha in [(28,"0a"),(18,"18"),(8,"30")]:
            self.create_oval(mx1-spread, my1-spread, mx2+spread, my2+spread,
                             fill=ab(PINK, alpha), outline="", tags="ui")

        # body gradient (pink → rose-dark)
        BODY_H = mh + 28
        for i in range(BODY_H):
            t = i / BODY_H
            r = _lerp(0xf0, 0xc0, t)
            g = _lerp(0x60, 0x30, t)
            b = _lerp(0xa0, 0x65, t)
            col = f"#{r:02x}{g:02x}{b:02x}"
            self.create_rectangle(mx1, my1+i, mx2, my1+i+1,
                                  fill=col, outline="", tags="ui")

        # frame border
        rr(self, mx1,my1, mx2,my2+28, radius=20,
           fill="", outline=ab(WHITE,"25"), width=1, tags="ui")

        # screen area
        sx1,sy1 = mx1+12, my1+12
        sx2,sy2 = mx2-12, my2-2
        rr(self, sx1,sy1, sx2,sy2, radius=8, fill="#10042a", outline="", tags="ui")

        # screen UI bars (fake mini UI)
        bx = sx1 + 10
        rows = [(55,ab(PINK,"aa")),(38,ab(PURPLE,"aa")),(46,ab(BLUE,"aa")),(30,ab(TEAL,"aa"))]
        for i,(bw,bc) in enumerate(rows):
            by = sy1 + 12 + i*16
            rr(self, bx,by, bx+bw,by+9, radius=4, fill=bc, outline="", tags="ui")

        # screen corner sparkle
        self.create_text(sx2-14, sy1+12, text="✦", font=F(8),
                         fill=ab(WHITE,"44"), tags="ui")

        # camera
        self.create_oval(cx-3, my1-5, cx+3, my1+1,
                         fill=ab(WHITE,"33"), outline="", tags="ui")

        # chin band (lighter strip at bottom of body)
        self.create_rectangle(mx1+1, my2-4, mx2-1, my2+28,
                              fill="#d04070", outline="", tags="ui")
        rr(self, mx1,my2-4, mx2,my2+28, radius=0,
           fill="", outline=ab(WHITE,"25"), width=1, tags="ui")

        # stand neck
        nx1,nx2 = cx-7, cx+7
        self.create_rectangle(nx1, my2+28, nx2, my2+50,
                              fill="#c0809a", outline="", tags="ui")
        # base
        self.create_rectangle(cx-55, my2+50, cx+55, my2+62,
                              fill="#b06a88", outline="", tags="ui")
        rr(self, cx-55,my2+50, cx+55,my2+63, radius=6,
           fill="", outline=ab(WHITE,"20"), width=1, tags="ui")

    # ── Scan button ────────────────────────────────────────────
    def _draw_scan_btn(self, cx, cy):
        r = 54
        self._btn_cx, self._btn_cy, self._btn_r = cx, cy, r

        if not self.scanning:
            # Pulsing glow rings
            glow_oval(self, cx, cy, r, PINK, tag="ui")

        # Main circle
        self.create_oval(cx-r,cy-r, cx+r,cy+r,
                         fill=PINK, outline="", tags="ui")

        # Spinning arc when scanning
        if self.scanning:
            ar = r + 16
            self.create_arc(cx-ar,cy-ar, cx+ar,cy+ar,
                            start=self.angle, extent=250,
                            outline=PINK_L, width=3, style="arc", tags="ui")
            done  = len(self.results)
            total = len(JUNK_DEFS)
            pct   = int(done/total*100) if total else 0
            self.create_text(cx, cy-9, text=f"{pct}%",
                             font=F(17,True), fill=WHITE, anchor="center", tags="ui")
            self.create_text(cx, cy+10, text="Scanning…",
                             font=F(9), fill=ab(WHITE,"99"), anchor="center", tags="ui")
        else:
            label = "Scan Again" if self.results else "Scan"
            self.create_text(cx, cy, text=label,
                             font=F(17,True), fill=WHITE, anchor="center", tags="ui")

    # ── Result cards ───────────────────────────────────────────
    def _draw_cards(self, cx, cy, w):
        hits = [(jd["label"], self.results.get(jd["id"],0), jd["color"])
                for jd in JUNK_DEFS if self.results.get(jd["id"],0) > 0]
        if not hits: return
        hits.sort(key=lambda x:-x[1])
        hits = hits[:4]

        cw, gap = 168, 14
        total_w  = len(hits)*cw + (len(hits)-1)*gap
        sx = cx - total_w//2

        for i,(name,size,color) in enumerate(hits):
            x1 = sx + i*(cw+gap)
            y1,y2 = cy-56, cy-4
            rr(self, x1,y1, x1+cw,y2, radius=14,
               fill=CARD, outline=ab(color,"55"), width=1, tags="ui")
            self.create_oval(x1+12,y1+12, x1+22,y1+22,
                             fill=color, outline="", tags="ui")
            lbl = name[:18]+"…" if len(name)>18 else name
            self.create_text(x1+30, y1+17, text=lbl,
                             font=F(9,True), fill=TEXT2,
                             anchor="w", tags="ui")
            self.create_text(x1+cw//2, y1+42, text=fmt(size),
                             font=F(14,True), fill=color,
                             anchor="center", tags="ui")

        total = sum(self.results.values())
        self.create_text(cx, cy+5, text=f"Total: {fmt(total)} found",
                         font=F(12,True), fill=WHITE, anchor="center", tags="ui")

    # ── Disk bar ───────────────────────────────────────────────
    def _draw_disk_bar(self, cx, y, w):
        try:
            total,used,free = disk()
        except:
            return
        pct = used/total if total else 0
        bw  = min(w-100, 560)
        bh  = 6
        bx1,by1 = cx-bw//2, y-bh//2
        bx2,by2 = cx+bw//2, y+bh//2

        rr(self,bx1,by1,bx2,by2, radius=3,
           fill=ab(WHITE,"15"), outline="", tags="ui")
        fw = int(bw*pct)
        if fw > 6:
            col = GREEN if pct<0.7 else AMBER if pct<0.9 else RED
            rr(self,bx1,by1,bx1+fw,by2, radius=3,
               fill=col, outline="", tags="ui")

        self.create_text(cx, y-14,
            text=f"Macintosh HD  ·  {fmt(used)} used  /  {fmt(total)} total  ·  {fmt(free)} free",
            font=F(10), fill=TEXT3, anchor="center", tags="ui")

    # ── Interaction ────────────────────────────────────────────
    def _click(self, e):
        cx,cy,r = self._btn_cx, self._btn_cy, self._btn_r
        if r and math.sqrt((e.x-cx)**2+(e.y-cy)**2) <= r:
            if not self.scanning:
                self._start_scan()

    def _motion(self, e):
        cx,cy,r = self._btn_cx, self._btn_cy, self._btn_r
        if r:
            inside = math.sqrt((e.x-cx)**2+(e.y-cy)**2) <= r
            self.config(cursor="hand2" if inside else "")

    def _start_scan(self):
        self.scanning = True
        self.results  = {}
        self._spin()
        threading.Thread(target=self._do_scan, daemon=True).start()

    def _spin(self):
        if not self.scanning: return
        self.angle = (self.angle - 7) % 360
        self._render()
        self._spin_id = self.after(28, self._spin)

    def _do_scan(self):
        for jd in JUNK_DEFS:
            size = 0
            if jd.get("paths"):
                for p in jd["paths"]:
                    if Path(p).exists():
                        size += du(p)
            self.results[jd["id"]] = size
        self.scanning = False
        if self._spin_id:
            self.after_cancel(self._spin_id)
        self.after(0, self._render)


# ════════════════════════════════════════════════════════════════
#  SYSTEM JUNK PAGE
# ════════════════════════════════════════════════════════════════
class JunkPage(Page):
    def __init__(self, master, app_ref, mode="all", **kw):
        super().__init__(master, **kw)
        self.app  = app_ref
        self.mode = mode      # "all" | "trash" | "mail"
        self.items   = []
        self._built  = False

    def on_resize(self, w, h):
        if not self._built:
            self._built = True
            self._build()

    def _build(self):
        for c in self.winfo_children(): c.destroy()
        self._draw_bg(self.winfo_width(), self.winfo_height())

        if self.mode == "trash":
            title, sub = "Trash Bins", "Empty your Trash and free up space."
            defs = [d for d in JUNK_DEFS if d["id"]=="trash"]
            btn_color = RED
        elif self.mode == "mail":
            title, sub = "Mail & Downloads", "Clear mail attachments and download cache."
            defs = [d for d in JUNK_DEFS if d["id"]=="mail"]
            btn_color = PINK
        else:
            title, sub = "System Junk", "Remove cache, logs, and developer clutter safely."
            defs = JUNK_DEFS
            btn_color = PINK

        self._defs = defs

        tk.Label(self, text=title, font=F(24,True),
                 bg=BG, fg=WHITE).place(x=40, y=28)
        tk.Label(self, text=sub,
                 font=F(12), bg=BG, fg=TEXT2).place(x=40, y=60)

        self.scan_btn = tk.Button(self, text="  Analyze  ",
            font=F(12,True), bg=btn_color, fg=WHITE, relief="flat",
            bd=0, activebackground=PINK_L, activeforeground=WHITE,
            cursor="hand2", padx=6, pady=4, command=self._scan)
        self.scan_btn.place(x=40, y=96)

        # ── List ──────────────────────────────────────────────
        self.list_frame = tk.Frame(self, bg=BG)
        self.list_frame.place(x=0, y=146, relwidth=1, relheight=1, height=-210)

        lbl_frame = tk.Frame(self.list_frame, bg=SEP)
        lbl_frame.pack(fill="x")
        for txt,anchor,px in [("Category","w",56),("Description","w",12),
                               ("Size","e",16)]:
            tk.Label(lbl_frame, text=txt, font=F(9,True),
                     bg=SEP, fg=MUTED, padx=px, anchor=anchor,
                     ).pack(side="left" if anchor=="w" else "right",
                            pady=6, fill="x",
                            expand=(anchor=="w"))

        self.scroll_frame = tk.Frame(self.list_frame, bg=BG)
        self.scroll_frame.pack(fill="both", expand=True)

        # ── Status / action bar ───────────────────────────────
        bar = tk.Frame(self, bg=CARD, height=64)
        bar.place(x=0, rely=1.0, y=-64, relwidth=1, height=64)
        bar.pack_propagate(False)

        self.status_lbl = tk.Label(bar,
            text="Click Analyze to scan for junk",
            font=F(11), bg=CARD, fg=TEXT3)
        self.status_lbl.pack(side="left", padx=24)

        self.clean_btn = tk.Button(bar, text="  Clean Selected  ",
            font=F(13,True), bg=btn_color, fg=WHITE, relief="flat",
            bd=0, state="disabled", padx=6, pady=6,
            activebackground=PINK_L, activeforeground=WHITE,
            cursor="hand2", command=self._clean)
        self.clean_btn.pack(side="right", padx=24, pady=10)

    def _scan(self):
        for c in self.scroll_frame.winfo_children(): c.destroy()
        self.items.clear()
        self.scan_btn.config(state="disabled", text="  Scanning…  ")
        self.status_lbl.config(text="Scanning your Mac…", fg=TEXT2)
        threading.Thread(target=self._do_scan, daemon=True).start()

    def _do_scan(self):
        results = []
        for jd in self._defs:
            size = 0
            if jd.get("paths"):
                for p in jd["paths"]:
                    if Path(p).exists():
                        size += du(p)
            results.append((jd, size))
        self.after(0, lambda: self._show(results))

    def _show(self, results):
        self.scan_btn.config(state="normal", text="  Re-Analyze  ")
        total = sum(s for _,s in results)
        self.status_lbl.config(
            text=f"Found {fmt(total)} of junk across {len(results)} categories",
            fg=GREEN)
        self.clean_btn.config(state="normal")

        canvas = tk.Canvas(self.scroll_frame, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(self.scroll_frame, orient="vertical",
                          command=canvas.yview, bg=CARD, troughcolor=BG)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        inner = tk.Frame(canvas, bg=BG)
        win = canvas.create_window(0, 0, anchor="nw", window=inner)
        inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(win, width=e.width))

        for i,(jd,size) in enumerate(sorted(results, key=lambda x:-x[1])):
            self._add_row(inner, i, jd, size)

    def _add_row(self, parent, i, jd, size):
        bg  = CARD if i%2==0 else BG2
        row = tk.Frame(parent, bg=bg, height=60)
        row.pack(fill="x", pady=1)
        row.pack_propagate(False)

        var = tk.BooleanVar(value=size>0)
        tk.Checkbutton(row, variable=var, bg=bg,
                       activebackground=bg, selectcolor=BG2,
                       fg=PINK, activeforeground=PINK
                       ).pack(side="left", padx=(14,4), pady=10)

        tk.Label(row, text=jd["icon"], font=F(16), bg=bg,
                 fg=jd["color"]).pack(side="left", padx=(0,8))

        info = tk.Frame(row, bg=bg)
        info.pack(side="left", fill="both", expand=True, pady=10)
        tk.Label(info, text=jd["label"], font=F(12,True),
                 bg=bg, fg=WHITE, anchor="w").pack(anchor="w")
        tk.Label(info, text=jd["desc"], font=F(9),
                 bg=bg, fg=MUTED, anchor="w").pack(anchor="w")

        color = GREEN if size < 50<<20 else AMBER if size < 1<<30 else RED
        tk.Label(row, text=fmt(size), font=F(13,True),
                 bg=bg, fg=color, width=9).pack(side="right", padx=20)

        self.items.append({"jd":jd,"size":size,"var":var})

    def _clean(self):
        sel = [it for it in self.items if it["var"].get() and it["size"]>0]
        if not sel:
            messagebox.showinfo(APP,"No items selected."); return
        total = sum(it["size"] for it in sel)
        if not messagebox.askyesno(APP,
            f"Move {fmt(total)} of junk to Trash?\n\n"
            "Selected items will be trashed. Empty Trash to fully reclaim space.",
            icon="warning"): return
        self.clean_btn.config(state="disabled", text="  Cleaning…  ")
        threading.Thread(target=self._do_clean, args=(sel,), daemon=True).start()

    def _do_clean(self, sel):
        for it in sel:
            for p in (it["jd"].get("paths") or []):
                if Path(p).exists(): to_trash(str(p))
        self.after(0, self._after_clean)

    def _after_clean(self):
        self.clean_btn.config(state="normal", text="  Clean Selected  ")
        messagebox.showinfo(APP, "Done! Items moved to Trash.\nEmpty Trash to fully reclaim space.")
        self._scan()


# ════════════════════════════════════════════════════════════════
#  PRIVACY PAGE
# ════════════════════════════════════════════════════════════════
class PrivacyPage(Page):
    def __init__(self, master, app_ref, **kw):
        super().__init__(master, **kw)
        self.app    = app_ref
        self.items  = []
        self._built = False

    def on_resize(self, w, h):
        if not self._built:
            self._built = True
            self._build()

    def _build(self):
        for c in self.winfo_children(): c.destroy()
        self._draw_bg(self.winfo_width(), self.winfo_height())

        tk.Label(self, text="Privacy", font=F(24,True),
                 bg=BG, fg=WHITE).place(x=40, y=28)
        tk.Label(self, text="Clear browser history, cached websites, and usage traces.",
                 font=F(12), bg=BG, fg=TEXT2).place(x=40, y=60)

        self.scan_btn = tk.Button(self, text="  Scan  ",
            font=F(12,True), bg=PURPLE, fg=WHITE, relief="flat",
            bd=0, padx=6, pady=4, cursor="hand2",
            activebackground="#9b59b6", activeforeground=WHITE,
            command=self._scan)
        self.scan_btn.place(x=40, y=96)

        self.list_frame = tk.Frame(self, bg=BG)
        self.list_frame.place(x=0, y=146, relwidth=1, relheight=1, height=-210)

        lbl_frame = tk.Frame(self.list_frame, bg=SEP)
        lbl_frame.pack(fill="x")
        tk.Label(lbl_frame, text="Item",        font=F(9,True), bg=SEP,fg=MUTED,padx=56).pack(side="left",pady=6)
        tk.Label(lbl_frame, text="Description", font=F(9,True), bg=SEP,fg=MUTED,padx=12).pack(side="left",pady=6,fill="x",expand=True)
        tk.Label(lbl_frame, text="Size",        font=F(9,True), bg=SEP,fg=MUTED,padx=20).pack(side="right",pady=6)

        self.scroll_frame = tk.Frame(self.list_frame, bg=BG)
        self.scroll_frame.pack(fill="both", expand=True)

        bar = tk.Frame(self, bg=CARD, height=64)
        bar.place(x=0, rely=1.0, y=-64, relwidth=1, height=64)
        bar.pack_propagate(False)
        self.status_lbl = tk.Label(bar, text="Scan to find privacy-related data",
                                   font=F(11), bg=CARD, fg=TEXT3)
        self.status_lbl.pack(side="left", padx=24)
        self.clean_btn = tk.Button(bar, text="  Clear Selected  ",
            font=F(13,True), bg=PURPLE, fg=WHITE, relief="flat",
            bd=0, state="disabled", padx=6, pady=6, cursor="hand2",
            activebackground="#9b59b6", activeforeground=WHITE,
            command=self._clean)
        self.clean_btn.pack(side="right", padx=24, pady=10)

    def _scan(self):
        for c in self.scroll_frame.winfo_children(): c.destroy()
        self.items.clear()
        self.scan_btn.config(state="disabled", text="  Scanning…  ")
        threading.Thread(target=self._do_scan, daemon=True).start()

    def _do_scan(self):
        results = []
        for td in PRIV_TARGETS:
            size = sum(du(p) for p in td["paths"] if Path(p).exists())
            results.append((td, size))
        self.after(0, lambda: self._show(results))

    def _show(self, results):
        self.scan_btn.config(state="normal", text="  Re-Scan  ")
        total = sum(s for _,s in results)
        self.status_lbl.config(
            text=f"Found {fmt(total)} of privacy-related data", fg=TEAL)
        self.clean_btn.config(state="normal")

        canvas = tk.Canvas(self.scroll_frame, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(self.scroll_frame, orient="vertical",
                          command=canvas.yview, bg=CARD, troughcolor=BG)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        inner = tk.Frame(canvas, bg=BG)
        win = canvas.create_window(0,0, anchor="nw", window=inner)
        inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(win, width=e.width))

        for i,(td,size) in enumerate(sorted(results, key=lambda x:-x[1])):
            bg = CARD if i%2==0 else BG2
            row = tk.Frame(inner, bg=bg, height=60)
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)
            var = tk.BooleanVar(value=size>0)
            tk.Checkbutton(row,variable=var,bg=bg,activebackground=bg,
                           selectcolor=BG2,fg=PURPLE,activeforeground=PURPLE
                           ).pack(side="left",padx=(14,4),pady=10)
            tk.Label(row,text=td["icon"],font=F(15),bg=bg,fg=td["color"]
                     ).pack(side="left",padx=(0,8))
            info = tk.Frame(row,bg=bg)
            info.pack(side="left",fill="both",expand=True,pady=10)
            tk.Label(info,text=td["label"],font=F(12,True),bg=bg,fg=WHITE,anchor="w").pack(anchor="w")
            tk.Label(info,text=td["desc"],font=F(9),bg=bg,fg=MUTED,anchor="w").pack(anchor="w")
            col = GREEN if size<10<<20 else AMBER if size<200<<20 else RED
            tk.Label(row,text=fmt(size),font=F(13,True),bg=bg,fg=col,width=9).pack(side="right",padx=20)
            self.items.append({"td":td,"size":size,"var":var})

    def _clean(self):
        sel = [it for it in self.items if it["var"].get() and it["size"]>0]
        if not sel: messagebox.showinfo(APP,"Nothing selected."); return
        total = sum(it["size"] for it in sel)
        if not messagebox.askyesno(APP,
            f"Clear {fmt(total)} of privacy data?\n\nThis will be moved to Trash.",
            icon="warning"): return
        for it in sel:
            for p in it["td"]["paths"]:
                if Path(p).exists(): to_trash(str(p))
        messagebox.showinfo(APP,"Privacy data cleared!")
        self._scan()


# ════════════════════════════════════════════════════════════════
#  PERFORMANCE PAGE
# ════════════════════════════════════════════════════════════════
class PerformancePage(Page):
    def __init__(self, master, app_ref, **kw):
        super().__init__(master, **kw)
        self.app    = app_ref
        self._built = False
        self._tab   = "login"

    def on_resize(self, w, h):
        if not self._built:
            self._built = True
            self._build()

    def _build(self):
        for c in self.winfo_children(): c.destroy()
        self._draw_bg(self.winfo_width(), self.winfo_height())

        tk.Label(self, text="Performance", font=F(24,True),
                 bg=BG, fg=WHITE).place(x=40, y=28)
        tk.Label(self, text="Manage login items and background services.",
                 font=F(12), bg=BG, fg=TEXT2).place(x=40, y=60)

        # Tab bar
        tab_frame = tk.Frame(self, bg=CARD)
        tab_frame.place(x=40, y=96, height=36)
        for label, key in [("Login Items","login"),("Launch Agents","agents")]:
            active = key == self._tab
            tb = tk.Button(tab_frame, text=f"  {label}  ",
                font=F(11,bold=active),
                bg=PURPLE if active else CARD,
                fg=WHITE if active else TEXT3,
                relief="flat", bd=0, pady=6, cursor="hand2",
                activebackground=PURPLE, activeforeground=WHITE,
                command=lambda k=key: self._switch(k))
            tb.pack(side="left")

        self.list_frame = tk.Frame(self, bg=BG)
        self.list_frame.place(x=0, y=148, relwidth=1, relheight=1, height=-148)

        if self._tab == "login":
            self._load_login()
        else:
            self._load_agents()

    def _switch(self, tab):
        self._tab = tab
        self._built = False
        self._build()

    def _load_login(self):
        for c in self.list_frame.winfo_children(): c.destroy()
        items = []
        try:
            r = subprocess.run(
                ["osascript","-e",
                 'tell application "System Events" to get the name of every login item'],
                capture_output=True, text=True, timeout=10)
            if r.returncode == 0 and r.stdout.strip():
                items = [x.strip() for x in r.stdout.strip().split(",") if x.strip()]
        except: pass

        if not items:
            tk.Label(self.list_frame,
                text="No login items found.\n\n"
                     "If you expect items here, grant permission in:\n"
                     "System Settings → Privacy & Security → Automation",
                font=F(12), bg=BG, fg=MUTED, justify="center",
                wraplength=500).pack(pady=60)
            return

        canvas = tk.Canvas(self.list_frame, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(self.list_frame, orient="vertical",
                          command=canvas.yview, bg=CARD, troughcolor=BG)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        inner = tk.Frame(canvas, bg=BG)
        win = canvas.create_window(0,0,anchor="nw",window=inner)
        inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(win,width=e.width))

        for i,name in enumerate(items):
            bg = CARD if i%2==0 else BG2
            row = tk.Frame(inner, bg=bg, height=56)
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)
            tk.Label(row,text="⚡",font=F(16),bg=bg,fg=AMBER).pack(side="left",padx=16,pady=10)
            info = tk.Frame(row,bg=bg)
            info.pack(side="left",fill="both",expand=True,pady=10)
            tk.Label(info,text=name,font=F(12,True),bg=bg,fg=WHITE,anchor="w").pack(anchor="w")
            tk.Label(info,text="Launches at every login",font=F(9),bg=bg,fg=MUTED,anchor="w").pack(anchor="w")
            tk.Button(row,text="Remove",font=F(10),
                     bg="#3d1520",fg=RED,relief="flat",bd=0,padx=10,pady=4,
                     cursor="hand2",
                     command=lambda n=name: self._remove_login(n)
                     ).pack(side="right",padx=16,pady=10)

    def _remove_login(self, name):
        if not messagebox.askyesno(APP,f"Remove '{name}' from login items?"): return
        try:
            subprocess.run(["osascript","-e",
                f'tell application "System Events" to delete login item "{name}"'],
                capture_output=True, timeout=10)
        except: pass
        self._load_login()

    def _load_agents(self):
        for c in self.list_frame.winfo_children(): c.destroy()
        dirs  = [HOME/"Library"/"LaunchAgents",
                 Path("/Library/LaunchAgents"),
                 Path("/Library/LaunchDaemons")]
        agents = []
        for d in dirs:
            if d.exists():
                for f in sorted(d.glob("*.plist")):
                    agents.append((f.name, str(d), f))

        if not agents:
            tk.Label(self.list_frame,text="No launch agents found.",
                    font=F(12),bg=BG,fg=MUTED).pack(pady=60)
            return

        canvas = tk.Canvas(self.list_frame, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(self.list_frame, orient="vertical",
                          command=canvas.yview, bg=CARD, troughcolor=BG)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        inner = tk.Frame(canvas, bg=BG)
        win = canvas.create_window(0,0,anchor="nw",window=inner)
        inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(win,width=e.width))

        for i,(name,loc,path) in enumerate(agents[:80]):
            bg = CARD if i%2==0 else BG2
            row = tk.Frame(inner, bg=bg)
            row.pack(fill="x", pady=1)
            tk.Label(row,text="⚙",font=F(14),bg=bg,fg=BLUE).pack(side="left",padx=16,pady=10)
            info = tk.Frame(row,bg=bg)
            info.pack(side="left",fill="both",expand=True,pady=8)
            tk.Label(info,text=name,font=F(11,True),bg=bg,fg=WHITE,anchor="w").pack(anchor="w")
            tk.Label(info,text=loc, font=F(8),    bg=bg,fg=MUTED,anchor="w").pack(anchor="w")


# ════════════════════════════════════════════════════════════════
#  MALWARE PAGE
# ════════════════════════════════════════════════════════════════
class MalwarePage(Page):
    def __init__(self, master, app_ref, **kw):
        super().__init__(master, **kw)
        self.app      = app_ref
        self.scanning = False
        self._built   = False

    def on_resize(self, w, h):
        if not self._built:
            self._built = True
            self._build()

    def _build(self):
        for c in self.winfo_children(): c.destroy()
        self._draw_bg(self.winfo_width(), self.winfo_height())

        tk.Label(self, text="Malware Scan", font=F(24,True),
                 bg=BG, fg=WHITE).place(x=40, y=28)
        tk.Label(self, text="Detect suspicious launch agents, adware, and browser extensions.",
                 font=F(12), bg=BG, fg=TEXT2).place(x=40, y=60)

        self.scan_btn = tk.Button(self, text="  Start Scan  ",
            font=F(13,True), bg=RED, fg=WHITE, relief="flat",
            bd=0, padx=8, pady=6, cursor="hand2",
            activebackground="#e53935", activeforeground=WHITE,
            command=self._start)
        self.scan_btn.place(x=40, y=96)

        self.result_frame = tk.Frame(self, bg=BG)
        self.result_frame.place(x=40, y=160, relwidth=1, width=-80, relheight=1, height=-190)

        self.status_lbl = tk.Label(self,
            text="Your Mac has not been scanned yet.",
            font=F(11), bg=BG, fg=MUTED)
        self.status_lbl.place(relx=0.5, rely=1.0, y=-32, anchor="center")

    def _start(self):
        if self.scanning: return
        self.scanning = True
        self.scan_btn.config(state="disabled", text="  Scanning…  ")
        for c in self.result_frame.winfo_children(): c.destroy()
        self.status_lbl.config(text="Scanning for threats…", fg=TEXT2)
        threading.Thread(target=self._do_scan, daemon=True).start()

    def _do_scan(self):
        threats = []
        known_safe = {"com.apple","com.google","com.microsoft","org.macports",
                      "com.homebrew","com.spotify","com.adobe","com.dropbox",
                      "io.tailscale","com.docker","com.jetbrains","com.github"}

        for d in [HOME/"Library"/"LaunchAgents", Path("/Library/LaunchAgents")]:
            if not d.exists(): continue
            for f in d.glob("*.plist"):
                nm = f.stem.lower()
                if not any(nm.startswith(s) for s in known_safe):
                    threats.append(dict(
                        type="Suspicious Launch Agent",
                        path=str(f), severity="medium",
                        desc=f"Unknown: {f.name}"))

        ext_dir = HOME/"Library"/"Application Support"/"Google"/"Chrome"/"Default"/"Extensions"
        if ext_dir.exists():
            n = len([x for x in ext_dir.iterdir() if x.is_dir()])
            if n > 10:
                threats.append(dict(
                    type="Many Chrome Extensions",
                    path=str(ext_dir), severity="low",
                    desc=f"{n} Chrome extensions installed — review for unwanted ones"))

        for s in [HOME/"Library"/"Application Support"/"Adobe"/"OOBE"/"PDApp"/"core"]:
            if s.exists():
                threats.append(dict(
                    type="Potentially Unwanted Program",
                    path=str(s), severity="low",
                    desc="Adobe installer helper found in background services"))

        tmp_scripts = list(Path("/tmp").glob("*.sh")) + list(Path("/tmp").glob("*.py"))
        if tmp_scripts:
            threats.append(dict(
                type="Scripts in /tmp",
                path="/tmp", severity="low",
                desc=f"{len(tmp_scripts)} script(s) in /tmp — verify they're yours"))

        time.sleep(1.8)
        self.after(0, lambda: self._show(threats))

    def _show(self, threats):
        self.scanning = False
        self.scan_btn.config(state="normal", text="  Re-Scan  ")

        if not threats:
            self.status_lbl.config(text="✓  No threats found — Your Mac is clean!", fg=GREEN)
            tk.Label(self.result_frame, text="🛡", font=F(52), bg=BG, fg=GREEN).pack(pady=24)
            tk.Label(self.result_frame, text="No malware or suspicious items detected",
                    font=F(15,True), bg=BG, fg=GREEN).pack()
            tk.Label(self.result_frame, text="Your Mac looks healthy.",
                    font=F(11), bg=BG, fg=MUTED).pack(pady=8)
            return

        self.status_lbl.config(text=f"Found {len(threats)} potential issue(s) — review below",
                               fg=AMBER)
        canvas = tk.Canvas(self.result_frame, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(self.result_frame, orient="vertical",
                          command=canvas.yview, bg=CARD, troughcolor=BG)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        inner = tk.Frame(canvas, bg=BG)
        win = canvas.create_window(0,0,anchor="nw",window=inner)
        inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(win,width=e.width))

        for i,t in enumerate(threats):
            bg = CARD if i%2==0 else BG2
            row = tk.Frame(inner, bg=bg, height=62)
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)
            col = {dict(high=RED,medium=AMBER,low=BLUE).get(t["severity"],BLUE): 1}
            sc  = RED if t["severity"]=="high" else AMBER if t["severity"]=="medium" else BLUE
            tk.Label(row,text="⚠",font=F(18),bg=bg,fg=sc).pack(side="left",padx=16,pady=12)
            info = tk.Frame(row,bg=bg)
            info.pack(side="left",fill="both",expand=True,pady=10)
            tk.Label(info,text=t["type"],font=F(12,True),bg=bg,fg=WHITE,anchor="w").pack(anchor="w")
            tk.Label(info,text=t["desc"],font=F(9),bg=bg,fg=MUTED,anchor="w").pack(anchor="w")
            tk.Label(row,text=t["severity"].upper(),font=F(9,True),
                    bg=bg,fg=sc,width=8).pack(side="right",padx=16)


# ════════════════════════════════════════════════════════════════
#  SPACE LENS PAGE
# ════════════════════════════════════════════════════════════════
class SpaceLensPage(Page):
    COLORS = [PINK, PURPLE, BLUE, TEAL, GREEN, AMBER, RED, PINK_L,
              "#a78bfa","#34d399","#fb7185","#60a5fa"]

    def __init__(self, master, app_ref, **kw):
        super().__init__(master, **kw)
        self.app      = app_ref
        self._built   = False
        self._path    = HOME
        self._entries = []
        self._bubbles = []   # (cx,cy,r,entry,color)
        self._hover   = None
        self.bind("<Motion>",   self._motion)
        self.bind("<Button-1>", self._click)

    def on_resize(self, w, h):
        if not self._built:
            self._built = True
            self._scan(HOME)

    def _scan(self, path):
        self._path = path
        self._entries = []
        self._bubbles = []
        self.delete("all")
        w,h = self.winfo_width(), self.winfo_height()
        self._draw_bg(w, h)
        self.create_text(w//2, h//2, text=f"Reading {path.name}…",
                         font=F(14), fill=TEXT2, tags="loading")
        threading.Thread(target=self._do_scan, args=(path,), daemon=True).start()

    def _do_scan(self, path):
        entries = []
        try:
            for e in os.scandir(path):
                try:
                    if e.is_symlink(): continue
                    size = du(e.path)
                    entries.append({"name":e.name,"path":Path(e.path),
                                    "size":size,"is_dir":e.is_dir()})
                except: pass
        except: pass
        entries.sort(key=lambda x:-x["size"])
        self._entries = entries
        self.after(0, self._render_bubbles)

    def _render_bubbles(self):
        self.delete("all")
        w,h = self.winfo_width(), self.winfo_height()
        self._draw_bg(w, h)
        self._bubbles.clear()

        # Header
        self.create_text(40, 26, text=f"◎  Space Lens  —  {self._path}",
                         font=F(13,True), fill=WHITE, anchor="w")
        total = sum(e["size"] for e in self._entries)
        self.create_text(40, 48, text=f"Total: {fmt(total)}  ·  {len(self._entries)} items",
                         font=F(10), fill=TEXT3, anchor="w")

        if self._path != HOME:
            self.create_text(w-20, 36, text="← Back",
                             font=F(11,True), fill=BLUE, anchor="e", tags="back_btn")

        if not self._entries:
            self.create_text(w//2, h//2, text="Empty folder",
                             font=F(14), fill=MUTED); return

        area_x, area_y = 20, 66
        area_w, area_h = w-40, h-76
        max_sz = self._entries[0]["size"] or 1

        placed = []
        rng = random.Random(42)  # deterministic

        for i, entry in enumerate(self._entries[:24]):
            ratio = (entry["size"]/max_sz) ** 0.5
            r = max(22, min(int(ratio*100), area_h//2-10))
            color = self.COLORS[i % len(self.COLORS)]

            # Find position
            for _ in range(400):
                cx = rng.randint(area_x+r, area_x+area_w-r)
                cy = rng.randint(area_y+r, area_y+area_h-r)
                ok = all(math.sqrt((cx-px)**2+(cy-py)**2) > r+pr+8
                         for px,py,pr,_,_ in placed)
                if ok:
                    placed.append((cx,cy,r,entry,color)); break

        for cx,cy,r,entry,color in placed:
            # glow
            self.create_oval(cx-r-6,cy-r-6,cx+r+6,cy+r+6,
                             fill=ab(color,"22"),outline="")
            # fill
            self.create_oval(cx-r,cy-r,cx+r,cy+r,
                             fill=ab(color,"99"),outline=color,width=2)
            # label
            if r >= 32:
                nm = entry["name"][:13]+"…" if len(entry["name"])>13 else entry["name"]
                self.create_text(cx,cy-9,  text=nm,      font=F(9,True), fill=WHITE)
                self.create_text(cx,cy+10, text=fmt(entry["size"]),font=F(8),fill=ab(WHITE,"88"))
            elif r >= 22:
                self.create_text(cx,cy, text=fmt(entry["size"]),font=F(7),fill=WHITE)
            self._bubbles.append((cx,cy,r,entry,color))

    def _hit(self, x, y):
        for cx,cy,r,entry,_ in self._bubbles:
            if math.sqrt((x-cx)**2+(y-cy)**2) <= r: return entry
        return None

    def _motion(self, e):
        hit = self._hit(e.x, e.y)
        if hit != self._hover:
            self._hover = hit
            self.delete("tooltip")
            if hit:
                self._draw_tip(e.x, e.y, hit)
            self.config(cursor="hand2" if hit else "")

    def _draw_tip(self, x, y, entry):
        w = self.winfo_width()
        tx = min(x+14, w-185)
        ty = max(y-70, 70)
        rr(self,tx,ty,tx+180,ty+60,radius=10,
           fill=CARD,outline=SEP,width=1,tags="tooltip")
        self.create_text(tx+12,ty+14,anchor="w",text=entry["name"],
                         font=F(11,True),fill=WHITE,tags="tooltip")
        self.create_text(tx+12,ty+32,anchor="w",text=fmt(entry["size"]),
                         font=F(10),fill=TEXT2,tags="tooltip")
        kind = "Folder — click to drill in" if entry["is_dir"] else "File"
        self.create_text(tx+12,ty+48,anchor="w",text=kind,
                         font=F(9),fill=MUTED,tags="tooltip")

    def _click(self, e):
        # Back button
        if self._path != HOME:
            items = self.find_withtag("back_btn")
            if items:
                x1,y1,x2,y2 = self.bbox(items[0])
                if x1<=e.x<=x2 and y1<=e.y<=y2:
                    self._scan(self._path.parent); return
        hit = self._hit(e.x, e.y)
        if hit and hit["is_dir"]:
            self._scan(hit["path"])


# ════════════════════════════════════════════════════════════════
#  LARGE & OLD FILES PAGE
# ════════════════════════════════════════════════════════════════
class LargeFilesPage(Page):
    def __init__(self, master, app_ref, **kw):
        super().__init__(master, **kw)
        self.app    = app_ref
        self._built = False

    def on_resize(self, w, h):
        if not self._built:
            self._built = True
            self._build()

    def _build(self):
        for c in self.winfo_children(): c.destroy()
        self._draw_bg(self.winfo_width(), self.winfo_height())

        tk.Label(self, text="Large & Old Files", font=F(24,True),
                 bg=BG, fg=WHITE).place(x=40, y=28)
        tk.Label(self,
            text="Find files over 100 MB that haven't been opened recently.",
            font=F(12), bg=BG, fg=TEXT2).place(x=40, y=60)

        tk.Button(self, text="  Find Large Files  ",
            font=F(12,True), bg=AMBER, fg="#000000",
            relief="flat", bd=0, padx=6, pady=4,
            cursor="hand2",
            activebackground="#ffd54f", activeforeground="#000000",
            command=self._scan).place(x=40, y=96)

        frame = tk.Frame(self, bg=BG)
        frame.place(x=0, y=146, relwidth=1, relheight=1, height=-180)

        # Header row
        hdr = tk.Frame(frame, bg=SEP)
        hdr.pack(fill="x")
        tk.Label(hdr,text="File",        font=F(9,True),bg=SEP,fg=MUTED,padx=60).pack(side="left",pady=6)
        tk.Label(hdr,text="",            font=F(9,True),bg=SEP,fg=MUTED).pack(side="left",fill="x",expand=True)
        tk.Label(hdr,text="Size",        font=F(9,True),bg=SEP,fg=MUTED,padx=12,width=10).pack(side="left")
        tk.Label(hdr,text="Last Used",   font=F(9,True),bg=SEP,fg=MUTED,padx=12,width=12).pack(side="left")
        tk.Label(hdr,text="",            font=F(9,True),bg=SEP,fg=MUTED,width=10).pack(side="right",padx=20)

        self.list_canvas = tk.Canvas(frame, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(frame, orient="vertical",
                          command=self.list_canvas.yview, bg=CARD, troughcolor=BG)
        self.list_canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.list_canvas.pack(fill="both", expand=True)
        self.inner = tk.Frame(self.list_canvas, bg=BG)
        self._win = self.list_canvas.create_window(0,0,anchor="nw",window=self.inner)
        self.inner.bind("<Configure>",
            lambda e: self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all")))
        self.list_canvas.bind("<Configure>",
            lambda e: self.list_canvas.itemconfig(self._win,width=e.width))

        self.status = tk.Label(self,
            text="Click 'Find Large Files' to search ~/Downloads, ~/Documents, ~/Desktop, ~/Movies",
            font=F(10), bg=BG, fg=MUTED)
        self.status.place(relx=0.5, rely=1.0, y=-28, anchor="center")

    def _scan(self):
        for c in self.inner.winfo_children(): c.destroy()
        self.status.config(text="Searching… (may take a moment)", fg=TEXT2)
        threading.Thread(target=self._do_scan, daemon=True).start()

    def _do_scan(self):
        results = []
        MIN = 100<<20
        now = time.time()
        for base in [HOME/"Downloads",HOME/"Documents",HOME/"Desktop",
                     HOME/"Movies",HOME/"Music"]:
            if not base.exists(): continue
            try:
                for root,dirs,files in os.walk(base):
                    dirs[:] = [d for d in dirs if not d.startswith(".")]
                    for fn in files:
                        if fn.startswith("."): continue
                        fp = Path(root)/fn
                        try:
                            st = fp.stat()
                            if st.st_size >= MIN:
                                results.append({
                                    "path":fp,"name":fn,"size":st.st_size,
                                    "days":int((now-st.st_atime)/86400),
                                    "mod":datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d"),
                                })
                        except: pass
            except: pass
        results.sort(key=lambda x:-x["size"])
        self.after(0, lambda: self._show(results))

    def _show(self, results):
        for c in self.inner.winfo_children(): c.destroy()
        if not results:
            self.status.config(text="No files over 100 MB found — great!", fg=GREEN)
            return
        total = sum(f["size"] for f in results)
        self.status.config(
            text=f"Found {len(results)} files  ·  {fmt(total)} total",
            fg=AMBER)
        EXT_ICONS = {"zip":"◆","dmg":"◈","pkg":"◉","mp4":"◎","mov":"◎",
                     "avi":"◎","mkv":"◎","iso":"◇","rar":"◆","tar":"◆"}
        for i,f in enumerate(results[:120]):
            bg = CARD if i%2==0 else BG2
            row = tk.Frame(self.inner, bg=bg)
            row.pack(fill="x", pady=1)
            ext = f["name"].rsplit(".",1)[-1].lower() if "." in f["name"] else ""
            icon = EXT_ICONS.get(ext,"◆")
            tk.Label(row,text=icon,font=F(14),bg=bg,fg=AMBER).pack(side="left",padx=16,pady=10)
            info = tk.Frame(row,bg=bg)
            info.pack(side="left",fill="both",expand=True,pady=8)
            nm = f["name"][:46]+"…" if len(f["name"])>46 else f["name"]
            tk.Label(info,text=nm,font=F(10,True),bg=bg,fg=WHITE,anchor="w").pack(anchor="w")
            parent = str(f["path"].parent).replace(str(HOME),"~")
            tk.Label(info,text=parent,font=F(8),bg=bg,fg=MUTED,anchor="w").pack(anchor="w")
            col = RED if f["size"]>1<<30 else AMBER
            tk.Label(row,text=fmt(f["size"]),font=F(11,True),bg=bg,fg=col,width=9).pack(side="left",padx=8)
            days = f["days"]
            age = f"{days}d ago" if days<365 else f"{days//365}y ago"
            tk.Label(row,text=age,font=F(10),bg=bg,fg=MUTED,width=10).pack(side="left",padx=8)
            tk.Button(row,text="Trash",font=F(9),
                     bg="#3d1520",fg=RED,relief="flat",bd=0,padx=8,pady=4,
                     cursor="hand2",
                     command=lambda p=f["path"],r=row: self._trash_one(p,r)
                     ).pack(side="right",padx=16,pady=8)

    def _trash_one(self, path, row):
        if messagebox.askyesno(APP,f"Move to Trash?\n{path}"):
            to_trash(str(path))
            row.destroy()


# ════════════════════════════════════════════════════════════════
#  UNINSTALLER PAGE
# ════════════════════════════════════════════════════════════════
class UninstallerPage(Page):
    def __init__(self, master, app_ref, **kw):
        super().__init__(master, **kw)
        self.app    = app_ref
        self._built = False

    def on_resize(self, w, h):
        if not self._built:
            self._built = True
            self._build()

    def _build(self):
        for c in self.winfo_children(): c.destroy()
        self._draw_bg(self.winfo_width(), self.winfo_height())

        tk.Label(self, text="Uninstaller", font=F(24,True),
                 bg=BG, fg=WHITE).place(x=40, y=28)
        tk.Label(self,
            text="Remove applications and their leftover data completely.",
            font=F(12), bg=BG, fg=TEXT2).place(x=40, y=60)

        frame = tk.Frame(self, bg=BG)
        frame.place(x=0, y=110, relwidth=1, relheight=1, height=-110)

        hdr = tk.Frame(frame, bg=SEP)
        hdr.pack(fill="x")
        tk.Label(hdr,text="Application",font=F(9,True),bg=SEP,fg=MUTED,padx=60).pack(side="left",pady=8)
        tk.Label(hdr,text="",           font=F(9,True),bg=SEP,fg=MUTED).pack(side="left",fill="x",expand=True)
        tk.Label(hdr,text="Size",       font=F(9,True),bg=SEP,fg=MUTED,padx=16,width=10).pack(side="left")
        tk.Label(hdr,text="",           font=F(9,True),bg=SEP,fg=MUTED,width=14).pack(side="right",padx=16)

        canvas = tk.Canvas(frame, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(frame, orient="vertical",
                          command=canvas.yview, bg=CARD, troughcolor=BG)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        inner = tk.Frame(canvas, bg=BG)
        win = canvas.create_window(0,0,anchor="nw",window=inner)
        inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(win,width=e.width))

        threading.Thread(target=lambda: self._load(inner), daemon=True).start()

    def _load(self, inner):
        apps = []
        for folder in [Path("/Applications"), HOME/"Applications"]:
            if folder.exists():
                for a in sorted(folder.glob("*.app")):
                    apps.append({"name":a.stem,"path":a,"size":du(a)})
        apps.sort(key=lambda x:-x["size"])
        self.after(0, lambda: self._show(inner, apps))

    def _show(self, inner, apps):
        for c in inner.winfo_children(): c.destroy()
        if not apps:
            tk.Label(inner,text="No applications found.",
                    font=F(12),bg=BG,fg=MUTED).pack(pady=40); return

        for i,app in enumerate(apps):
            bg = CARD if i%2==0 else BG2
            row = tk.Frame(inner, bg=bg, height=60)
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)
            tk.Label(row,text="◈",font=F(18),bg=bg,fg=BLUE).pack(side="left",padx=16,pady=10)
            info = tk.Frame(row,bg=bg)
            info.pack(side="left",fill="both",expand=True,pady=10)
            tk.Label(info,text=app["name"],font=F(13,True),bg=bg,fg=WHITE,anchor="w").pack(anchor="w")
            tk.Label(info,text=str(app["path"].parent),
                    font=F(8),bg=bg,fg=MUTED,anchor="w").pack(anchor="w")
            col = RED if app["size"]>500<<20 else AMBER if app["size"]>100<<20 else GREEN
            tk.Label(row,text=fmt(app["size"]),font=F(12,True),
                    bg=bg,fg=col,width=9).pack(side="left",padx=8)
            tk.Button(row,text="Uninstall",font=F(10),
                     bg="#3d1520",fg=RED,relief="flat",bd=0,padx=8,pady=4,
                     cursor="hand2",
                     command=lambda a=app,r=row: self._uninstall(a,r)
                     ).pack(side="right",padx=16,pady=10)

    def _uninstall(self, app, row):
        if not messagebox.askyesno(APP,
            f"Uninstall {app['name']}?\n\n"
            f"The .app ({fmt(app['size'])}) and support files will be trashed.",
            icon="warning"): return
        to_trash(str(app["path"]))
        for lf in [
            HOME/"Library"/"Application Support"/app["name"],
            HOME/"Library"/"Preferences"/f"com.{app['name'].lower()}.plist",
            HOME/"Library"/"Caches"/f"com.{app['name'].lower()}",
            HOME/"Library"/"Logs"/app["name"],
        ]:
            if lf.exists(): to_trash(str(lf))
        row.destroy()
        messagebox.showinfo(APP, f"✓ {app['name']} uninstalled!")


# ════════════════════════════════════════════════════════════════
#  PLACEHOLDER PAGE
# ════════════════════════════════════════════════════════════════
class LockedPage(Page):
    """Beautiful 'Coming in v3.0' preview for locked/upcoming features."""
    def __init__(self, master, key, **kw):
        super().__init__(master, **kw)
        self._key = key
        self._info = LOCKED_INFO.get(key, dict(
            title=key.title(), icon="⊕", color=PURPLE, version="v3.0",
            tagline="Coming soon", desc="This feature is under development.",
            benefits=[]))
        self._star_hover = False
        self.bind("<Motion>", self._on_motion)
        self.bind("<Button-1>", self._on_click)

    def on_resize(self, w, h):
        self.delete("all")
        self._draw_bg(w, h)
        info = self._info
        color = info["color"]
        cx = w // 2

        # --- top badge row ---
        badge_y = 68
        badge_w = 110
        rr(self, cx - badge_w//2, badge_y - 14, cx + badge_w//2, badge_y + 14,
           radius=12, fill=ab(AMBER, "22"), outline=ab(AMBER, "55"), width=1)
        self.create_text(cx, badge_y, text=f"✦  Coming in {info['version']}",
                         font=F(9, True), fill=AMBER, anchor="center")

        # --- large icon with glow ---
        icon_y = 160
        glow_oval(self, cx, icon_y, 68, color)
        self.create_text(cx, icon_y, text=info["icon"], font=F(54),
                         fill=color, anchor="center")

        # --- title + tagline ---
        self.create_text(cx, icon_y + 78, text=info["title"],
                         font=F(28, True), fill=WHITE, anchor="center")
        self.create_text(cx, icon_y + 114, text=info["tagline"],
                         font=F(13), fill=TEXT2, anchor="center")

        # --- description card ---
        card_y = icon_y + 148
        card_w = min(w - 120, 560)
        card_x1, card_x2 = cx - card_w//2, cx + card_w//2
        rr(self, card_x1, card_y, card_x2, card_y + 66, radius=14,
           fill=ab(color, "18", BG2), outline=ab(color, "30"), width=1)
        self.create_text(cx, card_y + 33, text=info["desc"],
                         font=F(11), fill=TEXT2, anchor="center",
                         width=card_w - 40)

        # --- benefits bullets ---
        bul_y = card_y + 88
        benefits = info.get("benefits", [])
        if benefits:
            cols = 2
            per_col = math.ceil(len(benefits) / cols)
            col_w = card_w // cols
            for i, b in enumerate(benefits):
                col = i % cols
                row = i // cols
                bx = card_x1 + col * col_w + 20
                by = bul_y + row * 28
                # dot
                self.create_oval(bx - 2, by + 5, bx + 6, by + 13,
                                 fill=color, outline="")
                self.create_text(bx + 14, by + 9, text=b,
                                 font=F(11), fill=TEXT2, anchor="w")

        # --- CTA button ---
        btn_y = bul_y + per_col * 28 + 28 if benefits else card_y + 100
        btn_h = 44
        btn_w = 200
        self._btn = (cx - btn_w//2, btn_y, cx + btn_w//2, btn_y + btn_h)
        rr(self, *self._btn, radius=22,
           fill=ab(color, "33"), outline=color, width=1)
        self.create_text(cx, btn_y + btn_h//2,
                         text="★  Star us on GitHub",
                         font=F(12, True), fill=color, anchor="center",
                         tags="star_btn")

    def _on_motion(self, e):
        if hasattr(self, "_btn"):
            x1, y1, x2, y2 = self._btn
            inside = x1 <= e.x <= x2 and y1 <= e.y <= y2
            self.config(cursor="hand2" if inside else "")

    def _on_click(self, e):
        if hasattr(self, "_btn"):
            x1, y1, x2, y2 = self._btn
            if x1 <= e.x <= x2 and y1 <= e.y <= y2:
                import webbrowser
                webbrowser.open("https://github.com/harrytinklecloud/CleanDaMacintosh")


class PlaceholderPage(Page):
    def __init__(self, master, title, icon, color, **kw):
        super().__init__(master, **kw)
        self._t, self._i, self._c = title, icon, color

    def on_resize(self, w, h):
        self.delete("all")
        self._draw_bg(w, h)
        cx, cy = w//2, h//2
        glow_oval(self, cx, cy-40, 50, self._c)
        self.create_text(cx, cy-40, text=self._i, font=F(48),
                         fill=self._c, anchor="center")
        self.create_text(cx, cy+30,  text=self._t, font=F(24,True),
                         fill=WHITE, anchor="center")
        self.create_text(cx, cy+64,  text="Coming in a future update",
                         font=F(12), fill=MUTED, anchor="center")
        rr(self, cx-80, cy+84, cx+80, cy+116, radius=12,
           fill=ab(self._c,"22"), outline=ab(self._c,"55"), width=1)
        self.create_text(cx, cy+100, text="★  Star us on GitHub",
                         font=F(10), fill=self._c, anchor="center")


# ════════════════════════════════════════════════════════════════
#  MAIN APP WINDOW
# ════════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP)
        self.geometry(f"{WIN_W}x{WIN_H}+{(self.winfo_screenwidth()-WIN_W)//2}"
                      f"+{(self.winfo_screenheight()-WIN_H)//2}")
        self.minsize(900, 600)
        self.configure(bg=BG)

        if sys.platform == "darwin":
            try:
                # Dark title bar on macOS
                self.tk.call("::tk::unsupported::MacWindowStyle",
                             "style", self._w, "document",
                             "closeBox collapseBox resizeBox")
            except: pass

        self._pages: dict = {}
        self._current = None
        self._build()
        self._show("smartcare", "Smart Care")

    def _build(self):
        self.sidebar = Sidebar(self, self._show)
        self.sidebar.pack(side="left", fill="y")

        self.content = tk.Frame(self, bg=BG)
        self.content.pack(side="left", fill="both", expand=True)

    def _show(self, key, label=""):
        if key is None: return
        if self._current:
            self._current.pack_forget()
        if key not in self._pages:
            self._pages[key] = self._make(key)
        page = self._pages[key]
        page.pack(fill="both", expand=True)
        self._current = page

    def _make(self, key):
        c = self.content
        # Keys in LOCKED_INFO always show the locked preview page
        if key in LOCKED_INFO:
            return LockedPage(c, key)
        MAP = {
            "smartcare":  lambda: SmartCarePage(c, self),
            "junk":       lambda: JunkPage(c, self, mode="all"),
            "mail":       lambda: JunkPage(c, self, mode="mail"),
            "trash":      lambda: JunkPage(c, self, mode="trash"),
            "malware":    lambda: MalwarePage(c, self),
            "privacy":    lambda: PrivacyPage(c, self),
            "optimize":   lambda: PerformancePage(c, self),
            "uninstall":  lambda: UninstallerPage(c, self),
            "spacelens":  lambda: SpaceLensPage(c, self),
            "largeold":   lambda: LargeFilesPage(c, self),
        }
        return MAP.get(key, lambda: PlaceholderPage(c, key.title(),"◆",WHITE))()


if __name__ == "__main__":
    app = App()
    app.mainloop()
