# app-bad-channels

This is a draft of a future Brainlife App that detects bad channels in MEG recordings using [`mne.preprocessing.find_bad_channels_maxwell`](https://mne.tools/stable/generated/mne.preprocessing.maxwell_filter.html#mne.preprocessing.maxwell_filter).

# app-bad-channels documentation

1) Detect bad channels thanks to SSS without removing external components
2) Prevent artifacts in bad channels from spreading when MaxFilter is applied   
3) Input files are:
    * a MEG file in `.fif` format,
    * an optional fine calibration file in `.dat`,
    * an optional crosstalk compensation file in `.fif`,
    * an optional head position file in `.pos`.
4) Input parameters are:
    * `duration`: `float`, duration of the segments into which to slice the data for processing, in seconds. Default is 5.
    * `min_count`: `int`, minimum number of times a channel must show up as bad in a chunk. Default is 5.
    * `limit`: `float`, detection limit for noisy segments. Default is 7.
    * `h_freq`: `float`, optional the cutoff frequency (in Hz) of the low-pass filter that will be applied before processing the data. Default is 40.
    * `int_order`: `int`, order of internal component of spherical expansion. Default is 8.
    * `ext_order`: `int`, order of external component of spherical expansion. Default is 3.
    * `coord_frame`: `str`, the coordinate frame that the origin is specified in, either 'meg' or 'head'. Default is 'head'.
    * `regularize`: `str`, optional, the destination location for the head, either 'in' or `None`. Default is 'in'.
    * `ignore_ref`: `bool`, if `True`, do not include reference channels in compensation. Default is `False`.
    * `bad_condition`: `str`, how to deal with ill-conditioned SSS matrices, either 'error', 'warning', 'info' , 'ignore'. Default is 'error'.
    * `mag_scale`: `float`, the magenetometer scale-factor used to bring the magnetometers to approximately the same order of magnitude as the gradiometers, as they have different units (T vs T/m). Default is 100.
    * `param_skip_by_annotation`, `str` or `list of str`, any annotation segment that begins with the given string will not be included in filtering, and segments on either side of the given excluded annotated segment will be filtered separately.
      Default is `["edge, "bad acq skip"]`.
      
This list along with the parameters' default values correspond to the 0.22.0 version of MNE Python. 

5) Ouput files are:
    * a `.fif` MEG file with bad channels marked as "bad" in its `mne.info`,
    * an `.html` report containing figures.

### Authors
- [Aurore Bussalb](aurore.bussalb@icm-institute.org)

### Contributors
- [Aurore Bussalb](aurore.bussalb@icm-institute.org)
- [Maximilien Chaumon](maximilien.chaumon@icm-institute.org)

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
2. Inside the cloned directory, create `config.json` with something like the following content with paths to your input files (see `config.json.example`)

```json
{
  "fif": "rest1-raw.fif"
}
```

3. Launch the App by executing `main`

```bash
./main
```

## Output

The output file is a MEG file in `.fif` format with its channels detected as "bad" by this App are marked 
as "bad" in `mne.info` and `html` report.
