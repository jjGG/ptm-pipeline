"""Validation utilities for PTM pipeline."""

from pathlib import Path
import subprocess
import shutil
from dataclasses import dataclass

import yaml
from rich.console import Console
from rich.table import Table


console = Console()


@dataclass
class ValidationResult:
    """Result of a validation check."""
    name: str
    passed: bool
    message: str


def check_file_exists(path: Path, description: str) -> ValidationResult:
    """Check if a file exists."""
    if path.exists():
        return ValidationResult(description, True, str(path))
    return ValidationResult(description, False, f"Not found: {path}")


def check_dir_exists(path: Path, description: str) -> ValidationResult:
    """Check if a directory exists."""
    if path.exists() and path.is_dir():
        return ValidationResult(description, True, str(path))
    return ValidationResult(description, False, f"Not found: {path}")


def check_r_package(package: str) -> ValidationResult:
    """Check if an R package is installed."""
    try:
        result = subprocess.run(
            ["Rscript", "-e", f"library({package})"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return ValidationResult(f"R: {package}", True, "Installed")
        return ValidationResult(f"R: {package}", False, "Not installed")
    except subprocess.TimeoutExpired:
        return ValidationResult(f"R: {package}", False, "Timeout checking")
    except FileNotFoundError:
        return ValidationResult(f"R: {package}", False, "Rscript not found")


def check_prophosqua_wrapper() -> ValidationResult:
    """Check that the installed prophosqua ships the ptm.sh wrapper.

    Every rule runs through it, so an installed but too-old prophosqua fails
    the whole workflow at parse time. Naming that here is cheaper than reading
    a Snakemake traceback.
    """
    description = "prophosqua ptm.sh wrapper"
    try:
        result = subprocess.run(
            [
                "Rscript", "--vanilla", "-e",
                'cat(system.file("application", "bin/ptm.sh", '
                'package = "prophosqua"))',
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return ValidationResult(description, False, "Timeout checking")
    except FileNotFoundError:
        return ValidationResult(description, False, "Rscript not found")

    path = result.stdout.strip()
    if not path or not Path(path).exists():
        return ValidationResult(
            description,
            False,
            "Not found. Reinstall prophosqua: make -C <prophosqua> install",
        )
    return ValidationResult(description, True, str(Path(path).parent))


def check_command_exists(command: str, description: str) -> ValidationResult:
    """Check if a command is available in PATH."""
    if shutil.which(command):
        return ValidationResult(description, True, f"Found: {shutil.which(command)}")
    return ValidationResult(description, False, f"Command not found: {command}")


def check_uv_tool(tool_spec: str) -> ValidationResult:
    """Check if a uv tool can be accessed."""
    try:
        result = subprocess.run(
            ["uv", "tool", "run", "--from", tool_spec, "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            return ValidationResult("kinase-library", True, "Accessible via uv")
        return ValidationResult("kinase-library", False, "Failed to access")
    except subprocess.TimeoutExpired:
        return ValidationResult("kinase-library", False, "Timeout")
    except FileNotFoundError:
        return ValidationResult("kinase-library", False, "uv not found")


def validate_project(project_dir: Path, quick: bool = False) -> bool:
    """Validate project setup for PTM pipeline.

    Args:
        project_dir: Path to project directory
        quick: If True, skip slow checks (R packages, uv tools)

    Returns:
        True if all critical checks pass
    """
    project_dir = project_dir.resolve()
    results: list[ValidationResult] = []

    console.print(f"\n[bold]Validating PTM pipeline setup in:[/bold] {project_dir}\n")

    # Check config file
    config_file = project_dir / "ptm_config.yaml"
    results.append(check_file_exists(config_file, "ptm_config.yaml"))

    config = None
    if config_file.exists():
        with open(config_file) as f:
            config = yaml.safe_load(f)

    # Check Snakefile
    results.append(check_file_exists(project_dir / "Snakefile", "Snakefile"))
    results.append(check_file_exists(project_dir / "helpers.py", "helpers.py"))

    # The analysis code lives in prophosqua, reached through its wrappers.
    # Resolving one of them proves both that the package is installed and that
    # it is new enough to carry them.
    results.append(check_prophosqua_wrapper())

    # Check DEA folders if config exists
    if config:
        phospho_dir = project_dir / config.get("phospho_dea_dir", "")
        protein_dir = project_dir / config.get("protein_dea_dir", "")
        annot_file = project_dir / config.get("annot_file", "")

        results.append(check_dir_exists(phospho_dir, "Phospho DEA folder"))
        results.append(check_dir_exists(protein_dir, "Protein DEA folder"))
        results.append(check_file_exists(annot_file, "Annotation file"))

    # Check commands
    results.append(check_command_exists("snakemake", "Snakemake"))
    results.append(check_command_exists("Rscript", "Rscript"))
    results.append(check_command_exists("uv", "uv"))

    if not quick:
        # Check R packages (slow)
        console.print("[dim]Checking R packages (this may take a moment)...[/dim]")
        r_packages = [
            "tidyverse",
            "readxl",
            "writexl",
            "arrow",
            "prolfquapp",
            "prophosqua",
            "clusterProfiler",
            "ggseqlogo",
        ]
        for pkg in r_packages:
            results.append(check_r_package(pkg))

        # Check kinase-library (slow)
        console.print("[dim]Checking kinase-library access...[/dim]")
        if config and "kinaselib" in config:
            repo = config["kinaselib"].get("repo", "git+https://github.com/wolski/kinase-library")
            results.append(check_uv_tool(repo))

    # Display results
    table = Table(title="Validation Results")
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Details", style="dim")

    critical_failed = False
    for r in results:
        status = "[green]PASS[/green]" if r.passed else "[red]FAIL[/red]"
        table.add_row(r.name, status, r.message)
        if not r.passed and r.name in ["ptm_config.yaml", "Snakefile", "Phospho DEA folder", "Protein DEA folder"]:
            critical_failed = True

    console.print(table)

    passed = sum(1 for r in results if r.passed)
    total = len(results)

    console.print(f"\n[bold]Summary:[/bold] {passed}/{total} checks passed")

    if critical_failed:
        console.print("[red]Critical checks failed. Pipeline cannot run.[/red]")
        return False

    if passed < total:
        console.print("[yellow]Some checks failed. Pipeline may not work correctly.[/yellow]")
        return False

    console.print("[green]All checks passed. Pipeline is ready to run![/green]")
    return True
