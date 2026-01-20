#!/usr/local/bin/python3

import mne
import json
import warnings
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import random


def find_bad_channels(raw, cross_talk_file, calibration_file, head_pos_file, param_h_freq, param_limit,
                      param_duration, param_min_count, param_int_order, param_ext_order, param_coord_frame,
                      param_regularize, param_ignore_ref, param_bad_condition, param_skip_by_annotation,
                      param_mag_scale):
    """Detect bad channels and save file with bad channels marked as bad in raw.info.

    Parameters
    ----------
    raw: instance of mne.io.Raw
        Data to be filtered.
    cross_talk_file: str or None
        Path to the FIF file with cross-talk correction information.
    calibration_file: str or None
        Path to the '.dat' file with fine calibration coefficients. This file is machine/site-specific.
    head_pos_file: array or None
        If array, movement compensation will be performed.
    param_h_freq: float or None
        The cutoff frequency (in Hz) of the low-pass filter that will be applied before processing the data. 
        This defaults to 40., which should provide similar results to MaxFilter. 
    param_limit: float
        Detection limit for noisy segments (default is 7.). Smaller values will find more bad channels at increased risk of including good ones.
    param_duration: float
        Duration of the segments into which to slice the data for processing, in seconds. Default is 5.
    param_min_count: int
        Minimum number of times a channel must show up as bad in a chunk. Default is 5.
    param_int_order: int
        Order of internal component of spherical expansion.
    param_ext_order: int
        Order of external component of spherical expansion.
    param_coord_frame: str
        The coordinate frame that the origin is specified in, either 'meg' or 'head'.
    param_regularize: str or None
        Basis regularization type, must be “in” or None.
    param_ignore_ref: bool
        If True, do not include reference channels in compensation.
    param_bad_condition: str
        How to deal with ill-conditioned SSS matrices. Can be “error” (default), “warning”, “info”, or “ignore”.
    param_skip_by_annotation: str or list of str
        If a string (or list of str), any annotation segment that begins with the given string will not be included in
        filtering, and segments on either side of the given excluded annotated segment will be filtered separately.
    param_mag_scale: float
        The magenetometer scale-factor used to bring the magnetometers to approximately the same order of magnitude as
        the gradiometers (default 100.), as they have different units (T vs T/m).

    Returns
    -------
    raw: instance of mne.io.Raw
        The raw data with bad channels marked as "bad" in info.
    noisy_chs: list
        List of bad MEG channels that were automatically detected as being noisy among the good MEG channels.
    flat_chs: list
        List of MEG channels that were detected as being flat in at least min_count segments.
    scores: dict
        A dictionary with information produced by the scoring algorithms
    """

    # Find bad channels
    raw_check = raw.copy()
    auto_noisy_chs, auto_flat_chs, auto_scores = mne.preprocessing.find_bad_channels_maxwell(raw_check,
                                                                                             cross_talk=cross_talk_file,
                                                                                             calibration=calibration_file,
                                                                                             head_pos=head_pos_file,
                                                                                             return_scores=True,
                                                                                             h_freq=param_h_freq,
                                                                                             limit=param_limit,
                                                                                             duration=param_duration,
                                                                                             min_count=param_min_count,
                                                                                             int_order=param_int_order,
                                                                                             ext_order=param_ext_order,
                                                                                             coord_frame=param_coord_frame,
                                                                                             regularize=param_regularize,
                                                                                             ignore_ref=param_ignore_ref,
                                                                                             bad_condition=param_bad_condition,
                                                                                             skip_by_annotation=param_skip_by_annotation,
                                                                                             mag_scale=param_mag_scale)

    del raw_check

    # Add bad channels in raw.info
    bads = raw.info['bads'] + auto_noisy_chs + auto_flat_chs
    raw.info['bads'] = bads

    # Save file
    raw.save("out_dir_bad_channels/bad_channels-raw.fif", overwrite=True)

    return raw, auto_noisy_chs, auto_flat_chs, auto_scores


