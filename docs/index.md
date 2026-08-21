---
layout: default
title: PTM Pipeline
---

# PTM Pipeline

Deploy and run integrated phosphoproteomics PTM analysis pipelines.
PTM Pipeline scaffolds [Snakemake](https://snakemake.readthedocs.io/)-based workflows
on top of [prolfquapp](https://github.com/prolfqua/prolfquapp) differential expression results.

## Analysis Types

The pipeline implements three complementary statistical approaches for PTM analysis:

| Analysis | Description |
|----------|-------------|
| **DPA** | Differential PTM Abundance -- tests for changes in PTM-site intensity between conditions |
| **DPU** | Differential PTM Usage -- tests whether the PTM-to-protein ratio changes, independent of protein abundance |
| **CorrectFirst** | Applies protein-level correction before testing PTM sites |

Each analysis includes kinase activity inference via [Kinase Library](https://kinase-library.phosphosite.org/) (motif enrichment) and [PTM-SEA](https://doi.org/10.1074/mcp.TIR118.000943) (site-set enrichment).

These analyses are implemented in [**prophosqua**](https://github.com/prolfqua/prophosqua) ([![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15845272.svg)](https://doi.org/10.5281/zenodo.15845272)), described in:

> Wolski W, Dittmann A, Panse C, Kunz L, Grossmann J.
> "Integrated Analysis of Post-Translational Modifications and Total Proteome: Methods for Distinguishing Abundance from Usage Changes."
> *Methods in Molecular Biology*, 2025.

## What the pipeline adds to the DEA results

The two DEA runs happen **before** this pipeline, in prolfquapp: one on the enriched
phospho sample at site level, one on the total proteome at protein level. The pipeline
reads their output and never re-quantifies anything.

So the DPA table is the site-level DEA result -- with its protein-level counterpart
joined alongside, column for column, suffixed `.site` and `.protein`. What the step adds
to a plain DEA result is the pairing and what the pairing makes possible:

- site annotation (`posInProtein`, `modAA`, `SequenceWindow`) joined back onto each row,
- contaminants dropped and UniProt IDs canonicalised so site and protein rows meet,
- untested sites (no FDR) dropped, so DPA and DPU describe the same set of sites,
- the matched/unmatched count per contrast -- a site whose protein was never quantified
  keeps a DPA row with empty `.protein` columns and can carry no DPU value,
- **DPU**, computed from the pair: the effect is the difference of the two log2 fold
  changes, its standard error the root of the summed squares.

`CorrectFirst` starts from the same two DEA runs but goes the other way round: it
corrects site abundances by their protein abundance and *then* fits the model, rather
than comparing two finished models.

## Workflow

```mermaid
flowchart TB
    subgraph up["prolfquapp DEA -- upstream, before this pipeline"]
        SITE["phospho DEA<br/>site level"]
        PROT["total-proteome DEA<br/>protein level"]
    end

    SITE --> DPADPU["compute_dpa_dpu"]
    PROT --> DPADPU
    SITE --> CFDEA["compute_cf_dea"]
    PROT --> CFDEA

    DPADPU --> XDPA["Result_DPA.xlsx"]
    DPADPU --> XDPU["Result_DPU.xlsx"]
    CFDEA --> XCF["CorrectFirst_PTM_usage_results.xlsx"]
    DPADPU --> RDPA["report_dpa_dpu"]
    DPADPU --> ROV["render_dpu_overview"]
    CFDEA --> RCF["report_cf_dea"]

    XDPA --> COMBINE["combine_results"]
    XDPU --> COMBINE
    XCF --> COMBINE
    COMBINE --> PTMRES["PTM_results.xlsx<br/>sheets DPA, DPU, CF + abundances"]

    SIGDB["prep_ptmsigdb<br/>once, shared"] --> PTMSEA

    subgraph per["everything below runs three times: DPA, DPU, CorrectFirst"]
        direction TB
        PREPKL["prep_kinaselib"]
        SCAN["scan_motifs<br/>kinase-library CLI"]
        GSEA["compute_kinaselib_gsea"]
        MEARUN["run_mea<br/>one job per contrast"]
        MEACOL["compute_mea"]
        PTMSEA["compute_ptmsea"]
        NTOC["n_to_c"]
        SEQ["seqlogo"]
        RSEA["ptmsea report"]
        RKL["analysis_kinaselib"]
        RMEA["vis_mea"]
        PREPKL --> SCAN
        SCAN --> GSEA
        PREPKL --> MEARUN
        MEARUN --> MEACOL
        PTMSEA --> RSEA
        GSEA --> RKL
        MEACOL --> RMEA
    end

    PTMRES --> PTMSEA
    PTMRES --> PREPKL
    PTMRES --> GSEA
    PTMRES --> NTOC
    PTMRES --> SEQ

    RSEA --> INDEX["top_index"]
    RKL --> INDEX
    RMEA --> INDEX
    NTOC --> INDEX
    SEQ --> INDEX
    RDPA --> INDEX
    ROV --> INDEX
    RCF --> INDEX
    INDEX --> ZIP["zip"]

    classDef compute fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
    classDef report fill:#dcfce7,stroke:#22c55e,color:#14532d
    classDef file fill:#fef3c7,stroke:#f59e0b,color:#78350f
    classDef ext fill:#f3f4f6,stroke:#9ca3af,color:#374151
    class DPADPU,CFDEA,COMBINE,PTMSEA,PREPKL,SCAN,GSEA,MEARUN,MEACOL,SIGDB compute
    class RDPA,ROV,RCF,RSEA,RKL,RMEA,NTOC,SEQ,INDEX,ZIP report
    class XDPA,XDPU,XCF,PTMRES file
    class SITE,PROT ext
```

Blue steps compute and write data; green steps render HTML. That split is what the two
tier targets name: `snakemake -j1 data` stops after the blue ones, `snakemake -j1 reports`
renders from what they wrote, so correcting a caption costs a render and not a reanalysis.

Every step runs through one wrapper shipped with prophosqua -- `ptm.sh <step>` -- which
resolves the step's R code from the installed package. `./ptm.sh help` lists them.

## Quick Start

```bash
# Install
uv tool install git+https://github.com/wolski/ptm-pipeline

# Initialize and run
cd /path/to/project_with_DEA_results
ptm-pipeline init
make all
```

Or use Docker (no local R/Python setup needed):

```bash
./ptm-pipeline.sh init-default DEA_data/ output/
./ptm-pipeline.sh run output/
```

See the [README](https://github.com/wolski/ptm-pipeline#readme) for full documentation.

## Example Reports

The CI pipeline runs three test datasets on every push to `main`.
The rendered HTML reports are available as downloadable artifacts:

| Dataset | Description |
|---------|-------------|
| PTM_FP_TMT_example | FragPipe TMT quantification |
| PTM_FP_LFQ_example | FragPipe label-free quantification |
| PTM_BGS_Spectronaut_DIA_example | Spectronaut DIA quantification |

**[Download latest test reports](https://github.com/wolski/ptm-pipeline/actions/workflows/ci.yml?query=branch%3Amain+is%3Asuccess)** -- click the latest successful run, then scroll to "Artifacts".

## Methods and References

See [Methods](methods.md) for a full description of the computational workflow, software components, and citation information.

## Links

- [GitHub Repository](https://github.com/wolski/ptm-pipeline)
- [Docker Image](https://github.com/wolski/ptm-pipeline/pkgs/container/ptm-pipeline-ci)
- [prolfqua](https://github.com/prolfqua/prolfqua) / [prolfquapp](https://github.com/prolfqua/prolfquapp)
- [prophosqua](https://github.com/prolfqua/prophosqua)

<!--
  Jekyll turns a ```mermaid fence into a highlighted code block, so the diagram
  above would ship as source unless something renders it. This hands each such
  block's text to mermaid. github.com renders the same fence natively, so the
  fence stays the single source of the diagram either way.
-->
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";

  const blocks = document.querySelectorAll(
    "div.language-mermaid, pre > code.language-mermaid"
  );
  for (const block of blocks) {
    const pre = document.createElement("pre");
    pre.className = "mermaid";
    // textContent, not innerHTML: the highlighter may have wrapped the source
    // in spans, and mermaid needs the graph text as written.
    pre.textContent = block.textContent.trim();
    block.replaceWith(pre);
  }

  mermaid.initialize({ startOnLoad: false, theme: "neutral" });
  await mermaid.run();
</script>
