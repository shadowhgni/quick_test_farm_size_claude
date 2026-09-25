// Builds Methods_Results.docx and Supplementary_Material.docx
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, ImageRun, LevelFormat, PageBreak, Footer, PageNumber,
} = require("docx");

const FIG = __dirname + "/figs/";
const SIZES = JSON.parse(fs.readFileSync(__dirname + "/sizes.json"));
SIZES["fig3_nelson_difference.png"] = [2538, 1703];
const FONT = "Calibri";
const TEXT_W = 9026; // A4 with 2.54 cm margins, DXA

// --- inline markup: **bold**, *italic*, ^sup^, ~sub~
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|\^[^^]+\^|~[^~]+~)/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else if (t.startsWith("*")) out.push(new TextRun({ text: t.slice(1, -1), italics: true, ...base }));
    else if (t.startsWith("^")) out.push(new TextRun({ text: t.slice(1, -1), superScript: true, ...base }));
    else out.push(new TextRun({ text: t.slice(1, -1), subScript: true, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}
const P = (t, o = {}) => new Paragraph({ children: runs(t), spacing: { after: 120, line: 300 }, alignment: AlignmentType.JUSTIFIED, ...o });
const H1 = (t) => new Paragraph({ text: t, heading: HeadingLevel.HEADING_1, spacing: { before: 240, after: 120 } });
const H2 = (t) => new Paragraph({ text: t, heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 100 } });
const H3 = (t) => new Paragraph({ text: t, heading: HeadingLevel.HEADING_3, spacing: { before: 160, after: 80 } });
const EQ = (t, n) => new Paragraph({
  children: [...runs(t, { italics: false }), new TextRun({ text: n ? `\t(${n})` : "" })],
  alignment: AlignmentType.CENTER, spacing: { before: 60, after: 120 },
});
const BUL = (t) => new Paragraph({ children: runs(t), numbering: { reference: "bullets", level: 0 }, spacing: { after: 60, line: 290 } });
const NOTE = (t) => new Paragraph({
  children: runs(t, { color: "7A4F00" }), shading: { type: ShadingType.CLEAR, fill: "FFF4D6" },
  spacing: { before: 80, after: 160 }, border: { left: { style: BorderStyle.SINGLE, size: 12, color: "E0A800", space: 6 } },
});
const CAP = (t) => new Paragraph({ children: runs(t, { size: 19 }), spacing: { before: 60, after: 200, line: 270 }, alignment: AlignmentType.JUSTIFIED });

function FIGURE(file, widthIn, caption) {
  const [w, h] = SIZES[file];
  const W = Math.round(widthIn * 96), Hh = Math.round(W * h / w);
  return [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 40 },
    children: [new ImageRun({ type: "png", data: fs.readFileSync(FIG + file), transformation: { width: W, height: Hh } })] }),
    CAP(caption)];
}

const border = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
function TABLE(headers, rows, widths, caption, note) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (t, i, head) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA },
    shading: head ? { type: ShadingType.CLEAR, fill: "E8EEF7" } : undefined,
    margins: { top: 40, bottom: 40, left: 80, right: 80 },
    borders: { top: border, bottom: border, left: border, right: border },
    children: [new Paragraph({ children: runs(String(t), { size: 17, bold: head }),
      alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.RIGHT })],
  });
  const out = [CAP(caption), new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, i, true)) }),
      ...rows.map((r) => new TableRow({ children: r.map((c, i) => cell(c, i, false)) }))],
  })];
  if (note) out.push(new Paragraph({ children: runs(note, { size: 16, color: "52514E" }), spacing: { before: 60, after: 200 } }));
  else out.push(new Paragraph({ text: "", spacing: { after: 120 } }));
  return out;
}
const TEXTTABLE = (headers, rows, widths, caption, note) => {
  // left-aligned all columns (for descriptive tables)
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (t, i, head) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA },
    shading: head ? { type: ShadingType.CLEAR, fill: "E8EEF7" } : undefined,
    margins: { top: 40, bottom: 40, left: 80, right: 80 },
    borders: { top: border, bottom: border, left: border, right: border },
    children: [new Paragraph({ children: runs(String(t), { size: 17, bold: head }) })],
  });
  const out = [CAP(caption), new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, i, true)) }),
      ...rows.map((r) => new TableRow({ children: r.map((c, i) => cell(c, i, false)) }))],
  })];
  out.push(note ? new Paragraph({ children: runs(note, { size: 16, color: "52514E" }), spacing: { before: 60, after: 200 } })
                : new Paragraph({ text: "", spacing: { after: 120 } }));
  return out;
};

const styles = {
  default: { document: { run: { font: FONT, size: 22 } } },
  paragraphStyles: [
    { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: 30, bold: true, color: "1F3864", font: FONT }, paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 0 } },
    { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: 25, bold: true, color: "1F3864", font: FONT }, paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 } },
    { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: 22, bold: true, italics: true, color: "1F3864", font: FONT }, paragraph: { spacing: { before: 160, after: 80 }, outlineLevel: 2 } },
  ],
};
const numbering = { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
  alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] };
const page = { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } };
const footer = { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
  children: [new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "52514E" })] })] }) };

