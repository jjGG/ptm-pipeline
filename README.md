# PTM Pipeline

**[Documentation & Example Reports](https://wolski.github.io/ptm-pipeline)** | [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18349420.svg)](https://doi.org/10.5281/zenodo.18349420)

Deploy phosphoproteomics PTM analysis pipeline to new projects.

## Installation

```bash
# Install from GitHub
uv tool install git+https://github.com/wolski/ptm-pipeline

# Update to latest version from GitHub
uv tool upgrade ptm-pipeline

# Install from a local checkout (after code changes, use --force --reinstall)
uv tool install --force --reinstall /path/to/ptm-pipeline
```

## Usage

```bash
cd ~/Dropbox/DataAnalysis/o40XXX_NewProject
# DEA folders should already exist from prolfquapp

ptm-pipeline init    # Auto-detect DEA folders, generate config
make all             # Run the pipeline
```

### Makefile Targets

| Target | Description |
|--------|-------------|
| `make help` | Show available targets |
| `make all` | Run the full pipeline |
| `make dry-run` | Show what would be executed |
| `make validate` | Validate project setup |
| `make clean` | Remove output files (keeps config) |
| `make install` | Install ptm-pipeline tool |
| `make upgrade` | Upgrade to latest version |
| `make update` | Update pipeline files (keeps config) |

### CLI Commands

| Command | Description |
|---------|-------------|
| `ptm-pipeline init [INPUT_DIR] [OUTPUT_DIR] [--name NAME] [--dry-run] [--force] [--default]` | Initialize pipeline (interactive) |
| `ptm-pipeline init-default [INPUT_DIR] [OUTPUT_DIR]` | Initialize with defaults (non-interactive, for CI) |
| `ptm-pipeline run [DIR] [-j CORES] [--dry-run]` | Run the analysis pipeline |
| `ptm-pipeline clean [DIR] [--dry-run] [--force]` | Remove pipeline files (keeps DEA data) |
| `ptm-pipeline validate [DIR] [--quick]` | Check dependencies |
| `ptm-pipeline update [DIR] [--dry-run]` | Update pipeline files |
| `ptm-pipeline info [DIR]` | Show discovered DEA folders |

## Project Structure

Before `ptm-pipeline init`:
```
o40XXX_NewProject/
├── DEA_*_WUphospho_*/    # or DEA_*_WUcombined_*, DEA_*_*STY*
│   └── Inputs_WU_*/
└── DEA_*_WUprot_*/       # or DEA_*_WUtotal_*
```

After `ptm-pipeline init`:
```
o40XXX_NewProject/
├── DEA_*/...
├── ptm_config.yaml       # Generated config, the only project-owned file
├── Makefile              # Convenience targets
├── Snakefile             # Pipeline
├── helpers.py
└── ptm.sh                # One wrapper: ./ptm.sh help lists the steps
```

There is no `src/`. The analysis code lives in the installed prophosqua package:
`ptm.sh <command>` resolves that command's R script from the install path, and the
pipeline calls the same wrapper the same way. To change how an analysis behaves, edit prophosqua and reinstall
it — an edit in a project directory would be discarded by the next
`ptm-pipeline update`.

## Requirements

- Python 3.11+, Snakemake, uv
- R packages: tidyverse, readxl, writexl, arrow, prolfquapp, prophosqua, clusterProfiler, ggseqlogo

Alternatively, use `ptm-pipeline.sh` which runs everything inside Docker — no local R/Python setup needed.
The image is pulled automatically on first use.

```bash
./ptm-pipeline.sh init-default DEA_data/ output/
./ptm-pipeline.sh run output/
./ptm-pipeline.sh run output/ --dry-run
./ptm-pipeline.sh validate output/
```

Options:

| Flag | Description |
|------|-------------|
| `--image-version VERSION` | Image tag (default: `0.3.0`) |
| `--image-repo REPO` | Image repository (default: `ghcr.io/wolski/ptm-pipeline-ci`) |

## Configuration

The `ptm_config.yaml` file controls pipeline behavior. Key options:

| Option | Description |
|--------|-------------|
| `fdr` | FDR threshold for significance (default: 0.05) |
| `log2fc` | Log2 fold change threshold (default: 0.5) |
| `max_fig` | Maximum figures per report (default: 10) |

PTM report templates are resolved from the installed `prophosqua` package via
`system.file("application", ..., package = "prophosqua")`.

## Development

```bash
git clone https://github.com/wolski/ptm-pipeline
cd ptm-pipeline
uv sync
uv run ptm-pipeline --help
```

### Running Test Examples

Three test datasets are shipped as zips in `tests/data/`. To run them locally:

```bash
cd ptm-pipeline                          # repository root
uv tool install --force --reinstall .    # install from local checkout

make -C tests all      # unzip -> init -> run (all test pipelines)
make -C tests clean    # remove unzipped dirs and PTM_* output
```

To regenerate the test data zips from full source datasets (requires source data in `test_data/`):

```bash
cd ptm-pipeline                          # repository root
make -C test_data all                    # generate small subsets
make -C test_data zip                    # zip into tests/data/*.zip
```

### Managing uv.lock

Regenerate after changing `pyproject.toml` or to update dependencies:

```bash
uv lock                          # Regenerate lock file
uv lock --upgrade-package click  # Update specific package
uv sync                          # Sync environment
```

Commit `uv.lock` to ensure reproducible installs.

## Materials and Methods

See [METHODS.md](METHODS.md) for a description of the computational workflow, software components, and references for citing this pipeline.

## License

MIT
