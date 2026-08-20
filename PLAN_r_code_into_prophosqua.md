# Plan: move the pipeline's R code into prophosqua

Status: **proposed, not started.** Extends finding F9 of the separation analysis.

Goal: a PTM analysis work directory contains no R code at all. Functions live in
`prophosqua` with roxygen docs, runnable `@examples` and testthat tests; the CLI scripts
live in `prophosqua/inst/application/`; only thin shell wrappers are copied into a project.

This follows the `prolfquapp` layout exactly: `inst/application/CMD_*.R` for the scripts,
`inst/application/bin/*.sh` for the wrappers, and a `copy_shell_script()`-style helper that
places the wrappers in the working directory. Each wrapper resolves the installed script:

```bash
PACKAGE_PATH=$(Rscript --vanilla -e "cat(system.file(package = 'prophosqua'))")
R_SCRIPT_PATH="${PACKAGE_PATH}/application/CMD_<NAME>.R"
```

## What exists today

`ptm-pipeline/template/src/`, 9 files, 16 function definitions:

| File | Lines | Functions | Kind |
|:--|--:|--:|:--|
| `dea_utils.R` | 226 | 9 | pure functions, `source()`d into renders |
| `feature_preparation.R` | 27 | 1 | pure function, `source()`d |
| `combine_ptm_results.R` | 207 | 5 | CLI script with functions |
| `prep_ptmsigdb.R` | 111 | 1 | CLI script, logic mostly top-level |
| `prep_kinaselib.R` | 120 | **0** | CLI script, all top-level |
| `render_dpu_overview.R` | 98 | **0** | render driver, all top-level |
| `Analysis_DPA_DPU.Rmd` | 192 | — | compute + report mixed |
| `Analysis_CorrectFirst_DEA.Rmd` | ~450 | — | compute + report mixed |
| `create_top_index.Rmd` | ~200 | — | report |

The two with zero functions are the most work: their logic has to be *extracted* into a
function before it can be tested, not merely relocated.

## Target layout in prophosqua

```
R/dea_io.R                 the 9 dea_utils.R functions
R/feature_preparation.R    + validate_sequence_window (file already exists)
R/combine_ptm_results.R    standardize_results, combine_ptm_results
R/prep_ptmsigdb.R          prepare_ptmsigdb, write_gmt
R/prep_kinaselib.R         prep_kinaselib_inputs            (extracted)
R/compute_dpa_dpu.R        compute_dpa_dpu                  (extracted, F2a)
R/compute_cf_dea.R         compute_cf_dea                   (extracted, F2b)
R/render_reports.R         render_dpu_overview, render_dpa_dpu, render_cf_dea

inst/application/          CMD_*.R  (thin optparse front ends)
                           Analysis_DPA_DPU.Rmd, Analysis_CorrectFirst_DEA.Rmd,
                           create_top_index.Rmd  (beside the six already here)
inst/application/bin/      ptm_*.sh

tests/testthat/            one test file per R/ file above
man/                       roxygen, every exported function with @examples
```

Work directory ends up as: `ptm_config.yaml`, `Snakefile`, `helpers.py`, `Makefile`, and
the `.sh` wrappers. Nothing R, nothing that can be wrongly edited.

## Sequence

Each step ships and verifies on its own. Do not batch them — every step needs one pipeline
run, and a byte-comparison of the reports it should not have changed.

**Step 1 — the pure functions.** `dea_utils.R` (9) and `validate_sequence_window` into
`prophosqua/R/`, with tests and `@examples`. The Rmds call `prophosqua::` instead of
`source()`ing. Delete both files from the template.
*Why first:* it is the only step that removes a bug class rather than moving code. A
`source()`d file can shadow a package function of the same name — that is exactly how
`prepare_ntoc_data` came to report every site as `observed`. Namespaced functions cannot.
*Risk:* low, no behaviour change. *Verify:* full run, reports byte-identical.

**Step 2 — F2a, split and move DPA/DPU.** Extract `compute_dpa_dpu()`; add
`CMD_DPA_DPU.R` + `ptm_dpa_dpu.sh`; move the report Rmd to `inst/application/`. The
`analysis_dea` rule becomes two: `compute_dpa_dpu` (workbooks + rds) and `report_dpa_dpu`
(html). *Verify:* the three data outputs byte-identical to the current run.

**Step 3 — F5, the tier targets.** `rule data:` and `rule reports:`. Cheap, and only
meaningful once step 2 exists.

**Step 4 — F2b, split and move CorrectFirst.** Same shape, plus `cf_objects.rds` carrying
the counts the prose quotes so the report needs no model refit. This is the step that pays
for itself: a caption fix drops from 85 s plus a downstream cascade to ~10 s and no
invalidation.

**Step 5 — the three CLI scripts.** `combine_ptm_results`, `prep_ptmsigdb`,
`prep_kinaselib` → functions, `CMD_*.R`, `ptm_*.sh`. `prep_kinaselib.R` needs its logic
extracted first. *Verify:* `PTM_results.xlsx` and the `.rnk` files byte-identical.

**Step 6 — F3b, enrichment compute out of the renders.** GSEA/MEA computation into
prophosqua functions writing `*_results.rds`; the vignettes render from that. Then the six
enrichment outputs can finally be declared, which today they cannot — their export chunks
are guarded by `has_*_results`, so an empty enrichment writes nothing and declaring them
would turn that into a rule failure.

## Invocation

The **Snakefile calls the shell wrapper**; the wrapper resolves the installed R script.
That is the whole chain — one path, no second mechanism:

```
rule -> ptm_<name>.sh -> system.file(package = "prophosqua") -> application/CMD_<NAME>.R
```

The wrappers are copied into the work directory (by `ptm-pipeline init`, or by a
`prophosqua::copy_ptm_shell_scripts()` it calls) and are the same entry point a human uses
by hand.

Consequence to be aware of, not to work around: the rule's declared input is then the
`.sh`, which does not change when prophosqua is reinstalled, so a package reinstall will not
by itself invalidate a rule. Rebuild those steps explicitly when you reinstall. The six
`template = get_prophosqua_vignette(...)` declarations already in the Snakefile stay as they
are; nothing here removes them.

We build against the latest local install. No version pinning or version assertion in the
Snakefile.

## Two invariants to hold at every step

1. **Byte-compare the outputs that should not change.** Every step is a relocation, not a
   behaviour change; the workbooks and the reports are the test.
2. **One step, one pipeline run.** Do not batch them - a failure in a batch costs the whole
   cascade to localise.
