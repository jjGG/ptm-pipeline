#!/usr/bin/env Rscript
#' Prepare kinase-library input files from the combined PTM results
#'
#' Reads the same workbook, sheet and ranking statistic as PTM-SEA and the
#' KinaseLib GSEA, so all enrichment analyses rank the sites identically.
#'
#' Usage: Rscript src/prep_kinaselib.R <xlsx_file> <output_dir> <analysis_type> <sheet> <stat_column>
#'
#' Arguments:
#'   xlsx_file     Path to the combined PTM_results.xlsx
#'   output_dir    Output directory for kinase-library files (e.g., PTM_DPA/KinaseLib)
#'   analysis_type Analysis type: DPA, DPU, or CF (used for output file names)
#'   sheet         Sheet to read (DPA, DPU, or CF)
#'   stat_column   Column to rank the sites on, as declared in ptm_config.yaml
#'
#' Output files:
#'   {analysis_type}_seqwindows.tsv     All unique SequenceWindows (for scan-motifs)
#'   {analysis_type}_MEA_{contrast}.rnk Per-contrast ranked files (for run-mea)
#'
#' @author FGCZ
#' @date 2024-12

suppressPackageStartupMessages({
  library(readxl)
  library(dplyr)
})

# Parse command line arguments
args <- commandArgs(trailingOnly = TRUE)

if (length(args) < 5) {
  stop("Usage: Rscript prep_kinaselib.R <xlsx_file> <output_dir> <analysis_type> <sheet> <stat_column>")
}

xlsx_file <- args[1]
output_dir <- args[2]
analysis_type <- args[3]  # DPA, DPU, or CF
sheet <- args[4]
stat_col <- args[5]

message("=== Preparing kinase-library inputs ===")
message("Input file: ", xlsx_file)
message("Output dir: ", output_dir)
message("Analysis type: ", analysis_type)
message("Ranking on: ", stat_col)

# Read Excel file
message("Reading sheet: ", sheet)
data <- read_xlsx(xlsx_file, sheet = sheet)
message("  Loaded ", nrow(data), " rows")

# Handle flanking column name variations
if (!"SequenceWindow" %in% names(data)) {
  if ("PTM_FlankingRegion" %in% names(data)) {
    data <- data |> rename(SequenceWindow = PTM_FlankingRegion)
    message("  Renamed PTM_FlankingRegion -> SequenceWindow")
  } else {
    stop("No SequenceWindow or PTM_FlankingRegion column found")
  }
}

# Validate statistic column exists (same ranking statistic as PTM-SEA)
if (!stat_col %in% names(data)) {
  stop("Statistic column '", stat_col, "' not found. Available: ",
       paste(head(names(data), 10), collapse = ", "))
}

# Create output directory
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

# Clean sequence windows (remove leading/trailing underscores, filter valid)
data_clean <- data |>
  filter(
    !is.na(SequenceWindow),
    SequenceWindow != "",
    !grepl("^_", SequenceWindow),
    !grepl("_$", SequenceWindow),
    nchar(SequenceWindow) >= 7
  ) |>
  mutate(SequenceWindow = toupper(SequenceWindow))

message("  After filtering: ", nrow(data_clean), " rows with valid SequenceWindow")

# 1. seqwindows.tsv - all unique sequences (for scan-motifs)
seqwindows <- data_clean |>
  select(SequenceWindow) |>
  distinct() |>
  arrange(SequenceWindow)

seqwindows_file <- file.path(output_dir, paste0(analysis_type, "_seqwindows.tsv"))
write.table(seqwindows, seqwindows_file,
            sep = "\t", row.names = FALSE, quote = FALSE)
message("Wrote ", nrow(seqwindows), " unique sequences to: ", seqwindows_file)

# 2. Per-contrast MEA RNK files (for run-mea)
contrasts <- unique(data_clean$contrast)
message("Found ", length(contrasts), " contrasts")

for (ctr in contrasts) {
  ctr_data <- data_clean |>
    filter(contrast == ctr, !is.na(.data[[stat_col]])) |>
    transmute(
      SequenceWindow,
      statistic.site = .data[[stat_col]]
    ) |>
    # Deduplicate: keep row with max absolute statistic per SequenceWindow
    group_by(SequenceWindow) |>
    slice(which.max(abs(statistic.site))) |>
    ungroup() |>
    arrange(desc(statistic.site))

  ctr_clean <- gsub("[^A-Za-z0-9_-]", "_", ctr)
  rnk_file <- file.path(output_dir, paste0(analysis_type, "_MEA_", ctr_clean, ".rnk"))

  write.table(ctr_data, rnk_file,
              sep = "\t", row.names = FALSE, quote = FALSE)
  message("  ", ctr, ": ", nrow(ctr_data), " sites -> ", basename(rnk_file))
}

message("=== Done ===")
