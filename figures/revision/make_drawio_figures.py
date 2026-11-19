#!/usr/bin/env python3
"""Write the data figures of the manuscript (Figs. 2 and 3) as draw.io files.

Reads only the frozen result tables of the public repository and writes
Fig2.drawio, Fig3.drawio and figure_ledger.json to the output directory.
export_figures.sh then turns every figures/Fig*.drawio into the PDF used by
main.tex. Fig. 1 (schematic) is edited directly in draw.io and is not
written here.

Fig. 2: a ranked energy gaps of the nesting test, b continuation of the
certified failures, c feasibility gain of each loss relative to the
feasibility control. Fig. 3: a, b graph-level held-out contrasts for H1 and
H2, c CVaR gain split by whether the CVaR state reached P_feas >= alpha.

The canvas is 517 draw.io units wide. draw.io exports 100 units per inch, so
the PDF is 372 pt wide, the text width of the manuscript, and main.tex
includes the figures at their natural size (1 unit = 0.72 pt).

Usage: python make_drawio_figures.py --repo <repository root> --out <figures dir>
"""
from __future__ import annotations

import argparse
import html
import json
import math
import re
from pathlib import Path
from xml.sax.saxutils import quoteattr

import numpy as np
import pandas as pd

WIDTH = 517
FONT = 'Helvetica'
# Colours: one per loss, used in every figure.
INK, AXIS, GRID = '#2D3748', '#A0AEC0', '#EDF2F7'
MEAN, PENALTY, CONTROL, CVAR = '#8796A8', '#B4C0CE', '#2A9D8F', '#E76F51'
FAIL, PALE = '#6C5B7B', '#CBD5E0'
TICK, LABEL, LETTER = 11.5, 12, 14   # font sizes in draw.io units (x 0.72 = pt)
MINUS = '−'
G = '<i>G</i><sub>feas</sub>'
P = '<i>P</i><sub>feas</sub>'

# Advance widths (1/1000 em) of a Helvetica-metric font (FreeSans), used to
# size text boxes so that labels never reach outside the canvas.
_CHARS = (' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`'
          'abcdefghijklmnopqrstuvwxyz{|}~−–αΔ×≥≤·')
_WIDTHS = [250, 333, 333, 556, 556, 889, 667, 200, 333, 333, 389, 584, 278, 333, 250, 278,
           556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 250, 250, 584, 584, 584, 556,
           1015, 666, 664, 709, 698, 633, 599, 765, 721, 278, 528, 674, 563, 846, 730, 784,
           656, 784, 709, 667, 632, 720, 645, 937, 657, 678, 615, 278, 278, 277, 469, 556,
           250, 543, 559, 506, 559, 533, 280, 550, 536, 222, 243, 514, 214, 812, 537, 534,
           559, 559, 332, 493, 280, 537, 496, 722, 476, 478, 486, 333, 250, 333, 500, 584,
           500, 578, 699, 584, 584, 584, 250]
ADVANCE = dict(zip(_CHARS, _WIDTHS))


def text_extent(value: str, size: float, bold: bool = False) -> tuple[float, int]:
    """Approximate width (draw.io units) and line count of an HTML label."""
    widest, lines = 0.0, value.split('<br>')
    for line in lines:
        width, scale = 0.0, 1.0
        for token in re.split(r'(<[^>]+>)', line):
            if token.startswith('<'):
                scale = 0.83 if token in ('<sub>', '<sup>') else (
                    1.0 if token in ('</sub>', '</sup>') else scale)
                continue
            for ch in html.unescape(token):
                width += ADVANCE.get(ch, 600) * scale
        widest = max(widest, width * size / 1000 * (1.07 if bold else 1.0))
    return widest, len(lines)


def signed(value: float, fmt: str) -> str:
    """Format a number with a typographic minus sign."""
    return format(value, fmt).replace('-', MINUS)


