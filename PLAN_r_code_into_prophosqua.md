# Plan: move the pipeline's R code into prophosqua

Status: **done, all six steps, 2026-08-20.** Extends finding F9 of the separation
analysis. Two points below were decided differently while implementing; both are marked
in place. The inventory table below describes the state before the move.

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

## What existed before the move

`ptm-pipeline/template/src/`, 9 files, 16 function definitions. The directory no longer
exists; this is the inventory the move worked from:

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

As built:

```
R/dea_io.R                 the 9 dea_utils.R functions
R/feature_preparation.R    + validate_sequence_window (file already existed)
R/combine_ptm_results.R    standardize_ptm_results, combine_ptm_results
R/prep_ptmsigdb.R          prepare_ptmsigdb, write_gmt
R/prep_kinaselib.R         prep_kinaselib_inputs            (extracted)
R/compute_dpa_dpu.R        compute_dpa_dpu                  (extracted, F2a)
R/compute_cf_dea.R         compute_cf_dea                   (extracted, F2b)
R/compute_enrichment.R     compute_ptmsea, compute_kinaselib_gsea,
                           compute_mea                      (extracted, F3b)
R/render_reports.R         render_ptm_report, render_dpu_overview

inst/application/          CMD_*.R  (thin optparse front ends), 10 of them
                           Analysis_DPA_DPU.Rmd, Analysis_CorrectFirst_DEA.Rmd,
                           create_top_index.Rmd  (beside the six already there)
inst/application/bin/      ptm.sh, one dispatcher for all of them
R/prophosqua_copy_helpers.R  copy_ptm_shell_script

tests/testthat/            one test file per R/ file above
man/                       roxygen; runnable @examples for the pure functions,
                           \dontrun{} for the ones needing a DEA directory
```

One deviation from the target: instead of a `render_dpa_dpu()` and a
`render_cf_dea()`, there is a single `render_ptm_report(name, output_file, output_dir,
params)`. Every report is rendered the same way and differs only in its name and its
parameters, so one function and one wrapper serve all seven of them.

Work directory ends up as: `ptm_config.yaml`, `Snakefile`, `helpers.py`, `Makefile`, and
the `.sh` wrappers. Nothing R, nothing that can be wrongly edited.

## Sequence

Each step ships and verifies on its own. Do not batch them — every step needs one pipeline
run, and a byte-comparison of the reports it should not have changed.

**Step 1 — the pure functions.** *Done, `prophosqua` `4a68703` / `ptm-pipeline` `9a06335`.* `dea_utils.R` (9) and `validate_sequence_window` into
`prophosqua/R/`, with tests and `@examples`. The Rmds call `prophosqua::` instead of
`source()`ing. Delete both files from the template.
*Why first:* it is the only step that removes a bug class rather than moving code. A
`source()`d file can shadow a package function of the same name — that is exactly how
`prepare_ntoc_data` came to report every site as `observed`. Namespaced functions cannot.
*Risk:* low, no behaviour change. *Verify:* full run, reports byte-identical.

**Step 2 — F2a, split and move DPA/DPU.** *Done. The two workbooks and `combined_test_diff.rds` verified against the previous run: the RDS byte-identical, both workbooks content-identical (74,106 x 42 and 91,416 x 49 cells); the workbook bytes differ only by writexl's embedded timestamp.* Extract `compute_dpa_dpu()`; add
`CMD_DPA_DPU.R` + `ptm.sh dpa_dpu`; move the report Rmd to `inst/application/`. The
`analysis_dea` rule becomes two: `compute_dpa_dpu` (workbooks + rds) and `report_dpa_dpu`
(html). *Verify:* the three data outputs byte-identical to the current run.

**Step 3 — F5, the tier targets.** *Done.* `rule data:` and `rule reports:`. Cheap, and
only meaningful once step 2 exists.

**Step 4 — F2b, split and move CorrectFirst.** *Done. All three CorrectFirst workbooks content-identical to the previous run; the report render dropped from about 85 s to 14.5 s. The saved object is `cf_objects.rds`, 30 MB, which is the price of that.* Same shape, plus `cf_objects.rds` carrying
the counts the prose quotes so the report needs no model refit. This is the step that pays
for itself: a caption fix drops from 85 s plus a downstream cascade to ~10 s and no
invalidation.

