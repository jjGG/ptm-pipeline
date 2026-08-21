"""Project initialization logic."""

from pathlib import Path
import shutil
import subprocess

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table

from .discover import (
    find_all_dea_folders,
    find_annotation_file,
    parse_contrasts,
    get_experiment_name,
)
from .config import generate_config, write_config, config_to_yaml_string


console = Console()


def get_template_dir() -> Path:
    """Get path to template directory from package data."""
    try:
        import ptm_pipeline
        pkg_dir = Path(ptm_pipeline.__file__).parent

        # Prefer the template beside an editable source checkout. A virtual
        # environment may retain an older installed copy under share/.
        template_path = pkg_dir.parent.parent / "template"
        if template_path.exists():
            return template_path

        # Try one level above the normal editable-install layout.
        template_path = pkg_dir.parent.parent.parent / "template"
        if template_path.exists():
            return template_path

        import sys
        if sys.prefix != sys.base_prefix:
            template_path = Path(sys.prefix) / "share" / "ptm-pipeline" / "template"
            if template_path.exists():
                return template_path

    except Exception:
        pass

    raise FileNotFoundError(
        "Could not find template directory. "
        "Make sure the package is installed correctly."
    )


def copy_template_files(project_dir: Path, dry_run: bool = False) -> list[str]:
    """Copy template files to project directory.

    The project gets the workflow and nothing else: Snakefile, helpers.py and
    Makefile, plus the ptm.sh wrapper prophosqua ships. No R code is copied,
    because there is none to copy -- every rule reaches its R script through
    that wrapper, which resolves it from the installed package.

    Returns list of copied file paths (relative to project_dir).
    """
    template_dir = get_template_dir()
    copied_files = []

    # Files to copy at root level
    root_files = ["Snakefile", "helpers.py", "Makefile"]

    for filename in root_files:
        src = template_dir / filename
        dst = project_dir / filename
        if src.exists():
            if not dry_run:
                shutil.copy2(src, dst)
            copied_files.append(filename)

    copied_files.extend(copy_shell_wrapper(project_dir, dry_run=dry_run))
    copied_files.extend(remove_legacy_src(project_dir, dry_run=dry_run))
    copied_files.extend(remove_legacy_wrappers(project_dir, dry_run=dry_run))

    return copied_files


