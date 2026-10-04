/*
 * Build the case-study report (SNA_Case_Study_Report.docx) from report_data.json.
 *
 *   python3 report/report_data.py && node report/build_report.js
 *
 * All numbers come from report_data.json, which is generated from the
 * analysis outputs, so rerun both after changing the pipeline.
 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, ImageRun,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, Header, Footer,
  PageNumber, PageBreak, TableOfContents, LevelFormat, TabStopType,
} = require("docx");

const data = JSON.parse(fs.readFileSync(path.join(__dirname, "report_data.json"), "utf8"));
const D = data.depts;
const T = data.temporal;
const F = data.figures;
const DEPTS = ["Dept1", "Dept2", "Dept3", "Dept4"];
const FRAG = DEPTS.filter((k) => D[k].wcc > 1);
const CONN = DEPTS.filter((k) => D[k].wcc === 1);

// ── formatting helpers ───────────────────────────────────────────────────────
const n = (x, dp = 2) => Number(x).toFixed(dp);
const int = (x) => Math.round(x).toLocaleString("en-US");
const pct = (x, dp = 0) => `${Number(x).toFixed(dp)}%`;
const vals = (key, ds = DEPTS) => ds.map((k) => D[k][key]);
const range = (key, dp = 2, ds = DEPTS, suffix = "") =>
  `${n(Math.min(...vals(key, ds)), dp)}${suffix}–${n(Math.max(...vals(key, ds)), dp)}${suffix}`;
const list = (xs) => (xs.length <= 1 ? xs.join("") : `${xs.slice(0, -1).join(", ")} and ${xs[xs.length - 1]}`);
const intersect = (lists) => lists.reduce((a, b) => a.filter((x) => b.includes(x)));

const sharedHigh = intersect(DEPTS.map((k) => T.high[k]));
const sharedLow = intersect(DEPTS.map((k) => T.low[k]));
const highIn3 = ["M13"].filter((m) => DEPTS.filter((k) => T.high[k].includes(m)).length === 3);
const perChannelMax = DEPTS.reduce((a, b) => (D[a].per_channel > D[b].per_channel ? a : b));
const perChannelMin = DEPTS.reduce((a, b) => (D[a].per_channel < D[b].per_channel ? a : b));
const btwMaxOthers = Math.max(...vals("top_btw", DEPTS.filter((k) => k !== "Dept3")));
const recipRatio = DEPTS.map((k) => D[k].reciprocity / D[k].reciprocity_random);
const lowLens = T.low_weeks.map((w) => w.end - w.start + 1);
const longestLow = T.low_weeks[lowLens.indexOf(Math.max(...lowLens))];
const days = T.main_end + 1;
const flaggedLow = new Set(DEPTS.flatMap((k) => T.low[k]));
const missedLow = [...new Set(T.low_weeks.filter((w) => w.months.length === 1).map((w) => w.months[0]))]
  .filter((m) => !flaggedLow.has(m)).sort();

// ── layout constants (A4, 1" margins) ────────────────────────────────────────
const PAGE_W = 11906, PAGE_H = 16838, MARGIN = 1440;
const CONTENT_W = PAGE_W - 2 * MARGIN;          // 9026 DXA
const IMG_W = 600;                              // px ≈ 6.25"
const NAVY = "1F3864", GREY = "595959", RULE = "BFBFBF", HEAD_FILL = "1F3864", ALT_FILL = "F2F5FA";

// **bold** and *italic* inline markup → TextRuns
function runs(text, base = {}) {
  return text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/).filter(Boolean).map((part) => {
    if (part.startsWith("**")) return new TextRun({ ...base, text: part.slice(2, -2), bold: true });
    if (part.startsWith("*")) return new TextRun({ ...base, text: part.slice(1, -1), italics: true });
    return new TextRun({ ...base, text: part });
  });
}
const P = (text, opts = {}) => new Paragraph({ children: runs(text), spacing: { after: 140 }, ...opts });
const H1 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(text)] });
const H2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(text)] });
const H3 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(text)] });
const bullet = (text) => new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: runs(text), spacing: { after: 80 } });
const rq = (text) => new Paragraph({ numbering: { reference: "rqs", level: 0 }, children: runs(text), spacing: { after: 100 } });
const pageBreak = () => new Paragraph({ children: [new PageBreak()] });

let figNo = 0, tabNo = 0;
function figure(name, caption) {
  const f = F[name];
  figNo += 1;
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 }, keepNext: true,
      children: [new ImageRun({
        type: "png", data: fs.readFileSync(f.path),
        transformation: { width: IMG_W, height: Math.round(IMG_W * f.height / f.width) },
        altText: { title: `Figure ${figNo}`, description: caption, name: name },
      })],
    }),
    new Paragraph({ style: "Caption", children: runs(`**Figure ${figNo}.** ${caption}`) }),
  ];
}

const border = { style: BorderStyle.SINGLE, size: 4, color: RULE };
function table(headers, rows, widths, caption) {
  tabNo += 1;
  const total = widths.reduce((a, b) => a + b, 0);
  const scaled = widths.map((w) => Math.round(w * CONTENT_W / total));
  scaled[scaled.length - 1] += CONTENT_W - scaled.reduce((a, b) => a + b, 0);
  const cell = (text, i, header, shade) => new TableCell({
    width: { size: scaled[i], type: WidthType.DXA },
    shading: header ? { fill: HEAD_FILL, type: ShadingType.CLEAR, color: "auto" }
      : shade ? { fill: ALT_FILL, type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: [new Paragraph({
      alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.CENTER,
      children: runs(String(text), header ? { bold: true, color: "FFFFFF", size: 19 } : { size: 19 }),
    })],
  });
  return [
    new Paragraph({ style: "Caption", keepNext: true, spacing: { before: 160, after: 80 },
      children: runs(`**Table ${tabNo}.** ${caption}`) }),
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: scaled,
      borders: { top: border, bottom: border, left: border, right: border, insideHorizontal: border, insideVertical: border },
      rows: [
        new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, i, true)) }),
        ...rows.map((r, ri) => new TableRow({ children: r.map((v, i) => cell(v, i, false, ri % 2 === 1)) })),
      ],
    }),
    new Paragraph({ spacing: { after: 120 }, children: [] }),
  ];
}

// ── content ──────────────────────────────────────────────────────────────────
const title = "Communication Structure and Rhythm in a Research Institution";
const subtitle = "A Social Network Analysis of Intra-Department Email";

const titlePage = [
  new Paragraph({ spacing: { before: 2200 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "23CSE2356 · SOCIAL NETWORK ANALYSIS", size: 22, color: GREY, bold: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 600 },
    children: [new TextRun({ text: "Case Study Report", size: 24, color: GREY })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 },
    children: [new TextRun({ text: title, size: 48, bold: true, color: NAVY })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 1400 },
    children: [new TextRun({ text: subtitle, size: 30, color: NAVY })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
    children: [new TextRun({ text: "Submitted by", size: 22, color: GREY })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
    children: [new TextRun({ text: "[Team member names and roll numbers]", size: 24, bold: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 800 },
    children: [new TextRun({ text: "Dataset: SNAP email-Eu-core-temporal (four department subsets)", size: 20, color: GREY })] }),
  new Paragraph({ alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Code: github.com/Ashwin-deals/employee-collab-network", size: 20, color: GREY })] }),
  pageBreak(),
];

const abstract = [
  H1("Abstract"),
  P(`Email records show how work is actually coordinated inside an organisation, which often differs from its formal structure. This study applies social network analysis to ${int(data.totals.emails)} internal emails exchanged by ${data.totals.nodes} employees in four departments of a European research institution (SNAP email-Eu-core-temporal). Each department is modelled as a weighted directed network and compared on cohesion, fragmentation, reciprocity, clustering, community structure and centrality, and its communication is followed over ${days} days.`),
  P(`The departments follow two distinct organisational patterns. ${list(CONN)} forms a single connected network held together by a few brokers, with sub-teams that stay in contact. ${list(FRAG)} each consist of ${range("wcc", 0, FRAG)} close-knit teams, with clustering ${range("clustering_ratio", 1, FRAG)}× a random baseline, that never email each other within the department; their high modularity reflects this separation rather than well-formed sub-groups. Communication is reciprocal everywhere (${range("reciprocity")} of ties answered). Over time, all four departments share the same high and low months, far more overlap than chance (p = ${n(T.sync_p, 4)}), and the largest swings are week-long breaks and a single surge week. The findings point to bridging isolated teams and reducing reliance on single hub individuals.`),
  P("**Keywords:** social network analysis; organisational networks; email; community detection; centrality; temporal networks"),
  pageBreak(),
  new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Contents")], pageBreakBefore: false }),
  new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }),
  P("*If the contents list is empty, right-click it in Word and choose Update Field.*", { spacing: { before: 120 } }),
  pageBreak(),
];

// 1. Introduction
const intro = [
  H1("1. Introduction"),
  H2("1.1 Background and motivation"),
  P("Organisations run on informal communication networks that formal organisation charts do not show: who actually asks whom for help, which teams talk to each other, and who holds groups together (Cross & Parker, 2004). Email logs offer a large-scale, objective record of these networks, capturing who communicates with whom and when without relying on surveys or self-reports (Kossinets & Watts, 2006)."),
  P("Social network analysis (SNA) provides the tools to read such records. It can measure how cohesive a group is, detect sub-groups, identify central individuals such as hubs and brokers who connect otherwise separate parts of a network (Burt, 2004), and follow how communication changes over time. These are exactly the properties that determine how well information flows in an organisation and how exposed it is to losing key people."),
  H2("1.2 Problem statement"),
  P("Departments of the same institution, under the same policies and calendar, can organise their communication very differently: some as one connected group, others as separate teams that rarely interact. These differences matter for knowledge sharing, coordination and resilience, yet they are invisible without network analysis. Standard summary measures can also mislead: modularity, for example, is inflated in networks that are already split into disconnected parts. This study compares four departments of a European research institution to characterise these differences and interpret them carefully."),
  H2("1.3 Research questions"),
  rq("**Structure.** How do the four departments differ in communication structure: cohesion, fragmentation, reciprocity and team (community) structure?"),
  rq("**Key people.** Who occupies structurally important positions (hubs and brokers), and how concentrated is influence in each department?"),
  rq("**Time.** How does communication volume change over time, and are the temporal patterns shared across departments?"),
  H2("1.4 Contributions"),
  bullet("A structural comparison of four departmental email networks, with clustering and reciprocity tested against random baselines."),
  bullet("Identification of hubs and brokers in each department and of how concentrated influence is."),
  bullet("A temporal analysis at monthly and daily resolution, with a permutation test showing that the departments' shared rhythm is not due to chance."),
  bullet("Methodological care on three common pitfalls: modularity in fragmented networks, partial time periods, and misaligned timestamps."),
  bullet("A fully reproducible analysis pipeline, plus Gephi files for interactive and timeline visualisation."),
  P("Section 2 describes the data, Section 3 the methods, Section 4 the results, Section 5 discusses implications and limitations, and Section 6 concludes."),
];

// 2. Data
const dataSec = [
  H1("2. Data"),
  H2("2.1 Source and collection"),
  P("The data is the **email-Eu-core-temporal** dataset from the Stanford Network Analysis Project (SNAP), published by Paranjape, Benson and Leskovec (2017) and derived from the email-Eu-core network of Leskovec, Kleinberg and Faloutsos (2007). It was collected from the email system of a large European research institution and records emails exchanged between members of the institution. Identities are anonymised, and message content is not included."),
  P("SNAP provides four department subsets (Dept1–Dept4), each containing only emails sent between members of the same department. Every record is one email: an anonymised sender ID, a recipient ID, and a timestamp in seconds. This study analyses the four department subsets; the full dataset is used only to check time alignment and the weekly cycle, and for the Gephi exports."),
  H2("2.2 Why this dataset"),
  bullet("**Real organisational behaviour at scale:** tens of thousands of emails per department, recorded by the email system rather than reported by participants."),
  bullet("**A natural comparison:** four departments of one institution share the same policies and calendar, so differences between them reflect how each organises its communication."),
  bullet("**Timestamps** allow temporal analysis of how communication varies over time."),
  bullet("**Public, anonymised and widely used** in network research, which makes the analysis ethical and reproducible."),
  ...table(
    ["Department", "Employees", "Directed ties", "Emails", "Emails per tie", "Emails per person"],
    DEPTS.map((k) => [k, D[k].nodes, int(D[k].edges), int(D[k].emails), n(D[k].per_channel, 1), int(D[k].per_person)]),
    [1.4, 1.1, 1.2, 1.1, 1.2, 1.3],
    `Dataset summary. In total ${data.totals.nodes} employees and ${int(data.totals.emails)} emails.`),
  H2("2.3 Data preparation"),
  P("The raw files were not modified. All processing happens in the analysis code:"),
  bullet("**Aggregation:** repeated emails from the same sender to the same recipient are combined into one directed tie whose weight is the number of emails."),
  bullet("**Independent departments:** node IDs are local to each file (ID 5 in Dept1 and ID 5 in Dept2 are different people), so the four networks are never merged."),
  bullet(`**Time alignment:** each department file starts its clock at its own first email. Cross-correlating each department's hourly email counts with the full dataset shows the four clocks agree to within ${T.clock_spread_h} hours, which is negligible at the day and month scales used here.`),
  bullet(`**Coverage:** the data is continuous from day 0 to day ${T.main_end}, has no email until day ${T.resume_day}, and then records only 7 more days. Temporal analysis therefore uses the ${T.last_month} complete 30-day months (M01–M${String(T.last_month).padStart(2, "0")}); the partial month the data stops in and the final 7-day fragment are excluded, since their low counts reflect missing days rather than quiet periods.`),
];

// 3. Methodology
const methods = [
  H1("3. Methodology"),
  H2("3.1 Network model"),
  P("Each department is modelled as a weighted directed graph G = (V, E, w): nodes V are employees, a directed edge (u, v) ∈ E means u emailed v at least once, and the weight w(u, v) is the number of such emails. Direction is kept because sending and receiving are different roles; weight is kept because repeated contact signals a stronger working tie. Measures that are defined for undirected graphs (clustering and modularity) use the undirected projection, in which weights in both directions are summed."),
  H2("3.2 Measures and why they were chosen"),
  ...table(
    ["Measure", "What it shows", "Why it is used here"],
    [
      ["Density", "Share of possible ties that exist", "Overall cohesion of a department"],
      ["Distinct contacts", "Average number of different colleagues per person", "Breadth of each person's communication"],
      ["Weak / strong components", "Groups connected ignoring / following direction", "Fragmentation and whether information can circulate"],
      ["Reciprocity", "Share of ties u→v answered by v→u", "Whether communication is two-way; component size cannot show this"],
      ["Clustering coefficient", "Whether a person's contacts also email each other", "Distinguishes closed teams from broad hub-based networks (Watts & Strogatz, 1998)"],
      ["Degree centrality", "Number of distinct ties", "Most active communicators"],
      ["Betweenness centrality", "Share of shortest paths through a person", "Brokers linking otherwise separate people (Freeman, 1977; Burt, 2004)"],
      ["PageRank (weighted)", "Influence through email flow", "People who receive much email from other influential people (Brin & Page, 1998)"],
      ["Louvain modularity", "Division into communities", "Detects sub-teams (Blondel et al., 2008; Newman & Girvan, 2004)"],
    ],
    [1.5, 2.2, 2.6],
    "Network measures, what they capture, and why each was chosen."),
  H2("3.3 Community detection"),
  P("Communities are found with the Louvain method (Blondel et al., 2008), which maximises modularity Q (Newman & Girvan, 2004). Values above about 0.3 are commonly taken to indicate meaningful community structure. Louvain is randomised, so it is run with a fixed seed for reproducibility and re-run with 20 different seeds to check stability. Two extra measures guard against misreading Q: the number of communities per connected component, and the share of people with ties to another community. In a network that is already split into disconnected parts, Louvain assigns each part to its own community at no cost, so Q is inflated."),
  H2("3.4 Centrality and concentration"),
  P("Degree, betweenness and PageRank are computed within each department. Betweenness is unweighted, because email counts measure closeness of a tie rather than distance. Since node IDs are local, individuals are never compared across departments; instead, concentration is compared through the share of betweenness and email volume held by each department's top five people, and through how far the top person leads the next."),
  H2("3.5 Statistical validation"),
  bullet("**Clustering** is compared with 10 degree-preserving random rewirings of each network (Maslov & Sneppen, 2002): everyone keeps the same number of contacts, but who they are is randomised. A ratio well above 1 indicates real team structure rather than a side effect of density."),
  bullet("**Reciprocity** is compared with the density, which is the share of ties that would be answered by chance in a random directed graph of the same density."),
  bullet(`**Temporal synchrony** is tested by circularly shifting each department's monthly series by an independent random offset (${int(T.sync_perms)} permutations). This keeps each department's own pattern but breaks the alignment between departments, giving the overlap expected by chance.`),
  H2("3.6 Temporal analysis"),
  P("Emails are grouped into 30-day slices. A month is flagged as high or low when its volume differs from a centred five-month rolling mean by more than one standard deviation (|Z| > 1), so that slow trends do not mask short swings. Because 30-day bins have an arbitrary start and can split or dilute short events, daily counts are also examined: the 7-day cycle (to identify weekends) and low weeks, defined as 7-day windows with less than half the median weekly volume."),
  H2("3.7 Tools and reproducibility"),
  P("The analysis is written in Python using NetworkX (Hagberg et al., 2008), pandas, NumPy and Matplotlib, as a pipeline of scripts that regenerates every table and figure from the raw data with one command (Appendix A). The networks are also exported for Gephi (Bastian et al., 2009), including timeline versions for animating communication over time (Appendix B)."),
];

// 4. Results
const d1 = D.Dept1, d2 = D.Dept2, d3 = D.Dept3, d4 = D.Dept4;
const results = [
  H1("4. Results"),
  H2("4.1 Size and communication intensity"),
  P(`${"Dept1"} is both the largest department (${d1.nodes} people) and the busiest (${int(d1.emails)} emails), so total volume broadly follows headcount (Table 1). Intensity differs much more: ${perChannelMax} averages ${n(D[perChannelMax].per_channel, 0)} emails per tie and ${int(D[perChannelMax].per_person)} per person, while ${perChannelMin} averages only ${n(D[perChannelMin].per_channel, 0)} per tie. ${perChannelMax} concentrates its communication in a few heavily used channels; ${perChannelMin} spreads lighter traffic across many contacts.`),

  H2("4.2 Cohesion and fragmentation (RQ1)"),
  ...table(
    ["Department", "Density", "Contacts per person", "Components", "Largest component", "Reciprocity", "Clustering (× random)"],
    DEPTS.map((k) => [k, n(D[k].density, 3), n(D[k].contacts, 1), D[k].wcc, pct(D[k].largest_wcc_pct),
      n(D[k].reciprocity, 2), `${n(D[k].clustering, 2)} (${n(D[k].clustering_ratio, 1)}×)`]),
    [1.2, 0.9, 1.1, 1.1, 1.1, 1.0, 1.4],
    "Structural measures per department. Components are weakly connected components."),
  P(`The departments split into two groups (Table 3, Figures 1 and 2). ${list(CONN)} is the only department in which everyone is connected to everyone else, directly or indirectly. It has by far the highest density (${n(d3.density, 2)}, about one in ${n(1 / d3.density, 0)} possible ties in use) and the most contacts per person (${n(d3.contacts, 0)}, against roughly ${n((d1.contacts + d2.contacts + d4.contacts) / 3, 0)} elsewhere).`),
  P(`${list(FRAG)} each split into ${range("wcc", 0, FRAG)} separate groups that never email each other within the department; the largest group covers only ${range("largest_wcc_pct", 0, FRAG, "%")} of people. Part of the density gap is a size effect, since possible ties grow with the square of department size. The fragmentation is not: groups of colleagues with no email at all between them, inside the same department, are a structural feature rather than a consequence of headcount.`),
  ...figure("fig_networks_2x2", "Within-department networks. Node colour shows the Louvain community (colours are not comparable across panels); node size shows email volume. Dept3 is one connected network, while the other departments are sets of separate groups."),
  ...figure("fig_bar_comparison", "Cross-department comparison of six structural measures. Hatched modularity bars are inflated by disconnected components (Section 4.3)."),

  H3("Reciprocity: communication is two-way everywhere"),
  P(`Reciprocity is high in every department (${range("reciprocity")}): most ties are answered. In a random network of the same density only ${range("reciprocity_random")} of ties would be, so reciprocity is ${n(Math.min(...recipRatio), 0)}–${n(Math.max(...recipRatio), 0)}× what chance gives. This corrects a tempting misreading of the strong components. Dept1 has ${d1.scc} strongly connected components and its largest covers only ${pct(d1.largest_scc_pct)} of people, which might suggest one-way, hierarchical email. In fact ${d1.single_scc} of those components are single people, and ${d1.receive_only} people receive email from colleagues but never send any within the department, consistent with distribution lists or with people whose work lies mainly outside it. Dept1's many components come from fragmentation and peripheral members, not from one-way communication.`),
  H3("Clustering: closed teams versus a broad network"),
  P(`Clustering separates the two groups clearly. In ${list(FRAG)} it is ${range("clustering_ratio", 1, FRAG)}× the value in randomly rewired networks with the same contact counts: their groups are genuinely close-knit teams in which nearly everyone emails everyone. In Dept3, clustering is only ${n(d3.clustering_ratio, 2)}× random, almost entirely explained by its high density. Dept3's members have broad contact lists that span the department, so many of a person's contacts do not email each other.`),

  H2("4.3 Community structure (RQ1)"),
  ...table(
    ["Department", "Communities", "Modularity Q", "Q over 20 seeds", "Communities per component", "People tied to another community"],
    DEPTS.map((k) => [k, D[k].communities, n(D[k].q, 2), `${n(D[k].q_min, 3)}–${n(D[k].q_max, 3)}`, n(D[k].comms_per_wcc, 2), pct(D[k].cross_comm_pct)]),
    [1.2, 1.1, 1.0, 1.3, 1.4, 1.5],
    "Louvain community detection. The seed range shows results are stable."),
  P(`Modularity looks highest in ${list(FRAG)} (Q = ${range("q", 2, FRAG)}), which taken at face value would suggest the clearest sub-group structure. Table 4 shows why that reading is wrong. Their communities per component are ${range("comms_per_wcc", 2, FRAG)}: almost every community is simply one of the disconnected groups, which Louvain separates at no cost. In Dept4 the match is exact, and ${pct(d4.cross_comm_pct)} of people have a tie to another community.`),
  P(`Dept3 is the meaningful case. Within one connected network, Louvain still finds ${d3.communities} communities with Q = ${n(d3.q, 2)}, above the 0.3 rule of thumb, and ${pct(d3.cross_comm_pct)} of its people have ties into another community. These are distinct sub-teams that stay in contact with each other. The results are stable: across 20 seeds Q varies by at most ${n(Math.max(...DEPTS.map((k) => D[k].q_max - D[k].q_min)), 3)} and the number of communities by at most ${Math.max(...DEPTS.map((k) => D[k].comms_max - D[k].comms_min))}.`),

  H2("4.4 Key people and concentration of influence (RQ2)"),
  ...table(
    ["Department", "Top PageRank", "Leads next by", "Top betweenness", "Top-5 share of betweenness", "Never on a shortest path"],
    DEPTS.map((k) => [k, `node ${D[k].top_pr_node}`, `${n(D[k].pr_lead, 2)}×`, `node ${D[k].top_btw_node} (${n(D[k].top_btw, 3)})`, pct(100 * D[k].top5_btw_share), pct(D[k].zero_btw_pct)]),
    [1.1, 1.1, 1.0, 1.5, 1.3, 1.3],
    "Centrality summary. Node IDs are local to each department."),
  P("Each department concentrates influence differently (Table 5, Figure 3):"),
  bullet(`**Dept1 depends on one hub.** Node ${d1.top_pr_node} ranks first on degree, betweenness and PageRank, with a PageRank ${n(d1.pr_lead, 1)}× the next person's.${d1.brokers_in_largest_comm ? ` All five top brokers sit inside the department's largest community (${d1.largest_comm_size} people), so brokerage happens within that group rather than between groups.` : ""} This is a single point of failure.`),
  bullet(`**Dept2 is led by a small core.** Nodes ${list(d2.in_all_three.map(String))} rank in the top five on all three measures, and node ${d2.top_pr_node} handles ${int(d2.top_pr_node_emails)} emails sent and received, the most in the department.`),
  bullet(`**Dept3 has real brokers.** Its top betweenness (${n(d3.top_btw, 3)}) is ${n(d3.top_btw / btwMaxOthers, 0)}× the highest in any other department, and nodes ${list(d3.in_all_three.map(String))} rank top five on all measures: these people connect its sub-teams. Only ${pct(d3.zero_btw_pct)} of Dept3 is never on a shortest path, against ${range("zero_btw_pct", 0, FRAG, "%")} elsewhere, so passing on information is widely shared.`),
  bullet(`**Dept4 has no single leader.** Its top five PageRank scores are nearly equal (the first is only ${n(d4.pr_lead5, 1)}× the fifth), matching a set of self-contained teams of similar weight.`),
  P(`*Caveat:* betweenness is normalised over all pairs of people, and no shortest paths cross between disconnected groups, so ${list(FRAG)} score lower partly by construction. The patterns and shares are more reliable than the raw values.`),
  ...figure("fig_centrality_top", "Top five people per department by PageRank (top) and betweenness (bottom), on shared axes. Dept3's brokers stand out; Dept1 has one dominant hub."),

  H2("4.5 Communication over time (RQ3)"),
  ...table(
    ["Department", "High months", "Low months", "Monthly mean", "M14 volume"],
    DEPTS.map((k) => [k, T.high[k].join(", "), T.low[k].join(", "), int(T.monthly_mean[k]), `${int(T.m14[k])} (${pct(100 * T.m14[k] / T.monthly_mean[k])})`]),
    [1.1, 1.2, 1.5, 1.1, 1.3],
    `High and low months (|Z| > 1 against a centred 5-month rolling mean), complete months M01–M${String(T.last_month).padStart(2, "0")}.`),
  P(`All four departments rise and fall together (Table 6, Figure 4). ${list(sharedHigh)} is a high month in every department, and ${list(sharedLow)} are low months in every department. ${highIn3.length ? `M13 is high in three departments and just misses the cut-off in Dept3 (Z = ${n(T.dept3_m13_z, 3)}). ` : ""}In M14 every department falls sharply, Dept4 to ${pct(100 * T.m14.Dept4 / T.monthly_mean.Dept4)} and Dept3 to ${pct(100 * T.m14.Dept3 / T.monthly_mean.Dept3)} of their monthly averages.`),
  P(`**This synchrony is statistically significant.** A |Z| > 1 cut-off flags ${pct(100 * T.flagged_share)} of department-months, so any single department's flags could be chance. But ${T.sync_observed} months are flagged the same way in all four departments, against ${n(T.sync_expected, 2)} expected when each department's series is shifted at random (p = ${n(T.sync_p, 4)}, ${int(T.sync_perms)} permutations). Since the departments are separate networks with aligned clocks, this points to institution-wide drivers such as calendars, deadlines and holidays.`),
  ...figure("fig_temporal_heatmap", "Monthly email volume by department. Triangles mark high (▲) and low (▼) months; the same months stand out in every department."),
  P(`The daily view (Figure 5) shows that the real swings are week-long, which monthly bins blur:`),
  bullet(`Weekend days carry only ${pct(T.weekend_pct)} of a weekday's email, confirming that this is work communication.`),
  bullet(`The ${T.peak_month} peak is a single intense week: the 7 days around day ${T.peak_day} carry ${n(T.peak_ratio, 1)}× a median week's email.`),
  bullet(`There are ${T.low_weeks.length} breaks of ${Math.min(...lowLens)}–${Math.max(...lowLens)} days in which email falls to ${n(Math.min(...T.low_weeks.map((w) => w.pct)), 0)}–${n(Math.max(...T.low_weeks.map((w) => w.pct)), 0)}% of normal. The longest (${Math.max(...lowLens)} days) straddles ${list(longestLow.months)}, so the monthly bins split it${missedLow.length ? `, and the breaks in ${list(missedLow)} do not appear in the monthly analysis at all` : ""}.`),
  ...(T.annual_pairs.length ? [bullet(`Breaks starting on days ${T.annual_pairs[0][0]} and ${T.annual_pairs[0][1]} are ${T.annual_pairs[0][1] - T.annual_pairs[0][0]} days apart, suggesting a holiday that recurs each year. The calendar dates cannot be recovered, because the timestamps are relative.`)] : []),
  ...figure("fig_daily_rhythm", "Weekly email volume (7-day rolling total) with low weeks shaded, and average emails per day of the 7-day cycle."),
];

// 5. Discussion
const discussion = [
  H1("5. Discussion and Implications"),
  H2("5.1 Two organisational models"),
  P(`The results describe two distinct ways a department can organise its communication. Dept3 is an **integrated network**: one connected group with broad contact lists, modest clustering, and a few brokers who link its sub-teams. Dept1, Dept2 and Dept4 are **federations of closed teams**: tight groups in which almost everyone emails everyone (clustering ${range("clustering_ratio", 1, FRAG)}× random) but which never email each other within the department.`),
  P("Network theory suggests each model has strengths and risks. Closed teams support trust, fast coordination and shared norms, but they tend to circulate the same information internally. Brokers who span the gaps between groups give access to more diverse information and ideas (Burt, 2004), and weak ties between groups are what carry new information across an organisation (Granovetter, 1973). The federated departments therefore risk duplicated effort and slow diffusion of ideas between teams, while Dept3's integration depends on a small number of brokers."),
  P("Reciprocity is high in all four departments, so the difference between the models lies in how teams connect, not in whether people reply. The heavy use of a few channels in Dept4 suggests concentrated, intense working relationships, while Dept3 sustains many lighter ones."),
  H2("5.2 Real-world implications"),
  bullet("**Bridge isolated teams.** Dept1's teams are the clearest candidates for deliberate bridging through joint meetings, shared projects or liaison roles. Because only internal email is observed, the first step is to check whether these teams already connect through other departments."),
  bullet(`**Manage key-person risk.** Dept1's reliance on node ${d1.top_pr_node}, and Dept3's on a handful of brokers, are continuity risks: if these people leave or are overloaded, parts of the network lose their main connection. Spreading coordination roles and documenting their knowledge reduces this exposure.`),
  bullet("**Use the shared calendar.** Every department follows the same rhythm, so institution-wide breaks are natural windows for planned changes and maintenance, and the surge week marks when the institution is under the most communication load."),
  bullet("**Read network metrics carefully.** High modularity can mean disconnection rather than healthy sub-teams, and partial time periods can masquerade as quiet ones. Analysts using SNA for organisational decisions should check such measures against connectivity, random baselines and data coverage, as done here."),
  H2("5.3 Limitations"),
  bullet("Only email within each department is included, so links between departments are invisible. Groups that look isolated may be connected through other departments."),
  bullet("Email is a proxy for collaboration. Volume may include distribution-list or automated messages, which cannot be separated out without message content."),
  bullet("The data is anonymised, with no roles or organisation chart, so communities and hubs cannot be checked against real teams or positions."),
  bullet(`Timestamps are relative, so calendar dates, and therefore the causes of peaks and breaks, are unknown. The 30-day bins are arbitrary, and there is a long gap in the data after day ${T.main_end}.`),
  bullet("Betweenness is not directly comparable between connected and fragmented networks; the analysis therefore compares patterns and shares rather than raw values."),
  H2("5.4 Future research directions"),
  bullet("Analyse the full dataset to map how departments connect to each other and whether the isolated teams found here are bridged elsewhere."),
  bullet("Study temporal motifs, the recurring sequences of who emails whom, which the dataset was originally published to support (Paranjape et al., 2017)."),
  bullet("Track communities month by month to see whether teams merge, split or persist, and test how well past communication predicts future ties (link prediction)."),
  bullet("Combine network data with role or survey information to validate hubs and communities against real organisational positions."),
];

// 6. Conclusion
const conclusion = [
  H1("6. Conclusion"),
  P(`This study applied social network analysis to ${int(data.totals.emails)} emails in four departments of a European research institution, combining structural measures, community detection, centrality and temporal analysis, with results tested against random baselines.`),
  P(`**RQ1 (structure).** The departments follow two models. Dept3 is a single, integrated network with genuine sub-teams that stay in contact (Q = ${n(d3.q, 2)} within one component). ${list(FRAG)} are federations of close-knit teams that never email each other internally; their high modularity reflects this separation, not well-formed sub-groups. Communication is reciprocal in all four (${range("reciprocity")}).`),
  P(`**RQ2 (key people).** Influence is concentrated differently: Dept1 depends on one hub, Dept2 on a core of ${d2.in_all_three.length} people, Dept3 on a few brokers between sub-teams, while Dept4 has no single leader.`),
  P(`**RQ3 (time).** All departments share one institutional rhythm, with the same high and low months, far more overlap than chance (p = ${n(T.sync_p, 4)}). The largest swings are week-scale: one surge week at ${n(T.peak_ratio, 1)}× normal and breaks of up to ${Math.max(...lowLens)} days, one recurring about a year later.`),
  P("Beyond these findings, the study shows that common SNA summaries can mislead without careful checks: modularity in fragmented networks, partial periods in temporal data, and misaligned clocks across sources. For the institution, the results identify where bridging between teams would help most and where reliance on a few individuals creates risk."),
];

// References
const refs = [
  "Bastian, M., Heymann, S., & Jacomy, M. (2009). Gephi: An open source software for exploring and manipulating networks. *Proceedings of the International AAAI Conference on Weblogs and Social Media (ICWSM)*.",
  "Blondel, V. D., Guillaume, J.-L., Lambiotte, R., & Lefebvre, E. (2008). Fast unfolding of communities in large networks. *Journal of Statistical Mechanics: Theory and Experiment*, 2008(10), P10008.",
  "Brin, S., & Page, L. (1998). The anatomy of a large-scale hypertextual Web search engine. *Computer Networks and ISDN Systems*, 30(1–7), 107–117.",
  "Burt, R. S. (2004). Structural holes and good ideas. *American Journal of Sociology*, 110(2), 349–399.",
  "Cross, R., & Parker, A. (2004). *The Hidden Power of Social Networks: Understanding How Work Really Gets Done in Organizations*. Harvard Business School Press.",
  "Freeman, L. C. (1977). A set of measures of centrality based on betweenness. *Sociometry*, 40(1), 35–41.",
  "Granovetter, M. S. (1973). The strength of weak ties. *American Journal of Sociology*, 78(6), 1360–1380.",
  "Hagberg, A. A., Schult, D. A., & Swart, P. J. (2008). Exploring network structure, dynamics, and function using NetworkX. *Proceedings of the 7th Python in Science Conference (SciPy 2008)*, 11–15.",
  "Kossinets, G., & Watts, D. J. (2006). Empirical analysis of an evolving social network. *Science*, 311(5757), 88–90.",
  "Leskovec, J., Kleinberg, J., & Faloutsos, C. (2007). Graph evolution: Densification and shrinking diameters. *ACM Transactions on Knowledge Discovery from Data*, 1(1), Article 2.",
  "Maslov, S., & Sneppen, K. (2002). Specificity and stability in topology of protein networks. *Science*, 296(5569), 910–913.",
  "Newman, M. E. J., & Girvan, M. (2004). Finding and evaluating community structure in networks. *Physical Review E*, 69(2), 026113.",
  "Paranjape, A., Benson, A. R., & Leskovec, J. (2017). Motifs in temporal networks. *Proceedings of the Tenth ACM International Conference on Web Search and Data Mining (WSDM)*, 601–610.",
  "Watts, D. J., & Strogatz, S. H. (1998). Collective dynamics of 'small-world' networks. *Nature*, 393(6684), 440–442.",
];
const references = [
  H1("References"),
  ...refs.map((r) => new Paragraph({ children: runs(r), spacing: { after: 100 }, indent: { left: 540, hanging: 540 } })),
  P("Dataset: SNAP, email-Eu-core-temporal. https://snap.stanford.edu/data/email-Eu-core-temporal.html", { spacing: { before: 120 } }),
];

// Appendices
const appendix = [
  pageBreak(),
  H1("Appendix A. Reproducing the analysis"),
  P("All tables, figures and numbers in this report are generated from the raw data by the project code (github.com/Ashwin-deals/employee-collab-network). With Python 3 and the packages in requirements.txt installed, run from the repository root:"),
  new Paragraph({ children: [new TextRun({ text: "pip install -r requirements.txt", font: "Consolas", size: 19 })], indent: { left: 360 } }),
  new Paragraph({ children: [new TextRun({ text: "python3 run_pipeline.py", font: "Consolas", size: 19 })], indent: { left: 360 }, spacing: { after: 160 } }),
  ...table(
    ["Stage", "Purpose"],
    [
      ["1 build_graphs", "Weighted directed graph per department"],
      ["2 structural", "Density, components, reciprocity, clustering and random baselines"],
      ["3 centrality", "Degree, betweenness, PageRank and concentration"],
      ["4 community", "Louvain communities, modularity, seed stability"],
      ["5 cross_dept", "Combined comparison table"],
      ["6 visualization", "Network, comparison and centrality figures"],
      ["8–11 temporal", "Monthly slices, metrics, high/low months, synchrony test, figures"],
      ["14 daily_rhythm", "Clock alignment, weekday cycle, low weeks"],
      ["7 conclusion", "Text summary of all results (conclusion.txt)"],
      ["12–13 export_gephi", "Static and timeline Gephi files"],
    ],
    [1.4, 4.0],
    "Pipeline stages, in run order."),
  H1("Appendix B. Gephi files"),
  P("The folder analysis/gephi contains files for interactive exploration in Gephi:"),
  bullet("**Dept1–4.gexf** (File → Open): weighted networks with community, centrality, a precomputed layout, community colours and PageRank-based node sizes."),
  bullet("**Dept1–4_dynamic.gexf and Full_dynamic.gexf** (File → Open, then enable the Timeline): the same networks with each person and tie active only on days they emailed, for animating communication over time."),
  bullet("**Edge-list CSV files**, Dept1–4_edges.csv and Full_edges.csv (File → Import Spreadsheet, comma-separated, Edges table): Source, Target and Weight columns for all five datasets."),
];

// ── document ─────────────────────────────────────────────────────────────────
const doc = new Document({
  creator: "SNA case study",
  title: `${title}: ${subtitle}`,
  description: "Social network analysis case study of intra-department email (SNAP email-Eu-core-temporal)",
  features: { updateFields: true },
  styles: {
    default: { document: { run: { font: "Calibri", size: 22 }, paragraph: { spacing: { line: 276 } } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, color: NAVY }, paragraph: { spacing: { before: 360, after: 160 }, outlineLevel: 0, keepNext: true } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, color: NAVY }, paragraph: { spacing: { before: 260, after: 120 }, outlineLevel: 1, keepNext: true } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, italics: true, color: "2E5496" }, paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 2, keepNext: true } },
      { id: "Caption", name: "Caption", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 19, color: GREY }, paragraph: { alignment: AlignmentType.CENTER, spacing: { after: 200 } } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] },
      { reference: "rqs", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "RQ%1.", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 720 } } } }] },
    ],
  },
  sections: [{
    properties: {
      titlePage: true,
      page: { size: { width: PAGE_W, height: PAGE_H }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } },
    },
    headers: {
      first: new Header({ children: [new Paragraph({ children: [] })] }),
      default: new Header({ children: [new Paragraph({
        alignment: AlignmentType.RIGHT,
        border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: RULE, space: 4 } },
        children: [new TextRun({ text: "SNA Case Study · Intra-Department Email Networks", size: 17, color: GREY })],
      })] }),
    },
    footers: {
      first: new Footer({ children: [new Paragraph({ children: [] })] }),
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ children: ["Page ", PageNumber.CURRENT, " of ", PageNumber.TOTAL_PAGES], size: 17, color: GREY })],
      })] }),
    },
    children: [...titlePage, ...abstract, ...intro, ...dataSec, ...methods, ...results, ...discussion, ...conclusion, ...references, ...appendix],
  }],
});

const out = path.join(__dirname, "SNA_Case_Study_Report.docx");
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(out, buf);
  console.log(`Saved ${path.relative(path.join(__dirname, ".."), out)} (${figNo} figures, ${tabNo} tables)`);
});