def _generate_report(raw_before_preprocessing, raw_after_preprocessing, auto_scores, auto_noisy_chs, auto_flat_chs,
                     data_file_before):
    # Generate a report

    # Instance of mne.Report
    report = mne.Report(title='Results identification of bad channels', verbose=True)

    # Plot diagnostic figures

    # Scores for automated noisy channels detection
    # Only select the data for gradiometer channels
    ch_type = 'grad'
    ch_subset = auto_scores['ch_types'] == ch_type
    ch_names = auto_scores['ch_names'][ch_subset]
    scores = auto_scores['scores_noisy'][ch_subset]
    limits = auto_scores['limits_noisy'][ch_subset]
    bins = auto_scores['bins']  # The windows that were evaluated
    # We will label each segment by its start and stop time, with up to 3
    # digits before and 3 digits after the decimal place (1 ms precision).
    bin_labels = [f'{start:3.3f} – {stop:3.3f}'
                  for start, stop in bins]

    # Store the data in a Pandas DataFrame. The seaborn heatmap function
    # we will call below will then be able to automatically assign the correct
    # labels to all axes.
    data_to_plot = pd.DataFrame(data=scores,
                                columns=pd.Index(bin_labels, name='Time (s)'),
                                index=pd.Index(ch_names, name='Channel'))

    # Plot the "raw" scores
    fig_noisy, ax = plt.subplots(1, 2, figsize=(18, 16))
    sns.heatmap(data=data_to_plot, cmap='Reds', cbar_kws=dict(label='Score'),
                ax=ax[0])
    [ax[0].axvline(x, ls='dashed', lw=0.25, dashes=(25, 15), color='gray')
        for x in range(1, len(bins))]
    ax[0].set_title('All Scores', fontweight='bold')

    # Adjust the color range to highlight segments that exceeded the limit
    sns.heatmap(data=data_to_plot,
                vmin=np.nanmin(limits),  # bads in input data have NaN limits
                cmap='Reds', cbar_kws=dict(label='Score'), ax=ax[1])
    [ax[1].axvline(x, ls='dashed', lw=0.25, dashes=(25, 15), color='gray')
        for x in range(1, len(bins))]
    ax[1].set_title('Scores > Limit', fontweight='bold')

    # Add figures to report
    report.add_figs_to_section(fig_noisy, captions=f'Automated noisy channel detection: {ch_type}',
                               comments=f'Noisy channels detected (grad and mag): {auto_noisy_chs}',
                               section='Diagnostic figures')

    # Scores for automated flat channels detection
    # Only select the data for gradiometer channels
    scores = auto_scores['scores_flat'][ch_subset]
    limits = auto_scores['limits_flat'][ch_subset]

    # Store the data in a Pandas DataFrame
    data_to_plot = pd.DataFrame(data=scores,
                                columns=pd.Index(bin_labels, name='Time (s)'),
                                index=pd.Index(ch_names, name='Channel'))

    # Plot the "raw" scores
    fig_flat, ax = plt.subplots(1, 2, figsize=(18, 16))
    sns.heatmap(data=data_to_plot, cmap='Reds', cbar_kws=dict(label='Score'),
                ax=ax[0])
    [ax[0].axvline(x, ls='dashed', lw=0.25, dashes=(25, 15), color='gray')
        for x in range(1, len(bins))]
    ax[0].set_title('All Scores', fontweight='bold')

    # Adjust the color range to highlight segments that are below the limit
    sns.heatmap(data=data_to_plot,
                vmax=np.nanmax(limits),  # bads in input data have NaN limits
                cmap='Reds_r', cbar_kws=dict(label='Score'), ax=ax[1])
    [ax[1].axvline(x, ls='dashed', lw=0.25, dashes=(25, 15), color='gray')
        for x in range(1, len(bins))]
    ax[1].set_title('Scores < Limit', fontweight='bold')

    # Add figures to report
    report.add_figs_to_section(fig_flat, captions=f'Automated flat channel detection: {ch_type}',
                               comments=f'Flat channels detected (grad and mag): {auto_flat_chs}',
                               section='Diagnostic figures')

    # If they exist, plot bad channels in time domain
    # Noisy channels
    if auto_noisy_chs:

        # Select random grad channels to plot including the noisy ones
        ch_to_plot = random.sample(ch_names.tolist(), 49)
        ch_to_plot += auto_noisy_chs
        raw_ch_to_plot = raw_after_preprocessing.copy()

        # Plot channels in time domain
        raw_ch_to_plot.pick_channels(ch_to_plot)
        fig_raw_noisy_channels = raw_ch_to_plot.plot(duration=20, n_channels=50, scalings='auto', butterfly=False,
                                                     show_scrollbars=False)
        del raw_ch_to_plot

        report.add_figs_to_section(fig_raw_noisy_channels, captions=f'MEG signals including automated '
                                                                    f'detected noisy channels',
                                   comments='The noisy channels are in gray.', section='Time domain')

    # Flat channels
    if auto_flat_chs:
        # Select random grad channels to plot including the flat ones
        ch_to_plot = random.sample(ch_names.tolist(), 49)
        ch_to_plot += auto_flat_chs
        raw_ch_to_plot = raw_after_preprocessing.copy()

        # Plot channels in time domain
        raw_ch_to_plot.pick_channels(ch_to_plot)
        fig_raw_flat_channels = raw_ch_to_plot.plot(duration=20, n_channels=50, scalings='auto', butterfly=False,
                                                    show_scrollbars=False)
        del raw_ch_to_plot

        report.add_figs_to_section(fig_raw_flat_channels, captions=f'MEG signals including automated '
                                                                   f'detected flat channels',
                                   comments='The flat channels are in gray.', section='Time domain')

    # Plot PSD of all channels including bads
    raw_before_preprocessing.pick_types(meg=True)
    raw_after_preprocessing.pick_types(meg=True)
    bads = auto_flat_chs + auto_noisy_chs
    channels = raw_after_preprocessing.info['ch_names']
    all_channels = bads + channels
    fig_raw_psd_all_before = mne.viz.plot_raw_psd(raw_before_preprocessing, picks=all_channels)

    # Plot PSD of all channels excluding bads
    fig_raw_psd_all_after = mne.viz.plot_raw_psd(raw_after_preprocessing, picks='meg')

    # Add figures to report
    captions_fig_raw_psd_all_before = f'Power spectral density of MEG signals including the automated ' \
                                      f'detected noisy channels'
    captions_fig_raw_psd_all_after = f'Power spectral density of grad signals without the automated ' \
                                     f'detected noisy channels'
    report.add_figs_to_section(figs=[fig_raw_psd_all_before, fig_raw_psd_all_after],
                               captions=[captions_fig_raw_psd_all_before, captions_fig_raw_psd_all_after],
                               section='Power Spectral Density')

    # Give some info about the file before preprocessing
    bad_channels = raw_before_preprocessing.info['bads']
    sampling_frequency = raw_before_preprocessing.info['sfreq']
    highpass = raw_before_preprocessing.info['highpass']
    lowpass = raw_before_preprocessing.info['lowpass']

    # Put this info in html format
    # Info on data
    html_text_info = f"""<html>

    <head>
        <style type="text/css">
            table {{ border-collapse: collapse;}}
            td {{ text-align: center; border: 1px solid #000000; border-style: dashed; font-size: 15px; }}
        </style>
    </head>

    <body>
        <table width="50%" height="80%" border="2px">
            <tr>
                <td>Input file: {data_file_before}</td>
            </tr>
            <tr>
                <td>Bad channels before automated detection: {bad_channels}</td>
            </tr>
            <tr>
                <td>Sampling frequency: {sampling_frequency}Hz</td>
            </tr>
            <tr>
                <td>Highpass: {highpass}Hz</td>
            </tr>
            <tr>
                <td>Lowpass: {lowpass}Hz</td>
            </tr>
        </table>
    </body>

    </html>"""

    # Add html to reports
    report.add_htmls_to_section(html_text_info, captions='MEG recording features', section='Info', replace=False)

    # Save report
    report.save('out_dir_report/report_bad_channels.html', overwrite=True)