// =====================================================================================
// MAIN DOCUMENT
// =====================================================================================
const REF_HEADING = H1("References (main text and Supplementary Material)");
const main = [
  new Paragraph({ children: [new TextRun({ text: "Updating global travel-time accessibility for new road developments: methods and results", bold: true, size: 34, color: "1F3864" })], spacing: { after: 120 } }),
  new Paragraph({ children: [new TextRun({ text: "Draft Methods, Results and Discussion, followed by the Supplementary Material", italics: true, size: 21, color: "52514E" })], spacing: { after: 200 } }),
  NOTE("**Status of the results.** The Methods describe the full global workflow (script *global_accessibility_v2.py*, version 2.0). The Results reported here come from the complete end-to-end application of that workflow to a regional test domain (1°W–4.5°E, 5.5–13.5°N: Benin, Togo and neighbouring parts of Ghana, Burkina Faso, Niger and Nigeria) for 2015 and 2026. All numbers in brackets marked [global] must be replaced after the global run on the 30″ Nelson et al. (2019) extent; the structure, tables and figures are generated by the same code."),

  H1("2. Methods"),
  H2("2.1 Study design"),
  P("We estimated travel time from every location to the nearest settlement and port of a range of sizes for two reference years, a start year *t*~0~ = 2015 and an end year *t*~1~ = 2026, and attributed the change between them to new or newly mapped roads. The start year matches the reference year of the global accessibility indicators of Nelson et al. (2019), which we used for comparison. Both years were modelled with the same method, grid, speed tables and land cover, so that differences between them arise from the transport network and, where stated, from settlement growth. The workflow (Figure 1) builds a friction surface for each year (minutes needed to cross one metre), computes least-cost travel time to 17 sets of destinations, and compares the results with Nelson et al. (2019) for 2015 and with an independent routing engine for 2026."),
  ...FIGURE("fig1_workflow.png", 6.3, "**Figure 1.** Workflow. Inputs (left) are combined into one friction surface per reference year, from which travel time to 12 settlement and 5 port layers is computed; outputs are compared with Nelson et al. (2019) and validated against OSRM. The 2015 completion step uses the Weiss et al. (2018) friction surface only for the start year."),

  H2("2.2 Computational grid"),
  P("All layers were computed on a regular geographic grid (WGS84) with a cell size of 30 arc-seconds (≈0.93 km at the equator), aligned with and covering the same extent as Nelson et al. (2019): 180°W–180°E and 60°S–85°N (43,200 × 17,400 cells). The grid wraps across the antimeridian. Cell areas and step lengths account for the convergence of meridians (Section 2.9). A light version at 300 arc-seconds (≈10 km) was derived by averaging valid 30″ cells in blocks of 10 × 10."),

  H2("2.3 Road network"),
  H3("OpenStreetMap snapshots"),
  P("Roads for each year were taken from OpenStreetMap (OSM) snapshots of 1 January of that year, distributed as regional extracts by Geofabrik. For each year we used, for every part of the domain, the smallest Geofabrik region for which a snapshot of that date exists; where a region did not yet exist (regions have been subdivided over time), its parent region was used, and nested duplicates were removed. For the current year the latest extract was used if the 1 January snapshot was not yet published. All ways tagged *highway* with a class listed in Table S2 were read; ways of other classes (paths, footways, cycleways), waterways and ferry routes were not used as travel links."),
  H3("Speeds"),
  P("Each road class was assigned a free-flow speed (Table S2), from 100 km/h for motorways to 15 km/h for tracks. Speeds were multiplied by 0.7 when the way was tagged with an unpaved surface, or when the surface was not tagged and the class is usually unpaved (tertiary and lower). Roads were burned into the grid with every touched cell receiving the speed of the fastest road crossing it."),
  H3("Governance penalty"),
  P("Travel on roads was slowed in proportion to perceived corruption, which we used as a proxy for delays from informal checkpoints and poorly maintained infrastructure. We used the World Bank Worldwide Governance Indicators *Control of Corruption* score (0–100, higher = better control; indicator GOV_WGI_CC.SC) for the latest year not later than the reference year, and the continental median for countries without a score. With *S* the score of the country containing a cell and *c* = 1 − *S*/100, road speeds were multiplied by"),
  EQ("*f*~corr~ = 1 − *K* · *c*", 1),
  P("with *K* = 0.10, so that the road speeds of a country with the lowest score are reduced by at most 10%. Off-road walking was not penalised. Because *K* has no empirical basis, it is treated as a scenario parameter; values per country and year are given in Table S5."),
  H3("Microsoft road detections"),
  P("For the end year only, roads detected by Microsoft from satellite imagery (Global ML Road Detections, release of 28 April 2025) were added in cells without any OSM road, at 15 km/h. They were not used for the start year because their imagery date is not known."),
  H3("Roads on open water"),
  P("To exclude mapping errors and false detections, a road cell was removed when at least 90% of its area is permanent water (share computed from WorldCover 2021 at ≈185 m within each 30″ cell), unless the OSM way is tagged as a bridge, causeway, ford or embankment. Microsoft roads on such cells were always removed. Using the water share rather than the dominant class keeps roads along lake shores and coasts."),
  H3("Completion of the 2015 network"),
  P("OSM was much less complete in 2015 than today in many low- and middle-income countries. The friction surface of Weiss et al. (2018), which underlies the Nelson et al. (2019) indicators, combined OSM with Google road data for 2015; the Google data are not public, but the friction surface is (Malaria Atlas Project, CC BY 4.0). We converted it to speed (*v* = 60 / (1000 *f*), km/h) and, before any travel-time calculation, added a 2015 road to every cell where (i) OSM 2015 has no road, (ii) the Weiss surface implies a transport network (*v* ≥ 10 km/h), (iii) OSM of the end year has a road, and (iv) the cell is not open water. Condition (iii) restricts the completion to roads that exist today and removes the rivers, sea lanes and railways that are also present in the Weiss surface. The added cells received the lower of the Weiss speed and the end-year OSM speed, so that no road is faster in 2015 than in the end year."),
  H3("Completeness of OSM 2015"),
  P("To identify areas where OSM 2015 alone was already informative, we computed, for 2° × 2° tiles (the tile size used by Weiss et al., 2018, for validation), the share of Weiss 2015 network cells that are end-year OSM roads and were already OSM roads in 2015, before completion. Tiles with ≥80% completeness and ≥50 such cells were classed as *OSM 2015 complete* and used as a separate subset in the comparison with Nelson et al. (2019)."),

  H2("2.4 Off-road travel"),
  P("Off-road cells were assigned a walking speed on flat ground according to their dominant ESA WorldCover 2021 class (Table S3), multiplied by Tobler's hiking factor for the mean slope of the cell:"),
  EQ("*v*~off~ = *v*~lc~ · exp(−3.5 · tan θ)", 2),
  P("where tan θ is the mean of the slope computed from the Copernicus GLO-90 digital elevation model at 6″ (≈185 m) within each 30″ cell. Using one land-cover map (2021) for both years ensures that the change in travel time is not driven by differences between the WorldCover 2020 (v100) and 2021 (v200) products, which were produced with different algorithm versions. Permanent water is impassable (speed 0) unless crossed by a road."),

  H2("2.5 Border crossings"),
  P("Crossing an international land border between two African countries (Natural Earth, 1:10 m) added a delay at official crossing points only, defined as the intersections of motorways, trunk, primary and secondary roads (and their links) with such borders. The delay applies to all travellers using these crossings. Borders elsewhere in the world, and informal crossings away from major roads, were not penalised. The delay was scaled by the mean governance score of the two countries, *c̄*:"),
  EQ("*D* = 15 min / (1 − *K* · *c̄*)", 3),
  P("and added to the friction of the grid cell containing the crossing as *D* / *L*, where *L* is the cell's mean step length, so that a path through the cell accumulates approximately *D*."),

  H2("2.6 Friction surface"),
  P("The speed of each cell was the larger of the road speed (after the governance factor) and the off-road speed; friction was expressed in minutes per metre:"),
  EQ("*F* = 60 / (1000 · max(*v*~road~ · *f*~corr~, *v*~off~))", 4),
  P("Cells with speed 0 (open water, no data) were impassable."),

  H2("2.7 Destinations"),
  H3("Settlements"),
  P("Settlements were delineated for each reference year from the Global Human Settlement Layer (GHSL, release R2023A) at 1 km: contiguous (8-connected) cells classified by the degree-of-urbanisation model (GHS-SMOD) as urban centre, dense or semi-dense urban cluster, or suburban cell (classes 30, 23, 22 and 21), with population summed from GHS-POP. Urban clusters have at least 5,000 inhabitants by definition. The GHSL epoch nearest to each reference year was used (2015 for 2015, 2025 for 2026); GHSL epochs after 2020 are projections [check against the GHSL documentation]. Settlement cells were transferred to the 30″ grid by nearest-neighbour resampling."),
  H3("Ports"),
  P("Ports were taken from the current edition of the World Port Index (NGA Publication 150) and classified by harbour size. Ports falling on impassable cells were moved to the nearest passable cell within 5 km."),
  H3("Layers"),
  P("We reproduced the 17 layers of Nelson et al. (2019) (Table S4): travel time to settlements of each of nine population classes (layers 1–9, from 5–50 million to 5,000–10,000), to settlements of ≥20,000 (layer 10), 50,000–50 million (layer 11, the headline indicator used here) and ≥5,000 (layer 12), and to ports of each size (layers 1–4) and of any size (layer 5)."),

  H2("2.8 Least-cost travel time"),
  P("Travel time from every cell to the nearest destination cell was computed with a multi-source Dijkstra algorithm over the 8-neighbour graph of the grid. The cost of a step between two adjacent cells *i* and *j* is"),
  EQ("*C*~ij~ = ½ (*F*~i~ + *F*~j~) · *d*~ij~", 5),
  P("where *d*~ij~ is the great-circle step length on a sphere of radius 6,371,007 m: *R* Δφ north–south, *R* cos φ Δλ east–west at the latitude φ of the row, and the hypotenuse of the two (east–west length at the mean latitude of the two rows) for diagonal steps. All cells of a destination settlement are sources with time zero. Results are in minutes and were stored as 16-bit integers (nodata 65535), as in Nelson et al. (2019). The implementation was verified against scikit-image (MCP_Geometric) near the equator (agreement within 0.02%) and against analytical distances at 60°N."),

  H2("2.9 Summary indicators"),
  P("Travel times were summarised as population-weighted means and as the share of population within 60 minutes, using GHS-POP of the same epoch as the settlements, re-projected to the 30″ grid while conserving population (mean density × cell area). Population in cells from which no destination can be reached was reported separately. Summaries are given for each country, continent and the whole domain; in the regional test, country values refer only to the part of each country inside the domain."),

  H2("2.10 Comparison with Nelson et al. (2019)"),
  P("Our 2015 and end-year layers were compared cell by cell with the corresponding 2015 layers of Nelson et al. (2019) (figshare 10.6084/m9.figshare.7638134, version 4; the rasters are identical to version 3 cited by the R package geodata, verified by MD5 checksum). For each layer we report the mean and mean absolute difference, the share of cells within ±30 minutes, the Pearson correlation of log(1 + minutes), and population-weighted means, for all cells and for the *OSM 2015 complete* tiles (Section 2.3)."),

  H2("2.11 Validation against a routing engine"),
  P("End-year travel times were validated against the free Open Source Routing Machine (OSRM; car profile on current OSM data, public servers of the OSRM project and FOSSGIS), queried at no more than one request per second in line with the servers' usage policies. We drew a sample of settlements of ≥50,000 inhabitants stratified by continent (in proportion to the square root of their number, at least five per continent; 250 globally [global], 12 in the regional test) and, for each, up to ten origins between 10 and 150 km (great-circle) sampled from populated cells with probability proportional to population. Our time was obtained from a single-source least-cost run from the settlement over the end-year friction surface; the reference was the OSRM table duration between the same points. Pairs for which OSRM moved an origin or the settlement point by more than 1 km to reach its road network were discarded. OSRM gives free-flow car times without walking segments or border delays and is therefore a lower-bound reference rather than an observed journey time."),

  H2("2.12 Implementation"),
  P("The workflow is a single Python script (*global_accessibility_v2.py*; Python 3.11–3.13) that installs missing packages, downloads all inputs, runs the stages above and writes Cloud Optimized GeoTIFFs at 30″ and 300″ (one 17-band file per year, a change file, and the friction surface), global maps, summary tables and a folder with all parameters, input versions, checksums and run logs (Text S1). The least-cost algorithm is compiled with Numba; OSM extracts and travel-time layers are processed in parallel with a scheduler that limits the number of concurrent tasks by their estimated memory. Stages are resumable. The regional test ran on a GitHub-hosted runner (2 cores available) in about 6 minutes; software versions are listed in Table S10."),

  H2("2.13 Sensitivity analysis"),
  P("Because the governance factor *K* and the border delay rest on assumptions, we varied them one at a time around the baseline (*K* = 0.10, delay = 15 minutes): *K* ∈ {0, 0.05, 0.10, 0.20} with the delay at 15 minutes, and delay ∈ {0, 15, 30, 60} minutes with *K* at 0.10, giving seven scenarios including the baseline (a full factorial design of 16 combinations is available as an option). For each scenario the friction surfaces of both years were rebuilt from the same road and off-road speeds, so that only *K* and the delay differ, and travel time to settlements of 50,000–50 million inhabitants (cities 11) and to ports of any size (ports 5) was recomputed and summarised as in Section 2.9, for the whole domain, each continent and each country, together with the change between the two years."),

  // ------------------------------------------------------------------ RESULTS
  H1("3. Results"),
  NOTE("Regional test domain (1°W–4.5°E, 5.5–13.5°N). Replace with the global run where marked [global]."),
  H2("3.1 Road network and friction"),
  P("For 2015 no country-level Geofabrik snapshots exist for the domain, so the Africa extract of 1 January 2015 was used; for 2026, the six country extracts (Benin, Burkina Faso, Ghana, Niger, Nigeria, Togo). The length of OSM roads in the domain grew almost five-fold, from 79,100 km in 2015 to 382,000 km in 2026 (Table S8). Growth was concentrated in unclassified (10,400 → 148,300 km), residential (18,000 → 118,200 km) and track (5,500 → 43,500 km) roads, whereas the length of primary roads decreased (13,500 → 10,800 km) while trunk roads increased (1,500 → 6,700 km), consistent with reclassification. On the grid, OSM 2015 roads occupied 66,886 cells; the completion with the Weiss et al. (2018) surface added 79,233 cells, giving 146,119 road cells in 2015. In 2026 there were 252,709 road cells, of which 29,882 were contributed by Microsoft road detections (1.08 million segments, 220,000 km in the domain). The open-water rule removed 35 (2015) and 111 (2026) OSM road cells and 29 Microsoft cells, and kept 9 and 12 cells tagged as bridges or causeways."),
  P("None of the twelve 2° tiles assessed reached the 80% completeness threshold: OSM 2015 contained between 14% and 73% (median 39%) of the Weiss network cells that are roads today (Table S7). Completeness was highest in the west of the domain (Ghana, 61–73%) and lowest in southern and central Nigeria and Benin (14–35%)."),
  P("The governance factor reduced road speeds by 5.6–7.5% (Table S5; Nigeria 7.5%, Benin 5.7%, Togo 6.6% in 2026). Sixty-five official border crossings were identified in 2015 and 87 in 2026, mostly on the Togo–Ghana (25) and Benin–Togo (25) borders and the Benin–Nigeria border (17) (Table S6); their delays ranged from 15.9 to 16.1 minutes after the governance scaling."),

  H2("3.2 Accessibility in 2015 and 2026"),
  P("The number of settlements rose from 1,219 in 2015 to 1,369 in 2025, and those of ≥50,000 inhabitants from 186 to 198 (Table S9). The population-weighted mean travel time to the nearest settlement of ≥50,000 inhabitants fell from 22.0 minutes in 2015 to 19.0 minutes in 2026, and the share of the population within 60 minutes rose from 87.1% to 88.7% (Table 1; Figure 2). Travel time to the nearest settlement of ≥5,000 fell from 8.7 to 6.4 minutes (97.6% of people within 60 minutes in 2026), and to the nearest port of any size from 262 to 244 minutes. About 0.3% of the population (0.23–0.25 million) lived in cells from which no destination could be reached, mostly on land enclosed by water."),
  ...TABLE(["Layer", "Destinations 2015", "Destinations 2026", "Mean 2015 (min)", "Mean 2026 (min)", "≤60 min 2015", "≤60 min 2026"], [
    ["Settlements ≥ 5,000 (cities 12)", "1,209", "1,352", "8.7", "6.4", "95.8%", "97.6%"],
    ["Settlements ≥ 20,000 (cities 10)", "373", "413", "14.9", "11.4", "92.1%", "94.2%"],
    ["Settlements 50,000–50 M (cities 11)", "186", "198", "22.0", "19.0", "87.1%", "88.7%"],
    ["Settlements 100,000–200,000 (cities 5)", "48", "57", "71.5", "62.5", "68.1%", "71.3%"],
    ["Settlements 1–5 M (cities 2)", "6", "9", "160.2", "155.8", "34.1%", "40.7%"],
    ["Any port (ports 5)", "7", "7", "261.6", "243.5", "36.2%", "37.4%"],
  ], [3000, 1000, 1000, 1000, 1000, 1013, 1013],
  "**Table 1.** Population-weighted mean travel time and share of population within 60 minutes, regional test domain [global]. Population: GHS-POP 2015 (67.1 million) and 2025 (84.4 million). Destinations are counted within the domain. All 17 layers are in Table S9.",
  "Mean and share are weighted by GHS-POP of the epoch used for the settlements."),
  ...FIGURE("fig2_cities50k.png", 6.3, "**Figure 2.** Travel time to the nearest settlement of 50,000–50 million inhabitants (layer cities 11) in (a) 2015 and (b) 2026, and (c) the change 2026 − 2015 (negative = faster). Lines: African land borders. White: water or no data. Regional test domain [global]."),
  P("The improvement was widespread but uneven (Figure 2c). The largest reductions, often more than 60 minutes, occurred in rural areas, notably in Burkina Faso, Niger and west of Lake Volta in Ghana; most new OSM roads in the domain are unclassified roads and tracks (Table S8). In a few areas travel time increased, in places by more than 60 minutes (e.g. north of 11°N between 1° and 2°E, near the Benin–Burkina Faso–Niger borders); these are cells whose 2015 road (from OSM or from the completion) has no counterpart, or a slower class, in the 2026 network, and increases can also arise where GHSL 2025 no longer contains a settlement that was a destination in 2015. For layers restricted to one population class, growth can move settlements out of the class: the number of settlements of 50,000–100,000 inhabitants fell from 104 to 98 and the mean travel time to that class rose from 53.6 to 62.4 minutes, whereas it fell for the cumulative layers."),

  H2("3.3 Differences between countries"),
  P("Within the domain, mean travel time to settlements of ≥50,000 in 2026 ranged from 6.8 minutes in the Nigerian part to 80.2 minutes in the Burkinabè part (Table 2). The largest absolute reductions were in Niger (−13.2 minutes) and Burkina Faso (−9.6 minutes) and the largest relative reduction in Togo (−24%, from 20.9 to 15.8 minutes); in Benin the mean fell from 22.9 to 20.4 minutes and the share of people within 60 minutes rose from 85.5% to 86.6%."),
  ...TABLE(["Country (part in domain)", "Population 2025 (M)", "Cities 11, 2015 (min)", "Cities 11, 2026 (min)", "≤60 min 2015", "≤60 min 2026", "Ports 5, 2026 (min)"], [
    ["Benin", "14.4", "22.9", "20.4", "85.5%", "86.6%", "222"],
    ["Togo", "9.4", "20.9", "15.8", "86.7%", "91.4%", "189"],
    ["Ghana (part)", "16.8", "16.9", "13.7", "92.7%", "94.0%", "192"],
    ["Nigeria (part)", "34.1", "8.0", "6.8", "95.5%", "96.2%", "146"],
    ["Burkina Faso (part)", "5.7", "89.8", "80.2", "46.3%", "52.4%", "740"],
    ["Niger (part)", "3.6", "79.2", "66.0", "47.7%", "52.5%", "866"],
  ], [2300, 1100, 1150, 1150, 1100, 1100, 1126],
  "**Table 2.** Population-weighted travel time to settlements of 50,000–50 million inhabitants (cities 11) and to any port, by country, regional test domain [global: all countries in Table S11].",
  "Only the part of each country inside the domain is included; for Ghana, Nigeria, Burkina Faso and Niger this is a small, non-representative part of the country, and destinations outside the domain (e.g. ports of Lagos, Tema and Abidjan) are not reachable."),

  H2("3.4 Comparison with Nelson et al. (2019)"),
  P("After completion of the 2015 network, our 2015 estimates agreed closely with Nelson et al. (2019) for settlements (Table 3). For settlements of ≥50,000, the population-weighted mean was 22.0 minutes against 23.1 minutes in Nelson et al.; 67% of cells were within ±30 minutes and the correlation of log travel times was 0.89. Without the completion step, i.e. with OSM 2015 roads only, the same indicators were 33.8 minutes, 44% and 0.80. For settlements of ≥5,000, the means were 8.7 and 7.9 minutes (r = 0.87). Travel time to ports was spatially consistent (r = 0.97) but on average longer in our estimates (262 against 203 minutes), which we attribute, at least in part, to the domain boundary: Nelson et al. can reach ports outside the domain, such as Lagos, Tema and Abidjan, which our regional run cannot [global: to be verified]. No tile of the domain reached the completeness threshold, so the comparison restricted to *OSM 2015 complete* areas could not be made here [global]. Our 2026 estimates were shorter than the 2015 values of Nelson et al. for settlements (19.0 against 24.4 minutes for ≥50,000; population weights of 2025), consistent with the network growth described above."),
  ...TABLE(["Layer and version", "Cells", "Mean diff. (min)", "Mean abs. diff. (min)", "Within ±30 min", "r (log)", "Pop.-weighted: ours / Nelson (min)"], [
    ["Cities 11, 2015, OSM only", "576,291", "72.1", "84.0", "44%", "0.80", "33.8 / 23.1"],
    ["Cities 11, 2015, completed", "576,822", "16.2", "33.1", "67%", "0.89", "22.0 / 23.1"],
    ["Cities 11, 2026", "577,282", "−6.6", "33.7", "64%", "0.85", "19.0 / 24.4"],
    ["Cities 12, 2015, OSM only", "576,383", "68.1", "73.7", "49%", "0.77", "15.8 / 7.9"],
    ["Cities 12, 2015, completed", "576,917", "19.9", "27.5", "74%", "0.87", "8.7 / 7.9"],
    ["Cities 12, 2026", "577,401", "−3.8", "25.4", "74%", "0.82", "6.4 / 9.1"],
    ["Ports 5, 2015, OSM only", "576,251", "190.4", "192.6", "12%", "0.92", "281.6 / 203.0"],
    ["Ports 5, 2015, completed", "576,765", "123.1", "128.5", "20%", "0.97", "262.1 / 202.9"],
    ["Ports 5, 2026", "577,215", "63.3", "86.4", "26%", "0.96", "244.0 / 207.5"],
  ], [2500, 950, 1000, 1050, 950, 800, 1776],
  "**Table 3.** Comparison with the 2015 layers of Nelson et al. (2019), regional test domain [global]. Differences are ours − Nelson. *OSM only*: run without the 2015 completion step; *completed*: final method. Population weights: GHS-POP of our settlement epoch (2015 or 2025).",
  "The OSM-only rows come from an earlier run of the same code without the completion step (identical inputs otherwise)."),
  ...FIGURE("fig3_nelson_difference.png", 6.3, "**Figure 3.** Difference between our 2015 estimates and Nelson et al. (2019), in minutes (blue = shorter in this study), for settlements of 50,000–50 million (left) and ports of any size (right), mean of 10 × 10 cells. Regional test domain [global]."),

  H2("3.5 Validation against OSRM"),
  P("For 12 sampled settlements of ≥50,000 inhabitants, 120 origin–settlement pairs were queried (great-circle distances 12–149 km); 105 remained after removing pairs with a road snap distance above 1 km. Our 2026 travel times agreed closely with OSRM free-flow car times (Figure 4): the median was 118.7 minutes in our estimates and 113.5 minutes in OSRM, the median ratio 0.98, the median difference −1.6 minutes and the mean absolute difference 14.2 minutes; 90.5% of pairs were within ±30% and the correlation of log travel times was 0.94 [global: 250 settlements, results by continent]. Because both estimates rely on current OSM roads, this comparison validates the speed model and the least-cost computation rather than the completeness of the network."),
  ...FIGURE("fig4_osrm.png", 3.4, "**Figure 4.** End-year (2026) travel time from 105 origins to settlements of ≥50,000 inhabitants: this study against OSRM car routing (free flow). Solid line: 1:1; dashed lines: ±30%. Log scales. Regional test domain [global]."),

  H2("3.6 Sensitivity to the governance factor and the border delay"),
  P("The governance factor changed the level of travel time but hardly its change between years (Table 4; Figure 5). For settlements of ≥50,000, the population-weighted mean in 2015 ranged from 20.9 minutes without the penalty (*K* = 0) to 23.3 minutes with *K* = 0.20 (−5% to +6% around the baseline of 22.0 minutes), while the 2015–2026 change stayed between −2.99 and −3.09 minutes. Travel times to ports, which involve long road journeys, were more sensitive (244.8 to 280.9 minutes in 2015, −6% to +7%), and their change ranged from −16.3 to −20.3 minutes. The border delay had almost no effect at domain level: removing it shortened travel time to settlements of ≥50,000 by 0.13 minutes in 2015, and raising it from 15 to 60 minutes lengthened it by only 0.03 minutes. Country results followed the same pattern (Table S11): in Benin the 2026 mean ranged from 19.3 minutes (*K* = 0) to 21.7 minutes (*K* = 0.20) and the 2015–2026 change from −2.4 to −2.6 minutes, and in the Nigerien part of the domain from 62.1 to 70.5 minutes, with a change of −12.6 to −13.6 minutes, while the border delay changed no country mean by more than 0.3 minutes; the largest effect of the delay on the change was in the Burkinabè part of the domain (−8.4 minutes without delay against −9.6 to −9.9 minutes with it)."),
  ...TABLE(["Scenario", "Cities 11: 2015", "2026", "Change", "Ports 5: 2015", "2026", "Change"], [
    ["K = 0, delay 15 min", "20.90", "17.92", "−2.99", "244.8", "228.5", "−16.3"],
    ["K = 0.05, delay 15 min", "21.45", "18.44", "−3.01", "252.9", "235.8", "−17.1"],
    ["**K = 0.10, delay 15 min (baseline)**", "**22.03**", "**19.00**", "**−3.04**", "**261.6**", "**243.5**", "**−18.1**"],
    ["K = 0.20, delay 15 min", "23.33", "20.23", "−3.09", "280.9", "260.6", "−20.3"],
    ["K = 0.10, delay 0 min", "21.90", "18.96", "−2.94", "260.5", "242.9", "−17.6"],
    ["K = 0.10, delay 30 min", "22.06", "19.00", "−3.06", "261.6", "243.5", "−18.1"],
    ["K = 0.10, delay 60 min", "22.06", "19.01", "−3.06", "261.7", "243.5", "−18.1"],
  ], [2900, 1000, 1000, 1000, 1050, 1000, 1076],
  "**Table 4.** Sensitivity of the population-weighted mean travel time (minutes) to the governance factor *K* and to the border-crossing delay, regional test domain [global]. Change = 2026 − 2015.",
  "One-at-a-time design around the baseline; population weights as in Table 1."),
  ...FIGURE("fig5_sensitivity.png", 5.8, "**Figure 5.** Population-weighted mean travel time to settlements of 50,000–50 million (top) and to ports of any size (bottom) in 2015 and 2026, as a function of the governance factor *K* (left, delay 15 minutes) and of the border delay (right, *K* = 0.10). Dashed lines: baseline. Rows share the same scale. Regional test domain [global]."),

  H1("4. Discussion"),
  NOTE("The discussion is written for the regional test; figures marked [global] and the scope of the claims should be revisited after the global run."),
  H2("4.1 Principal findings"),
  P("We present a reproducible way to update global travel-time accessibility for any pair of years from open data, keeping the method fixed so that differences between years reflect the transport network and settlement growth. Applied to Benin, Togo and neighbouring areas, it shows a reduction of the population-weighted travel time to the nearest settlement of ≥50,000 inhabitants from 22.0 minutes in 2015 to 19.0 minutes in 2026, with the largest gains in the rural, less connected parts of Burkina Faso and Niger and smaller gains in coastal areas that were already well connected. Our 2015 estimates reproduce the Nelson et al. (2019) indicators for settlements closely once the 2015 road network is completed, and our 2026 estimates agree with OSRM routing within ±30% for 90% of the origin–settlement pairs tested."),
  H2("4.2 Construction or mapping?"),
  P("The main difficulty in dating accessibility change with OSM is that the growth of the map is not the growth of the network. In the test domain, OSM road length grew almost five-fold between 2015 and 2026, mostly as unclassified, residential and track roads, which fits the pattern of humanitarian and corporate mapping campaigns better than that of construction; the decrease in primary roads alongside an increase in trunk roads points to reclassification. Using OSM 2015 as it was would attribute to 2015–2026 many roads that already existed. Completing the 2015 network with the Weiss et al. (2018) surface, which drew on Google road data in addition to OSM, doubled the number of 2015 road cells and reduced the apparent 2015–2026 gain from about 15 minutes to 3 minutes for settlements of ≥50,000, while raising the agreement with Nelson et al. (2019) from r = 0.80 to 0.89. We consider the completed estimate the more credible one, but it is still an upper bound on the effect of new roads: roads that exist in 2026 but were missing from both OSM 2015 and the 2015 Google data are counted as new, and completeness of OSM 2015 remained below 80% in all tiles of the domain even before completion. Separating construction from mapping more strictly would require dated road inventories or multi-temporal imagery."),
  H2("4.3 Comparison with previous global products"),
  P("After completion, the settlement layers agree well with Nelson et al. (2019) in both level and pattern, despite differences in inputs: GHSL R2023A rather than the 2016 settlement layers, WorldCover rather than the earlier land cover, a different speed table and our governance and border penalties. The port layers agree in pattern (r = 0.97) but are about one hour longer in our estimates. In the regional test this is expected at least partly, because ports outside the domain, among them the larger ports of Lagos, Tema and Abidjan, cannot be reached; whether a difference remains in the global run is to be verified [global]. Differences in the World Port Index edition (current against the 26th edition used by Nelson et al.) may also contribute."),
  H2("4.4 Validation"),
  P("The agreement with OSRM (median ratio 0.98) indicates that our speeds and least-cost computation reproduce routed car travel times on the current network. It is not an independent validation of the network itself, since both rely on OSM, and OSRM free-flow times are a lower bound for real trips: they include no congestion, no stops and no border delays. Nelson et al. (2019), using Google journey times, found their estimates shorter than Google's in 72% of validation tiles (median difference −13.7 minutes), which suggests that routing-engine times are a more lenient benchmark than observed trips. The routing validation is available only for the end year, because free routing engines use current data; for the start year, the comparison with Nelson et al. (2019) is the closest available reference."),
  H2("4.5 Governance and border penalties"),
  P("The governance and border penalties are new relative to earlier global maps and rest on assumptions rather than measurements: we are not aware of empirical estimates that relate corruption scores to travel speed or crossing times for people. With *K* = 0.10 they slow roads by 5.6–7.5% in the test domain and add about one minute to the 15-minute delay at each official crossing. The sensitivity analysis (Section 3.6) shows that *K* shifts the level of travel time roughly in proportion to its size (about ±6% for settlements and ±7% for ports between *K* = 0 and 0.20) but leaves the 2015–2026 change almost unchanged, so conclusions about change do not depend on this assumption, whereas absolute travel times and comparisons between countries with different governance scores do."),
  P("The border delay, in contrast, had almost no effect, and increasing it beyond 15 minutes changed nothing. Two reasons are likely. First, for most people the nearest settlement of ≥50,000 inhabitants is in their own country, so few least-cost paths cross a border. Second, because the delay applies only at official crossings, as intended (including within ECOWAS, whose free-movement protocol does not remove border procedures in practice), a path can avoid a large delay by leaving the road and crossing the border on foot in an adjacent cell; at 30″ resolution such a detour costs roughly 15–30 minutes of walking, which caps the effective delay. We did not trace individual paths to confirm the second explanation. This behaviour is realistic for people on foot but not for vehicles and goods, which cannot leave the road; if the delay is meant to represent motorised crossings, it should be combined with a restriction that prevents vehicles from crossing a border elsewhere, which requires a mode-specific cost surface."),
  H2("4.6 Limitations"),
  BUL("**Speeds are not calibrated.** Road speeds follow common practice and walking speeds are placeholders (Table S3); both affect absolute travel times more than any other choice and should be calibrated, for example against the OSRM pairs, survey data or local knowledge."),
  BUL("**Fixed land cover and water.** One land-cover map (2021) is used for both years, so land-cover change does not contribute to the change in accessibility. Ferries and navigable waterways are not modelled, which makes islands served only by ferry unreachable from the mainland."),
  BUL("**Settlements.** Destinations come from GHSL epochs (2015, 2025); the 2025 epoch is a projection [check], and single-class layers can change because settlements move between population classes rather than because access changes (Section 3.2)."),
  BUL("**Microsoft road detections** are undated and are used for the end year only; their contribution is therefore attributed entirely to the end year."),
  BUL("**Resolution and mode.** At 30″, all roads in a cell take the fastest speed, and travel is modelled as a single fastest mode without seasonality, congestion or vehicle availability."),
  BUL("**Regional test.** The domain boundary truncates destinations outside it and parts of the neighbouring countries; country values for Ghana, Nigeria, Burkina Faso and Niger are not representative of those countries [global]."),
  H2("4.7 Outlook"),
  P("Because the workflow is a single script with the reference years as parameters, the maps can be updated as new OSM snapshots and GHSL epochs become available, and extended to other start years for which a reference network exists. Priorities for the global application are to report the comparison with Nelson et al. (2019) for tiles where OSM 2015 was complete, to run the sensitivity analyses of the governance and border parameters, and to calibrate the speed tables against the routing validation pairs [global]."),

  // REFERENCES_START
  REF_HEADING,
  ...[
    "Luxen, D., Vetter, C. (2011). Real-time routing with OpenStreetMap data. Proceedings of the 19th ACM SIGSPATIAL International Conference on Advances in Geographic Information Systems, 513–516. (OSRM; https://project-osrm.org)",
    "Microsoft (2025). Global ML Road Detections, release 2025-04-28. https://github.com/microsoft/RoadDetections (ODbL).",
    "Nelson, A. (2019). Travel time to cities and ports in the year 2015. figshare, dataset, version 4. https://doi.org/10.6084/m9.figshare.7638134.v4 (CC BY 4.0).",
    "Nelson, A., Weiss, D. J., van Etten, J., Cattaneo, A., McMenomy, T. S., Koo, J. (2019). A suite of global accessibility indicators. Scientific Data 6, 266. https://www.nature.com/articles/s41597-019-0265-5",
    "NGA – National Geospatial-Intelligence Agency. World Port Index, Publication 150 (current edition). https://msi.nga.mil/Publications/WPI",
    "OpenStreetMap contributors. Planet data (ODbL), regional extracts and yearly snapshots by Geofabrik GmbH. https://download.geofabrik.de",
    "Natural Earth. Admin 0 – Countries, 1:10 m. https://www.naturalearthdata.com (public domain).",
    "European Commission, Joint Research Centre (2023). GHSL Data Package 2023: GHS-SMOD and GHS-POP, release R2023A. https://ghsl.jrc.ec.europa.eu",
    "Tobler, W. (1993). Three presentations on geographical analysis and modeling. NCGIA Technical Report 93-1.",
    "Weiss, D. J., Nelson, A., Gibson, H. S. et al. (2018). A global map of travel time to cities to assess inequalities in accessibility in 2015. Nature 553, 333–336. https://doi.org/10.1038/nature25181",
    "Weiss, D. J. et al. (2018). Global friction surface 2015 (Accessibility__201501_Global_Travel_Speed_Friction_Surface). Malaria Atlas Project, CC BY 4.0. https://data.malariaatlas.org",
    "World Bank. Worldwide Governance Indicators, Control of Corruption: score (GOV_WGI_CC.SC). https://www.worldbank.org/en/publication/worldwide-governance-indicators",
    "Zanaga, D. et al. (2022). ESA WorldCover 10 m 2021 v200. European Space Agency. https://esa-worldcover.org (CC BY 4.0).",
    "European Space Agency (2021). Copernicus Global Digital Elevation Model GLO-90. https://registry.opendata.aws/copernicus-dem/",
  ].map((r) => new Paragraph({ children: runs(r, { size: 19 }), spacing: { after: 80 }, indent: { left: 360, hanging: 360 } })),
];

