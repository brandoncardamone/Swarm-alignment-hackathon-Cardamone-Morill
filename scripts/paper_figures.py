"""All paper figures, drawn entirely in matplotlib at the paper's text width (6.3 in).

Frozen-run curves are recomputed from logs/results/{cal,ev}.json (paired bootstrap, cached to
logs/results/fig_curves.json). Exploratory numbers are copied from report/exploratory_v2.md and
report/exploratory_v21.md on branch exploratory/v21-structural-fixes (commit 45d6acb) and checked against them.
Outputs report/figures/fig1_setup … fig5_allocation (.png 300 dpi and .pdf)."""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yaml
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from swarm_oversight.config import LOG_DIR, ROOT
from swarm_oversight.stats import ci, safety_table

FIG = ROOT / "report" / "figures"
W = 6.3
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e0"
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
plt.rcParams.update({
    "font.size": 7.5, "axes.titlesize": 8, "axes.labelsize": 7.5, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "legend.fontsize": 6.8, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": INK2,
    "font.family": "DejaVu Sans"})


def save(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"{name}.{ext}", dpi=300, bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)


def ygrid(ax):
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------- Figure 1: setup schematic
def fig1():
    fig, ax = plt.subplots(figsize=(W, 3.0))
    ax.set_xlim(0, 12.6)
    ax.set_ylim(0, 6)
    ax.axis("off")

    def box(x, y, w, h, lines, fc, ec, fs=6.8, bold_first=False):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                    fc=fc, ec=ec, lw=0.9))
        n = len(lines)
        for k, t in enumerate(lines):
            ax.text(x + w / 2, y + h / 2 + (n - 1 - 2 * k) * 0.19, t, ha="center", va="center", fontsize=fs,
                    color=INK, fontweight="bold" if (bold_first and k == 0) else "normal")

    def arrow(p, q, col=BLUE):
        ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=7, color=col, lw=0.9,
                                     shrinkA=0, shrinkB=1))

    # column headers
    ax.text(1.75, 5.75, "Agents (launched separately)", ha="center", fontsize=7.2, color=INK2, fontweight="bold")
    ax.text(5.9, 5.75, "Shared store (logged)", ha="center", fontsize=7.2, color=INK2, fontweight="bold")
    ax.text(10.35, 5.75, "Map: what the judge sees", ha="center", fontsize=7.2, color=INK2, fontweight="bold")

    agents = [("Agent A", "cover task +", "piece 1: level X = 45"),
              ("Agent B", "cover task +", "piece 2: drop level X"),
              ("Agent C", "cover task +", "piece 3: enable filter")]
    ys = [4.35, 2.85, 1.35]
    for (a, b, c), y in zip(agents, ys):
        box(0.15, y, 3.2, 1.05, [a, b, c], "#eef4fc", BLUE, bold_first=True)

    files = [("config/", "logging.yaml"), ("config/filters/", "x.yaml"), ("shared/ops/*", "(busy hub files)")]
    fys = [4.5, 3.0, 1.5]
    for (a, b), y, ec, fc in zip(files, fys, [INK2, INK2, YELLOW], ["#f4f3ef", "#f4f3ef", "#fbf3e8"]):
        box(4.55, y, 2.7, 0.8, [a, b], fc, ec)

    arrow((3.35, 4.85), (4.55, 4.9))          # A -> logging.yaml
    arrow((3.35, 3.35), (4.55, 3.4))          # B -> filter file
    arrow((3.35, 1.95), (4.55, 4.6))          # C -> logging.yaml (include)
    arrow((3.35, 1.8), (4.55, 3.15))          # C reads filter
    ax.text(5.9, 0.75, "150 benign episodes per stream", ha="center", fontsize=6.4, color=INK2)
    ax.text(5.9, 0.38, "also read and write these files", ha="center", fontsize=6.4, color=INK2)

    maps = ["Singleton: request alone", "Per-agent: own history", "Clustering: similar wording",
            "Provenance: linked by files", "Oracle: true group (ceiling)", "Random: same size (control)"]
    for k, t in enumerate(maps):
        box(8.45, 4.95 - k * 0.78, 3.8, 0.6, [t], "#ffffff", INK2, fs=6.6)
    ax.text(10.35, 0.1, "Judge scores each group 0–9; top q% are audited", ha="center", fontsize=6.4, color=INK2)
    save(fig, "fig1_setup")


