#' Feature Preparation Utilities
#'
#' Pipeline-specific functions for preparing data across analysis templates.
#' Note: filter_significant_sites(), summarize_significant_sites() and
#' prepare_ntoc_data() are now provided by the prophosqua package - use
#' prophosqua::prepare_ntoc_data() etc.

library(dplyr)

#' Validate sequence window by checking central residue
#'
#' Ensures the central amino acid (position 8 in 15-mer) matches the modAA column.
#'
#' @param data Data frame with SequenceWindow and modAA columns
#' @param seq_col Name of sequence window column (default: "SequenceWindow")
#' @param mod_col Name of modified amino acid column (default: "modAA")
#' @param window_center Position of central residue (default: 8 for 15-mer)
#' @return Filtered data frame with only validated sequences
validate_sequence_window <- function(data, seq_col = "SequenceWindow",
                                      mod_col = "modAA", window_center = 8) {
  data |>
    dplyr::mutate(
      .central_aa = toupper(substr(.data[[seq_col]], window_center, window_center))
    ) |>
    dplyr::filter(.central_aa == .data[[mod_col]]) |>
    dplyr::select(-.central_aa)
}
