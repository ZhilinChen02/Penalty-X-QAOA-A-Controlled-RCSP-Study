#!/usr/bin/env python3
"""Redesign main figures at the manuscript's 31-pica width using frozen evidence.

Writes only to a designated output directory. No optimization, resampling,
scientific implementation edits, or updates to canonical outputs are performed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch
from matplotlib.ticker import NullLocator, PercentFormatter
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
WIDTH = 372 / 72.27  # sn-jnl single-column text width: 31 TeX pica.
INK = '#111111'
GRAY = '#777777'
LIGHT = '#B5B5B5'
O0 = '#253E57'
O2 = '#087C80'
O3 = '#BA4E16'
FAILURE = '#913747'
BUDGETS = (120, 240, 480)
INPUTS = (
    'results/phase0_v2_dilution_stress/task_characterization.csv',
    'results/phase0_v2_dilution_stress/penalty_contract_comparison.csv',
    'data/manifests/phase0_v2_dilution_stress.json',
    'configs/phase0_v2_dilution_stress.yaml',
    'results/phase1_1_optimization_diagnostic/p3_random_vs_embedded.csv',
    'results/phase1_1_optimization_diagnostic/analysis/continuation_paired_comparison.csv',
    'results/phase2_confirmatory_v1/graph_level_contrasts.csv',
    'results/phase2_confirmatory_v1/confirmatory_statistics.json',
    'results/reviewer_robustness/B1_depth_budget/figure_data_nested_failure.csv',
    'results/reviewer_robustness/B1_depth_budget/depth_budget_summary_graph.csv',
    'results/reviewer_robustness/B1_depth_budget/depth_budget_effect_summary.csv',
    'results/reviewer_robustness/B1_depth_budget/B1_DEPTH_BUDGET.md',
    'results/reviewer_robustness/A3_finite_shot/finite_shot_training_effect_summary.csv',
    'results/reviewer_robustness/A3_finite_shot/finite_shot_training_summary_task.csv',
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv(name: str) -> pd.DataFrame:
    return pd.read_csv(ROOT / name)


def style() -> None:
    plt.rcParams.update({
        'font.family': 'STIXGeneral', 'font.size': 9,
        'mathtext.fontset': 'stix', 'text.color': INK,
        'axes.labelcolor': INK, 'axes.labelsize': 9,
        'axes.edgecolor': INK, 'axes.linewidth': .65,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.grid': False, 'xtick.color': INK, 'ytick.color': INK,
        'xtick.labelsize': 8, 'ytick.labelsize': 8,
        'xtick.major.size': 3, 'ytick.major.size': 3,
        'xtick.major.width': .65, 'ytick.major.width': .65,
        'xtick.direction': 'out', 'ytick.direction': 'out',
        'legend.fontsize': 8, 'legend.frameon': False,
        'lines.linewidth': 1.1, 'lines.markersize': 4,
        'figure.facecolor': 'white', 'axes.facecolor': 'white',
        'savefig.facecolor': 'white', 'savefig.dpi': 300,
        'pdf.fonttype': 42, 'ps.fonttype': 42, 'svg.fonttype': 'none',
        'svg.hashsalt': 'qroute-figure-v3',
    })


def tidy(ax) -> None:
    ax.tick_params(pad=3)
    ax.xaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_minor_locator(NullLocator())


def heading(fig, x, y, letter, title):
    fig.text(x, y, letter, fontsize=11, fontweight='bold', va='baseline')
    fig.text(x+.045, y, title, fontsize=10, fontweight='bold', va='baseline')


def jitter(n, width=.16):
    return ((np.arange(n) * .61803398875) % 1 - .5) * 2 * width


def save(fig, out, name):
    fig.canvas.draw()
    name = name.replace('_v3', '').replace('figS_finite_shot', 'finite_shot')
    for ext in ('pdf', 'png'):
        opts = {'metadata': {'CreationDate': None, 'ModDate': None}} if ext == 'pdf' else {}
        fig.savefig(out / f'{name}.{ext}', **opts)
    plt.close(fig)


def figure1(out, ledger):
    from qroute_dilution.reviewer_robustness.common import task_from_manifest_row

    tasks, scales = csv(INPUTS[0]), csv(INPUTS[1])
    manifest = json.loads((ROOT / INPUTS[2]).read_text())
    task = task_from_manifest_row(manifest['tasks'][0])
    ref = tasks.set_index('task_id').loc[task.task_id]
    assert task.graph.graph_id == ref.graph_id
    assert len(task.feasible_routes) == ref.n_feasible_states == 1
    assert task.optimal_cost == ref.optimal_cost == 4
    assert len(task.graph.edges) == 7 and len(tasks) == len(scales) == 140
    optimum = task.optimal_routes[0]
    assert optimum.resource == task.budget == 926
    fig = plt.figure(figsize=(WIDTH, 3.5))
    graph = fig.add_axes([.035, .615, .29, .235])
    dilution = fig.add_axes([.495, .17, .48, .67])
    scale = fig.add_axes([.13, .17, .18, .265])
    heading(fig, .02, .93, 'a', 'RCSP instance')
    heading(fig, .435, .93, 'b', 'Full-space dilution')
    heading(fig, .02, .49, 'c', 'Scale control')

    pos = {0:(0,0), 1:(.75,.60), 2:(.75,-.60), 3:(1.5,.60), 4:(1.5,-.60), 5:(2.25,0)}
    for edge in task.graph.edges:
        chosen = edge.index in optimum.edge_indices
        arrow = FancyArrowPatch(pos[edge.source], pos[edge.target], arrowstyle='-|>',
            mutation_scale=8, shrinkA=5, shrinkB=5,
            connectionstyle='arc3,rad=.24' if edge.index == 2 else 'arc3,rad=0',
            linewidth=1.65 if chosen else .7, color=INK if chosen else LIGHT, zorder=2 if chosen else 1)
        graph.add_patch(arrow)
    for node, xy in pos.items():
        graph.plot(*xy, 'o', ms=5, mfc=INK if node in optimum.nodes else 'white',
                   mec=INK if node in optimum.nodes else GRAY, mew=.7, zorder=4)
    graph.text(-.13, -.23, '$s$', fontsize=11, ha='center')
    graph.text(2.39, -.23, '$t$', fontsize=11, ha='center')
    graph.set(xlim=(-.3,2.55), ylim=(-.83,.88)); graph.axis('off')
    fig.text(.175, .585, r'$C^*=4,\quad R=B=926$', ha='center', fontsize=8)
    fig.text(.175, .54, r'$m=7:\quad |\mathcal{F}|/2^m=1/128$', ha='center', fontsize=8.5)

    for m, group in tasks.groupby('n_edges'):
        dilution.scatter(m+jitter(len(group),.18), group.feasible_state_fraction,
                         s=18, color=INK, edgecolors='white', linewidths=.25, zorder=3)
    dilution.set(yscale='log', xlim=(6,20), ylim=(1.4e-6,.075), xticks=[7,10,13,16,19],
                 yticks=[1e-5,1e-4,1e-3,1e-2], xlabel='Edge-bit variables, $m$',
                 ylabel=r'Feasible fraction, $|\mathcal{F}|/2^m$')
    dilution.text(.97,.96,'140 tasks\n25 base graphs', transform=dilution.transAxes,
                  ha='right', va='top', fontsize=8.5)
    fig.text(.495,.865,r'$P_{\rm feas}(|+\rangle^{\otimes m})=|\mathcal{F}|/2^m$',fontsize=8.7)
    tidy(dilution)
    for x, column, marker, color in [(0,'current_energy_span','o',GRAY),
                                     (1,'controlled_energy_span','s',INK)]:
        values=scales[column].to_numpy()
        scale.scatter(x+jitter(len(values),.22),values,s=8,color=color,alpha=.8,
                      marker=marker,linewidths=0,zorder=3)
        scale.plot([x-.26,x+.26],[np.median(values)]*2,color=INK,lw=1.2,zorder=4)
    scale.set(yscale='log', xlim=(-.5,1.5), ylim=(1e2,1e10),
              yticks=[1e3,1e6,1e9], xticks=[0,1], xticklabels=['Raw','Controlled'])
    scale.set_ylabel('Energy span',labelpad=1,fontsize=8.5)
    scale.tick_params(axis='x',labelsize=8)
    tidy(scale)
    fig.text(.02,.055,'Exact optima preserved: 140/140',fontsize=8.5)
    ledger['figure1']={'illustrated_task':task.task_id,'graph':task.graph.to_dict(),
        'optimal_route':optimum.to_dict(),'budget':task.budget,'n_tasks':140,
        'all_dilution_and_scale_rows_retained':True,'scale_display':'all points and medians; no new inference'}
    save(fig,out,'fig1_v3')


def figure2(out,ledger):
    gap, cont = csv(INPUTS[4]), csv(INPUTS[5])
    merged=cont.merge(gap[['task_id','optimizer_seed','original_p3_worse_than_embedded_p2']],
                      on=['task_id','optimizer_seed'],validate='one_to_one')
    mask=merged.original_p3_worse_than_embedded_p2.astype(bool)
    assert len(gap)==len(merged)==168 and mask.sum()==29
    better=(merged.loc[mask,'G_feas_final'] > merged.loc[mask,'original_p3_G_feas']).sum()
    objective_better=(merged.loc[mask,'objective_final'] < merged.loc[mask,'original_p3_objective']).sum()
    assert better==27 and objective_better==29
    fig=plt.figure(figsize=(WIDTH,3.05))
    a=fig.add_axes([.115,.23,.405,.60])
    b=fig.add_axes([.665,.23,.31,.60])
    heading(fig,.02,.925,'a','Certified optimizer failure')
    heading(fig,.60,.925,'b','Continuation')
    ordered=gap.sort_values('p3_optimization_gap_vs_embedded_p2')
    ranks=np.arange(1,169); failure=ordered.original_p3_worse_than_embedded_p2.to_numpy()
    values=ordered.p3_optimization_gap_vs_embedded_p2.to_numpy()
    a.axhline(0,color=INK,lw=.8,zorder=1)
    a.vlines(ranks[failure],0,values[failure],color=FAILURE,lw=.6,zorder=2)
    a.plot(ranks[~failure],values[~failure],'.',color=GRAY,ms=3.8,zorder=3)
    a.plot(ranks[failure],values[failure],'D',color=FAILURE,ms=2.5,mew=.2,zorder=4)
    a.set(xlim=(-3,176),ylim=(-.76,.68),xticks=[1,56,112,168],yticks=[-.6,-.3,0,.3,.6],
          xlabel='Seed-level comparisons, ranked',ylabel=r'$E_{p=3}-E_{p=2\to3}$')
    a.annotate('29/168\ncertified failures',xy=(155,.26),xytext=(9,.40),fontsize=8.7,
               ha='left',color=FAILURE,arrowprops={'arrowstyle':'-','lw':.7,'color':FAILURE})
    for sel, color, marker, size in [(~mask,LIGHT,'o',13),(mask,FAILURE,'D',21)]:
        b.scatter(merged.loc[sel,'original_p3_G_feas'],merged.loc[sel,'G_feas_final'],
                  s=size,c=color,marker=marker,edgecolors='white',linewidths=.3,zorder=3)
    low=min(merged.original_p3_G_feas.min(),merged.G_feas_final.min())-.10
    high=max(merged.original_p3_G_feas.max(),merged.G_feas_final.max())+.10
    b.plot([low,high],[low,high],color=INK,lw=1,ls=(0,(4,2)),zorder=2)
    b.set(xlim=(low,high),ylim=(low,high),xlabel=r'Original $G_{\rm feas}$',
          ylabel=r'Continued $G_{\rm feas}$')
    b.set_aspect('equal',adjustable='box')
    b.text(.045,.98,'27/29 failures\ngain feasibility',transform=b.transAxes,
           fontsize=8.2,va='top',ha='left',color=FAILURE)
    for ax in (a,b):tidy(ax)
    fig.text(.115,.072,'Continuation lowers the objective in all 29 certified failures.',fontsize=8.5)
    ledger['figure2']={'pairs':168,'failures':29,'objective_improves':29,'feasibility_improves':27,
                      'all_pairs_retained':True,'original_tolerance':gap.comparison_tolerance.unique().tolist()}
    save(fig,out,'fig2_v3')


def figure3(out,ledger):
    graph=csv(INPUTS[6]); stats=json.loads((ROOT/INPUTS[7]).read_text())
    assert len(graph)==15 and stats['n_base_graphs']==15
    fig=plt.figure(figsize=(WIDTH,3.65))
    axes=[fig.add_axes([.11,.285,.375,.55]),fig.add_axes([.61,.285,.365,.55])]
    for ax, letter, hyp, col, title, null, limits, ticks in [
        (axes[0],'a','H1','Delta1_CVAR_MEAN','H1: O3 − O0',0,(-.10,1.20),[0,.4,.8,1.2]),
        (axes[1],'b','H2','Delta2_CVAR_CAPACITY','H2: O3 − O2',-.1,(-.145,.145),[-.1,0,.1])]:
        result=stats[hyp]; x=np.sort(graph[col].to_numpy()); y=np.arange(1,16)
        mean=result['effect_mean']; lower=result['one_sided_95_lower_bound']
        heading(fig,ax.get_position().x0-.08,.928,letter,title)
        ax.axvline(null,color=GRAY,lw=.9,ls=(0,(3,2)),zorder=1)
        ax.hlines(y,0,x,color='#BBBBBB',lw=.6,zorder=2)
        if hyp=='H2':ax.axvline(0,color=LIGHT,lw=.55,zorder=1)
        ax.scatter(x,y,color=O3,s=15,edgecolor=INK,linewidths=.25,zorder=3)
        # One-sided interval: a lower cap and an open-ended arrow, never a
        # finite upper endpoint. The diamond is the frozen mean effect.
        ax.annotate('',xy=(limits[1]-.01*(limits[1]-limits[0]),-1.3),xytext=(lower,-1.3),
                    arrowprops={'arrowstyle':'->','lw':1.4,'color':O3})
        ax.plot([lower,lower],[-1.75,-.85],color=O3,lw=1.3)
        ax.plot(mean,-1.3,'D',ms=5.5,color=O3,mec=INK,mew=.4,zorder=4)
        ax.axhline(0,color=LIGHT,lw=.45,zorder=1)
        ax.set(xlim=limits,ylim=(-2.5,16.1),xticks=ticks,yticks=[1,5,10,15],
               xlabel=r'$\Delta G_{\rm feas}$ (decades)')
        if hyp=='H1':ax.set_ylabel('Graph rank')
        fig.text(ax.get_position().x0,.865,f"Mean {mean:+.4f}",fontsize=10,fontweight='bold')
        fig.text(ax.get_position().x0,.13,rf"One-sided $L_{{95}}={lower:+.4f}$",fontsize=8.8)
        fig.text(ax.get_position().x0,.082,r"$p_{\rm Holm}=2.44\times10^{-4}$",fontsize=8.8)
        tidy(ax)
        assert f"{result['holm_adjusted_p_value']:.3g}"=='0.000244'
    fig.text(.11,.022,'Frozen, preregistered held-out evaluation: 84 tasks / 15 graphs',fontsize=8.5)
    ledger['figure3']={'statistics':stats,'all_15_graph_effects_retained':True,
        'interval_representation':'one-sided 95% lower cap with arrow to positive infinity; diamond=mean',
        'graph_order':'ranked independently within each hypothesis','no_statistical_refit':True}
    save(fig,out,'fig3_v3')


def depth_effects():
    text=(ROOT/INPUTS[11]).read_text()
    pattern=(r'- (O[03]), (\d+) nfev: p4−p3 graph-mean G_feas=([\d.]+) '
             r'\(95% graph bootstrap CI \[([\d.]+), ([\d.]+)\]\)')
    rows=[{'objective':o,'budget':int(b),'mean':float(m),'lower':float(l),'upper':float(u)}
          for o,b,m,l,u in re.findall(pattern,text)]
    assert len(rows)==6
    graph=csv(INPUTS[9])
    for row in rows:
        frame=graph.loc[graph.objective.eq(row['objective']) & graph.budget.eq(row['budget'])]
        wide=frame.pivot(index='graph_id',columns='depth',values='G_feas')
        gains=wide[4]-wide[3]
        assert len(gains)==10 and (gains>0).all()
        assert abs(gains.mean()-row['mean']) < .000051
    return pd.DataFrame(rows)


def figure4(out,ledger):
    nested=csv(INPUTS[8]); effects=depth_effects()
    pooled=nested.groupby(['budget','transition'],as_index=False).nested_failure_rate.mean()
    fig=plt.figure(figsize=(WIDTH,3.2))
    a=fig.add_axes([.12,.25,.33,.55]); b=fig.add_axes([.645,.25,.33,.55])
    heading(fig,.02,.925,'a','Failure persists')
    heading(fig,.55,.925,'b','Depth adds feasible mass')
    for transition,marker,style_,fill in [('p2->p3','o','--','white'),('p3->p4','D','-',FAILURE)]:
        frame=pooled[pooled.transition.eq(transition)].sort_values('budget')
        assert len(frame)==3,pooled.transition.tolist()
        a.plot([0,1,2],frame.nested_failure_rate,color=FAILURE,marker=marker,ls=style_,
               ms=4.5,mfc=fill,mew=.9,lw=1)
    a.set(xticks=[0,1,2],xticklabels=BUDGETS,xlim=(-.2,2.2),ylim=(0,.4),
          yticks=[0,.1,.2,.3,.4],xlabel='Objective-call budget',ylabel='Nested failure rate')
    a.yaxis.set_major_formatter(PercentFormatter(1,decimals=0))
    a.text(.04,.98,r'$p=3\to4$',transform=a.transAxes,fontsize=9,va='top',color=FAILURE)
    a.text(.04,.40,r'$p=2\to3$',transform=a.transAxes,fontsize=9,color=FAILURE)
    for i,budget in enumerate(BUDGETS):
        for o,color,marker,offset in [('O0',O0,'o',.14),('O3',O3,'^',-.14)]:
            r=effects[effects.objective.eq(o)&effects.budget.eq(budget)].iloc[0]
            b.errorbar(r['mean'],2-i+offset,xerr=[[r['mean']-r.lower],[r.upper-r['mean']]],
                fmt=marker,color=color,ms=4.5,capsize=2.4,lw=1.1,mec=color,
                mfc='white' if o=='O0' else color,zorder=3)
    b.axvline(0,color=GRAY,ls=(0,(3,2)),lw=.8,zorder=1)
    b.set(yticks=[2,1,0],yticklabels=BUDGETS,ylim=(-.65,2.65),xlim=(-.06,1.16),
          xticks=[0,.5,1],xlabel=r'$G_{\rm feas}(p=4)-G_{\rm feas}(p=3)$',ylabel='Objective-call budget')
    b.set_xlabel(r'$p=4-p=3$ gain (decades)',fontsize=8.6)
    b.legend(handles=[Line2D([],[],color=O0,marker='o',mfc='white',ls='-',label='O0'),
                      Line2D([],[],color=O3,marker='^',ls='-',label='O3')],
             loc='upper left',bbox_to_anchor=(-.02,1.17),ncol=2,handlelength=1.2,
             columnspacing=1,handletextpad=.4,borderaxespad=0)
    for ax in (a,b):tidy(ax)
    fig.text(.12,.09,'Post-hoc subset: 24 tasks / 10 graphs; graph-bootstrap 95% CIs in b.',fontsize=8.2)
    ledger['figure4']={'nested_failure_rates':pooled.to_dict('records'),
        'depth_gains_and_CIs':effects.to_dict('records'),
        'CI_source':'Existing B1_DEPTH_BUDGET.md, unchanged at its reported four-decimal precision',
        'graph_gain_means_verified_against_frozen_graph_table':True,
        'finite_shot_moved_to_supplement':True,'main_panel_count':2}
    save(fig,out,'fig4_v3')


def supplement(out,ledger):
    effects=csv(INPUTS[12]);tasks=csv(INPUTS[13])
    regimes=['EXACT_CANONICAL','SHOT_10000','SHOT_1000']
    frame=effects.set_index('regime').loc[regimes]
    fig=plt.figure(figsize=(WIDTH,3.3))
    a=fig.add_axes([.16,.24,.31,.57]);b=fig.add_axes([.66,.24,.31,.57])
    heading(fig,.02,.92,'a','Training effect')
    heading(fig,.57,.92,'b','Terminal distribution')
    means=frame.graph_effect_mean.to_numpy();low=frame.graph_effect_ci_lower.to_numpy();high=frame.graph_effect_ci_upper.to_numpy()
    a.errorbar(means,[2,1,0],xerr=[means-low,high-means],fmt='D',color=O3,ms=4.5,capsize=3,lw=1.2)
    a.axvline(0,color=GRAY,lw=.9,ls=(0,(3,2)))
    a.set(yticks=[2,1,0],yticklabels=['Exact','$10^4$ shots','$10^3$ shots'],ylim=(-.6,2.6),
          xlim=(-.07,.64),xticks=[0,.2,.4,.6],xlabel=r'$\Delta G_{\rm feas}$ (O3 − O0)')
    arrays=[tasks.loc[tasks.training_regime.eq(r),'G_feas'].to_numpy() for r in regimes]
    assert [len(v) for v in arrays]==[20]*3
    b.boxplot(arrays,positions=[0,1,2],widths=.48,showfliers=False,
              medianprops={'color':INK,'lw':1.2},boxprops={'color':INK,'lw':.7},
              whiskerprops={'color':GRAY,'lw':.7},capprops={'color':GRAY,'lw':.7})
    for i,arr in enumerate(arrays):
        b.scatter(i+jitter(len(arr),.14),arr,s=10,color=GRAY,alpha=.7,linewidths=0,zorder=3)
    b.set(xticks=[0,1,2],xticklabels=['Exact','$10^4$','$10^3$'],ylim=(-.6,3.85),
          xlabel='Training shots per call',ylabel=r'Exact terminal $G_{\rm feas}$')
    for ax in (a,b):tidy(ax)
    fig.text(.16,.09,'10 held-out graphs; both shot-trained effect intervals cross zero.',fontsize=8.3)
    assert (low[1:]<0).all() and (high[1:]>0).all()
    ledger['supplement_finite_shot']={'effects':frame.reset_index().to_dict('records'),
        'terminal_distribution_quantiles':{r:np.quantile(v,[0,.25,.5,.75,1]).tolist() for r,v in zip(regimes,arrays)},
        'sample_sizes':[20]*3,'source':'same task-summary groups as the existing PDF, verified in Figure v2 audit'}
    save(fig,out,'figS_finite_shot_v3')
