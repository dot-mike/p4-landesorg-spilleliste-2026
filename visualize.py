# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib>=3.9"]
# ///
"""Charts for the P4 landesorg playlist.

Run:  uv run visualize.py [playlist.csv]
Out:  charts/*.png (lys) og charts/dark/*.png (mørk)
"""
import csv
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, HourLocator

OSLO = ZoneInfo("Europe/Oslo")

# The dark steps are picked for the dark surface, not an inverted copy of the light ones.
THEMES = {
    "light": dict(blue="#2a78d6", dim="#9ec5f4", ink="#0b0b0b",
                  muted="#52514e", grid="#e6e5e2", surface="#fcfcfb"),
    "dark":  dict(blue="#3987e5", dim="#184f95", ink="#ffffff",
                  muted="#c3c2b7", grid="#383835", surface="#1a1a19"),
}


def set_theme(name):
    global BLUE, BLUE_LIGHT, INK, MUTED, GRID, SURFACE
    t = THEMES[name]
    BLUE, BLUE_LIGHT, INK = t["blue"], t["dim"], t["ink"]
    MUTED, GRID, SURFACE = t["muted"], t["grid"], t["surface"]
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.size": 9, "text.color": INK,
        "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.edgecolor": GRID, "axes.linewidth": 0.8,
        "xtick.major.size": 0, "ytick.major.size": 0,
    })


set_theme("light")


def load(path):
    """-> list of (local datetime, artist, title), chronological."""
    with open(path, encoding="utf-8", newline="") as f:
        rows = [(datetime.strptime(r["time_oslo"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=OSLO),
                 r["artist"], r["title"]) for r in csv.DictReader(f)]
    return sorted(rows)


def style(ax, title, subtitle=None):
    # offsets in points, not axes fractions — a 20-inch-tall figure must not squash them
    lines = subtitle.count("\n") + 1 if subtitle else 0
    ax.set_title(title, loc="left", fontsize=13, weight="bold", pad=14 + 12 * lines)
    if subtitle:
        ax.annotate(subtitle, xy=(0, 1), xycoords="axes fraction", xytext=(0, 7),
                    textcoords="offset points", fontsize=9, color=MUTED, va="bottom")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.spines["bottom"].set_color(GRID)


def timeline(rows, out):
    """One row per unique title, a dot per play — shows the rotation loop."""
    order, plays = [], {}
    for t, artist, title in rows:
        key = f"{artist} - {title}"
        if key not in plays:
            order.append(key)
            plays[key] = []
        plays[key].append(t)

    fig, ax = plt.subplots(figsize=(11, 0.235 * len(order) + 2.2))
    for y, key in enumerate(order):
        ts = plays[key]
        if len(ts) > 1:                      # connector: makes repeats read as one row
            ax.plot([ts[0], ts[-1]], [y, y], color=GRID, lw=2, zorder=1, solid_capstyle="round")
        ax.scatter(ts, [y] * len(ts), s=34, color=BLUE, zorder=2,
                   edgecolors=SURFACE, linewidths=1.2)          # 2px surface ring
        if len(ts) > 1:
            ax.text(ts[-1] + timedelta(minutes=8), y, f"{len(ts)} ganger", va="center",
                    fontsize=7, color=MUTED)

    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order, fontsize=7)
    ax.set_ylim(len(order) - 0.5, -0.5)
    ax.set_xlim(rows[0][0] - timedelta(minutes=20), rows[-1][0] + timedelta(minutes=105))
    ax.xaxis.set_major_locator(HourLocator(interval=1))
    ax.xaxis.set_major_formatter(DateFormatter("%H", tz=OSLO))
    ax.set_xlabel("Klokkeslett, norsk tid")
    ax.grid(axis="x", color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    style(ax, "Sangene P4 spilte 28. august 2026",
          f"{len(rows)} avspillinger av {len(order)} ulike sanger.\n"
          "Radene er sortert etter når sangen ble spilt første gang.\n"
          "Tallet til høyre viser hvor mange ganger sangen ble spilt.")
    fig.tight_layout()
    fig.savefig(out, dpi=160)
    plt.close(fig)


def most_played(rows, out, top=15):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.4))
    for ax, (label, counts) in zip(axes, [
            ("artistene", Counter(a for _, a, _ in rows)),
            ("sangene", Counter(f"{t} ({a})" for _, a, t in rows))]):
        items = counts.most_common(top)[::-1]
        names = [n if len(n) < 52 else n[:50] + "…" for n, _ in items]
        vals = [v for _, v in items]
        ax.barh(names, vals, height=0.68, color=BLUE)
        for y, v in enumerate(vals):
            ax.text(v + 0.08, y, str(v), va="center", fontsize=8, color=MUTED)
        ax.set_xlim(0, max(vals) + 1)
        ax.set_xticks(range(0, max(vals) + 2))
        ax.tick_params(axis="y", labelsize=8)
        ax.grid(axis="x", color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        style(ax, f"Dette er {label} som ble spilt mest")
        ax.set_xlabel("Antall avspillinger")
    fig.tight_layout()
    fig.savefig(out, dpi=160)
    plt.close(fig)


def airtime(rows, out):
    """Two stacked panels on one shared time axis — never a second y-scale."""
    times = [t for t, _, _ in rows]
    hours = Counter(t.hour for t in times)
    gaps = [(times[i], (times[i + 1] - times[i]).total_seconds() / 60) for i in range(len(times) - 1)]
    partial = {times[0].hour, times[-1].hour}

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7.8), sharex=True)

    hs = sorted(hours)
    xs = [datetime(times[0].year, times[0].month, times[0].day, h, 30, tzinfo=OSLO) for h in hs]
    ax1.bar(xs, [hours[h] for h in hs], width=timedelta(minutes=40),
            color=[BLUE_LIGHT if h in partial else BLUE for h in hs],
            hatch=["///" if h in partial else "" for h in hs],   # texture, not colour alone
            edgecolor=SURFACE, linewidth=0)
    for x, h in zip(xs, hs):
        ax1.text(x, hours[h] + 0.3, str(hours[h]), ha="center", fontsize=8, color=MUTED)
    ax1.set_ylabel("Sanger")
    ax1.set_ylim(0, max(hours.values()) + 2)
    ax1.grid(axis="y", color=GRID, lw=0.8)
    ax1.set_axisbelow(True)
    style(ax1, "Antall sanger per time", "Data fra perioden mellom kl. 08:30 og 21:00")

    ax2.vlines([g[0] for g in gaps], 0, [g[1] for g in gaps], color=GRID, lw=1.6)
    ax2.scatter([g[0] for g in gaps], [g[1] for g in gaps], s=30, color=BLUE, zorder=3,
                edgecolors=SURFACE, linewidths=1.2)
    for t, m in gaps:
        if m >= 10:                                   # selective direct labels, not every point
            ax2.text(t, m + 0.6, f"{m:.0f} min", ha="center", fontsize=7.5, color=MUTED)
    ax2.set_ylabel("Minutter")
    ax2.set_ylim(0, max(m for _, m in gaps) + 4)
    ax2.set_xlabel("Klokkeslett, norsk tid")
    ax2.set_xlim(times[0].replace(hour=7, minute=50), times[0].replace(hour=22, minute=0))
    ax2.xaxis.set_major_locator(HourLocator(interval=1))
    ax2.xaxis.set_major_formatter(DateFormatter("%H", tz=OSLO))
    ax2.grid(axis="y", color=GRID, lw=0.8)
    ax2.set_axisbelow(True)
    style(ax2, "Pause mellom sangene",
          "Lange pauser betyr nyheter, sending fra seremonien eller prat i studio.")

    fig.tight_layout(h_pad=3.2)
    fig.savefig(out, dpi=160)
    plt.close(fig)


