"""Helper functions for Snakefile

This module contains utility functions for finding DEA directories
and constructing file paths used by the Snakemake pipeline.
"""

import glob
import os
import subprocess


def get_prophosqua_file(relpath: str) -> str:
    """Resolve a file shipped under prophosqua's inst/application.

    Every R script, report template and shell wrapper this pipeline runs lives
    in the installed package, not in the project. Resolving them here, at parse
    time, lets a rule declare the exact file it runs, and fails the parse rather
    than a rule halfway through a run when the package is missing or too old.
    Invalidation on reinstall comes from get_prophosqua_install_stamp().

    Args:
        relpath: Path below inst/application, e.g. "CMD_RENDER.R" or
            "bin/ptm.sh"

    Returns:
        Full path to the installed file

    Raises:
        ValueError: If the file is not found in the installed prophosqua
    """
    cmd = [
        'Rscript', '--vanilla', '-e',
        f'cat(system.file("application", "{relpath}", package = "prophosqua"))'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    path = result.stdout.strip()
    if not path or not os.path.exists(path):
        raise ValueError(
            f"prophosqua application file not found: {relpath}. "
            "Is prophosqua installed and up to date?"
        )
    return path


def get_prophosqua_install_stamp() -> str:
    """Resolve a file of the installed prophosqua that every reinstall rewrites.

    A rule declares the wrapper it calls and the script or template that wrapper
    reaches, but the script's real work happens in the package's R code, which
    is not any of those files. Without this, editing a prophosqua function and
    reinstalling would leave every rule looking up to date -- the exact blindness
    that makes "I reinstalled prophosqua and the figure is still wrong" happen.

    Meta/package.rds is rewritten by every `R CMD INSTALL`, so declaring it makes
    a reinstall invalidate every rule that runs R. That is coarse on purpose: a
    reinstall can change any function any rule reaches, and there is no cheaper
    declaration that is still true.

    Returns:
        Full path to the installed package's Meta/package.rds

    Raises:
        ValueError: If prophosqua is not installed
    """
    cmd = [
        'Rscript', '--vanilla', '-e',
        'cat(system.file("Meta", "package.rds", package = "prophosqua"))'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    path = result.stdout.strip()
    if not path or not os.path.exists(path):
        raise ValueError(
            "prophosqua is not installed, or its installation is incomplete. "
            "Install it with: make -C <prophosqua checkout> install"
        )
    return path


def render_tmp_dir(analysis: str, step: str) -> str:
    """Build the private intermediates directory of one R Markdown render.

    knitr names its intermediate files after the input .Rmd, so several rules
    rendering the same vignette for different analysis types must not share an
    intermediates directory: with -j2 or more they would overwrite each other's
    .knit.md and every report would end up with the content of whichever render
    finished last. Giving each rule its own directory keeps the renders
    independent.

    Args:
        analysis: Analysis type (e.g., "dpa")
        step: Rule family (e.g., "vis_mea")

    Returns:
        Path to the intermediates directory for that rule
    """
    return f".render/{step}_{analysis}"


def _dea_file(dea_dir: str, filename: str, description: str) -> str:
    """Resolve one file inside the Results_WU_* subdirectory of a DEA directory.

    Mirrors prophosqua::get_dea_file() so that a file declared as a rule
    input is the same file the R code opens. Matches are sorted before the first
    is taken: a DEA directory is expected to hold one Results_WU_*, and sorting
    keeps the choice reproducible if it ever holds more.

    Args:
        dea_dir: Path to DEA output directory
        filename: File to find inside Results_WU_* (glob patterns allowed)
        description: Wording for the error message

    Returns:
        Path to the file

    Raises:
        ValueError: If no such file is found
    """
    matches = sorted(glob.glob(f"{dea_dir}/Results_WU_*/{filename}"))
    if not matches:
        raise ValueError(f"No {description} found in {dea_dir}")
    return matches[0]


def get_parquet_path(dea_dir: str) -> str:
    """Get the normalized abundance parquet of a DEA directory.

    Args:
        dea_dir: Path to DEA output directory (e.g., "DEA_setup/DEA_20260109_WUphospho_SHP2_vsn")

    Returns:
        Path to the normalized parquet file
    """
    return _dea_file(dea_dir, "lfqdata_normalized.parquet", "parquet file")


def get_dea_yaml_path(dea_dir: str) -> str:
    """Get the analysis configuration YAML of a DEA directory.

    Args:
        dea_dir: Path to DEA output directory

    Returns:
        Path to lfqdata.yaml
    """
    return _dea_file(dea_dir, "lfqdata.yaml", "yaml file")


def get_dea_xlsx_path(dea_dir: str) -> str:
    """Get the results workbook of a DEA directory.

    Prefers the DE_-prefixed workbook that prolfquapp writes, as
    prophosqua::get_dea_xlsx() does, so that the declared input is the
    workbook the reports actually read.

    Args:
        dea_dir: Path to DEA output directory

    Returns:
        Path to the results workbook
    """
    matches = sorted(glob.glob(f"{dea_dir}/Results_WU_*/*.xlsx"))
    if not matches:
        raise ValueError(f"No Excel file found in {dea_dir}")
    preferred = [m for m in matches if os.path.basename(m).startswith("DE_")]
    return preferred[0] if preferred else matches[0]


def build_analysis_lookups(dir_out: str, analyses_config: dict) -> dict:
    """Build lookup dictionaries for analysis configurations.

    Args:
        dir_out: Base output directory
        analyses_config: Dictionary of analysis configurations

    Returns:
        Dictionary containing:
        - types: List of analysis type keys
        - dirs: Dict mapping analysis -> output directory
        - sheets: Dict mapping analysis -> Excel sheet name
        - xlsx_inputs: Dict mapping analysis -> input Excel filename
        - stat_columns: Dict mapping analysis -> statistic column name
    """
    return {
        "types": list(analyses_config.keys()),
        "dirs": {k: f"{dir_out}/{v['subdir']}" for k, v in analyses_config.items()},
        "sheets": {k: v["sheet"] for k, v in analyses_config.items()},
        "xlsx_inputs": {k: v["xlsx_input"] for k, v in analyses_config.items()},
        "stat_columns": {k: v["stat_column"] for k, v in analyses_config.items()},
    }