def main():

    # Generate a json.product to display messages on Brainlife UI
    dict_json_product = {'brainlife': []}

    # Load inputs from config.json
    with open('config.json') as config_json:
        config = json.load(config_json)

    # Read the raw file
    data_file = (config.pop('fif'))
    raw = mne.io.read_raw_fif(data_file, allow_maxshield=True)

    # Read the calibration files
    if 'cross_talk_correction' in config.keys():
        cross_talk_file = config.pop('cross_talk_correction')
    else:
        cross_talk_file = None

    if 'calibration' in config.keys():
        calibration_file = config.pop('calibration')
    else:
        calibration_file = None

    # Head pos file
    if 'head_position' in config.keys():
        head_pos_file = config.pop('head_position')
        if head_pos_file is not None:  # when App is run locally and "head_position": null in config.json
            head_pos_file = mne.chpi.read_head_pos(head_pos_file)
    else:
        head_pos_file = None

    # Warning if h_freq is None
    h_freq_param = config['param_h_freq']
    if h_freq_param is None:
        user_warning_message = f'No low-pass filter will be applied to the data. ' \
                               f'Make sure line noise and cHPI artifacts were removed before finding ' \
                               f'bad channels.'
        warnings.warn(user_warning_message)
        dict_json_product['brainlife'].append({'type': 'warning', 'msg': user_warning_message})

    raw_copy = raw.copy()
    raw_bad_channels, auto_noisy_chs, auto_flat_chs, auto_scores = find_bad_channels(raw_copy, cross_talk_file,
                                                                                     calibration_file,
                                                                                     head_pos_file, h_freq_param,
                                                                                     config['param_limit'],
                                                                                     config['param_duration'],
                                                                                     config['param_min_count'],
                                                                                     config['param_int_order'],
                                                                                     config['param_ext_order'],
                                                                                     config['param_coord_frame'],
                                                                                     config['param_regularize'],
                                                                                     config['param_ignore_ref'],
                                                                                     config['param_bad_condition'],
                                                                                     config['param_skip_by_annotation'],
                                                                                     config['param_mag_scale'])

    # Success message in product.json
    dict_json_product['brainlife'].append({'type': 'success', 'msg': 'Bad channels were successfully detected.'})

    # Info message in product.json
    dict_json_product['brainlife'].append({'type': 'info', 'msg': f'This algorithm is not fully reliable. '
                                                                  f"Don't hesitate to check all of the signals visually "
                                                                  f"before performing an another preprocessing step."})

    # Generate report
    _generate_report(raw, raw_bad_channels, auto_scores, auto_noisy_chs, auto_flat_chs, data_file)

    # Save the dict_json_product in a json file
    with open('product.json', 'w') as outfile:
        json.dump(dict_json_product, outfile)


if __name__ == '__main__':
    main()