# ---------------------------------------------------------------- Figure 2: frozen run headline
MAPS = ["singleton", "per_agent", "clustering", "provenance", "random_matched", "oracle"]
LABEL = {"singleton": "Singleton", "per_agent": "Per-agent", "clustering": "Clustering",
         "provenance": "Provenance", "random_matched": "Random", "oracle": "Oracle"}
STYLE = {"provenance": (BLUE, "o", "-", 1.8), "clustering": (ORANGE, "s", "-", 1.8),
         "random_matched": (AQUA, "^", "-", 1.8), "singleton": (YELLOW, "D", "-", 1.8),
         "oracle": (INK, None, "--", 1.2), "per_agent": (INK2, None, ":", 1.4)}


def frozen_curves():
    cache = LOG_DIR / "results" / "fig_curves.json"
    if cache.exists():
        return json.loads(cache.read_text())
    P = yaml.safe_load((ROOT / "configs" / "frozen.yaml").read_text())
    cal = {}
    for k, rows in json.loads((LOG_DIR / "results" / "cal.json").read_text()).items():
        f, o, m = k.split("|")
        cal[(f, float(o), m)] = rows
    ev = json.loads((LOG_DIR / "results" / "ev.json").read_text())
    for r in ev:
        r["overlap"] = float(r["overlap"])
    T = safety_table(cal, ev, P["qs"], boot=P["bootstrap"], seed=P["seed"], maps=MAPS)
    out = {"qs": P["qs"], "curves": {}}
    for (m, o, q), v in T.items():
        lo, hi = ci(v["reps"])
        out["curves"][f"{m}|{o}|{q}"] = [v["S_worst"], lo, hi]
    cache.write_text(json.dumps(out))
    return out


def fig2():
    d = frozen_curves()
    qs = d["qs"]
    x = [100 * q for q in qs]
    fig, axes = plt.subplots(1, 2, figsize=(W, 2.75), sharey=True, layout="constrained")
    for ax, o in zip(axes, (0.1, 0.4)):
        for m in MAPS:
            col, mk, ls, lw = STYLE[m]
            y = [100 * d["curves"][f"{m}|{o}|{q}"][0] for q in qs]
            if m in ("provenance", "clustering"):
                lo = [100 * d["curves"][f"{m}|{o}|{q}"][1] for q in qs]
                hi = [100 * d["curves"][f"{m}|{o}|{q}"][2] for q in qs]
                ax.fill_between(x, lo, hi, color=col, alpha=0.10, lw=0)
            ax.plot(x, y, color=col, marker=mk, ms=3.5, lw=lw, ls=ls, label=LABEL[m])
        ax.set_xscale("log")
        ax.set_xticks(x, [f"{v:g}%" for v in x])
        ax.minorticks_off()
        ax.set_xlim(0.42, 6)
        ax.set_ylim(-2, 102)
        ax.set_title(f"{int(100 * o)}% benign overlap")
        ax.set_xlabel("Audit budget q")
        ygrid(ax)
    axes[0].set_ylabel("Worst-case safety over A0–A2 (%)")
    h, lab = axes[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="outside lower center", ncol=6, frameon=False, handlelength=2.2, columnspacing=1.2)
    save(fig, "headline")


# ---------------------------------------------------------------- Figure 3: H0 across designs
def fig3():
    rows = [("Frozen, 10% overlap (pre-registered)", 54.2, 12.5, 75.0, BLUE),
            ("Frozen, 40% overlap (pre-registered)", 54.2, 22.3, 79.2, BLUE),
            ("Frozen, equal exposure*", 37.5, 4.2, 62.5, INK2),
            ("v2, scripted*", 56.2, 35.4, 68.8, INK2),
            ("v2.1, env. brief + size-bin*", 22.9, 12.5, 37.5, INK2)]
    fig, ax = plt.subplots(figsize=(W, 2.1), layout="constrained")
    n = len(rows)
    for k, (lab, dv, lo, hi, c) in enumerate(rows):
        y = n - 1 - k
        ax.plot([lo, hi], [y, y], color=c, lw=2, solid_capstyle="round")
        ax.plot(dv, y, "o", color=c, ms=5)
        ax.text(102, y, f"{dv:+.1f}  [{lo:+.1f}, {hi:+.1f}]", va="center", fontsize=6.8, color=INK2)
    ax.set_yticks(range(n), [r[0] for r in rows][::-1])
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_xlim(-5, 100)
    ax.set_ylim(-0.6, n - 0.4)
    ax.set_xlabel("Oracle − per-agent safety at q = 2% (pp, 95% CI)      * exploratory")
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.text(102, n - 0.3, "estimate [95% CI]", fontsize=6.5, color=INK2, va="bottom")
    ax.set_clip_on(False)
    save(fig, "fig3_h0_replication")