**Step 5 — the three CLI scripts.** *Done. Every text data product byte-identical to the previous run: 43 files, comprising the 3 seqwindow lists, 18 `.rnk` files, 18 `mea_*.csv`, 3 `term2gene.csv` and the PTMsigDB `.gmt`, plus the PTMsigDB `.rds`. `PTM_results.rds` byte-identical and `PTM_results.xlsx` content-identical after one fix: refactoring the column selection had swapped `gene_name` and `protein_length` in the CF sheet. A test now pins the column order of all three sheets.* `combine_ptm_results`, `prep_ptmsigdb`,
`prep_kinaselib` → functions, `CMD_*.R`, `ptm.sh` commands. `prep_kinaselib.R` needs its logic
extracted first. *Verify:* `PTM_results.xlsx` and the `.rnk` files byte-identical.

**Step 6 — F3b, enrichment compute out of the renders.** *Done. The six workbooks and RDS files are declared outputs, because the compute step writes them whether or not anything was enriched. Their contents cannot be compared to the previous run: GSEA sets no seed, so two runs of identical code differ as much as this run differs from the previous one (max |delta NES| 0.073 vs 0.075, and a few sets crossing the reporting cutoff). `setSize` is identical for every matched set, which pins the ranking and set matching. Seeding them is a separate decision -- it would change results -- and is not done here.* GSEA/MEA computation into
prophosqua functions writing `*_results.rds`; the vignettes render from that. Then the six
enrichment outputs can finally be declared, which today they cannot — their export chunks
are guarded by `has_*_results`, so an empty enrichment writes nothing and declaring them
would turn that into a rule failure.

## Invocation

The **Snakefile calls the shell wrapper**; the wrapper resolves the installed R script.
That is the whole chain — one path, no second mechanism. It applies to *every* rule that
runs R, report renders included; see the correction under "Invocation, as built" below.

```
rule -> ptm.sh <name> -> system.file(package = "prophosqua") -> application/CMD_<NAME>.R
```

The wrapper is copied into the work directory (by `ptm-pipeline init`, or by a
`prophosqua::copy_ptm_shell_script()` it calls) and is the same entry point a human uses
by hand. There is one wrapper, not one per script; see deviation 3 below.

## Invocation, as built

Two things were decided differently from the paragraphs above.

**1. No `Rscript -e` survives in the Snakefile, including the report renders.** The plan
said the six `template = get_prophosqua_vignette(...)` rules would "stay as they are",
which would have left six inline `rmarkdown::render()` calls and a generated R snippet
(`rmd_path_r_code()`) in the workflow. They are gone: `ptm.sh render` takes the report name,
the output file and the report's parameters as arguments, and `helpers.py` resolves any
installed file through one function, `get_prophosqua_file()`.

**2. A reinstall invalidates every rule that runs R.** The plan accepted that declaring
the `.sh` as the input would break invalidation, because a wrapper's mtime does not move
when the package is rebuilt, and concluded "rebuild those steps explicitly when you
reinstall". Declaring the resolved `CMD_*.R` and `.Rmd` alongside the wrapper is not enough
either: the work those scripts do happens in prophosqua's `R/`, which is none of the files
a rule names. So every rule that runs R also declares the installed package's
`Meta/package.rds`, which `R CMD INSTALL` rewrites every time.

This is coarse — a reinstall reruns all 17 R rules, about half an hour — and that is the
honest cost. A reinstall can change any function any rule reaches, and no cheaper
declaration is still true. It is finding F0 applied to the new mechanism: declare what the
rule reads, rather than reaching for `--forcerun` later.

**3. One wrapper, not one per script.** The plan followed prolfquapp exactly:
`inst/application/bin/*.sh`, one wrapper per `CMD_*.R`, all of them copied into the work
directory. Ten near-identical files differing only in the script name is ten files of clutter
in a directory whose whole point is to hold nothing editable. There is one `ptm.sh` instead,
taking the step as its first argument -- `./ptm.sh dpa_dpu`, `./ptm.sh render`,
`./ptm.sh help`. It resolves both the command list and each command's script from the
installation, so adding a `CMD_*.R` to prophosqua adds a command with no wrapper edit and no
work-directory change, and `help` cannot describe a set of steps the package does not have.

We build against the latest local install. No version pinning or version assertion in the
Snakefile.

## Two invariants to hold at every step

1. **Byte-compare the outputs that should not change.** Every step is a relocation, not a
   behaviour change; the workbooks and the reports are the test.
2. **One step, one pipeline run.** Do not batch them - a failure in a batch costs the whole
   cascade to localise.