def swarm(values: np.ndarray, diameter: float, limit: float) -> np.ndarray:
    """Offsets across the value axis so that dots do not overlap (beeswarm)."""
    step, placed = diameter * 0.55, []
    offsets = np.zeros(len(values))
    for i in np.argsort(values):
        v, k = values[i], 0
        while True:
            off = ((k + 1) // 2) * step * (1 if k % 2 else -1)
            near = [(pv, po) for pv, po in placed if abs(v - pv) < diameter]
            if all((v - pv) ** 2 + (off - po) ** 2 >= (0.96 * diameter) ** 2
                   for pv, po in near) or abs(off) > limit:
                break
            k += 1
        offsets[i] = max(-limit, min(limit, off))
        placed.append((v, offsets[i]))
    return offsets


class Diagram:
    """Minimal writer for an uncompressed draw.io (mxGraph) file."""

    def __init__(self, name: str, width: float, height: float):
        self.name, self.width, self.height = name, width, height
        self.cells: list[str] = []
        self.extents: list[tuple[str, float, float, float, float]] = []
        self.count = 0
        # An invisible frame fixes the cropped PDF to width x height.
        self.vertex(0, 0, width, height, 'fillColor=none;strokeColor=none;')

    def _id(self) -> str:
        self.count += 1
        return f'{self.name.lower()}-{self.count}'

    def vertex(self, x, y, w, h, style, value='', rotated=False) -> str:
        cid = self._id()
        self.cells.append(
            f'<mxCell id="{cid}" value={quoteattr(value)} style={quoteattr(style)} '
            f'vertex="1" parent="1"><mxGeometry x="{x:.2f}" y="{y:.2f}" '
            f'width="{w:.2f}" height="{h:.2f}" as="geometry"/></mxCell>')
        if rotated:  # a quarter turn about the centre swaps the extents
            cx, cy = x + w / 2, y + h / 2
            x, y, w, h = cx - h / 2, cy - w / 2, h, w
        self.extents.append((value or cid, x, y, x + w, y + h))
        return cid

    def text(self, x, y, value, size=TICK, align='center', valign='middle',
             color=INK, bold=False, rotation=0) -> str:
        """Text anchored at (x, y) according to align and valign."""
        width, lines = text_extent(value, size, bold)
        w, h = width + 3, lines * size * 1.2 + 2
        bx = {'left': x, 'center': x - w / 2, 'right': x - w}[align]
        by = {'top': y, 'middle': y - h / 2, 'bottom': y - h}[valign]
        style = (f'text;html=1;align={align};verticalAlign={valign};'
                 'spacing=0;spacingTop=0;spacingBottom=0;spacingLeft=0;spacingRight=0;'
                 f'fontFamily={FONT};fontSize={size};fontColor={color};'
                 'whiteSpace=nowrap;fillColor=none;strokeColor=none;'
                 + ('fontStyle=1;' if bold else '')
                 + (f'rotation={rotation};' if rotation else ''))
        return self.vertex(bx, by, w, h, style, value, rotated=rotation in (90, -90, 270))

    def line(self, points, color=INK, width=1.0, dash=None, arrow=False, end_size=5) -> None:
        cid = self._id()
        style = (f'html=1;rounded=0;startArrow=none;strokeColor={color};strokeWidth={width};'
                 + (f'endArrow=block;endFill=1;endSize={end_size};' if arrow else 'endArrow=none;')
                 + (f'dashed=1;dashPattern={dash};' if dash else ''))
        (x1, y1), (x2, y2) = points[0], points[-1]
        inner = ''.join(f'<mxPoint x="{x:.2f}" y="{y:.2f}"/>' for x, y in points[1:-1])
        array = f'<Array as="points">{inner}</Array>' if inner else ''
        self.cells.append(
            f'<mxCell id="{cid}" style={quoteattr(style)} edge="1" parent="1">'
            f'<mxGeometry relative="1" as="geometry">'
            f'<mxPoint x="{x1:.2f}" y="{y1:.2f}" as="sourcePoint"/>'
            f'<mxPoint x="{x2:.2f}" y="{y2:.2f}" as="targetPoint"/>{array}'
            f'</mxGeometry></mxCell>')
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        self.extents.append((cid, min(xs), min(ys), max(xs), max(ys)))

    def dot(self, cx, cy, size, fill, stroke='#FFFFFF', sw=0.6, kind='o') -> str:
        shape = {'o': 'ellipse;', 'D': 'rhombus;'}[kind]
        style = (f'{shape}html=1;fillColor={fill};strokeColor={stroke};'
                 + (f'strokeWidth={sw};' if stroke != 'none' else ''))
        return self.vertex(cx - size / 2, cy - size / 2, size, size, style)

    def letter(self, x, y, s) -> None:
        self.text(x, y, s, size=LETTER, align='left', valign='top', bold=True)

    def save(self, path: Path) -> None:
        outside = [e for e in self.extents
                   if e[1] < -0.01 or e[2] < -0.01 or e[3] > self.width + 0.01
                   or e[4] > self.height + 0.01]
        assert not outside, f'{self.name}: elements outside the canvas: {outside[:3]}'
        body = '\n'.join(self.cells)
        path.write_text(
            '<mxfile host="make_drawio_figures.py" compressed="false">\n'
            f'<diagram id="{self.name}" name="{self.name}">\n'
            '<mxGraphModel dx="0" dy="0" grid="0" gridSize="10" guides="1" tooltips="1" '
            'connect="0" arrows="0" fold="1" page="0" pageScale="1" '
            f'pageWidth="{self.width}" pageHeight="{self.height}" math="0" shadow="0">\n'
            '<root>\n<mxCell id="0"/>\n<mxCell id="1" parent="0"/>\n'
            f'{body}\n</root>\n</mxGraphModel>\n</diagram>\n</mxfile>\n')


class Axes:
    """Axes with horizontal grid lines, a left and a bottom spine."""

    def __init__(self, dg: Diagram, x0, y0, w, h, xlim, ylim):
        self.dg, self.x0, self.y0, self.w, self.h = dg, x0, y0, w, h
        self.xlim, self.ylim = xlim, ylim

    def X(self, v: float) -> float:
        lo, hi = self.xlim
        return self.x0 + (v - lo) / (hi - lo) * self.w

    def Y(self, v: float) -> float:
        lo, hi = self.ylim
        return self.y0 + self.h - (v - lo) / (hi - lo) * self.h

    def grid(self, yticks) -> None:
        for t in yticks:
            self.dg.line([(self.x0, self.Y(t)), (self.x0 + self.w, self.Y(t))], GRID, 0.8)

    def yaxis(self, yticks, ylabels, ylabel=None, offset=34) -> None:
        dg, x0 = self.dg, self.x0
        dg.line([(x0, self.y0), (x0, self.y0 + self.h)], AXIS, 0.9)
        for t, s in zip(yticks, ylabels):
            dg.line([(x0 - 3, self.Y(t)), (x0, self.Y(t))], AXIS, 0.9)
            dg.text(x0 - 5, self.Y(t), s, align='right')
        if ylabel:
            dg.text(x0 - offset, self.y0 + self.h / 2, ylabel, size=LABEL, rotation=-90)

    def xaxis(self, xticks, xlabels, xlabel=None, ticks=True) -> None:
        dg, yb = self.dg, self.y0 + self.h
        dg.line([(self.x0, yb), (self.x0 + self.w, yb)], AXIS, 0.9)
        for t, s in zip(xticks, xlabels):
            if ticks:
                dg.line([(self.X(t), yb), (self.X(t), yb + 3)], AXIS, 0.9)
            dg.text(self.X(t), yb + 5, s, valign='top')
        if xlabel:
            dg.text(self.x0 + self.w / 2, yb + 20, xlabel, size=LABEL, valign='top')


def figure2(repo: Path, out: Path) -> dict:
    """Discovery set: nesting test (a), continuation (b), losses vs control (c)."""
    res = repo / 'results'
    gap = pd.read_csv(res / 'phase1_1_optimization_diagnostic/p3_random_vs_embedded.csv')
    cont = pd.read_csv(res / 'phase1_1_optimization_diagnostic/analysis/continuation_paired_comparison.csv')
    merged = cont.merge(gap[['task_id', 'optimizer_seed', 'original_p3_worse_than_embedded_p2']],
                        on=['task_id', 'optimizer_seed'], validate='one_to_one')
    mask = merged.original_p3_worse_than_embedded_p2.astype(bool)
    assert len(gap) == len(merged) == 168 and mask.sum() == 29
    fails = merged.loc[mask]
    better = int((fails.G_feas_final > fails.original_p3_G_feas).sum())
    assert better == 27 and int((fails.objective_final < fails.original_p3_objective).sum()) == 29

    runs = pd.read_csv(res / 'phase1_2_objective_alignment/objective_results.csv')
    assert len(runs) == 224 and set(runs.cvar_alpha) == {0.1}
    gain = runs.pivot(index='task_id', columns='objective_id', values='log_feasibility_gain')
    deltas = {o: (gain[o] - gain['O2']).to_numpy() for o in ('O0', 'O1', 'O3')}
    medians = {o: float(np.median(d)) for o, d in deltas.items()}
    assert [f'{abs(medians[o]):.3f}' for o in ('O0', 'O1')] == ['0.219', '0.242']
    assert f'{abs(medians["O3"]):.4f}' == '0.0069'

    dg = Diagram('Fig2', WIDTH, 172)
    top, height = 12, 118

    # a: ranked energy gaps; certified failures above zero.
    a = Axes(dg, 48, top, 120, height, (-4, 172), (-0.78, 0.68))
    dg.letter(0, 0, 'a')
    a.grid([-0.6, -0.3, 0.3, 0.6])
    ordered = gap.sort_values('p3_optimization_gap_vs_embedded_p2')
    vals = ordered.p3_optimization_gap_vs_embedded_p2.to_numpy()
    fail = ordered.original_p3_worse_than_embedded_p2.to_numpy().astype(bool)
    dg.line([(a.X(-4), a.Y(0)), (a.X(172), a.Y(0))], INK, 0.9)
    for rank, (v, f) in enumerate(zip(vals, fail), start=1):
        if f:
            dg.line([(a.X(rank), a.Y(0)), (a.X(rank), a.Y(v))], FAIL, 0.6)
    for rank, (v, f) in enumerate(zip(vals, fail), start=1):
        dg.dot(a.X(rank), a.Y(v), 4.0 if f else 3.4, FAIL if f else MEAN, 'none')
    a.yaxis([-0.6, -0.3, 0, 0.3, 0.6], [signed(t, '.1f') for t in (-0.6, -0.3, 0, 0.3, 0.6)],
            'Energy gap', offset=37)
    a.xaxis([1, 168], ['1', '168'], 'Run (ranked)')
    dg.text(a.X(6), a.Y(0.42), '29/168', size=15, color=FAIL, bold=True, align='left')

    # b: continuation of the 29 failed runs (slope chart).
    lo = math.floor(min(fails.original_p3_G_feas.min(), fails.G_feas_final.min()) * 2) / 2
    hi = math.ceil(max(fails.original_p3_G_feas.max(), fails.G_feas_final.max()) * 2) / 2
    b = Axes(dg, 236, top, 96, height, (0, 1), (lo, hi))
    dg.letter(196, 0, 'b')
    yt = [t for t in range(math.ceil(lo), math.floor(hi) + 1)]
    b.grid(yt)
    xa, xb = 0.18, 0.82
    for _, r in fails.iterrows():
        up = r.G_feas_final > r.original_p3_G_feas
        dg.line([(b.X(xa), b.Y(r.original_p3_G_feas)), (b.X(xb), b.Y(r.G_feas_final))],
                FAIL if up else PALE, 0.9)
    for _, r in fails.iterrows():
        up = r.G_feas_final > r.original_p3_G_feas
        dg.dot(b.X(xa), b.Y(r.original_p3_G_feas), 4.2, PALE if not up else MEAN)
        dg.dot(b.X(xb), b.Y(r.G_feas_final), 4.2, FAIL if up else PALE)
    b.yaxis(yt, [signed(t, 'd') for t in yt], f'{G} (decades)', offset=22)
    b.xaxis([xa, xb], ['Original', 'Continued'], ticks=False)
    dg.text(b.X(1.0), b.Y(lo) - 2, '27/29', size=15, color=FAIL, bold=True, align='right',
            valign='bottom')

    # c: feasibility gain of each loss relative to the feasibility control.
    c = Axes(dg, 398, top, 114, height, (0, 3), (-1.12, 0.36))
    dg.letter(358, 0, 'c')
    c.grid([-1, -0.5])
    dg.line([(c.X(0), c.Y(0)), (c.X(3), c.Y(0))], CONTROL, 1.2, dash='4 2')
    colours = {'O0': MEAN, 'O1': PENALTY, 'O3': CVAR}
    for i, o in enumerate(('O0', 'O1', 'O3')):
        cx = c.X(i + 0.5)
        ys = np.array([c.Y(v) for v in deltas[o]])
        offs = swarm(ys, 4.4, 17)
        for y, off in zip(ys, offs):
            dg.dot(cx + off, y, 4.4, colours[o], '#FFFFFF', 0.4)
        dg.line([(cx - 15, c.Y(medians[o])), (cx + 15, c.Y(medians[o]))], INK, 2.0)
    c.yaxis([-1, -0.5, 0], [signed(-1, 'd'), signed(-0.5, '.1f'), '0'],
            f'Δ{G} vs control', offset=39)
    c.xaxis([0.5, 1.5, 2.5], ['O0', 'O1', 'O3'], ticks=False)

    dg.save(out / 'Fig2.drawio')
    return {'nesting': {'pairs': 168, 'failures': 29, 'continued_runs_gaining_G': better},
            'median_gap_to_control': medians}


def strip(dg: Diagram, x0, w, yc, xlim, xticks, values, mean, lower, xlabel, note,
          margin=None):
    """Horizontal strip of graph-level contrasts with mean and one-sided interval."""
    ax = Axes(dg, x0, yc - 22, w, 44, xlim, (0, 1))
    yb = yc + 22
    dg.line([(ax.X(0), yc - 24), (ax.X(0), yb)], AXIS, 0.9)
    if margin is not None:
        dg.line([(ax.X(margin), yc - 24), (ax.X(margin), yb)], CONTROL, 1.2, dash='4 2')
        dg.text(ax.X(margin) + 3, yc - 24, 'margin', color=CONTROL, align='left', valign='top')
    xs = np.array([ax.X(v) for v in values])
    offs = swarm(xs, 6.0, 12)
    for x, off in zip(xs, offs):
        dg.dot(x, yc - 6 + off, 6.0, CVAR, '#FFFFFF', 0.6)
    yci = yc + 14
    dg.line([(ax.X(lower), yci), (ax.X(xlim[1]) - 1, yci)], CVAR, 1.6, arrow=True, end_size=5)
    dg.line([(ax.X(lower), yci - 4), (ax.X(lower), yci + 4)], CVAR, 1.6)
    dg.dot(ax.X(mean), yci, 9.0, CVAR, INK, 0.7, kind='D')
    dg.text(x0 + w + 6, yci, note, size=14, color=CVAR, bold=True, align='left')
    ax.y0, ax.h = yb - 1, 1   # bottom axis at yb
    ax.xaxis(xticks, [signed(t, '.1f') if t else '0' for t in xticks], xlabel)


def figure3(repo: Path, out: Path) -> dict:
    """Held-out tests H1 (a) and H2 (b); CVaR gain split by tail status (c)."""
    res = repo / 'results/phase2_confirmatory_v1'
    graph = pd.read_csv(res / 'graph_level_contrasts.csv')
    stats = json.loads((res / 'confirmatory_statistics.json').read_text())
    tasks = pd.read_csv(res / 'task_level_contrasts.csv')
    assert len(graph) == 15 and stats['n_base_graphs'] == 15 and len(tasks) == 84
    for h in ('H1', 'H2'):
        assert stats[h]['pass'] and f"{stats[h]['holm_adjusted_p_value']:.3g}" == '0.000244'
    h1, h2 = stats['H1'], stats['H2']

    dg = Diagram('Fig3', WIDTH, 176)
    dg.letter(0, 0, 'a')
    strip(dg, 26, 290, 28, (-0.15, 1.15), [0, 0.5, 1.0], graph.Delta1_CVAR_MEAN.to_numpy(),
          h1['effect_mean'], h1['one_sided_95_lower_bound'],
          f'Δ{G}: CVaR − mean energy', '2.3×')
    dg.letter(0, 88, 'b')
    strip(dg, 26, 290, 116, (-0.16, 0.14), [-0.1, 0, 0.1],
          graph.Delta2_CVAR_CAPACITY.to_numpy(), h2['effect_mean'],
          h2['one_sided_95_lower_bound'], f'Δ{G}: CVaR − control', f'{MINUS}2%',
          margin=-0.1)

    # c: task-level CVaR gain, split by whether the CVaR state reached P_feas >= alpha.
    diff = (tasks.log_feasibility_gain_O3 - tasks.log_feasibility_gain_O0).to_numpy()
    high = tasks.p_feas_O3.to_numpy() >= 0.10
    med = {'low': float(np.median(diff[~high])), 'high': float(np.median(diff[high]))}
    assert int(high.sum()) == 20 and f"{med['high']:.3f}" == '0.056' and f"{med['low']:.3f}" == '0.386'
    c = Axes(dg, 398, 12, 114, 118, (0, 2), (-0.2, 2.35))
    dg.letter(358, 0, 'c')
    c.grid([1, 2])
    dg.line([(c.X(0), c.Y(0)), (c.X(2), c.Y(0))], AXIS, 0.9)
    for i, (sel, key) in enumerate(((~high, 'low'), (high, 'high'))):
        cx = c.X(i + 0.5)
        ys = np.array([c.Y(v) for v in diff[sel]])
        offs = swarm(ys, 4.4, 24)
        for y, off in zip(ys, offs):
            dg.dot(cx + off, y, 4.4, CVAR, '#FFFFFF', 0.4)
        dg.line([(cx - 20, c.Y(med[key])), (cx + 20, c.Y(med[key]))], INK, 2.0)
    c.yaxis([0, 1, 2], ['0', '1', '2'], f'Δ{G}: O3 − O0', offset=24)
    c.xaxis([0.5, 1.5], [f'{P} < α', f'{P} ≥ α'], ticks=False)

    dg.save(out / 'Fig3.drawio')
    return {'H1': h1, 'H2': h2,
            'cvar_tail_split': {'tasks_pfeas_at_least_alpha': int(high.sum()),
                                'median_contrast_pfeas_at_least_alpha': med['high'],
                                'median_contrast_pfeas_below_alpha': med['low']}}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    ledger = {'Fig2': figure2(args.repo, args.out), 'Fig3': figure3(args.repo, args.out)}
    (args.out / 'figure_ledger.json').write_text(json.dumps(ledger, indent=2) + '\n')
    print(json.dumps(ledger['Fig2'], indent=1))


if __name__ == '__main__':
    main()
