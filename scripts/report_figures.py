"""Report figures for 'Who Draws the Map, and Who Sets the Threshold?'.

Run from the repository root:  uv run python scripts/report_figures.py
Writes paper/figures/fig1_setup.pdf, fig2_frozen_headline.pdf, fig3_h0_gains.pdf, fig4_channels.pdf.
Figure 2 is the frozen-run headline produced by scripts/paper_figures.py (report/figures/headline.pdf)."""
import csv
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

REPO = Path(__file__).resolve().parents[1]
CT = REPO / "analysis/exploratory_v21/common_threshold/3939c470c469"
OUT = REPO / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

# Fixed map colours, shared with the frozen-run headline figure.
C = {"singleton": "#eda100", "per_agent": "#6b6b6b", "clustering": "#eb6834",
     "provenance": "#2a78d6", "random": "#1baf7a", "oracle": "#1a1a19"}
INK, MUTED, GRID = "#1a1a19", "#5f5e58", "#e3e2dc"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8.5, "axes.edgecolor": MUTED,
    "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 9, "axes.titleweight": "bold", "legend.frameon": False,
    "pdf.fonttype": 42,
})


def grid(ax, axis="y"):
    ax.grid(True, axis=axis, color=GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------- Figure 1: setup
def fig1():
    fig, ax = plt.subplots(figsize=(7.4, 3.0))
    ax.set_xlim(0, 100); ax.set_ylim(0, 40); ax.axis("off")

    def box(x, y, w, h, text, fc="#f6f5f1", ec=MUTED, fs=8.5, bold=False, color=INK):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2",
                                    fc=fc, ec=ec, lw=0.9, zorder=2))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
                color=color, fontweight="bold" if bold else "normal", zorder=3, linespacing=1.25)

    def arrow(x0, y0, x1, y1, color=MUTED, ls="-", lw=0.9):
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=9,
                                     color=color, lw=lw, ls=ls, zorder=1))

    for i, (y, lab) in enumerate(zip([30, 19, 8], ["Agent 1", "Agent 2", "Agent 3"])):
        box(1, y, 12, 7, lab, fc="#eef3fb", ec=C["provenance"], bold=True)
        box(15.5, y, 13, 7, "cover task", fs=8)
        box(31, y, 11, 7, f"piece {i+1}", fc="#fdeee8", ec=C["clustering"], fs=8)
        arrow(13, y + 3.5, 15.5, y + 3.5)
        arrow(28.5, y + 3.5, 31, y + 3.5)
        arrow(42, y + 3.5, 47, y + 3.5)
    box(47, 5, 15, 32, "logged\nshared store\n\nbenign agents\nread and write\nhere too", fc="#f6f5f1", fs=8)
    box(65, 25, 17, 9, "map\n(grouping rule)", fc="#eef3fb", ec=C["provenance"], bold=True, fs=8)
    box(65, 7, 17, 9, "calibration\n(cutoff at q)", fc="#fff6e0", ec=C["singleton"], bold=True, fs=8)
    box(85.5, 15, 14, 12, "trusted judge\nscores group\n0–9", fc="#f6f5f1", fs=8)
    arrow(62, 29.5, 65, 29.5); arrow(82, 29.5, 86, 26.5)
    arrow(82, 11.5, 86, 15.5)
    ax.text(92.5, 8, "audit the most\nsuspicious q = 2%", ha="center", va="center", fontsize=7.5, color=MUTED, linespacing=1.25)
    ax.text(21, 1.5, "scripted plan arrives via each agent's prompt (unlogged channel)", ha="center", fontsize=7.5, color=MUTED, style="italic")
    fig.savefig(OUT / "fig1_setup.pdf", bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- Figure 3: H0 gains
def fig3():
    rows = [  # label, est, lo, hi, preregistered?
        ("Frozen, 10% overlap", 54.2, 12.5, 75.0, True),
        ("Frozen, 40% overlap", 54.2, 22.3, 79.2, True),
        ("Frozen, one chance per request, 10%", 37.5, 4.2, 62.5, False),
        ("Frozen, one chance per request, 40%", 41.7, 16.7, 74.3, False),
        ("v2 (global cutoff)", 56.2, 35.4, 68.8, False),
        ("v2.1 (global cutoff)", 39.6, 27.1, 52.1, False),
        ("v2.1 (size-bin cutoff, primary)", 22.9, 12.5, 37.5, False),
    ]
    fig, ax = plt.subplots(figsize=(5.2, 2.3))
    grid(ax, "x")
    for i, (lab, est, lo, hi, pre) in enumerate(rows):
        y = len(rows) - 1 - i
        col = C["provenance"] if pre else MUTED
        ax.plot([lo, hi], [y, y], color=col, lw=1.6, solid_capstyle="round", zorder=2)
        ax.plot(est, y, "o", color=col, ms=5, zorder=3)
        ax.text(hi + 2, y, f"+{est:.1f} [{lo:+.1f}, {hi:+.1f}]", va="center", fontsize=7, color=INK)
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows][::-1], fontsize=7.5)
    ax.set_xlim(-5, 118); ax.set_xlabel("Oracle − per-agent safety at q = 2% (pp, 95% paired CI)")
    ax.plot([], [], "o-", color=C["provenance"], label="pre-registered"); ax.plot([], [], "o-", color=MUTED, label="exploratory")
    ax.legend(loc="lower right", fontsize=7)
    fig.savefig(OUT / "fig3_h0_gains.pdf", bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- Figure 4: channels
def read_csv(p):
    with open(p) as f:
        return list(csv.DictReader(f))


def fig4():
    fams = ["audit_off", "label_poison", "config_backdoor"]
    fig, axes = plt.subplots(1, 3, figsize=(8.2, 3.5), gridspec_kw={"width_ratios": [1.15, 1.15, 0.95], "wspace": 0.75})
    FS = 7.5

    # (a) random control under four audit rules, scores fixed; keyed by marker
    ax = axes[0]; grid(ax)
    rules = ["any\ngroup", "one\nchance", "global\ncutoff", "size-bin\ncutoff"]
    key = {"10%": ("o", "none"), "40%": ("o", C["random"]),
           "audit_off": ("s", C["random"]), "label_poison": ("^", C["random"]), "config_backdoor": ("D", C["random"])}
    pts = {0: [("10%", 50), ("40%", 71)], 1: [("10%", 9), ("40%", 17)],
           2: [("audit_off", 2.1), ("label_poison", 52.1), ("config_backdoor", 0.0)],
           3: [("audit_off", 100), ("label_poison", 89.6), ("config_backdoor", 95.8)]}
    jitter = {"10%": -0.1, "40%": 0.1, "audit_off": -0.15, "label_poison": 0.0, "config_backdoor": 0.15}
    for x, lst in pts.items():
        for lab, v in lst:
            m, fc = key[lab]
            ax.plot(x + jitter[lab], v, marker=m, ls="none", ms=6, mfc=fc, mec=C["random"], mew=1.2, zorder=3)
    ax.set_xticks(range(4)); ax.set_xticklabels(rules, fontsize=6.6); ax.set_xlim(-0.6, 3.6)
    ax.text(0.5, -27, "frozen run", ha="center", fontsize=FS, color=MUTED, clip_on=False)
    ax.text(2.5, -27, "v2.1", ha="center", fontsize=FS, color=MUTED, clip_on=False)
    ax.set_ylim(-4, 106); ax.set_ylabel("Random-control safety (%)", fontsize=FS)
    ax.tick_params(axis="y", labelsize=FS)
    ax.set_title("(a) Random control", loc="left")
    handles = [plt.Line2D([], [], marker=key[k][0], ls="none", ms=5.5, mfc=key[k][1], mec=C["random"], mew=1.1, label=lab)
               for k, lab in [("10%", "frozen, 10% overlap"), ("40%", "frozen, 40% overlap"),
                              ("audit_off", "v2.1 audit_off"), ("label_poison", "v2.1 label_poison"),
                              ("config_backdoor", "v2.1 config_backdoor")]]
    ax.legend(handles=handles, fontsize=6.3, loc="upper center", bbox_to_anchor=(0.5, -0.3), handletextpad=0.3, borderpad=0.3)

    # (b) decomposition
    ax = axes[1]; grid(ax, "x")
    dec = {(r["family"], r["map"]): r for r in read_csv(CT / "exploratory_decomposition.csv")
           if r["variant"] == "singleton_cutoff" and r["baseline"] == "singleton" and r["scope"] == "all_pieces"}
    labels, ys = [], []
    y = 0
    for fam in fams[::-1]:
        for m, k in [("provenance", "provenance"), ("random", "size_root_matched")]:
            r = dec[(fam, k)]
            sc, al, ob = 100 * float(r["score_context"]), 100 * float(r["allocation"]), 100 * float(r["observed"])
            lo, hi = 100 * float(r["observed_low"]), 100 * float(r["observed_high"])
            col = C[m]
            ax.barh(y, sc, color=col, height=0.6, zorder=2, edgecolor="white", lw=0.5)
            ax.barh(y, al, left=sc, fc="none", edgecolor=col, hatch="////", height=0.6, zorder=3, lw=0.6)
            ax.plot([lo, hi], [y, y], color=INK, lw=0.8, zorder=4)
            ax.plot(ob, y, "D", color=INK, ms=3, zorder=5)
            labels.append(m); ys.append(y); y += 1
        ax.text(-34, y - 0.15, fam, fontsize=FS, fontweight="bold", va="center", ha="left", color=INK)
        y += 1.0
    ax.set_yticks(ys); ax.set_yticklabels(labels, fontsize=FS); ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", labelsize=FS)
    ax.axvline(0, color=INK, lw=0.8); ax.set_xlim(-36, 105); ax.set_ylim(-0.7, y - 0.6)
    ax.set_xlabel("Private gain over singleton (pp)", fontsize=FS)
    ax.set_title("(b) Gain split", loc="left")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(fc=MUTED, label="common-cutoff gain"),
                       Patch(fc="white", ec=MUTED, hatch="////", label="allocation residual"),
                       plt.Line2D([], [], marker="D", color=INK, ms=3, lw=0.8, label="primary gain, 95% CI")],
              fontsize=6.3, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=1, handlelength=1.6, borderpad=0.3)

    # (c) paired later-piece scores
    ax = axes[2]; grid(ax, "x")
    ls = {(r["family"], r["piece"]): r for r in read_csv(CT / "exploratory_later_scores.csv")}
    for i, fam in enumerate(fams[::-1]):
        for piece, off, ms, col in [("piece_2", -0.25, 4, "#9ec5f4"), ("piece_3", 0.25, 4, "#9ec5f4"),
                                    ("both_later_pieces", 0.0, 6, C["provenance"])]:
            r = ls[(fam, piece)]
            m, lo, hi = float(r["mean"]), float(r["mean_low"]), float(r["mean_high"])
            ax.plot([lo, hi], [i + off, i + off], color=col, lw=1.3 if piece.startswith("both") else 1.0, zorder=2)
            ax.plot(m, i + off, "o", color=col, ms=ms, zorder=3)
        ax.text(float(ls[(fam, "both_later_pieces")]["mean_high"]) + 0.15, i,
                f"+{float(ls[(fam, 'both_later_pieces')]['mean']):.1f}", fontsize=FS, va="center")
    ax.set_yticks(range(3)); ax.set_yticklabels(fams[::-1], fontsize=FS)
    ax.tick_params(axis="x", labelsize=FS)
    ax.axvline(0, color=INK, lw=0.8); ax.set_xlim(-0.3, 4.6); ax.set_ylim(-0.7, 2.7)
    ax.set_xlabel("Provenance − random judge score\n(points, 0–9 scale, same later piece)", fontsize=FS)
    ax.set_title("(c) Judge-score shift", loc="left")
    ax.plot([], [], "o", color=C["provenance"], ms=6, label="both later pieces (n=96)")
    ax.plot([], [], "o", color="#9ec5f4", ms=4, label="piece 2 / piece 3 (n=48 each)")
    ax.legend(fontsize=6.3, loc="upper center", bbox_to_anchor=(0.5, -0.3), borderpad=0.3)

    fig.savefig(OUT / "fig4_channels.pdf", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    fig1(); fig3(); fig4()
    shutil.copy(REPO / "report" / "figures" / "headline.pdf", OUT / "fig2_frozen_headline.pdf")
    print("ok", sorted(p.name for p in OUT.iterdir()))
