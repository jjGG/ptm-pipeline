"""Helper functions for Snakefile

This module contains utility functions for finding DEA directories
and constructing file paths used by the Snakemake pipeline.
"""

import glob
import subprocess


def get_prophosqua_vignette(name: str) -> str:
    """Get path to a prophosqua vignette.

    Looks for the template in the installed prophosqua package.

    Args:
        name: Vignette filename (e.g., "Analysis_seqlogo.Rmd")

    Returns:
        Full path to the vignette file

    Raises:
        ValueError: If vignette not found in prophosqua
    """
    cmd = [
        'Rscript', '-e',
        f'''
        path <- system.file("application", "{name}", package="prophosqua")
        cat(path)
        '''
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    path = result.stdout.strip()
    if not path:
        raise ValueError(f"Application template {name} not found in prophosqua package")
    return path


def rmd_path_r_code(name: str, dev_path: str = "") -> str:
    """Generate R code to find a prophosqua vignette path.

    Uses files installed by prophosqua under inst/application.

    Args:
        name: Vignette filename (e.g., "Analysis_KinaseLibrary.Rmd")
        dev_path: Deprecated; ignored.

    Returns:
        R code string that sets rmd_path variable
    """
    return f"""
            rmd_path <- system.file('application', '{name}', package='prophosqua')
            if (rmd_path == '') stop('prophosqua application template not found: {name}', call. = FALSE)"""


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


def get_parquet_path(dea_dir: str) -> str:
    """Get parquet file path from a DEA directory.

    Finds the lfqdata_normalized.parquet file within the Results_WU_* subdirectory.

    Args:
        dea_dir: Path to DEA output directory (e.g., "DEA_setup/DEA_20260109_WUphospho_SHP2_vsn")

    Returns:
        Path to the normalized parquet file

    Raises:
        ValueError: If no parquet file is found
    """
    pattern = f"{dea_dir}/Results_WU_*/lfqdata_normalized.parquet"
    matches = glob.glob(pattern)
    if not matches:
        raise ValueError(f"No parquet file found in {dea_dir}")
    return matches[0]


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
