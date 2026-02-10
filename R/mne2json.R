library(tidyverse)
library(rjson)

# first write parameters in config.json format

dirroot <- "/network/lustre/iss02/cenir/analyse/meeg/BRAINLIFE/code/R"

# onlinedoc won't work because it's expecting a "function" and this is a method...
onlinedoc = 'https://mne.tools/stable/generated/mne.io.Raw.html#mne.io.Raw.filter'

# copy function and parameters into mnefun.txt before running this.

(mnefun <- read_lines(file = file.path(dirroot, 'mnefun.txt')) %>%
  str_split(', ')) 

fun <- mnefun[[1]][1] %>%
  str_replace('(\\w+)\\(.*','\\1')
args <- mnefun[[1]]%>%
  str_replace(paste0(fun,'\\('),'')  %>%
  str_replace('\\)','') %>%
  str_match("\\*.*|(\\w+)=?('?\\w+'?)?")

vals <- args[,3] %>%
  str_replace('None','') %>%
  str_replace_all("'","")
names(vals) <- args[,2]

write(toJSON(vals, indent = 4), file.path(dirroot, 'brainlife.json'))

# then arguments in .py file

nuargs <- character()
for (i in args[,2]) {
  nuargs[i] <- paste0(i, "=config['", i, "'],")
}

write(nuargs,'brainlife.py')

# then documentation in .md file

library(rvest)
page <- read_html(onlinedoc)

fun <- page %>% html_elements(css='dl.py.function') %>%
  html_elements(css = '.field-odd')  

params <- fun %>% html_elements("strong") %>%
  str_replace('<strong>(.*)</strong>','\\1')

cls <- fun %>% html_elements(css = '.classifier') %>%
  html_text() %>%
  str_replace_all('(Raw|Epochs|None|str|list of str|bool|int|float)','`\\1`')

txt <- fun %>% html_elements('dd') %>% html_text() %>%
  str_replace_all('\\n',' ') %>%
  str_replace('New in version [\\d.]+.', '')%>%
  str_replace('.*<p>(.*)</p>.*','\\1') 

paramDoc = '#### Input parameters are:'
for (ipar in 1:length(params)) {
  paramDoc[ipar + 1] = paste0('* `', params[ipar], '`: ', cls[ipar], ' ', txt[ipar])
}
writeLines(paramDoc, 'ParamDoc.md')
# 
# 
# page <- read_html('https://mne.tools/stable/generated/mne.Epochs.html#mne.Epochs.plot_psd')
# 
# 
#   
# val <- NA
# def <- NA
# i <- 1
# while 1 {
#   
#   val[i] <- page %>% html_elements(css=str_c('#mne\\.Epochs\\.plot_psd > em:nth-child(' i ') > span:nth-child(1) > span:nth-child(1)')) %>% html_text()
#   def[i] <- page %>% html_elements(css='#mne\\.Epochs\\.plot_psd > em:nth-child(7) > span:nth-child(3) > span:nth-child(1)') %>% html_text()
# 
# }
# 
