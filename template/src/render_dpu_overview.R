#!/usr/bin/env Rscript
#' Render DPU Overview Report
#'
#' This script renders the prophosqua integration overview document
#' for DPU (Differential PTM Usage) results.
#'
#' Usage:
#'   Rscript render_dpu_overview.R <combined_test_diff.rds> <output_dir> [project_id] [work_unit_id]
#'
#' Arguments:
#'   combined_test_diff.rds - RDS file containing combined test diff data
#'   output_dir            - Directory for output HTML
#'   project_id            - Optional project identifier (default: "PTM_analysis")
#'   work_unit_id          - Optional work unit ID (default: "DPU_Integration")

suppressPackageStartupMessages({
  library(prolfquapp)
  library(prophosqua)
})

args <- commandArgs(trailingOnly = TRUE)

if (length(args) < 2) {
  stop("Usage: Rscript render_dpu_overview.R <combined_test_diff.rds> <output_dir> [project_id] [work_unit_id]")
}

input_rds <- args[1]
output_dir <- args[2]
project_id <- if (length(args) >= 3) args[3] else "PTM_analysis"
work_unit_id <- if (length(args) >= 4) args[4] else "DPU_Integration"

# Validate input
if (!file.exists(input_rds)) {
  stop("Input RDS file not found: ", input_rds)
}

# Create output directory
if (!dir.exists(output_dir)) {
  dir.create(output_dir, recursive = TRUE)
}

# Load combined test diff data
message("Loading data from: ", input_rds)
combined_test_diff <- readRDS(input_rds)

# Create DEA config
drumm <- prolfquapp::make_DEA_config_R6(
  PROJECTID = project_id,
  ORDERID = "fgcz_project",
  WORKUNITID = work_unit_id
)

# Copy the template and its bibliography into a private render directory.
# Rendering in the working directory would leave both files in the project root
# and let two concurrent renders overwrite each other's knitr intermediates,
# which are named after the input .Rmd. tempdir() is private to this R process
# and is removed when it exits.
render_dir <- file.path(tempdir(), "dpu_overview")
dir.create(render_dir, recursive = TRUE, showWarnings = FALSE)

integration_files <- c(
  "application/_Overview_PhosphoAndIntegration_site.Rmd",
  "application/bibliography2025.bib"
)
for (file in integration_files) {
  src <- system.file(file, package = "prophosqua", mustWork = FALSE)
  if (!nzchar(src) || !file.exists(src)) {
    stop("prophosqua integration file not found: ", file, call. = FALSE)
  }
  file.copy(src, file.path(render_dir, basename(file)), overwrite = TRUE)
}

# Render the overview document. knit_root_dir keeps the chunks running in the
# project directory, as they did when the template was rendered in place.
message("Rendering DPU overview report...")
rmarkdown::render(
  file.path(render_dir, "_Overview_PhosphoAndIntegration_site.Rmd"),
  knit_root_dir = getwd(),
  params = list(
    data = combined_test_diff,
    grp = drumm
  ),
  output_format = bookdown::html_document2(
    toc = TRUE,
    toc_float = TRUE
  ),
  envir = new.env(parent = globalenv())
)

# Move output to target location
output_file <- file.path(output_dir, "Result_DPU.html")
file.copy(
  from = file.path(render_dir, "_Overview_PhosphoAndIntegration_site.html"),
  to = output_file,
  overwrite = TRUE
)

message("DPU overview report saved to: ", output_file)