// =====================================================================================
// SUPPLEMENTARY MATERIAL
// =====================================================================================
const supp = [
  new Paragraph({ children: [new TextRun({ text: "Supplementary Material", bold: true, size: 34, color: "1F3864" })], spacing: { after: 80 } }),
  new Paragraph({ children: [new TextRun({ text: "Updating global travel-time accessibility for new road developments", italics: true, size: 22, color: "52514E" })], spacing: { after: 200 } }),
  NOTE("Values are from the regional test domain (1°W–4.5°E, 5.5–13.5°N) unless stated; tables marked [global] will be regenerated from the global run (files in the results folder: methods/ and tables/)."),

  H1("Text S1. Implementation and reproducibility"),
  P("The workflow is implemented in one Python file (*global_accessibility.py*), configured in a block at the top of the file (reference years, folders, speed tables, penalties, destination layers, validation settings). On start, the script installs any missing package into a local folder (no administrator rights needed). It then runs eight resumable stages: download, grids, roads, friction, travel time, outputs, comparison, validation and clean-up; completed stages are skipped when the script is restarted."),
  BUL("**Parallelism.** The script reads the number of usable cores and the available memory, including container (cgroup) limits, and plans each parallel stage from a per-task memory estimate plus ≈0.35 GB of process overhead, within 75% of the available memory. OSM extracts are processed in parallel (estimated 1.5 GB + 7 × file size per extract, largest first); the 34 travel-time layers (2 years × 17) are computed in parallel (≈10 bytes per grid cell, ≈7.8 GB for the global 30″ grid), with the friction surface shared through memory-mapped files. Remote reads of WorldCover and Copernicus tiles use threads."),
  BUL("**Least-cost algorithm.** Multi-source Dijkstra with an indexed binary heap, compiled with Numba; 32-bit indices (up to 2.1 billion cells). One layer on a 32-million-cell grid takes ≈40 s on one core."),
  BUL("**Outputs.** Cloud Optimized GeoTIFFs (DEFLATE, internal overviews) at 30″ and 300″: *traveltime_<year>* (17 bands, uint16 minutes, nodata 65535, band descriptions and units), *traveltime_change_<end>_minus_<start>* (int16 minutes, nodata −32768), *friction_<year>* (float32, minutes per metre); PNG maps of every layer, year and change; population-weighted tables by country, continent and domain; the comparison with Nelson et al. (2019) and the routing validation."),
  BUL("**Methods folder.** Configuration (all parameters as run), speed and land-cover tables, governance scores and factors per country and year, border crossings with their delays, African border lines, settlements per epoch (population and centroid), destinations per layer, OSM extracts used per year, road length by class and extract, OSM 2015 completeness tiles, input manifest (URL, size, date, Last-Modified), figshare record and MD5 checksums of the Nelson et al. layers, software versions, run times and log."),
  BUL("**Sensitivity stage (version 2.0).** For each scenario of *K* and border delay, friction is rebuilt from the saved road speeds (before the governance factor) and off-road speeds, so the baseline scenario reproduces the main run exactly; the headline layers are recomputed for both years in parallel and summarised; scenario grids are deleted afterwards. Default: one-at-a-time design, 7 scenarios, 24 extra travel-time runs."),
  BUL("**Tests.** 21 automated tests on synthetic data cover the grid, the least-cost algorithm (against scikit-image and analytical distances), road speeds and lengths, border and checkpoint detection, the governance factor and delay, the open-water rule, the 2015 completion and completeness, settlements, COG writing and aggregation, the memory-budgeted scheduler, port snapping, the routing validation (with a mocked server) and an integration of all stages from friction to comparison and the sensitivity analysis."),

  H1("Supplementary tables"),
  ...TEXTTABLE(["Input", "Source and version", "Use"], [
    ["Roads", "OpenStreetMap, Geofabrik extracts of 1 January of each year (africa-150101 for 2015; country extracts -260101 for 2026)", "Road network and speeds"],
    ["Roads (end year)", "Microsoft Global ML Road Detections, release 2025-04-28 (Western_Africa.zip in the test; World.zip globally)", "Gap filling, end year"],
    ["2015 network", "Weiss et al. (2018) global friction surface 2015, MAP WCS (CC BY 4.0)", "Completion of 2015 roads; completeness"],
    ["Land cover", "ESA WorldCover 2021 v200, 10 m (2,651 tiles; 12 in the test)", "Walking speed; water share"],
    ["Elevation", "Copernicus DEM GLO-90 (26,475 tiles; 52 in the test)", "Slope (Tobler)"],
    ["Settlements, population", "GHSL R2023A GHS-SMOD and GHS-POP, 1 km, epochs 2015 and 2025", "Destinations; population weights"],
    ["Ports", "World Port Index, NGA Pub. 150 (current edition; 3,807 ports)", "Port destinations"],
    ["Countries, borders", "Natural Earth Admin 0, 1:10 m", "Governance factor; African borders"],
    ["Governance", "World Bank WGI, Control of Corruption score (GOV_WGI_CC.SC), 1996–2024", "Road-speed and border penalties"],
    ["Reference layers", "Nelson et al. (2019), figshare 7638134 v4 (= v3 rasters)", "Comparison, 2015"],
    ["Reference routing", "OSRM, car profile (router.project-osrm.org; routing.openstreetmap.de)", "Validation, end year"],
  ], [1900, 4826, 2300], "**Table S1.** Input data."),
  ...TABLE(["OSM highway class", "Speed (km/h)", "Paved if surface missing", "Unpaved speed (km/h)"], [
    ["motorway", "100", "yes", "70"], ["trunk", "80", "yes", "56"], ["primary", "70", "yes", "49"],
    ["secondary", "55", "yes", "38.5"], ["tertiary", "40", "no", "28"], ["unclassified", "30", "no", "21"],
    ["residential", "25", "no", "17.5"], ["motorway_link", "60", "yes", "42"], ["trunk_link", "50", "yes", "35"],
    ["primary_link", "45", "yes", "31.5"], ["secondary_link", "40", "yes", "28"], ["tertiary_link", "30", "no", "21"],
    ["service", "20", "no", "14"], ["track", "15", "no", "10.5"], ["living_street", "15", "no", "10.5"],
    ["Microsoft ML road (end year)", "15", "–", "–"],
  ], [3200, 1800, 2200, 1826], "**Table S2.** Road speeds by OSM class before the governance factor. Unpaved speed = speed × 0.7, applied when the surface is tagged unpaved (unpaved, dirt, gravel, ground, earth, sand, compacted, mud, fine_gravel, grass, laterite) or, for classes marked *no*, when the surface is not tagged."),
  ...TABLE(["WorldCover 2021 class", "Code", "Walking speed on flat ground (km/h)"], [
    ["Tree cover", "10", "2.5"], ["Shrubland", "20", "3.0"], ["Grassland", "30", "4.0"], ["Cropland", "40", "4.0"],
    ["Built-up", "50", "5.0"], ["Bare / sparse vegetation", "60", "3.0"], ["Snow and ice", "70", "1.0"],
    ["Permanent water bodies", "80", "0 (impassable)"], ["Herbaceous wetland", "90", "1.5"], ["Mangroves", "95", "1.0"],
    ["Moss and lichen", "100", "3.0"],
  ], [4000, 1200, 3826], "**Table S3.** Off-road walking speeds on flat ground, multiplied by exp(−3.5 tan θ). Values are placeholders within the 1–5 km/h range and should be calibrated."),
  ...TABLE(["Layer", "Destinations", "Nelson et al. (2019) file"], [
    ["cities 1", "settlements 5,000,000 – <50,000,000", "travel_time_to_cities_1"], ["cities 2", "1,000,000 – <5,000,000", "…_cities_2"],
    ["cities 3", "500,000 – <1,000,000", "…_cities_3"], ["cities 4", "200,000 – <500,000", "…_cities_4"],
    ["cities 5", "100,000 – <200,000", "…_cities_5"], ["cities 6", "50,000 – <100,000", "…_cities_6"],
    ["cities 7", "20,000 – <50,000", "…_cities_7"], ["cities 8", "10,000 – <20,000", "…_cities_8"],
    ["cities 9", "5,000 – <10,000", "…_cities_9"], ["cities 10", "20,000 – <110,000,000", "…_cities_10"],
    ["cities 11 (headline)", "50,000 – <50,000,000", "…_cities_11"], ["cities 12", "5,000 – <110,000,000", "…_cities_12"],
    ["ports 1", "Large", "travel_time_to_ports_1"], ["ports 2", "Medium", "…_ports_2"], ["ports 3", "Small", "…_ports_3"],
    ["ports 4", "Very small", "…_ports_4"], ["ports 5", "Any size (incl. unclassified)", "…_ports_5"],
  ], [2400, 3800, 2826], "**Table S4.** Destination layers, as defined by Nelson et al. (2019). Layers 1–9 and ports 1–4 are single classes; cities 10–12 and ports 5 are cumulative."),
  ...TABLE(["Country", "2015: WGI year", "2015: score", "2015: road factor", "2026: WGI year", "2026: score", "2026: road factor"], [
    ["Benin", "2015", "37.6", "0.938", "2024", "43.0", "0.943"], ["Togo", "2015", "35.1", "0.935", "2024", "34.4", "0.934"],
    ["Ghana", "2015", "42.3", "0.942", "2024", "43.9", "0.944"], ["Nigeria", "2015", "24.3", "0.924", "2024", "25.3", "0.925"],
    ["Burkina Faso", "2015", "41.2", "0.941", "2024", "42.7", "0.943"], ["Niger", "2015", "39.1", "0.939", "2024", "35.4", "0.935"],
  ], [1900, 1180, 1180, 1180, 1180, 1180, 1226], "**Table S5.** Governance (WGI Control of Corruption score, 0–100) and resulting road-speed factor 1 − 0.1 (1 − score/100), countries of the test domain [global: all countries in methods/corruption_<year>.csv]."),
  ...TABLE(["Border", "Official crossings, 2026"], [
    ["Benin – Togo", "25"], ["Togo – Ghana", "25"], ["Nigeria – Benin", "17"], ["Burkina Faso – Togo", "8"],
    ["Nigeria – Niger", "4"], ["Burkina Faso – Ghana", "3"], ["Niger – Burkina Faso", "3"], ["Benin – Burkina Faso", "1"],
    ["Benin – Niger", "1"], ["Total (2015: 65)", "87"],
  ], [5000, 4026], "**Table S6.** Official border crossings (major roads crossing an African land border) in the test domain, 2026. Delay per crossing after governance scaling: 15.9–16.1 min (mean 16.0)."),
  ...TABLE(["Tile (west, north)", "Weiss network cells that are OSM roads in 2026", "…of which in OSM 2015", "Completeness"], [
    ["1°W, 13.5°N", "8,347", "5,176", "62%"], ["1°E, 13.5°N", "5,480", "2,776", "51%"], ["3°E, 13.5°N", "7,497", "3,062", "41%"],
    ["1°W, 11.5°N", "15,485", "9,446", "61%"], ["1°E, 11.5°N", "13,091", "4,808", "37%"], ["3°E, 11.5°N", "9,945", "2,371", "24%"],
    ["1°W, 9.5°N", "11,692", "7,829", "67%"], ["1°E, 9.5°N", "14,382", "4,047", "28%"], ["3°E, 9.5°N", "12,608", "1,777", "14%"],
    ["1°W, 7.5°N", "15,237", "11,188", "73%"], ["1°E, 7.5°N", "16,212", "5,363", "33%"], ["3°E, 7.5°N", "10,886", "3,786", "35%"],
  ], [2300, 2900, 2200, 1626], "**Table S7.** Completeness of OSM 2015 per 2° tile, before completion with the Weiss et al. (2018) surface. Threshold for *OSM 2015 complete*: ≥80%."),
  ...TABLE(["OSM highway class", "2015 (km)", "2026 (km)"], [
    ["unclassified", "10,435", "148,256"], ["residential", "17,954", "118,193"], ["track", "5,502", "43,482"],
    ["tertiary", "17,336", "31,640"], ["secondary", "11,238", "14,799"], ["primary", "13,479", "10,836"],
    ["service", "934", "7,101"], ["trunk", "1,472", "6,731"], ["motorway", "480", "719"], ["links and living streets", "268", "271"],
    ["Total", "79,098", "382,028"],
  ], [4000, 2500, 2526], "**Table S8.** Length of OSM roads intersecting the test domain, by class. Great-circle lengths of whole segments; roads added by the 2015 completion (raster cells) are not included."),
  ...TABLE(["Layer", "Destinations 2015", "2026", "Mean 2015 (min)", "2026", "≤60 min 2015", "2026"], [
    ["cities 1", "1", "2", "331.4", "239.9", "28.0%", "38.1%"], ["cities 2", "6", "9", "160.2", "155.8", "34.1%", "40.7%"],
    ["cities 3", "6", "8", "301.4", "204.4", "28.1%", "31.2%"], ["cities 4", "21", "24", "107.5", "91.2", "31.3%", "39.4%"],
    ["cities 5", "48", "57", "71.5", "62.5", "68.1%", "71.3%"], ["cities 6", "104", "98", "53.6", "62.4", "73.5%", "47.4%"],
    ["cities 7", "187", "215", "49.0", "40.1", "73.2%", "85.1%"], ["cities 8", "331", "359", "40.3", "34.3", "87.1%", "90.9%"],
    ["cities 9", "505", "580", "37.2", "34.1", "89.9%", "92.8%"], ["cities 10", "373", "413", "14.9", "11.4", "92.1%", "94.2%"],
    ["cities 11", "186", "198", "22.0", "19.0", "87.1%", "88.7%"], ["cities 12", "1,209", "1,352", "8.7", "6.4", "95.8%", "97.6%"],
    ["ports 1", "1", "1", "383.8", "348.3", "18.4%", "18.1%"], ["ports 2", "3", "3", "314.7", "279.9", "9.3%", "11.5%"],
    ["ports 3", "2", "2", "291.2", "272.5", "26.7%", "26.3%"], ["ports 4", "1", "1", "391.8", "358.8", "3.7%", "4.2%"],
    ["ports 5", "7", "7", "261.6", "243.5", "36.2%", "37.4%"],
  ], [1600, 1300, 1000, 1400, 1100, 1400, 1226], "**Table S9.** All 17 layers: destinations inside the test domain, population-weighted mean travel time and share of population within 60 minutes [global]."),
  ...TABLE(["Item", "Value"], [
    ["Script", "global_accessibility_v2.py, version 2.0.0"], ["Python", "3.13.15"], ["GDAL", "3.12.4"], ["numpy / pandas / geopandas", "2.5.3 / 3.0.6 / 1.1.4"],
    ["rasterio / pyogrio / shapely / pyproj", "1.5.1 / 0.13.0 / 2.1.2 / 3.8.0"], ["numba / scipy", "0.67.0 / 1.18.1"],
    ["Test run: grid", "660 × 960 cells (30″), 577,709 passable in 2026"], ["Test run: cores / memory", "2 / 4.8 GB available"],
    ["Test run: time", "download 1.5 min; roads 3.5 min (Microsoft roads 1.8 min); 34 travel-time layers 10.5 s; outputs 23.5 s; validation 13 s; sensitivity (7 scenarios, 24 runs) 9 s"],
  ], [3500, 5526], "**Table S10.** Software and run time of the regional test."),
  ...TABLE(["Scenario", "Benin", "Togo", "Ghana (part)", "Nigeria (part)", "Burkina Faso (part)", "Niger (part)"], [
    ["K = 0", "19.3 (−2.4)", "14.8 (−4.9)", "13.0 (−3.1)", "6.3 (−1.2)", "76.0 (−9.5)", "62.1 (−13.6)"],
    ["K = 0.05", "19.9 (−2.4)", "15.3 (−5.0)", "13.4 (−3.1)", "6.5 (−1.3)", "78.0 (−9.6)", "64.0 (−13.4)"],
    ["**K = 0.10 (baseline)**", "**20.4 (−2.5)**", "**15.8 (−5.1)**", "**13.7 (−3.2)**", "**6.8 (−1.3)**", "**80.2 (−9.6)**", "**66.1 (−13.1)**"],
    ["K = 0.20", "21.7 (−2.6)", "16.9 (−5.4)", "14.5 (−3.3)", "7.3 (−1.3)", "85.0 (−9.7)", "70.5 (−12.6)"],
    ["delay 0 min", "20.4 (−2.5)", "15.7 (−5.0)", "13.7 (−3.1)", "6.8 (−1.3)", "80.1 (−8.4)", "66.0 (−13.2)"],
    ["delay 30 min", "20.4 (−2.5)", "15.8 (−5.1)", "13.7 (−3.2)", "6.8 (−1.3)", "80.2 (−9.9)", "66.1 (−13.1)"],
    ["delay 60 min", "20.4 (−2.5)", "15.8 (−5.1)", "13.7 (−3.2)", "6.8 (−1.3)", "80.2 (−9.9)", "66.1 (−13.1)"],
  ], [2000, 1150, 1150, 1150, 1150, 1250, 1176],
  "**Table S11.** Sensitivity by country: population-weighted mean travel time in 2026 to settlements of 50,000–50 million (minutes), with the 2015–2026 change in brackets, test domain [global: all countries in sensitivity/sensitivity_country.csv]. *K* scenarios with a 15-minute delay; delay scenarios with *K* = 0.10."),
  NOTE("Table S12 (population-weighted travel time by country for all countries) will be taken from tables/pop_weighted_traveltime_by_country.csv of the global run [global]."),

  H1("Supplementary figures"),
  ...FIGURE("figS_ports.png", 6.3, "**Figure S1.** Travel time to the nearest port of any size (ports 5) in (a) 2015 and (b) 2026, and (c) the change 2026 − 2015. Ports outside the domain (e.g. Lagos, Tema, Abidjan) are not reachable in the regional run [global]."),
  ...FIGURE("figS_friction.png", 5.6, "**Figure S2.** Speed implied by the friction surface (km/h) in (a) 2015, after completion with the Weiss et al. (2018) surface, and (b) 2026, including Microsoft road detections. Off-road cells are below 6 km/h."),
];

function doc(children) {
  return new Document({ styles, numbering, sections: [{ properties: page, footers: footer, children }] });
}
(async () => {
  const iRef = main.findIndex((p) => p === REF_HEADING);
  const body = main.slice(0, iRef), refs = main.slice(iRef);
  const suppBody = supp.slice(2);          // drop the separate title lines
  const all = [...body,
    new Paragraph({ children: [new PageBreak()] }),
    new Paragraph({ children: [new TextRun({ text: "Supplementary Material", bold: true, size: 34, color: "1F3864" })], spacing: { after: 160 } }),
    ...suppBody,
    new Paragraph({ children: [new PageBreak()] }),
    ...refs];
  fs.writeFileSync(__dirname + "/Manuscript_v2_Methods_Results_Discussion_Suppl.docx", await Packer.toBuffer(doc(all)));
  console.log("written");
})();
