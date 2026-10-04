# Employee Collaboration Network

A social network analysis case study of internal email in four departments of a European research institution (SNAP [email-Eu-core-temporal](https://snap.stanford.edu/data/email-Eu-core-temporal.html)).

**Report:** [`report/SNA_Case_Study_Report.docx`](report/SNA_Case_Study_Report.docx) · **Text summary:** [`analysis/conclusion.txt`](analysis/conclusion.txt)

## Research questions

1. **Structure:** how do the departments differ in cohesion, fragmentation, reciprocity and team structure?
2. **Key people:** who are the hubs and brokers, and how concentrated is influence?
3. **Time:** how does communication change over time, and is the rhythm shared across departments?

## Main findings

- **Two organisational models.** Dept3 is one connected network held together by a few brokers. Dept1, Dept2 and Dept4 are each made up of 6–9 close-knit teams (clustering about 5× a random baseline) that never email each other within the department.
- **High modularity can mislead.** Dept1/2/4's high Q mostly reflects that disconnection; only Dept3's Q describes sub-teams inside one connected network.
- **Communication is two-way everywhere:** 71–82% of ties are answered.
- **Influence is concentrated differently:** one dominant hub in Dept1, a core of three in Dept2, brokers in Dept3, no single leader in Dept4.
- **A shared institutional rhythm.** All departments have the same high and low months, far more overlap than chance (permutation test, p ≈ 0.0006). The largest swings are week-long breaks and one surge week.

## Repository layout

```
data/        raw SNAP data: email-Eu-core-temporal/ (edge lists, src dst timestamp)
             and email-Eu-core/ (static network with department labels)
analysis/    pipeline scripts (stage*.py) and every generated table, figure and Gephi file
report/      Word report and the scripts that build it from the analysis outputs
run_pipeline.py   runs all analysis stages in the correct order
```

## Reproducing the analysis

```bash
pip install -r requirements.txt
python3 run_pipeline.py
```

Stage numbers reflect the order the stages were written; `run_pipeline.py` runs them in dependency order (the conclusion, stage 7, runs after the temporal stages 8–11 and 14).

To rebuild the report after rerunning the analysis (needs Node.js):

```bash
cd report && npm install && cd ..
python3 report/report_data.py
node report/build_report.js
```

## Gephi

`analysis/gephi/` has ready-made files:

- `Dept1–4.gexf`: open with **File → Open**; includes layout, community colours, PageRank sizes and centrality columns.
- `*_dynamic.gexf`: the same networks with timestamps; open, then enable the **Timeline** to animate communication over time.
- `*_edges.csv`: `Source,Target,Weight` edge lists for **Import Spreadsheet**.

The raw files can't be imported into Gephi directly: they have no header and one row per email, so Gephi reads timestamps as nodes.

## Data source

A. Paranjape, A. R. Benson and J. Leskovec. *Motifs in Temporal Networks.* WSDM 2017. Data from the [Stanford Network Analysis Project](https://snap.stanford.edu/data/email-Eu-core-temporal.html).
