#!/usr/bin/env Rscript
# combine_ptm_results.R
# Combines DPA, DPU, CF results into standardized multi-sheet Excel and RDS
#
# Usage:
#   Rscript combine_ptm_results.R \
#     dpa.xlsx dpu.xlsx cf.xlsx \
#     protein.parquet site.parquet \
#     output.xlsx output.rds

suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(readxl)
  library(writexl)
  library(arrow)
})

#' Standardize PTM results based on analysis type
#'
#' Config-driven standardization that handles column renaming for DPA, DPU, and CF.
#'
#' @param data Data frame with PTM results
#' @param analysis_type One of "dpa", "dpu", or "cf"
#' @return Standardized data frame
standardize_results <- function(data, analysis_type) {
  analysis_type <- tolower(analysis_type)

  # Column configuration for each analysis type
  # DPA and CF now export diff.site, FDR.site, statistic.site directly.
  # DPU still uses diff_diff, FDR_I, tstatistic_I (from prophosqua::test_diff).
  configs <- list(
    dpa = list(
      rename = c(gene_name = "gene_name.site"),
      direct_cols = c("protein_Id", "site", "contrast", "posInProtein", "modAA",
                      "SequenceWindow", "protein_length", "diff.site", "FDR.site",
                      "statistic.site", "diff.protein", "FDR.protein", "statistic.protein",
                      "estimate_type.site", "estimate_type.protein")
    ),
    dpu = list(
      rename = c(gene_name = "gene_name.site", diff.site = "diff_diff",
                 FDR.site = "FDR_I", statistic.site = "tstatistic_I"),
      direct_cols = c("protein_Id", "site", "contrast", "posInProtein", "modAA",
                      "SequenceWindow", "protein_length",
                      "estimate_type.site", "estimate_type.protein")
    ),
    cf = list(
      # CF has a single estimate per site, exported unsuffixed as estimate_type
      rename = c(estimate_type.site = "estimate_type"),
      direct_cols = c("protein_Id", "site", "contrast", "posInProtein", "modAA",
                      "SequenceWindow", "gene_name", "protein_length",
                      "diff.site", "FDR.site", "statistic.site")
    )
  )

  if (!analysis_type %in% names(configs)) {
    stop("Unknown analysis_type: ", analysis_type, ". Must be one of: dpa, dpu, cf")
  }

  config <- configs[[analysis_type]]

  # Build select specification: direct cols + renamed cols
  # Use select() with renaming to avoid duplicate column issues
  select_spec <- c(
    setNames(config$direct_cols, config$direct_cols),  # direct: col = col
    config$rename                                       # renamed: new_name = old_name
  )

  # Only select columns that exist in data
  existing <- select_spec[select_spec %in% names(data)]
  data |> dplyr::select(!!!existing)
}

# Backward compatibility wrappers
standardize_dpa <- function(data) standardize_results(data, "dpa")
standardize_dpu <- function(data) standardize_results(data, "dpu")
standardize_cf <- function(data) standardize_results(data, "cf")

