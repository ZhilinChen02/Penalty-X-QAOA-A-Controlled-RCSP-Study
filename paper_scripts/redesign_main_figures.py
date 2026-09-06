#!/usr/bin/env python3
"""Redraw the four main-text figures from frozen data into a separate review package.

Presentation only: no optimizer, statistical resampling, reference updates or
writes to the original paper/results. The fourth main figure combines the five
existing depth/budget and finite-shot panels on one consistent canvas.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import LogLocator, LogFormatterMathtext, MaxNLocator, PercentFormatter
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INPUTS = (
    'results/phase0_v2_dilution_stress/task_characterization.csv',
    'results/phase0_v2_dilution_stress/penalty_contract_comparison.csv',
    'results/phase1_1_optimization_diagnostic/p3_random_vs_embedded.csv',
    'results/phase1_1_optimization_diagnostic/analysis/continuation_paired_comparison.csv',
    'results/phase2_confirmatory_v1/graph_level_contrasts.csv',
    'results/phase2_confirmatory_v1/confirmatory_statistics.json',
    'results/reviewer_robustness/B1_depth_budget/figure_data_nested_failure.csv',
    'results/reviewer_robustness/B1_depth_budget/depth_budget_summary_graph.csv',
    'results/reviewer_robustness/B1_depth_budget/depth_budget_effect_summary.csv',
    'results/reviewer_robustness/A3_finite_shot/finite_shot_training_effect_summary.csv',
    'results/reviewer_robustness/A3_finite_shot/finite_shot_training_summary_task.csv',
)
FILES = (
    'fig02_dilution_scale_control',
    'fig03_optimizer_attribution',
    'fig06_heldout_confirmation',
    'fig_main04_robustness_boundaries',
)
INK = '#22313D'
MUTED = '#677683'
GRID = '#E6EBEE'
BLUE = '#326A91'
TEAL = '#177E80'
RUST = '#BA563A'
GRAY = '#84939F'
BUDGETS = (120, 240, 480)
BUDGET_COLORS = (BLUE, TEAL, '#B27B40')
BUDGET_MARKERS = ('o', 's', '^')


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(relative):
    return pd.read_csv(ROOT / relative)


def style():
    plt.rcParams.update({
        'font.family': 'DejaVu Sans', 'font.size': 8.5,
        'mathtext.fontset': 'dejavusans', 'axes.labelsize': 8.5,
        'axes.labelcolor': INK, 'text.color': INK,
        'axes.edgecolor': '#A8B2BB', 'axes.linewidth': .65,
        'xtick.color': MUTED, 'ytick.color': MUTED,
        'xtick.labelsize': 8, 'ytick.labelsize': 8,
        'xtick.major.size': 3, 'ytick.major.size': 3,
        'xtick.major.width': .65, 'ytick.major.width': .65,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.grid': False, 'legend.frameon': False, 'legend.fontsize': 7.5,
        'lines.linewidth': 1.35, 'lines.markersize': 4,
        'figure.facecolor': 'white', 'axes.facecolor': 'white',
        'pdf.fonttype': 42, 'ps.fonttype': 42, 'svg.fonttype': 'none',
        'savefig.facecolor': 'white', 'savefig.dpi': 240,
    })


def clean(ax, grid='y'):
    ax.set_axisbelow(True)
    ax.grid(axis=grid, color=GRID, linewidth=.6)
    ax.tick_params(pad=4)
    ax.minorticks_off()


def panel(fig, ax, letter, title, subtitle='', fontsize=9.8):
    pos = ax.get_position()
    fig.text(pos.x0 - .032, pos.y1 + .044, letter, size=11, weight='bold', va='bottom')
    fig.text(pos.x0, pos.y1 + .044, title, size=fontsize, weight='bold', va='bottom')
    if subtitle:
        fig.text(pos.x0, pos.y1 + .009, subtitle, size=7.4, color=MUTED, va='bottom')


def jitter(length, width=.12):
    # Same fixed display jitter as the legacy primary-figure builder; no RNG use.
    ranks = np.arange(length)
    return ((ranks * .61803398875) % 1.0 - .5) * 2.0 * width


def save(fig, output, name):
    for suffix in ('pdf', 'svg', 'png'):
        # Fixed physical canvas: do not allow tight-bbox to change panel font scaling.
        kwargs = {'metadata': {'CreationDate': None, 'ModDate': None}} if suffix == 'pdf' else {}
        fig.savefig(output / f'{name}.{suffix}', **kwargs)
    plt.close(fig)


def benchmark(output, ledger):
    tasks, scales = load(INPUTS[0]), load(INPUTS[1])
    assert len(tasks) == len(scales) == 140
    fig = plt.figure(figsize=(7.2, 3.5))
    left = fig.add_axes([.093, .20, .36, .59])
    right = fig.add_axes([.66, .20, .305, .59])
    for m, group in tasks.groupby('n_edges'):
        left.scatter(np.full(len(group), m) + jitter(len(group), .10),
                     group.feasible_state_fraction, s=18, color=TEAL,
                     alpha=.66, edgecolors='white', linewidths=.3, zorder=3)
    left.set(yscale='log', xticks=sorted(tasks.n_edges.unique()),
             xlabel='Edge-bit variables, $m$', ylabel=r'Feasible-state fraction, $\phi_{\mathrm{state}}$')
    left.set_ylim(tasks.feasible_state_fraction.min()/1.65,
                  tasks.feasible_state_fraction.max()*1.6)
    left.yaxis.set_major_locator(LogLocator(base=10, numticks=6))
    clean(left)
    panel(fig, left, 'a', 'Feasible-space dilution', '140 tasks across 25 base graphs')

    data = [scales.current_energy_span.to_numpy(), scales.controlled_energy_span.to_numpy()]
    positions = [1, 0]
    bp = right.boxplot(data, positions=positions, widths=.36, orientation='horizontal',
        patch_artist=True, showfliers=False, medianprops={'color': INK, 'linewidth':1.3},
        whiskerprops={'color': GRAY, 'linewidth':.8}, capprops={'color': GRAY, 'linewidth':.8})
    for box, color in zip(bp['boxes'], (GRAY, TEAL)):
        box.set(facecolor=color, edgecolor=color, alpha=.23)
    for x, y, color in zip(data, positions, (GRAY, TEAL)):
        right.scatter(x, y+jitter(len(x), .12), s=9, alpha=.42, color=color, edgecolors='none', zorder=3)
    right.set(xscale='log', yticks=positions, yticklabels=['Raw', 'Scale-\ncontrolled'],
              xlabel='Hamiltonian energy span', ylim=(-.65,1.65))
    right.set_xlim(min(data[1])*.50, max(data[0])*2.0)
    right.set_xticks([1e3,1e5,1e7,1e9])
    right.xaxis.set_major_formatter(LogFormatterMathtext())
    right.spines['left'].set_visible(False)
    right.tick_params(axis='y', length=0, labelsize=8)
    clean(right,'x')
    panel(fig, right, 'b', 'Energy-span control', 'Raw and controlled Hamiltonians', fontsize=9.5)
    fig.text(.093, .048, 'No duplicate primary feasible sets', fontsize=8, color=MUTED)
    fig.text(.57, .048, 'Exact ground states preserved: 140/140', fontsize=8, color=TEAL)
    ledger['figure_1']={'tasks':len(tasks),'scale_rows':len(scales),'all_points_retained':True,
        'controlled_span_min':float(data[1].min()),'controlled_span_max':float(data[1].max()),
        'display_change':'energy-span panel rotated; same rows and boxplot statistics'}
    save(fig,output,FILES[0])


def optimizer(output,ledger):
    gap,cont=load(INPUTS[2]),load(INPUTS[3])
    merged=cont.merge(gap[['task_id','optimizer_seed','original_p3_worse_than_embedded_p2']],
                      on=['task_id','optimizer_seed'],how='left',validate='one_to_one')
    failure=merged.original_p3_worse_than_embedded_p2.astype(bool)
    assert len(gap)==len(merged)==168 and int(failure.sum())==29
    fig=plt.figure(figsize=(7.2,3.85))
    a=fig.add_axes([.10,.30,.355,.52]);b=fig.add_axes([.625,.30,.30,.52])
    ordered=gap.sort_values('p3_optimization_gap_vs_embedded_p2').reset_index(drop=True)
    colors=np.where(ordered.original_p3_worse_than_embedded_p2,RUST,GRAY)
    a.scatter(np.arange(1,len(ordered)+1),ordered.p3_optimization_gap_vs_embedded_p2,
              s=15,c=colors,alpha=.88,edgecolors='white',linewidths=.18,zorder=3)
    a.axhline(0,color=INK,linewidth=.8,zorder=2)
    a.set(xlabel='Seed-level comparisons, ranked by gap',ylabel=r'$E_{p=3}^{\mathrm{original}}-E_{p=2}^{\mathrm{embedded}}$',
          xlim=(-3,173),xticks=[1,42,84,126,168])
    a.yaxis.set_major_locator(MaxNLocator(5))
    clean(a)
    panel(fig,a,'a','Nested objective gap','Positive gaps certify optimizer failure')
    for mask,color,size,alpha in ((~failure,GRAY,19,.52),(failure,RUST,25,.88)):
        b.scatter(merged.loc[mask,'original_p3_G_feas'],merged.loc[mask,'G_feas_final'],
                  s=size,color=color,alpha=alpha,edgecolors='white',linewidths=.4,zorder=3)
    low=min(merged.original_p3_G_feas.min(),merged.G_feas_final.min())
    high=max(merged.original_p3_G_feas.max(),merged.G_feas_final.max())
    pad=(high-low)*.07;limits=(low-pad,high+pad)
    b.plot(limits,limits,color=GRAY,ls=(0,(4,3)),lw=.9,zorder=1)
    b.set(xlim=limits,ylim=limits,xlabel=r'Original $p=3$ $G_{\mathrm{feas}}$',
          ylabel=r'Continuation $p=3$ $G_{\mathrm{feas}}$')
    b.set_aspect('equal',adjustable='box');clean(b)
    panel(fig,b,'b','Feasibility after continuation','Dashed line: unchanged feasibility')
    fig.text(.10,.11,'29 / 168',color=RUST,weight='bold',size=12)
    fig.text(.23,.11,'certified failures',size=8,color=MUTED)
    fig.text(.61,.11,'27 / 29',color=RUST,weight='bold',size=12)
    fig.text(.74,.11,'gain feasibility',size=8,color=MUTED)
    fig.legend(handles=[Line2D([],[],marker='o',ls='',color=GRAY,label='Other pairs',markersize=4),
        Line2D([],[],marker='o',ls='',color=RUST,label='Original failure set',markersize=4)],
        loc='lower center',bbox_to_anchor=(.5,.017),ncol=2,columnspacing=2.4,handletextpad=.5)
    ledger['figure_2']={'comparisons':168,'certified_failures':29,
        'feasibility_improvements_in_failure_set':int((merged.loc[failure,'G_feas_final']>merged.loc[failure,'original_p3_G_feas']).sum()),
        'all_points_retained':True}
    assert ledger['figure_2']['feasibility_improvements_in_failure_set']==27
    save(fig,output,FILES[1])


def heldout(output,ledger):
    graph=load(INPUTS[4]);stats=json.loads((ROOT/INPUTS[5]).read_text())
    assert len(graph)==15 and stats['n_base_graphs']==15
    fig=plt.figure(figsize=(7.2,4.15))
    axes=[fig.add_axes([.10,.35,.355,.43]),fig.add_axes([.60,.35,.355,.43])]
    specs=[('H1','Delta1_CVAR_MEAN','O3 − O0',0.0,TEAL),
           ('H2','Delta2_CVAR_CAPACITY','O3 − O2',-.10,BLUE)]
    for letter,ax,(hyp,column,title,null,color) in zip('ab',axes,specs):
        result=stats[hyp];values=graph.sort_values(column)[column].to_numpy()
        rank=np.arange(1,16)
        ax.scatter(values,rank,s=26,color=color,edgecolors='white',linewidths=.5,zorder=4)
        ax.axvline(null,color=INK,ls=(0,(4,3)),lw=1,zorder=2)
        ax.axvline(result['effect_mean'],color=color,lw=1.55,zorder=2)
        ax.axvline(result['one_sided_95_lower_bound'],color=color,ls=':',lw=1.4,zorder=2)
        ax.set(ylim=(.3,15.7),yticks=[1,5,10,15],xlabel=r'Graph-level $\Delta G_{\mathrm{feas}}$ (decades)')
        if hyp=='H1':
            ax.set_ylabel('Graphs, ranked within each panel')
            ax.set_xlim(min(values.min(),null)-.07,values.max()+.07)
            ax.set_xticks([0,.3,.6,.9,1.2])
        else:
            ax.set_xlim(min(values.min(),null)-.016,values.max()+.016)
            ax.set_xticks([-.10,-.05,0,.05,.10])
        clean(ax,'x')
        panel(fig,ax,letter,f'{hyp}  |  {title}',
              'Superiority over mean energy' if hyp=='H1' else 'Noninferiority to capacity control')
        x=ax.get_position().x0
        fig.text(x,.204,'Mean effect',size=7.6,color=MUTED)
        fig.text(x+.205,.204,f"{result['effect_mean']:+.4f}",size=11,weight='bold',color=color)
        fig.text(x,.148,'One-sided 95% lower bound',size=7.6,color=MUTED)
        fig.text(x+.255,.148,f"{result['one_sided_95_lower_bound']:+.4f}",size=8.8,color=color)
        fig.text(x,.10,f"Holm-adjusted $p={result['holm_adjusted_p_value']:.6f}$",size=7.6,color=MUTED)
    fig.text(.10,.932,'Preregistered held-out evaluation',size=11.5,weight='bold')
    fig.text(.10,.885,'84 tasks  /  15 base graphs',size=8.4,color=MUTED)
    handles=[Line2D([],[],color=GRAY,lw=1.5,label='Mean'),
             Line2D([],[],color=GRAY,ls=':',lw=1.4,label='One-sided 95% lower bound'),
             Line2D([],[],color=INK,ls=(0,(4,3)),lw=1,label='Null / noninferiority margin')]
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.51,.006),ncol=3,
               fontsize=7,columnspacing=1.5,handlelength=2.2)
    ledger['figure_3']={'graph_count':len(graph),'task_count':84,'statistics':stats,
                      'inference_unchanged':True,'interval_type':'one-sided lower bound, not two-sided CI'}
    save(fig,output,FILES[2])


def robustness(output,ledger):
    nested,graph,effects,training,tasks=[load(p) for p in INPUTS[6:]]
    assert len(nested)==12 and len(graph)==180 and len(effects)==9 and len(training)==3
    fig=plt.figure(figsize=(7.2,6.8))
    a=fig.add_axes([.085,.615,.22,.23])
    b=fig.add_axes([.414,.615,.22,.23])
    c=fig.add_axes([.743,.615,.22,.23])
    d=fig.add_axes([.17,.11,.325,.2175])
    e=fig.add_axes([.67,.11,.293,.2175])
    fig.text(.052,.970,'Depth and evaluation budget',weight='bold',size=11)
    fig.text(.052,.938,'Post-hoc subset: 24 tasks on 10 graphs',color=MUTED,size=8)
    graph_depth=graph.groupby(['objective','depth','budget'],as_index=False).G_feas.median()
    plotted_nested=[]
    for index,(budget,color,marker) in enumerate(zip(BUDGETS,BUDGET_COLORS,BUDGET_MARKERS)):
        combined=nested[nested.budget.eq(budget)].groupby('transition',as_index=False).nested_failure_rate.mean()
        plotted_nested.extend(combined.assign(budget=budget).to_dict('records'))
        a.plot([0,1],combined.nested_failure_rate,color=color,marker=marker,ms=4.2,
               markeredgecolor='white',markeredgewidth=.35)
        for objective,linestyle in [('O0','--'),('O3','-')]:
            group=graph_depth[graph_depth.budget.eq(budget)&graph_depth.objective.eq(objective)].sort_values('depth')
            b.plot(group.depth,group.G_feas,color=color,ls=linestyle,marker=marker,ms=3.5,
                   markerfacecolor='white' if objective=='O0' else color,markeredgewidth=.65,lw=1.1)
        group=effects[effects.budget.eq(budget)].sort_values('depth')
        x=group.depth.to_numpy()+(index-1)*.065
        c.errorbar(x,group.graph_effect_mean,
            yerr=[group.graph_effect_mean-group.graph_effect_ci_lower,group.graph_effect_ci_upper-group.graph_effect_mean],
            color=color,marker=marker,ms=3.6,lw=.9,elinewidth=.85,capsize=2.2,capthick=.85,ls='none',zorder=3)
    a.set(xticks=[0,1],xticklabels=[r'$p=2\!\to\!3$',r'$p=3\!\to\!4$'],
          ylabel='Nested failure rate',xlim=(-.18,1.18),ylim=(0,.40),yticks=[0,.1,.2,.3,.4])
    a.yaxis.set_major_formatter(PercentFormatter(1,decimals=0))
    b.set(xticks=[2,3,4],xlabel='QAOA depth, $p$',ylabel=r'Median graph $G_{\mathrm{feas}}$',xlim=(1.85,4.15))
    b.yaxis.set_major_locator(MaxNLocator(4))
    c.set(xticks=[2,3,4],xlabel='QAOA depth, $p$',ylabel=r'Mean $\Delta G_{\mathrm{feas}}$  (O3 − O0)',xlim=(1.75,4.25),ylim=(0,1.3))
    c.set_yticks([0,.4,.8,1.2]);c.axhline(0,color=INK,lw=.8)
    for ax in (a,b,c):clean(ax)
    panel(fig,a,'a','Nested failures','O0 and O3 pooled',fontsize=9)
    panel(fig,b,'b','Terminal quality','Solid: O3  ·  dashed: O0',fontsize=9)
    panel(fig,c,'c','Objective contrast','Mean and 95% graph CI',fontsize=9)
    handles=[Line2D([],[],color=color,marker=marker,label=str(budget),ms=4,lw=1.2)
             for budget,color,marker in zip(BUDGETS,BUDGET_COLORS,BUDGET_MARKERS)]
    fig.text(.245,.535,'Objective-call budget',color=MUTED,size=7.8,va='center')
    fig.legend(handles=handles,loc='center left',bbox_to_anchor=(.45,.535),ncol=3,
               columnspacing=1.7,handlelength=1.7,handletextpad=.55)
    fig.add_artist(Line2D([.052,.965],[.488,.488],transform=fig.transFigure,color=GRID,lw=.85))
    fig.text(.052,.445,'Exact and finite-shot training',weight='bold',size=11)
    fig.text(.052,.417,'Post-hoc subset: 10 tasks on 10 held-out graphs',color=MUTED,size=8)

    order=['EXACT_CANONICAL','SHOT_10000','SHOT_1000']
    labels=['Exact','10,000 shots','1,000 shots']
    ordered=training.set_index('regime').loc[order]
    means=ordered.graph_effect_mean.to_numpy();lo=ordered.graph_effect_ci_lower.to_numpy();hi=ordered.graph_effect_ci_upper.to_numpy()
    y=np.arange(3)[::-1]
    d.errorbar(means,y,xerr=[means-lo,hi-means],fmt='o',color=TEAL,ms=5,
               elinewidth=1.5,capsize=3,capthick=1.2,zorder=3)
    d.axvline(0,color=INK,ls=(0,(4,3)),lw=.85)
    d.set(yticks=y,yticklabels=labels,ylim=(-.6,2.6),xlim=(-.095,.65),
          xticks=[0,.2,.4,.6],xlabel=r'Mean $\Delta G_{\mathrm{feas}}$  (O3 − O0)')
    d.spines['left'].set_visible(False);d.tick_params(axis='y',length=0);clean(d,'x')
    # Match the *existing PDF*: three groups of task summaries, not 100 noisy
    # optimizer runs per regime. The legacy aggregate caller now passes a different
    # frame; this entry point makes the existing rendered evidence source explicit.
    arrays=[tasks.loc[tasks.training_regime.eq(regime),'G_feas'].to_numpy() for regime in order]
    assert [len(values) for values in arrays]==[20,20,20]
    bp=e.boxplot(arrays,positions=[0,1,2],widths=.43,patch_artist=True,showfliers=False,
        medianprops={'color':TEAL,'lw':1.5},whiskerprops={'color':GRAY,'lw':.85},
        capprops={'color':GRAY,'lw':.85},boxprops={'edgecolor':GRAY,'lw':.85})
    for box in bp['boxes']:box.set(facecolor='#E6F0F0')
    for i,values in enumerate(arrays):
        e.scatter(i+jitter(len(values),.14),values,color=GRAY,s=9,alpha=.48,
                  edgecolors='white',linewidths=.2,zorder=2)
    e.set(xticks=[0,1,2],xticklabels=['Exact','$10^4$ shots','$10^3$ shots'],
          ylabel=r'Exact terminal $G_{\mathrm{feas}}$',ylim=(-.6,3.9),yticks=[0,1,2,3],
          xlabel='Training regime')
    clean(e)
    panel(fig,d,'d','Training effect','Mean and 95% graph CI',fontsize=9)
    panel(fig,e,'e','Terminal distribution','20 task–objective summaries / regime',fontsize=9)
    assert all(lo[1:]<0) and all(hi[1:]>0)
    ledger['figure_4']={'nested_rates_same_legacy_mean':plotted_nested,
        'graph_quality_same_legacy_medians':graph_depth.to_dict('records'),
        'depth_effects_and_CIs':effects.to_dict('records'),
        'training_effects_and_CIs':ordered.reset_index().to_dict('records'),
        'terminal_distribution_regime_order':order,
        'terminal_distribution_sample_sizes':[len(v) for v in arrays],
        'terminal_distribution_quantiles':{regime:np.quantile(v,[0,.25,.5,.75,1]).tolist() for regime,v in zip(order,arrays)},
        'terminal_distribution_source':'finite_shot_training_summary_task.csv, matching existing three-regime figure',
        'existing_builder_caller_issue':'aggregate_finite_shot_training passes runs-only data with two regimes; existing PDF has three task-summary regimes. Scientific source and existing PDF untouched.'}
    save(fig,output,FILES[3])


def paper_copy(output):
    paper=output/'paper'
    shutil.copytree(ROOT/'overleaf',paper,ignore=shutil.ignore_patterns('*.log','*.aux','*.bbl','*.blg','__pycache__'))
    for name in FILES:
        shutil.copy2(output/'figures'/f'{name}.pdf',paper/'figures'/f'{name}.pdf')
    for name in ('sn-jnl.cls','sn-mathphys-num.bst'):
        source=ROOT/'paper_assets/springer_nature_latex_2024_12'/name
        if source.exists() and not (paper/name).exists():shutil.copy2(source,paper/name)
    section=paper/'sections/04_optimizer_attribution.tex'
    old=('  \\includegraphics[width=\\textwidth]{fig12_reviewer_depth_budget.pdf}\n'
         '  \\includegraphics[width=\\textwidth]{fig15_reviewer_finite_shot_training.pdf}')
    text=section.read_text()
    if text.count(old)!=1:raise RuntimeError('expected one exact main-figure-4 inclusion block')
    section.write_text(text.replace(old,'  \\includegraphics[width=\\textwidth]{fig_main04_robustness_boundaries.pdf}'))
    # Preserve all captions, labels, scientific prose, tables and references.


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,help='new directory outside source tree; default unique temporary directory')
    args=parser.parse_args()
    if args.output_dir is None:output=Path(tempfile.mkdtemp(prefix='qroute-figures-v2-'))
    else:
        output=args.output_dir.resolve()
        if output==ROOT or ROOT in output.parents or output in ROOT.parents:parser.error('use an external review directory')
        output.mkdir(parents=True,exist_ok=False)
    figures=output/'figures';figures.mkdir()
    source_hashes={p:checksum(ROOT/p) for p in INPUTS}
    paper_hashes={p.relative_to(ROOT).as_posix():checksum(p) for p in (ROOT/'overleaf').rglob('*') if p.is_file()}
    style();ledger={}
    benchmark(figures,ledger);optimizer(figures,ledger);heldout(figures,ledger);robustness(figures,ledger)
    paper_copy(output)
    assert source_hashes=={p:checksum(ROOT/p) for p in INPUTS}
    assert paper_hashes=={p:checksum(ROOT/p) for p in paper_hashes}
    audit={'status':'PASS','optimizer_invoked':False,'statistics_refit':False,
           'scientific_inputs_unchanged':True,'original_paper_and_figures_unchanged':True,
           'source_hashes':source_hashes,'original_paper_hashes':paper_hashes,'plotted_data':ledger,
           'outputs':[f'figures/{name}.{suffix}' for name in FILES for suffix in ('pdf','svg','png')]}
    (output/'FIGURE_REDESIGN_AUDIT.json').write_text(json.dumps(audit,indent=2)+'\n')
    (output/'README.md').write_text('''# Main-figure redesign review

Four main-text figures rebuilt from frozen CSV/JSON without optimization or
statistical refitting. `figures/` contains vector PDF/SVG and PNG previews.
`paper/` is a separate copy with the redesigned figures integrated. Original
paper sources, original figures, results and the earlier public RC are unchanged.
All captions and numerical text are preserved; only the fourth main figure's
inclusion block changes to use a single five-panel canvas.

Reproduce from the original project:

```bash
python paper_scripts/redesign_main_figures.py
```

The audit JSON records each input hash, preserved inferential values, displayed
aggregations and denominators. Figure 3 retains ONE-SIDED lower bounds; Figure 4
retains its TWO-SIDED bootstrap CIs and both finite-shot intervals crossing zero.

## Existing plotting-provenance issue

The current finite-shot PDF contains three terminal-distribution boxes including
EXACT_CANONICAL. Its box statistics match `finite_shot_training_summary_task.csv`
(20 task–objective summaries per regime). The current aggregate caller passes
`finite_shot_training_runs.csv` to its plot helper, which contains only the two
shot regimes. This redesign explicitly uses the task-summary table matching the
existing PDF, and labels that aggregation accurately. It does not change the
scientific module, source data, run counts, conclusions or the original PDF.

This is a visual review package, not an updated public-release manifest. Existing
license, authorship and third-party template review requirements still apply.
''')
    print(json.dumps({'output':str(output),'figures':4,'files':12,'audit':'PASS'},indent=2))


if __name__=='__main__':main()
