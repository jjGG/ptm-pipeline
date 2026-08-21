---
title: Public PTM datasets for testing the pipeline
---

# Public PTM datasets for testing the pipeline

Search performed 21 August 2026. What we were looking for: a public
phosphoproteomics dataset the pipeline can be exercised on end to end —
**factorial design, ideally two levels per factor**, TMT or label-free DDA,
mammalian, recent, and with a **matched total proteome**.

The last requirement is the binding one. The pipeline consumes *two* DEA runs
(site-level phospho and protein-level total) over the same samples and the same
contrasts. A phospho-only deposit, however good, cannot drive DPU or
CorrectFirst at all.

## Recommendation

| Want | Take |
|:--|:--|
| A crossed design with a matched global proteome, and results already published by a DPA/DPU tool | **MSV000085565** — Atg16l1 × *S. flexneri* infection, TMT, mouse |
| The most recent factorial TMT dataset with both proteomes | **PXD058857** — ARID1A × vemurafenib × trametinib, human, 2026 — *but resolve the missing phospho raws first* |
| To reproduce a published 2×2 phospho analysis including an interaction contrast | **PXD043476** — the msqrob2PTM biological dataset, label-free DDA, human |

**MSV000085565 is the best first target.** It is genotype × infection state,
carries a global proteome next to the phospho enrichment, is TMT DDA on mouse
BMDMs, and — decisively — it is one of the six evaluation datasets of the
MSstatsPTM paper, so DPA/DPU output from our pipeline can be held against
published numbers instead of against nothing. Its one weakness is age (eLife
2021, not 2024+).

## What the msqrobPTM trail actually contains

