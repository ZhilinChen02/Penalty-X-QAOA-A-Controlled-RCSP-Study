#!/usr/bin/env python3
"""Build, compile and package a separate Figure v3 manuscript/review copy.

Requires the normal plotting dependencies, PyMuPDF (review/export only),
and working pdflatex/bibtex executables. Does not write canonical results.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

import pymupdf

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'Expected exactly one source block: {old[:80]!r}')
    return text.replace(old, new)


def replace_figure(text, label, image, caption):
    pattern=r'\\begin\{figure\}\[t\].*?\\end\{figure\}'
    matches=[m for m in re.finditer(pattern,text,re.S) if '\\label{'+label+'}' in m.group()]
    if len(matches)!=1:raise ValueError(label)
    match=matches[0]
    new=('\\begin{figure}[t]\n  \\centering\n'
         f'  \\includegraphics[width=\\linewidth]{{{image}}}\n'
         f'  \\caption{{{caption}}}\n  \\label{{{label}}}\n\\end{{figure}}')
    return text[:match.start()]+new+text[match.end():]


def integrate(out, template_dir=None):
    paper=out/'paper'
    shutil.copytree(ROOT/'overleaf',paper,dirs_exist_ok=True,
        ignore=shutil.ignore_patterns('*.aux','*.log','*.out','*.bbl','*.blg','*.fls','*.fdb_latexmk'))
    template = template_dir or ROOT/'paper_assets/springer_nature_latex_2024_12'
    for name in ('sn-jnl.cls','sn-mathphys-num.bst'):
        if not (template/name).is_file():
            raise FileNotFoundError(f'{name} is required. Obtain the official Springer template and pass --template-dir; see paper/README.md.')
        shutil.copy2(template/name,paper/name)
    for name in ['fig1_v3','fig2_v3','fig3_v3','fig4_v3','figS_finite_shot_v3']:
        shutil.copy2(out/f'{name}.pdf',paper/'figures'/f'{name}.pdf')
    methods=paper/'sections/03_methods.tex'
    s=replace_figure(methods.read_text(),'fig:dilution-scale','fig1_v3.pdf',r'''Controlled RCSP benchmark and representation-induced dilution.
  \textbf{a}, one frozen seven-edge task; the heavy path is its unique feasible
  and optimal route, with cost 4 and resource use equal to the budget 926.
  \textbf{b}, all 140 distinct-cardinality tasks on 25 base graphs. Uniform
  edge-bit states assign feasible mass $|\mathcal{F}|/2^m$.
  \textbf{c}, every raw and controlled energy span; horizontal marks are
  medians. Scale control preserves every exact ground state''')
    methods.write_text(s)
    results=paper/'sections/04_optimizer_attribution.tex';s=results.read_text()
    s=replace_figure(s,'fig:optimizer-attribution','fig2_v3.pdf',r'''Nested optimizer diagnosis and continuation.
  \textbf{a}, the original $p=3$ objective minus the exactly embedded $p=2$
  objective for all 168 task--seed pairs, ranked by signed gap. The 29
  certified failures are diamonds; the remaining pairs are grey circles.
  \textbf{b}, matched feasibility before and after continuation; the dashed
  line is equality and diamonds identify the same original failure set.
  Continuation lowers the objective in 29/29 failures and increases
  $\gfeas$ in 27/29''')
    s=replace_figure(s,'fig:heldout','fig3_v3.pdf',r'''Frozen, preregistered held-out objective alignment on 84 tasks and
  15 graphs. \textbf{a}, H1 (O3--O0); \textbf{b}, H2 (O3--O2). Each circle
  is a complete graph mean, ranked independently within its panel; stems
  extend from zero. Diamonds below the graph points are the mean effects.
  Each lower cap and rightward arrow denotes a one-sided 95\% interval
  extending to $+\infty$, not a two-sided interval. Dashed lines mark zero
  for H1 and the frozen $-0.10$ non-inferiority margin for H2; the thin
  solid line in b marks zero. $L_{95}$ is the one-sided lower bound and
  both displayed $p$-values are Holm adjusted''')
    s=replace_figure(s,'fig:robustness-boundaries','fig4_v3.pdf',r'''Depth and budget boundaries on the preselected post-hoc subset
  of 24 tasks and 10 graphs. \textbf{a}, certified nested-failure rates pool
  O0 and O3 over three seeds (144 comparisons per transition and budget).
  Increasing the tested objective-call budget does not monotonically reduce
  failures. \textbf{b}, equal-weight graph means and 95\% graph-bootstrap
  intervals for the $p=4$ minus $p=3$ feasibility gain; circles denote O0
  and triangles O3. Intervals retain the precision reported in the frozen
  depth--budget report. Finite-shot training and the full depth summaries
  are shown in Online Resource~1''')
    s=replace_once(s,'In the preselected 24-task depth--budget subset, pooled',
        'In the preselected 24-task depth--budget subset\n(\\cref{fig:robustness-boundaries}), pooled')
    s=replace_once(s,'decisive (\\cref{fig:robustness-boundaries}).',
        'decisive (Online Resource~1, finite-shot training analysis).')
    results.write_text(s)
    appendix=paper/'appendices/appendix_reviewer_robustness.tex';s=appendix.read_text()
    insertion=r'''

\begin{figure}[t]
  \centering
  \includegraphics[width=\linewidth]{fig12_reviewer_depth_budget.pdf}
  \caption{Full depth--budget summaries retained from the original
  robustness figure: pooled nested failures, terminal graph quality by depth
  and objective, and paired O3--O0 graph effects with 95\% graph-bootstrap
  intervals. These panels complement the main article's depth-gain and
  budget-boundary display}
  \label{fig:reviewer-depth-full}
\end{figure}
'''
    s=replace_once(s,'\\input{tables/tableS7_depth_budget.tex}',
        '\\input{tables/tableS7_depth_budget.tex}'+insertion)
    old=("The main article's robustness figure displays these graph intervals and\n"
         'terminal-state distributions; the complete numerical matrix remains in\n'
         '\\cref{tab:reviewer-finite-training}.')
    new=r'''\Cref{fig:reviewer-finite-training} displays these graph intervals and
terminal-state distributions; the complete numerical matrix remains in
\cref{tab:reviewer-finite-training}.

\begin{figure}[t]
  \centering
  \includegraphics[width=\linewidth]{figS_finite_shot_v3.pdf}
  \caption{Exact-terminal evaluation after exact or finite-shot training on
  ten held-out graphs. \textbf{a}, paired O3--O0 graph effects and two-sided
  95\% graph-bootstrap intervals; both shot-trained intervals cross zero.
  \textbf{b}, terminal quality for the same three training regimes, pooling
  20 task--objective summaries per regime. Boxes show quartiles and medians,
  whiskers extend to the most extreme observations within 1.5 interquartile
  ranges, and dots show all summaries. These are task summaries, not
  individual noisy-training runs}
  \label{fig:reviewer-finite-training}
\end{figure}'''
    s=replace_once(s,old,new);appendix.write_text(s)
    # Instrumentation reports the actual layout dimensions in the compile log.
    for name in ['main.tex','ESM_1.tex']:
        p=paper/name;s=p.read_text()
        p.write_text(replace_once(s,'\\begin{document}',
            '\\begin{document}\n\\typeout{FIGURE-V3-TEXTWIDTH=\\the\\textwidth; TEXTHEIGHT=\\the\\textheight}'))
    # All original science-bearing prose stays literal; only the two navigation
    # substitutions above and figure blocks differ in the main results section.
    strip=lambda t:re.sub(r'\\begin\{figure\}.*?\\end\{figure\}','',t,flags=re.S)
    original=strip((ROOT/'overleaf/sections/04_optimizer_attribution.tex').read_text())
    edited=strip(results.read_text())
    edited=edited.replace('In the preselected 24-task depth--budget subset\n(\\cref{fig:robustness-boundaries}), pooled',
                          'In the preselected 24-task depth--budget subset, pooled')
    edited=edited.replace('decisive (Online Resource~1, finite-shot training analysis).',
                          'decisive (\\cref{fig:robustness-boundaries}).')
    assert edited==original
    assert strip(methods.read_text())==strip((ROOT/'overleaf/sections/03_methods.tex').read_text())
    return paper


def compile_paper(paper,out,tex_bin):
    env=os.environ.copy()
    if tex_bin:env['PATH']=str(tex_bin)+os.pathsep+env['PATH']
    for tool in ['pdflatex','bibtex']:
        if not shutil.which(tool,path=env['PATH']):raise RuntimeError(f'{tool} is required; use --tex-bin')
    report={}
    for stem in ['main','ESM_1']:
        tex=['pdflatex','-interaction=nonstopmode','-halt-on-error',stem+'.tex']
        commands=[tex]+([['bibtex',stem]] if stem=='main' else [])+[tex]*3
        with (out/f'{stem}_compile_console.txt').open('w') as stream:
            for cmd in commands:
                stream.write('$ '+' '.join(cmd)+'\n');stream.flush()
                run=subprocess.run(cmd,cwd=paper,env=env,stdout=stream,stderr=subprocess.STDOUT)
                if run.returncode:raise RuntimeError(f'{stem} compile failed; inspect console log')
        log=(paper/f'{stem}.log').read_text(errors='replace')
        issues=[line for line in log.splitlines() if re.search(
            r'undefined references|Reference .+ undefined|Citation .+ undefined|multiply defined|Missing character|^!',line)]
        assert not issues,issues
        width=re.search(r'FIGURE-V3-TEXTWIDTH=([\d.]+)pt',log)
        assert width and abs(float(width[1])-372)<1e-6
        with pymupdf.open(paper/f'{stem}.pdf') as doc:pages=len(doc)
        report[stem]={'status':'PASS','pages':pages,'text_width_TeX_pt':float(width[1]),
            'undefined_references_or_citations':0,'overfull_warnings':[s for s in log.splitlines() if 'Overfull' in s]}
    shutil.copy2(paper/'main.pdf',out/'Q-RouteDilution-paper-figures-v3.pdf')
    shutil.copy2(paper/'ESM_1.pdf',out/'Q-RouteDilution-supplement-figures-v3.pdf')
    (out/'FULL_PAPER_COMPILE.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def exports(out,paper):
    merged=pymupdf.open()
    for i in range(1,5):
        with pymupdf.open(out/f'fig{i}_v3.pdf') as doc:merged.insert_pdf(doc)
    merged.set_metadata({'title':'Q-RouteDilution — Figure v3, four main figures'})
    merged.save(out/'main_figures_v3.pdf');merged.close()
    pages=out/'paper_pages';pages.mkdir(exist_ok=True)
    captions=['Controlled RCSP benchmark','Nested optimizer diagnosis and continuation',
              'Frozen, preregistered held-out objective alignment','Depth and budget boundaries']
    page_report=[]
    with pymupdf.open(paper/'main.pdf') as doc:
        for i,caption in enumerate(captions,1):
            hits=[n for n,p in enumerate(doc) if caption in ' '.join(p.get_text().split())]
            assert len(hits)==1,(i,hits)
            n=hits[0];page=doc[n]
            page.get_pixmap(matrix=pymupdf.Matrix(1.6,1.6)).save(pages/f'figure_{i}_page.png')
            page_report.append({'figure':i,'manuscript_page':n+1,'page_preview':f'paper_pages/figure_{i}_page.png'})
    (out/'MANUSCRIPT_FIGURE_PAGES.json').write_text(json.dumps(page_report,indent=2)+'\n')
    old=out/'v2';old.mkdir(exist_ok=True)
    comparison_available=all((ROOT/f'dist/figures_v2/fig{i}_redesign.png').is_file() for i in range(1,5))
    if comparison_available:
        for i in range(1,5):shutil.copy2(ROOT/f'dist/figures_v2/fig{i}_redesign.png',old/f'fig{i}.png')
    sections=[]
    for row in page_report:
        i=row['figure']
        sections.append(f'''<section><h2>Figure {i}</h2><p><a href="fig{i}_v3.pdf">PDF</a> · <a href="fig{i}_v3.svg">SVG</a> · <a href="fig{i}_v3.png">PNG</a> · <a href="{row['page_preview']}">论文第 {row['manuscript_page']} 页</a></p><div class="comparison"><figure class="old"><figcaption>v2</figcaption><img src="v2/fig{i}.png" alt="Figure {i} v2"></figure><figure><figcaption>v3 · 按论文实际宽度设计</figcaption><img src="fig{i}_v3.svg" alt="Figure {i} v3"></figure></div><details><summary>查看编译后的论文页面</summary><img class="page" src="{row['page_preview']}" alt="Compiled manuscript page"></details></section>''')
    html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Q-RouteDilution · Figure v3 review</title><style>body{max-width:1550px;margin:35px auto;padding:0 25px;color:#111;background:white;font:16px/1.6 Georgia,serif}h1{font-size:30px}h2{border-top:1px solid #ccc;padding-top:25px}a{color:#253e57}nav{line-height:2}.comparison{display:grid;grid-template-columns:1fr 1fr;gap:24px;align-items:start}figure{margin:0}figcaption{font-weight:bold;margin:12px 0}img{width:100%;height:auto}.page{max-width:840px}details{margin:16px 0 35px}button{background:white;color:#111;border:1px solid #777;padding:6px 12px;cursor:pointer;margin:12px 8px 12px 0}.new .old{display:none}.new .comparison{grid-template-columns:minmax(0,1000px)}@media(max-width:800px){.comparison{grid-template-columns:1fr}}@media print{.old,button,details,nav{display:none}.comparison{display:block}section{break-after:page}}</style><h1>Figure v3：结构重构与论文版式核验</h1><p>主文实际宽度 31 pica（约 13.1 cm）。高对比衬线字体；Figure 4 为两个大面板，finite-shot 完整移入补充材料。冻结数据与科学数值保持不变。</p><nav><a href="Q-RouteDilution-paper-figures-v3.pdf">完整论文 PDF</a> · <a href="Q-RouteDilution-supplement-figures-v3.pdf">补充材料 PDF</a> · <a href="main_figures_v3.pdf">四图 PDF</a> · <a href="Q-RouteDilution-figures-v3-review.zip">完整审阅包</a> · <a href="Q-RouteDilution-paper-figures-v3.zip">LaTeX 包</a> · <a href="FIGURE_V3_REVIEW.md">核验说明</a></nav><button onclick="document.body.classList.remove('new')">新旧并排</button><button onclick="document.body.classList.add('new')">只看 v3</button>'''+''.join(sections)+'''<section><h2>移入补充材料：finite-shot training</h2><p>两侧 95% graph-bootstrap 区间与原始分组保持一致。</p><img style="max-width:1000px" src="figS_finite_shot_v3.svg" alt="Supplementary finite-shot figure"></section></html>'''
    if not comparison_available:
        html=re.sub(r'<figure class="old">.*?</figure>','',html,flags=re.S)
        html=html.replace('<html lang="zh-CN">','<html lang="zh-CN" class="public-release">')
        html=html.replace('</style>','.public-release .comparison{grid-template-columns:minmax(0,1000px)}</style>')
        html=html.replace('新旧并排','并排查看').replace('v2/v3','v3')
    (out/'index.html').write_text(html)


def package(out,paper):
    keep=lambda p: p.suffix.lower() in {'.tex','.bib','.bst','.cls','.pdf','.csv','.txt','.md','.json'} and p.name not in {'main.pdf','ESM_1.pdf'}
    with zipfile.ZipFile(out/'Q-RouteDilution-paper-figures-v3.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(paper.rglob('*')):
            if p.is_file() and keep(p):z.write(p,p.relative_to(paper))
    target=out/'Q-RouteDilution-figures-v3-review.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.rglob('*')):
            rel=p.relative_to(out)
            if p.is_file() and p!=target and rel.parts[0] not in {'baseline','paper'} and p.suffix not in {'.log','.aux','.fls','.fdb_latexmk','.out','.bbl','.blg','.toc'}:
                if rel.as_posix()=='index.html':
                    # The extracted archive should not link to an absent copy
                    # of itself; the live shared-directory page keeps the link.
                    html=p.read_text().replace('<a href="Q-RouteDilution-figures-v3-review.zip">完整审阅包</a> · ','')
                    z.writestr('index.html',html)
                else:
                    z.write(p,rel)
    for p in [target,out/'Q-RouteDilution-paper-figures-v3.zip']:
        with zipfile.ZipFile(p) as z:assert z.testzip() is None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'dist/figures_v3')
    parser.add_argument('--tex-bin',type=Path)
    parser.add_argument('--template-dir',type=Path,help='official Springer template directory; required when vendor files are omitted')
    args=parser.parse_args();out=args.output_dir.resolve()
    if out==ROOT or out in ROOT.parents or any((ROOT/d)==out or (ROOT/d) in out.parents for d in ['src','data','results','configs','overleaf','reproduction','tests']):
        parser.error('output must be a separate review directory')
    if not (out/'FIGURE_V3_DATA_AUDIT.json').is_file():parser.error('render v3 figures first')
    paper=integrate(out,args.template_dir.resolve() if args.template_dir else None)
    report=compile_paper(paper,out,args.tex_bin)
    exports(out,paper)
    (out/'FIGURE_V3_REVIEW.md').write_text('''# Figure v3 review

Four main figures are designed at the actual 31-pica manuscript width. Text is
black STIX serif, with coordinated mathematical notation; minimum nominal
label size is 8 pt. O0 is dark blue, O2 teal, O3 burnt orange; reference data
are neutral and certified failures use restrained crimson. Marker shapes,
filled/open symbols and line styles supplement color.

1. RCSP: an actual frozen seven-edge instance accompanies the dominant dilution
   plot; the smaller energy-span panel retains all 140 paired observations.
2. Diagnosis: ranked objective gaps emphasize all 29 certified failures;
   continuation retains every pair, a visible equality line and the 27/29
   feasibility-recovery count. Objective-mismatch evidence stays in the
   original main-text paragraph and supplementary analyses.
3. Held-out inference: ranked graph effects plus a distinct inferential row.
   One-sided lower bounds have rightward arrows to indicate no finite upper
   endpoint. Means, lower bounds and Holm-adjusted p-values are frozen.
4. Depth/budget: two large panels show persistent nested failure and positive
   p=4 minus p=3 gains. The six depth-gain CIs come directly from the existing
   frozen report at its published four-decimal precision; graph means were
   independently checked against the frozen graph table. No bootstrap refit
   is used to draw the figures. Finite-shot results and full depth summaries
   are retained in the supplement; the main-text finite-shot numbers and
   conclusions are unchanged.

The independent `paper/` copy uses the original Springer class and retains
all author-action placeholders. Captions and figure navigation were updated
to match the new panel structure. Original paper sources and figures are
untouched. Both main manuscript and supplement compile with pdfLaTeX; see
`FULL_PAPER_COMPILE.json`, console logs and the actual page previews.

Scientific inputs, plotted values and hashes: `FIGURE_V3_DATA_AUDIT.json`.
The original finite-shot plotting-caller provenance issue remains documented
in Figure v2; this supplement uses the same verified task-summary groups.

Rebuild from the project with plotting dependencies and PyMuPDF installed:

```bash
python paper_scripts/redesign_main_figures_v3.py
python paper_scripts/build_figure_v3_review.py --tex-bin /path/to/texlive/bin
```

The HTML, compiled PDFs, editable SVGs, PNG previews, LaTeX ZIP and complete
review ZIP reside on the shared filesystem in `dist/figures_v3/`.
''')
    package(out,paper)
    print(json.dumps({'status':'PASS','compile':report,'output':str(out)},indent=2))


if __name__=='__main__':main()