def copy_shell_wrapper(project_dir: Path, dry_run: bool = False) -> list[str]:
    """Place prophosqua's ptm.sh wrapper in the project directory.

    The Snakefile calls the wrapper at its install path, so this copy is for a
    person at a prompt: running ./ptm.sh dpa_dpu by hand is running exactly what
    the pipeline runs, and ./ptm.sh help lists the steps. The wrapper resolves
    both its command list and each command's R script from the installed
    package, so the copy carries no analysis logic and cannot drift.
    """
    if dry_run:
        return ["ptm.sh"]

    result = subprocess.run(
        [
            "Rscript", "--vanilla", "-e",
            "invisible(prophosqua::copy_ptm_shell_script("
            f'{_r_string(str(project_dir))}))',
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        console.print(
            "[yellow]Warning:[/yellow] could not copy the prophosqua ptm.sh "
            "wrapper. The pipeline still runs -- it calls it at its install "
            "path -- but it will not be here to call by hand."
        )
        console.print(f"  {result.stderr.strip().splitlines()[-1:] or ''}")
        return []

    return sorted(p.name for p in project_dir.glob("ptm.sh"))


def remove_legacy_src(project_dir: Path, dry_run: bool = False) -> list[str]:
    """Delete the src/ directory of a project initialised before the move.

    Those files are copies of R code that now lives in prophosqua. Leaving them
    behind would be worse than deleting them: a stale copy of a report template
    invites an edit that no run will ever pick up.
    """
    legacy = project_dir / "src"
    if not legacy.is_dir():
        return []

    if not dry_run:
        shutil.rmtree(legacy)
    console.print(
        f"  {'Would remove' if dry_run else 'Removed'} src/ -- "
        "its R code now lives in the prophosqua package."
    )
    return []


def remove_legacy_wrappers(project_dir: Path, dry_run: bool = False) -> list[str]:
    """Delete the per-command ptm_<name>.sh wrappers of an older project.

    They have been replaced by one ptm.sh taking the command as its first
    argument. A left-behind ptm_ptmsea.sh would still run -- it resolves its
    script from the installed package like everything else -- until the day
    prophosqua stops shipping the script it names, at which point it fails with
    a missing file rather than saying it is obsolete.
    """
    legacy = sorted(project_dir.glob("ptm_*.sh"))
    if not legacy:
        return []

    for wrapper in legacy:
        if not dry_run:
            wrapper.unlink()
    console.print(
        f"  {'Would remove' if dry_run else 'Removed'} {len(legacy)} "
        "per-command ptm_*.sh wrapper(s) -- replaced by ptm.sh <command>."
    )
    return []


def _r_string(value: str) -> str:
    """Quote a path for interpolation into an R expression."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def init_project(
    project_dir: Path,
    input_dir: Path | None = None,
    name: str | None = None,
    dry_run: bool = False,
    force: bool = False,
    default: bool = False,
) -> bool:
    """Initialize PTM pipeline in project directory.

    Args:
        project_dir: Path to project directory (where pipeline files are written)
        input_dir: Path to directory containing DEA folders (defaults to project_dir)
        name: Optional experiment name (auto-detected if not provided)
        dry_run: If True, only show what would be done
        force: If True, overwrite existing files
        default: If True, use defaults for all prompts (non-interactive)

    Returns:
        True if initialization was successful
    """
    project_dir = project_dir.resolve()
    input_dir = input_dir.resolve() if input_dir else project_dir

    console.print(f"\n[bold]Initializing PTM pipeline in:[/bold] {project_dir}")
    if input_dir != project_dir:
        console.print(f"[bold]Discovering DEA folders in:[/bold] {input_dir}")
    console.print()

    # Check if already initialized
    config_file = project_dir / "ptm_config.yaml"
    snakefile = project_dir / "Snakefile"

    if (config_file.exists() or snakefile.exists()) and not force and not default:
        console.print(
            "[yellow]Warning:[/yellow] Pipeline files already exist. "
            "Use --force to overwrite."
        )
        if not Confirm.ask("Continue anyway?"):
            return False

    # Discover DEA folders
    console.print("[bold]Discovering DEA folders...[/bold]")
    all_folders = find_all_dea_folders(input_dir)

    if not all_folders["phospho"]:
        console.print("[red]Error:[/red] No phospho DEA folder found")
        console.print("  Expected patterns: DEA_*_WUphospho_*, DEA_*_WUcombined_*, DEA_*_*STY*")
        return False

    if not all_folders["protein"]:
        console.print("[red]Error:[/red] No protein DEA folder found (DEA_*_WUprot_* or DEA_*_WUtotal_*)")
        return False

    # Select folders if multiple found
    phospho_dir = all_folders["phospho"][0]
    protein_dir = all_folders["protein"][0]

    if len(all_folders["phospho"]) > 1 and not default:
        console.print("\n[yellow]Multiple phospho DEA folders found:[/yellow]")
        for i, d in enumerate(all_folders["phospho"]):
            console.print(f"  {i + 1}. {d.name}")
        choice = Prompt.ask(
            "Select folder",
            choices=[str(i + 1) for i in range(len(all_folders["phospho"]))],
            default="1"
        )
        phospho_dir = all_folders["phospho"][int(choice) - 1]

    if len(all_folders["protein"]) > 1 and not default:
        console.print("\n[yellow]Multiple protein DEA folders found:[/yellow]")
        for i, d in enumerate(all_folders["protein"]):
            console.print(f"  {i + 1}. {d.name}")
        choice = Prompt.ask(
            "Select folder",
            choices=[str(i + 1) for i in range(len(all_folders["protein"]))],
            default="1"
        )
        protein_dir = all_folders["protein"][int(choice) - 1]

    # Show selected folders
    table = Table(title="Selected DEA Folders")
    table.add_column("Type", style="cyan")
    table.add_column("Folder", style="green")
    table.add_row("Phospho", phospho_dir.name)
    table.add_row("Protein", protein_dir.name)
    console.print(table)

    # Find annotation file
    console.print("\n[bold]Looking for annotation file...[/bold]")
    annot_file = find_annotation_file(phospho_dir)

    if not annot_file:
        console.print("[red]Error:[/red] No annotation file found in phospho DEA folder")
        console.print("  Expected: Inputs_*/*_annot_*.tsv or Inputs_*/*_dataset*.tsv")
        return False

    console.print(f"  Found: {annot_file.relative_to(input_dir)}")

    # Parse contrasts
    console.print("\n[bold]Parsing contrasts...[/bold]")
    contrasts = parse_contrasts(annot_file)

    if not contrasts:
        console.print("[yellow]Warning:[/yellow] No contrasts found in annotation file")
        contrasts = ["contrast1"]  # Placeholder
    else:
        console.print(f"  Found {len(contrasts)} contrast(s):")
        for c in contrasts:
            console.print(f"    - {c}")

    # Get experiment name - suggest first contrast as default
    if not name:
        if contrasts and contrasts[0] != "contrast1":
            default_name = contrasts[0]
        else:
            default_name = get_experiment_name(phospho_dir)
        if default:
            name = default_name
            console.print(f"\n[bold]Experiment name:[/bold] {name}")
        else:
            console.print(f"\n[bold]Suggested experiment name:[/bold] {default_name}")
            name = Prompt.ask("Experiment name", default=default_name)

    # Get significance thresholds
    if default:
        fdr = 0.25
        log2fc = 0.5
    else:
        console.print("\n[bold]Significance thresholds for downstream analyses:[/bold]")
        fdr = float(Prompt.ask("FDR threshold", default="0.25"))
        log2fc = float(Prompt.ask("log2FC threshold", default="0.5"))

    # Analysis options
    if default:
        max_fig = 10
        run_kinase = True
    else:
        console.print("\n[bold]Analysis options:[/bold]")
        max_fig = int(Prompt.ask("Max n-to-c plots per analysis", default="10"))
        run_kinase = Confirm.ask("Run kinase activity analysis?", default=True)

    # Generate config
    console.print("\n[bold]Generating configuration...[/bold]")
    config = generate_config(
        phospho_dir=phospho_dir,
        protein_dir=protein_dir,
        annot_file=annot_file,
        contrasts=contrasts,
        output_name=name,
        project_dir=project_dir,
        fdr=fdr,
        log2fc=log2fc,
        max_fig=max_fig,
        run_kinase=run_kinase,
    )

    if dry_run:
        console.print("\n[yellow]Dry run - ptm_config.yaml would contain:[/yellow]")
        console.print(Panel(config_to_yaml_string(config), title="ptm_config.yaml"))
    else:
        write_config(config, config_file)
        console.print(f"  Written: ptm_config.yaml")

    # Copy template files
    console.print("\n[bold]Copying pipeline files...[/bold]")

    try:
        copied = copy_template_files(project_dir, dry_run=dry_run)
        for f in copied[:5]:  # Show first 5
            console.print(f"  {'Would copy' if dry_run else 'Copied'}: {f}")
        if len(copied) > 5:
            console.print(f"  ... and {len(copied) - 5} more files")
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        return False

    # Success message
    console.print("\n" + "=" * 60)
    if dry_run:
        console.print("[yellow]Dry run complete.[/yellow] No files were modified.")
    else:
        console.print("[green]Pipeline initialized successfully![/green]")
        console.print("\nNext steps:")
        console.print(f"  1. Review ptm_config.yaml")
        console.print(f"  2. Run: make all")

    return True
