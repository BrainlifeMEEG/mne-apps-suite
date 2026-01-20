# app-mean-transformation-matrix

This is a draft of a future Brainlife App using [MNE Python](https://mne.tools/stable/index.html) to compute 
the mean transformation matrix across all runs. 

# app-mean-transformation-matrix documentation

1) Compute the mean tranformation matrix across all runs  
2) Allow to have the same head position across all runs
3) Input files are:
    * a MEG file in `.fif` format corresponding to the first run,
    * a MEG file in `.fif` format corresponding to the second run,
    * an optional MEG file in `.fif` format corresponding to the third run,
    * ...
    * an optional MEG file in `.fif` format corresponding to the n<sup>th</sup> run.
4) Ouput file is a `.fif` file with the mean tranformation matrix in
   `raw.info["dev_head_t"]["trans"]`.
   
### Authors
- [Aurore Bussalb](aurore.bussalb@icm-institute.org)

### Contributors
- [Aurore Bussalb](aurore.bussalb@icm-institute.org)
- [Maximilien Chaumon](maximilien.chaumon@icm-institute.org)
- Christophe Gitton

### Funding Acknowledgement
brainlife.io is publicly funded and for the sustainability of the project it is helpful to Acknowledge the use of the platform. We kindly ask that you acknowledge the funding below in your code and publications. Copy and past the following lines into your repository when using this code.

[![NSF-BCS-1734853](https://img.shields.io/badge/NSF_BCS-1734853-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1734853)
[![NSF-BCS-1636893](https://img.shields.io/badge/NSF_BCS-1636893-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1636893)
[![NSF-ACI-1916518](https://img.shields.io/badge/NSF_ACI-1916518-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1916518)
[![NSF-IIS-1912270](https://img.shields.io/badge/NSF_IIS-1912270-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1912270)
[![NIH-NIBIB-R01EB029272](https://img.shields.io/badge/NIH_NIBIB-R01EB029272-green.svg)](https://grantome.com/grant/NIH/R01-EB029272-01)

### Citations
1. Avesani, P., McPherson, B., Hayashi, S. et al. The open diffusion data derivatives, brain data upcycling via integrated publishing of derivatives and reproducible open cloud services. Sci Data 6, 69 (2019). [https://doi.org/10.1038/s41597-019-0073-y](https://doi.org/10.1038/s41597-019-0073-y)

## Running the App 

### On Brainlife.io

This App has not yet been registered in Brainlife.io.

### Running Locally (on your machine)

1. git clone this repo
2. Inside the cloned directory, create `config.json` with something like the following content with paths to your input 
   files and values of the input parameters (see `config.json.example`).

```json
{
  "fif": [
    "rest1-raw.fif",
    "rest2-raw.fif"
    ]
}
```

3. Launch the App by executing `main`

```bash
./main
```

## Output

The output file is `.fif` file.