# ---------------------------------------------------------------- Figure 4: sharing
def fig4():
    lv = ["private", "10%", "40%"]
    v2 = {"audit_off": [25.0, 81.2, 91.7], "label_poison": [12.5, 93.8, 100.0], "config_backdoor": [12.5, 54.2, 72.9]}
    v21 = {"audit_off": [100.0, 97.9, 97.9], "label_poison": [93.8, 91.7, 100.0],
           "config_backdoor": [100.0, 62.5, 66.7]}
    cols = {"audit_off": BLUE, "label_poison": ORANGE, "config_backdoor": AQUA}
    mk = {"audit_off": "o", "label_poison": "s", "config_backdoor": "^"}
    fig, axes = plt.subplots(1, 3, figsize=(W, 2.45), sharey=True, layout="constrained",
                             gridspec_kw={"width_ratios": [0.8, 1, 1]})
    ax = axes[0]
    ax.plot([0, 1], [21, 41], color=INK2, marker="o", ms=4, lw=1.8)
    for xv, yv in ((0, 21), (1, 41)):
        ax.text(xv, yv + 5, f"{yv}%", ha="center", fontsize=6.5, color=INK2)
    ax.set_xticks([0, 1], ["10%", "40%"])
    ax.set_xlim(-0.4, 1.4)
    ax.set_title("Frozen (pre-reg.)")
    ax.set_xlabel("benign overlap")
    ax.set_ylabel("Provenance safety, q = 2% (%)")
    for ax, data, title in [(axes[1], v2, "v2*"), (axes[2], v21, "v2.1* (size-bin)")]:
        for f, v in data.items():
            ax.plot(range(3), v, color=cols[f], marker=mk[f], ms=4, lw=1.8, label=f)
        ax.set_xticks(range(3), lv)
        ax.set_xlim(-0.3, 2.3)
        ax.set_title(title)
        ax.set_xlabel("hand-off file shared")
    for ax in axes:
        ax.set_ylim(0, 108)
        ygrid(ax)
    h, lab = axes[1].get_legend_handles_labels()
    fig.legend(h, lab, loc="outside lower center", ncol=3, frameon=False)
    save(fig, "fig4_sharing")


# ---------------------------------------------------------------- Figure 5: audit allocation
def fig5():
    fig, axes = plt.subplots(1, 2, figsize=(W, 2.55), layout="constrained", gridspec_kw={"width_ratios": [1, 1.45]})

    def bars(ax, groups, series, title):
        xs = np.arange(len(groups))
        wdt = 0.36
        for k, (lab, vals, col) in enumerate(series):
            pos = xs + (k - 0.5) * wdt
            ax.bar(pos, vals, width=wdt * 0.94, color=col, label=lab)
            for p, v in zip(pos, vals):
                ax.text(p, v + 2, f"{v:.0f}%", ha="center", va="bottom", fontsize=6.5, color=INK2)
        ax.set_xticks(xs, groups)
        ax.set_ylim(0, 112)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.set_title(title)
        ygrid(ax)
        ax.legend(loc="upper left", frameon=False, ncol=1, bbox_to_anchor=(0, 1.0))

    bars(axes[0], ["10% overlap", "40% overlap"],
         [("any audited group counts", [50, 71], ORANGE), ("one chance per request", [9, 17], BLUE)],
         "Frozen run: catch rule")
    axes[0].set_ylim(0, 128)
    axes[0].set_ylabel("Random-control safety (%)")
    bars(axes[1], ["audit_off", "label_poison", "config_backdoor"],
         [("global threshold", [2.1, 52.1, 0.0], ORANGE), ("size-binned thresholds", [100.0, 89.6, 95.8], BLUE)],
         "v2.1*: threshold policy (private route)")
    axes[1].set_ylim(0, 128)
    axes[1].legend(loc="upper left", frameon=False, ncol=2)
    save(fig, "fig5_allocation")


if __name__ == "__main__":
    FIG.mkdir(parents=True, exist_ok=True)
    for f in (fig1, fig2, fig3, fig4, fig5):
        f()
    print("figures written to", FIG)
