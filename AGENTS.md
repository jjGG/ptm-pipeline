# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Changelog

Record every change to this project's code or user-visible behaviour in `CHANGELOG.md` at the repository root (Python
projects use `CHANGELOG.md`, not the R `NEWS.md`). Add a bullet under the heading for the current version
(`pyproject.toml`), creating a new version heading when a change opens one. Log the user-visible effect, not the
implementation detail. Do not log changes that only touch agent-instruction or repository meta files (`AGENTS.md`,
`CLAUDE.md`, and similar) unless explicitly asked.

## Project Overview

PTM Pipeline is a deployment tool for phosphoproteomics PTM (Post-Translational Modification) analysis. It scaffolds Snakemake-based workflows into projects that already have DEA (Differential Expression Analysis) output from `prolfquapp`.

## Commands

```bash
# Development
uv sync                              # Install dependencies
uv run ptm-pipeline --help           # Run CLI in development mode

# Documentation (MkDocs + Material, deployed by .github/workflows/pages.yml)
uv sync --only-group docs            # Install the docs toolchain
uv run mkdocs serve                  # Preview at http://127.0.0.1:8000
uv run mkdocs build --strict         # Build into public/ exactly as CI does

# CLI commands
ptm-pipeline init [DIR]              # Initialize pipeline (auto-discovers DEA folders)
ptm-pipeline validate [DIR]          # Check dependencies and setup
ptm-pipeline update [DIR]            # Update pipeline files, preserve config
ptm-pipeline info [DIR]              # Show discovered DEA folders (debugging)

# Run the analysis pipeline (after init)
snakemake -s Snakefile --configfile ptm_config.yaml -j1 all
```

## Architecture

```
src/ptm_pipeline/
├── cli.py          # Click-based CLI entry point (4 commands)
├── discover.py     # Auto-detection of DEA folders and annotation files
├── init.py         # Project initialization and template copying
├── config.py       # YAML config generation
└── validate.py     # Environment validation (files, R packages, tools)

template/                # Copied to target projects on init
├── Snakefile            # Main Snakemake orchestration
├── helpers.py           # Snakemake helper functions
└── Makefile             # Convenience targets
```

There is no `template/src/`. A project holds no R code: every rule calls
`ptm.sh <command>`, the one wrapper from the installed prophosqua's
`inst/application/bin`, which resolves that command's `CMD_*.R` from the install
path. `ptm-pipeline init` and `update` copy `ptm.sh` into the project so a person
can run the same entry point by hand, and `update` deletes a `src/` and any
per-command `ptm_*.sh` left over from before the move. To change analysis behaviour, edit prophosqua and reinstall it.

## Key Patterns

**DEA Folder Discovery** (`discover.py`):
- Phospho patterns: `DEA_*_WUphospho_*`, `DEA_*_WUcombined_*`, `DEA_*_*STY*`
- Protein patterns: `DEA_*_WUprot_*`, `DEA_*_WUtotal_*`
- Annotation files: `Inputs_*/*_annot_*.tsv` or `Inputs_*/*_dataset*.tsv`

**Template Location** (`init.py`):
- Three fallback paths: development (`./template`), installed (`importlib.resources`), system (`share/ptm-pipeline/template`)

**Analysis Types** (Snakemake):
- DPA: Differential PTM Abundance
- DPU: Differential PTM Usage
- CF: CorrectFirst (protein-corrected analysis)

## Dependencies

- Python: uv (not pip) - see pyproject.toml
- R packages: prolfquapp, prophosqua, tidyverse, readxl, writexl, arrow, clusterProfiler, ggseqlogo
- External: Snakemake, kinase-library (accessed via `uv tool run`)
