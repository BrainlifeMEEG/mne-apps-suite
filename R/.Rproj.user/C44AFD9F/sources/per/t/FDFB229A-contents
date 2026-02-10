## create BrainlifeApp.txt


library(tidyverse)

wd <- '/home/maximilien.chaumon/ownCloud/Lab/00-Projects/Brainlife/BRAINLIFE/code/R'
docfile <- 'Documentation.txt'

txt <- readLines(file.path(wd,docfile))


# plot_projs_topomap(ch_type=None, *, sensors=True, show_names=False, contours=6, outlines='head', sphere=None, image_interp='cubic', extrapolate='auto', border='mean', res=64, size=1, cmap=None, vlim=(None, None), cnorm=None, colorbar=False, cbar_fmt='%3.1f', units=None, axes=None, show=True)[source]
fun <- txt[1] %>%
  str_match('[^(]+')

params <- txt[1] %>%  
  str_replace('([^(]+)\\((.*)\\)\\[source\\]','\\2') %>%
  str_split(', (?![^(]*\\))')
  
i <- 3
Description = character()
while (txt[i] != 'Parameters:'){
  Description[length(Description) + 1] = txt[i]
  i <- i+1
}
i <- i+1
params = character()
paramtypes = character()
descs = character()
while (txt[i] != 'Returns:'){
  if (txt[i] == "") {i <- i+1; next}
  tmp = str_match(txt[i], '^    (\\w+)((‘|dict|int|str|bool|float|list|tuple|array|callable|instance of|matplotlib).*)')
  tmp[2]
  params[length(params) + 1] = tmp[2]
  paramtypes[length(paramtypes) + 1] = tmp[3]
  
  i <- i+1
  tmp = character()
  while (str_detect(txt[i], '^ {8}') | txt[i] == "") {
    if (txt[i] == "") {i <- i+1; next}
    if (str_detect(txt[i],'^ +New in version')) {i <- i+1; next}
    if (str_detect(txt[i],'^ +Changed in version')) {i <- i+1; next}
    tmp = c(tmp, str_match(txt[i], '^ {8}(.*)')[2])
    i <- i+1
  }
  descs[length(descs) + 1] = paste(tmp, collapse = '\n')
}
i <- i+1
outputs <- character()
outputtypes <- character()
outputdescs <- character()
while (!is.na(txt[i])){
  if (txt[i] == "") {i <- i+1; next}
  tmp = str_match(txt[i], '^    (\\w+)((‘|int|str|bool|float|list|tuple|array|callable|instance of|matplotlib).*)')
  outputs[length(outputs) + 1] = tmp[2]
  outputtypes[length(outputtypes) + 1] = tmp[3]
  
  i <- i+1
  tmp = character()
  while (str_detect(txt[i], '^ {8}') | txt[i] == "") {
    if (txt[i] == "") {i <- i+1; next}
    if (str_detect(txt[i],'^ +New in version')) {i <- i+1; next}
    if (str_detect(txt[i],'^ +Changed in version')) {i <- i+1; next}
    tmp = c(tmp, str_match(txt[i], '^ {8}(.*)')[2])
    i <- i+1
    if (!is.na(txt[i])) break
  }
  outputdescs[length(outputdescs) + 1] =  paste(tmp, sep = '\n')
}


sink('BrainlifeApp.txt')
cat('Description:\n')
cat('\n')
cat(Description, sep='\n')
cat('\n')
for (ipar in 1:length(params)){
  cat('Key:\n')
  cat('\n')
  cat(params[ipar],sep = '\n')
  cat('\n')
  cat('Desc:\n')
  cat('\n')
  cat('[', paramtypes[ipar], ']')
  cat('  ')
  cat(descs[ipar],sep = '\n')
  cat('\n')
  cat('\n')
}  
for (ipar in 1:length(outputs)){
  cat('Output:\n')
  cat('\n')
  cat(descs[ipar],sep = '\n')
  cat('\n')
  cat('Desc:\n')
  cat('\n')
  cat('[',outputtypes[ipar], ']')
  cat('  ')
  cat(outputdescs[ipar],sep = '\n')
  cat('\n')
}
sink()


sink('README.md')
cat('#', fun)
cat('\n')
cat('Brainlife App to ', Description, '\n')
cat('\n')
cat('# Documentation\n')
cat('\n')
cat('#### Input files are:\n')
cat('* [ADD HERE FILE AND DATATYPE].\n')
cat('\n')
cat('#### Input parameters are:\n')
for (ipar in 1:length(params)){
  cat('* `', params[ipar], '`: ', paramtypes[ipar], ', ', descs[ipar], '\n')
}
cat('\n')
cat('#### Output files/figures are:\n')
cat('* [ADD HERE FILE/FIGURES AND DATATYPE].\n')
cat('\n')
cat('\n')
cat('## Authors:\n')
cat('- [Name](email)\n')
cat('## Contributors:\n')
cat('- [Name](email)\n')

cat('### Funding Acknowledgement
brainlife.io is publicly funded and for the sustainability of the project it is helpful to Acknowledge the use of the platform. We kindly ask that you acknowledge the funding below in your code and publications. Copy and past the following lines into your repository when using this code.

[![NSF-BCS-1734853](https://img.shields.io/badge/NSF_BCS-1734853-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1734853)
[![NSF-BCS-1636893](https://img.shields.io/badge/NSF_BCS-1636893-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1636893)
[![NSF-ACI-1916518](https://img.shields.io/badge/NSF_ACI-1916518-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1916518)
[![NSF-IIS-1912270](https://img.shields.io/badge/NSF_IIS-1912270-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1912270)
[![NIH-NIBIB-R01EB029272](https://img.shields.io/badge/NIH_NIBIB-R01EB029272-green.svg)](https://grantome.com/grant/NIH/R01-EB029272-01)

### Citations
1. Avesani, P., McPherson, B., Hayashi, S. et al. The open diffusion data derivatives, brain data upcycling via integrated publishing of derivatives and reproducible open cloud services. Sci Data 6, 69 (2019). [https://doi.org/10.1038/s41597-019-0073-y](https://doi.org/10.1038/s41597-019-0073-y)
')