msqrob2PTM ([Demeulemeester et al., *MCP* 2023](https://doi.org/10.1016/j.mcpro.2023.100708))
is where DPA and DPU come from, so it was the obvious place to start. It
evaluates on six datasets, and it is worth being precise about which are ground
truth and which are biology:

| Role | Dataset | Modification | Acquisition | Accession |
|:--|:--|:--|:--|:--|
| Simulation | MSstatsPTM simulations | simulated | label-free | [GitHub](https://github.com/devonjkohler/MSstatsPTM_simulations) |
| **Ground truth spike-in** | 50 human modified peptides into human + *E. coli* | **ubiquitination** | label-free DDA | MSV000088971 / RMSV000000669 |
| Biology | USP30 / mitophagy | ubiquitination | label-free DDA | MSV000078977 / RMSV000000358 |
| **Biology, two-factor** | **human CSF phospho + total proteome** | **phosphorylation** | **label-free DDA** | **PXD043476** |

**There is no phospho spike-in with ground truth in the msqrobPTM line of work.**
Its only ground-truth PTM benchmark is a ubiquitination spike-in. If a
ground-truth *phospho* benchmark is what is wanted, the options are
[PXD007145](https://www.ebi.ac.uk/pride/archive/projects/PXD007145) (Hogrebe et
al. 2018 — a fixed-ratio phosphopeptide mixture across LFQ, SILAC and MS2/MS3
TMT; the canonical phospho quantification benchmark, but 2018 and no matched
total proteome) or the spike-in inside PXD050961 below.

The MSstatsPTM paper ([Kohler et al., *MCP* 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC9860394/))
is the more useful sibling: its dataset 5 *is* a TMT phospho experiment with a
matched global run, which is what led to MSV000085565.

## Candidates, with what is verified and what is not

Everything in the "design" column below was read out of the paper or the
deposited design file, not inferred from the title.

| Accession | Design | Levels | Acquisition | Both proteomes | Species | Published | Verdict |
|:--|:--|:--|:--|:--|:--|:--|:--|
| MSV000085565 | genotype × infection state | 2 × 3 | TMT DDA, 2 × 11-plex | **yes** | mouse | 2021 | **best pedigree** |
| PXD058857 | ARID1A × vemurafenib × trametinib | 2 × 2 × 2 | TMT 11-plex | claimed, **phospho raws not found** | human | 2026 | best if resolvable |
| PXD043476 | condition × subset | 2 × 2 (unbalanced) | label-free DDA | **yes** | human | 2024 | reference analysis exists |
| PXD050961 | MEK inhibitor × growth factors | 2 × 2 | **DIA** | **no** | human | 2025 | clean design, unusable shape |
| PXD067660 | cell species type × temperature/osmotic cycles | two-way, time-course | TMTpro 12-plex + DDA phospho | yes | human + mouse | 2026 | design too complex |
| PXD059659 | genotype only | 2 | TMT | yes | mouse | 2025 | not factorial |
| PXD077817 | treatment only | 2 | TMT, **COMPLETE** deposit | yes | mouse | 2026 | not factorial |

### MSV000085565 — Atg16l1 × *Shigella flexneri*

[eLife 2021, 10.7554/eLife.62320](https://doi.org/10.7554/eLife.62320);
MassIVE.quant reanalysis container RMSV000000357.

*Atg16l1*-WT vs myeloid-specific cKO bone-marrow-derived macrophages, each
either uninfected, or infected at an early (45–60 min) or late (3–3.5 h)
time point — 6 conditions, biological triplicates uninfected and quadruplicates
infected, across two 11-plex TMT experiments on an Orbitrap Fusion Lumos. Global
proteome, phospho-sites and KGG(Ub)-sites were all quantified (7260 proteins,
9418 phospho-sites, 3691 KGG sites).

For a two-levels-per-factor test, drop one infection time point and the design
becomes a clean 2 × 2 with the interaction that actually motivated the paper —
does autophagy loss change the *response* to infection, not just the baseline.
That interaction is what our factorial contrasts and DPU are for.

### PXD058857 — ARID1A × MAPK inhibitors, melanoma

Published as [Integrative multi-omics defines melanoma drug response networks
and ARID1A-dependent resistance](https://pmc.ncbi.nlm.nih.gov/articles/PMC13144321/)
(*Mol Syst Biol* 2026). A375 melanoma, ARID1A-WT and ARID1A-KO, each treated 6 h
with DMSO, vemurafenib, trametinib, or both, three biological replicates per
condition. TMT 11-plex with a pooled reference channel, Fe(III)-NTA phospho
enrichment on an AssayMap Bravo, Orbitrap Exploris, Mascot. Both a full proteome
and a phosphoproteome aliquot were taken from each of 20 concatenated hpH
fractions.

Read as vemurafenib ± × trametinib ± × genotype this is a full 2 × 2 × 2 with
n = 3 — the closest thing found to exactly what was asked for, and recent.

**The problem:** the paper's data availability statement says "Proteomics and
phosphoproteomics data has been deposited in PRIDE under the identifier
PDX058857" [sic], but the deposit holds 99 raw files, all named
`..._TMTproteome_plex{1,3,4,5,6}_F{1..20}.raw`, plus a checksum — 93.5 GB, no
file named for phospho enrichment and no search output. Five plexes × ~20
fractions is consistent with proteome *and* phospho having been uploaded under
one naming scheme (24 samples + reference channel needs about 2.5 plexes each),
but that is a guess. **Verify which plexes are enriched, or ask the authors,
before committing to a re-search.**

### PXD043476 — the msqrob2PTM biological phospho dataset

Human cerebrospinal fluid, label-free DDA, MaxQuant 1.6.17. Each sample was
split in two aliquots, one for total proteome (Q Exactive Plus) and one for
phospho enrichment (Q Exactive HF-X) — 90 phospho and 99 proteome runs,
189 SDRF rows. PRIDE publication date 2024-06-16, 100 files, 172 GB, submission
type PARTIAL. It ships `sdrf.tsv`, `human.fasta`, `pCSF_evidence.txt` (86 MB)
and two large annotated-spectra archives.

The design is not in PRIDE — the SDRF is anonymised, every row carries
`disease = Not available`. It is in the paper's repository, as
`biological phospho dataset/Experimental Design.csv` in
[statOmics/msqrob2PTMpaper](https://github.com/statOmics/msqrob2PTMpaper):
90 rows, `File, Experiment, Condition, Subset`, with `Condition` running A1–A47
and B1–B43 and `Subset` in {x, y}. Collapsed to the letter, the crosstab is

| | subset x | subset y |
|:--|--:|--:|
| condition A | 13 | 34 |
| condition B | 17 | 26 |

— an unbalanced 2 × 2. The published analysis fits `~condition*subset` and tests
`conditionA`, `conditionA:subsety`, `conditionA + conditionA:subsety` and two
weighted marginal contrasts, at both peptidoform and PTM level, for DPA and DPU.

This is the **only** candidate where a published 2×2 phospho analysis with an
explicit interaction contrast exists to compare our output against. Two real
costs: 172 GB of raw for a FragPipe re-search, and biology that is blinded —
"condition A vs B" and "subset x vs y" are all the public record says, so the
result is a statistical comparison, not a biological one.

### PXD050961 — SPIED-DIA, MEK inhibition in colorectal cancer

[Nat Commun 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12106795/). A textbook
2 × 2: selumetinib (10 µM, 3.5 h) or DMSO, crossed with a growth-factor cocktail
(EGF, HGF, FGF2, VEGF-C, 30 min) or BSA, in HCT116, DLD-1 and Caco2, biological
triplicates. It also carries its own ground truth — 240 detected heavy synthetic
phosphopeptides and a SILAC dilution series from 1:1 to 1:63.

Unusable here despite that: diaPASEF on a timsTOF Pro2 searched with DIA-NN, and
**no matched total proteome**. Recorded because it is the cleanest 2×2 phospho
design found, and because if the pipeline ever grows a DIA site reader plus a
tolerance for missing protein-level data, this is the dataset to test it on.

## None of these is FragPipe-ready

Every candidate needs a FragPipe re-search before the pipeline can see it:

- TMT → `abundance_single-site_None.tsv` → `-s prolfquappPTMreaders.FP_singlesite`
- label-free → `combined_site_STY_*.tsv` → `-s prolfquappPTMreaders.FP_combined_STY`

then two prolfquapp DEA runs with the same contrasts, then `ptm-pipeline init`
and `snakemake all`. Budget the re-search realistically: 172 GB (PXD043476) or
93.5 GB (PXD058857) of raw, and a TMT search with phospho as a variable
modification is not a quick job.

Two FragPipe-processed phospho datasets *with* matched proteomes did turn up —
[PXD055521](https://www.ebi.ac.uk/pride/archive/projects/PXD055521) (L1CAM
knockout and anti-L1CAM radioimmunotherapy in OVCAR8) and
[PXD053937](https://www.ebi.ac.uk/pride/archive/projects/PXD053937)
(anti-CD30 radioimmunotherapy in a T-cell lymphoma model, whose data processing
section names prolfqua explicitly). Neither is factorial: PXD053937 is four
one-way arms (PBS, cAC10, [177Lu]Lu-cAC10, [161Tb]Tb-cAC10, n = 4), and
PXD055521 is two separate comparisons rather than a crossed one. They are still
the least-effort datasets to smoke-test the readers on, since FragPipe was the
search engine.

## How the search was done

Reproducible, and worth knowing because one part of it misleads.

1. **PRIDE sweep.** The v3 search API (`/pride/ws/archive/v3/search/projects`)
   for `phosphoproteome`, `phosphoproteomics`, `phosphopeptide`,
   `phosphoproteomic`, `phosphosite`, paged out to 100 per page → 3190 distinct
   projects. Multi-word keywords return nothing — the parameter is matched as one
   token — so the AND has to happen locally.
2. **Local filtering** of title plus all three protocol texts for factorial
   language, matched-proteome language, mammalian species, and TMT/DDA/DIA;
   then the project record for each survivor for organism, publication date,
   quantification method and search engine.
3. **Europe PMC** full-text queries for the design vocabulary biologists
   actually use — `two-way ANOVA`, `genotype and treatment`,
   `alone or in combination` — restricted to 2024–2026.
4. **The design itself** read from the paper or the deposited design file. Never
   from the title.

**The trap:** free-text `2 x 2` in a PRIDE record is almost always a
TissueLyser setting — "2 × 2 min cycles at 30 Hz" — not an experimental design.
Two of the highest-scoring regex hits were exactly that. Likewise "interaction"
usually means protein-protein. Text mining PRIDE metadata for a design does not
work; the paper is the only reliable source, and Europe PMC full text is the
better entry point.

Also worth knowing: PRIDE web pages are client-rendered and fetch as an empty
shell. Use the API (`/pride/ws/archive/v3/projects/PXD######`,
`.../files?pageSize=2000`), and pull an SDRF straight from
`https://ftp.pride.ebi.ac.uk/pride/data/archive/<YYYY>/<MM>/<ACC>/sdrf.tsv`.