def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "p4-2026-08-28-0830-2100.csv")
    rows = load(src)
    for theme in THEMES:
        set_theme(theme)
        outdir = Path("charts") if theme == "light" else Path("charts/dark")
        outdir.mkdir(parents=True, exist_ok=True)
        timeline(rows, outdir / "1-rotation-timeline.png")
        most_played(rows, outdir / "2-most-played.png")
        airtime(rows, outdir / "3-airtime.png")
        print(f"{len(rows)} avspillinger -> {outdir}/ (3 bilder, {theme})")


def _selfcheck():
    """Aggregation logic, no plotting, no files."""
    d = datetime(2026, 8, 28, tzinfo=OSLO)
    rows = [(d.replace(hour=9, minute=0), "A", "x"),
            (d.replace(hour=9, minute=4), "B", "y"),
            (d.replace(hour=10, minute=24), "A", "x")]
    assert Counter(a for _, a, _ in rows).most_common(1) == [("A", 2)]
    ts = [t for t, _, _ in rows]
    gaps = [(ts[i + 1] - ts[i]).total_seconds() / 60 for i in range(len(ts) - 1)]
    assert gaps == [4.0, 80.0], gaps
    assert dict(Counter(t.hour for t in ts)) == {9: 2, 10: 1}
    print("selfcheck ok")


if __name__ == "__main__":
    _selfcheck() if "--selfcheck" in sys.argv else main()