#' Combine all PTM results into standardized format
#'
#' @param dpa_xlsx Path to DPA Excel file (Result_DPA.xlsx)
#' @param dpu_xlsx Path to DPU Excel file (Result_DPU.xlsx)
#' @param cf_xlsx Path to CF Excel file (CorrectFirst_PTM_usage_results.xlsx)
#' @param protein_parquet Path to normalized protein abundances parquet
#' @param site_parquet Path to normalized site abundances parquet
#' @param output_xlsx Output Excel file path
#' @param output_rds Output RDS file path
#' @return Invisibly returns the result list
combine_ptm_results <- function(dpa_xlsx, dpu_xlsx, cf_xlsx,
                                 protein_parquet, site_parquet,
                                 output_xlsx, output_rds) {

  message("Loading DPA results from: ", dpa_xlsx)
  dpa_raw <- readxl::read_xlsx(dpa_xlsx, sheet = "combinedSiteProteinData")

  message("Loading DPU results from: ", dpu_xlsx)
  dpu_raw <- readxl::read_xlsx(dpu_xlsx, sheet = "combinedStats")

  message("Loading CF results from: ", cf_xlsx)
  cf_raw <- readxl::read_xlsx(cf_xlsx, sheet = "results")

  # Standardize contrast results
  message("Standardizing column names...")
  dpa <- standardize_dpa(dpa_raw)
  dpu <- standardize_dpu(dpu_raw)
  cf <- standardize_cf(cf_raw)

  message("  DPA: ", nrow(dpa), " rows")
  message("  DPU: ", nrow(dpu), " rows")
  message("  CF:  ", nrow(cf), " rows")

  # Load normalized abundances
  message("Loading protein abundances from: ", protein_parquet)
  protein_abund <- arrow::read_parquet(protein_parquet) |>
    canonicalize_dea_sample_column(
      file.path(dirname(protein_parquet), "lfqdata.yaml")
    ) |>
    dplyr::filter(!grepl("^rev_", protein_Id)) |>
    canonicalize_uniprot_ids() |>
    dplyr::select(Name, protein_Id, normalized_abundance) |>
    tidyr::pivot_wider(names_from = Name, values_from = normalized_abundance)

  message("Loading site abundances from: ", site_parquet)
  site_raw <- arrow::read_parquet(site_parquet) |>
    canonicalize_dea_sample_column(
      file.path(dirname(site_parquet), "lfqdata.yaml")
    )

  # Get site column name (may be 'site' or 'protein_Id_site')
  site_col <- if ("site" %in% colnames(site_raw)) "site" else "protein_Id_site"

  site_abund_dpa <- site_raw |>
    dplyr::select(Name, site = !!sym(site_col), protein_Id, normalized_abundance) |>
    tidyr::pivot_wider(names_from = Name, values_from = normalized_abundance)

  # CF abundances (protein-corrected) - join site with protein, subtract
  message("Computing corrected abundances for CF...")

  # Read parquet again to get long format for joining
  site_long <- arrow::read_parquet(site_parquet) |>
    canonicalize_dea_sample_column(
      file.path(dirname(site_parquet), "lfqdata.yaml")
    ) |>
    dplyr::select(Name, site = !!sym(site_col), protein_Id, site_abund = normalized_abundance)

  protein_long <- arrow::read_parquet(protein_parquet) |>
    canonicalize_dea_sample_column(
      file.path(dirname(protein_parquet), "lfqdata.yaml")
    ) |>
    dplyr::filter(!grepl("^rev_", protein_Id)) |>
    canonicalize_uniprot_ids() |>
    dplyr::select(Name, protein_Id, protein_abund = normalized_abundance)

  site_abund_cf <- site_long |>
    dplyr::inner_join(protein_long, by = c("Name", "protein_Id")) |>
    dplyr::mutate(corrected_abundance = site_abund - protein_abund) |>
    dplyr::select(Name, site, corrected_abundance) |>
    tidyr::pivot_wider(names_from = Name, values_from = corrected_abundance)

  message("  Protein abundances: ", nrow(protein_abund), " proteins x ", ncol(protein_abund) - 1, " samples")
  message("  Site abundances (DPA): ", nrow(site_abund_dpa), " sites x ", ncol(site_abund_dpa) - 2, " samples")
  message("  Site abundances (CF): ", nrow(site_abund_cf), " sites x ", ncol(site_abund_cf) - 1, " samples")

  # Create list for output
  result_list <- list(
    DPA = dpa,
    DPU = dpu,
    CF = cf,
    abundances_protein = protein_abund,
    abundances_site_dpa = site_abund_dpa,
    abundances_site_cf = site_abund_cf
  )

  # Write outputs
  message("Writing Excel to: ", output_xlsx)
  writexl::write_xlsx(result_list, output_xlsx)

  message("Writing RDS to: ", output_rds)
  saveRDS(result_list, output_rds)

  message("Done!")
  invisible(result_list)
}

# CLI interface
if (!interactive()) {
  args <- commandArgs(trailingOnly = TRUE)

  if (length(args) < 8) {
    cat("Usage: Rscript combine_ptm_results.R <dpa.xlsx> <dpu.xlsx> <cf.xlsx>",
        "<protein.parquet> <site.parquet> <output.xlsx> <output.rds>",
        "<dea_utils.R>\n")
    quit(status = 1)
  }

  source(args[8])

  combine_ptm_results(
    dpa_xlsx = args[1],
    dpu_xlsx = args[2],
    cf_xlsx = args[3],
    protein_parquet = args[4],
    site_parquet = args[5],
    output_xlsx = args[6],
    output_rds = args[7]
  )
}
