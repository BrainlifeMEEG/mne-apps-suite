# a R script that will read 

library(tidyverse)

fs <- list( '/network/iss/cenir/analyse/meeg/BRAINLIFE/Analysis_Sheets/logs_Latinus_aggregate/T1_AnalysisSheet_aggregated.csv',
            '/network/iss/cenir/analyse/meeg/BRAINLIFE/Analysis_Sheets/logs_Latinus_aggregate/T2_AnalysisSheet_aggregated.csv')
out_dir <- '/network/iss/cenir/analyse/meeg/BRAINLIFE/code/local_scripts/AggregatedTrialDrop'
if (!dir.exists(out_dir)) {
  dir.create(out_dir)
}
for (f in fs) { 
  # read each line of f
  d <- read_lines(f) %>%
    str_split(pattern = ' ?, ?')
  # on each element of d, first element is Suj, second is Task, third is Pass. Pop these out of the original list
  Suj <- map(d, ~ .x[1])
  Task <- map(d, ~ .x[2])
  Pass <- map(d, ~ .x[3]) %>%
    str_remove(pattern = ' ')
  # remove the first three elements of each list element
  d <- map(d, ~ .x[-(1:3)])
 
  for (i in 1:length(d)) {
    write_lines(d[[i]],file.path(out_dir,paste0(Suj[[i]], '_', Task[[i]], '_', Pass[[i]], '.txt')), sep = ',')
    }
}

# add the same for 
fs <- list('/network/iss/cenir/analyse/meeg/BRAINLIFE/datasets/Latinus Data/logs_Latinus_aggregate/T1_AnalysisSheet_bad_channels_aggregated.csv',
           '/network/iss/cenir/analyse/meeg/BRAINLIFE/datasets/Latinus Data/logs_Latinus_aggregate/T2_AnalysisSheet_bad_channels_aggregated.csv')

out_dir <- '/network/iss/cenir/analyse/meeg/BRAINLIFE/code/local_scripts/AggregatedChannelDrop'
if (!dir.exists(out_dir)) {
  dir.create(out_dir)
}
for (f in fs) { 
  # read each line of f
  d <- read_lines(f) %>%
    # remove single quotes
    str_remove_all(pattern = "'") %>%
    str_split(pattern = ' ?, ?')
  # on each element of d, first element is Suj, second is Task, third is Pass. Pop these out of the original list
  Suj <- map(d, ~ .x[1])
  Task <- map(d, ~ .x[2])
  # remove the first two elements of each list element
  d <- map(d, ~ .x[-(1:2)])
  for (i in 1:length(d)) {
    print(Suj[[i]])
    print(d[[i]])
    write_lines(d[[i]],file.path(out_dir,paste0(Suj[[i]], '_', Task[[i]], '.txt')), sep = ',')
  }
}
