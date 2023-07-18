import os
import json
import pickle
import h5py
import numpy as np
import glob
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.preprocessing import StandardScaler
import seaborn as sns
from matplotlib.colors import ListedColormap
import warnings


def open_json(json_fpath):
    with open(json_fpath) as json_file:
        return json.load(json_file)


def zscore_(data, baseline_samples):
    scaler = StandardScaler()

    # note: have to reshape/transpose so that samples is in first dimension for scikitlearn
    if len(data.shape) == 1:
        scaler.fit(data[baseline_samples].reshape(-1, 1))
        scaled_data = scaler.transform(data.reshape(-1, 1))
    else:
        scaler.fit(data[..., baseline_samples].T)
        scaled_data = scaler.transform(data.T).T
    return scaled_data


def check_exist_dir(path):
    if not os.path.exists(path):
        os.mkdir(path)
    return path

##### LOADING FUNCTIONS

def load_h5(fpath):
    data_h5file = h5py.File(fpath, 'r')
    # load a snippit of data and get rid of un-needed singleton dimensions
    data_snip = np.squeeze(np.array(data_h5file['imaging'], dtype=int))

    """ typically it's good to have time as the last dimension because one doesn't usually iterate through time, so we'll
     reorganize the data dimension order"""
    return data_snip.transpose(1, 2, 0)


def load_signals(fpath):
    ### load and prepare time-series data
    glob_signal_files = glob.glob(fpath)
    _, fext = os.path.splitext(glob_signal_files[0])
    if len(glob_signal_files) == 0:
        print('Warning: No or signal files detected; please check your fname and fdir')
    if 'npy' in fext:
        signals = np.squeeze(np.load(glob_signal_files[0]))
    elif 'csv' in fext:
        df_signals = pd.read_csv(glob_signal_files[0], header=None)
        if 'Time(s)/Cell Status' in df_signals.values:
            # for inscopix data, drop first two rows and first column, and transpose
            signals = np.transpose(df_signals.drop([0,1], axis=0).iloc[:, 1:].values.astype(np.float32))
        else:
            signals = df_signals.values

    return signals

##### PLOTTING FUNCTIONS

def plot_single_img(to_plot, frame_num):
    plt.figure(figsize=(7, 7))
    plt.imshow(to_plot, cmap='gray')
    plt.title('Frame {}'.format(frame_num), fontsize=20)
    plt.axis('off')


def subplot_heatmap(axs, title, image, cmap=None, clims=None, zoom_window=None, extent_=None):
    """
        Takes in a numpy 2d array and a subplot location, and plots a heatmap at the subplot location without axes

        Parameters
        ----------
        axs : matplotlib AxesSubplot object
            Specific subplot from the ax output of pyplot.subplots()

        title : string
            Title name of the plot

        image : numpy 2d array

        cmap : string or colormap
            Colormap desired; default is seismic

        Optional Parameters
        -------------------

        clims : list
            List with entries: [minimum_colorbar_limit, maximum_colorbar_limit] . This is for setting the color ranges
            for the heatmap

        zoom_window : list
            List with entries: [xmin, xmax, ymin, ymax] . This is for zooming into the specific window dictated by the
            x min and max, and y min and max locations

        Returns
        -------
        im : ndarray
            imshow AxesImage object. Used to reference the dataset for a colorbar (eg. fig.colorbar(im) )

        """

    if len(image.shape) == 1:
        warnings.warn("Your data only has one trial!")
        image = image[np.newaxis, ...]

    if cmap is None:
        cmap = ListedColormap(sns.color_palette("RdBu_r", 100))
    im = axs.imshow(image, cmap, extent=extent_)
    axs.set_title(title, fontsize=15)

    if zoom_window is not None:
        axs.axis(zoom_window)
        axs.invert_yaxis()

    if clims is not None:
        im.set_clim(vmin=clims[0], vmax=clims[1])
    axs.set_aspect('auto')
    # axs.axis('off')

    return im  # for colorbar


def dict_key_len(dict_, key):
    return len(dict_[key])


###### DATA PROCESSING FUNCTIONS


def make_tile(start, end, num_rep):
    """
    Makes indices for tiles.

    Parameters
    ----------
    start_end : int
        List with two items where first int is start sample relative to trial onset.
        Second int is end sample relative to trial onset.

    num_rep : int
        Number of times to repeat the sample vector in the y axis

    Returns
    -------
    tile_array : ndarray
        Array with shape (num_rep, samples), where samples is number of samples between
        the items in start_end input

    """

    samp_vec = np.arange(start, end + 1)  # grab all samples between start/end

    tile_array = np.tile(samp_vec, (num_rep, 1))

    return tile_array


def remove_trials_out_of_bounds(data_end, these_frame_events, start_samp, end_samp):

    """

    :param data_end: int
        total number of samples in recording

    :param these_frame_events: list
        entries of list are samples/frames for the event start

    :param start_samp: int
        trial window start index relative to the beginning of the trial (eg. -5 if you want the trial start to be 5
        samples before event onset. In other words, if the sampling rate is 5 hz, -5 would be
        1 second before trial onset.)

    :param end_samp: int
        trial window end index relative to the beginning of the trial (similar to start_samp)

    :return:
    """

    after_start_bool = (these_frame_events + start_samp) > start_samp
    before_end_bool = (these_frame_events + end_samp) < data_end

    keep_events = []
    for idx, item in enumerate(after_start_bool*before_end_bool):
        if item:
            keep_events.append(these_frame_events[idx])

    return np.array(keep_events)


def extract_trial_data(data, tvec, start_end_samp, frame_events, conditions, baseline_start_end_samp=None, save_dir=None):
    """
        Takes a 3d video (across a whole session) and cuts out trials based on event times.
        Also groups trial data by condition

        Parameters
        ----------
        save_dir : string
            full path of folder where extracted trial data pickle file will be saved

        data : numpy 3d array
            3d video data where dimensions are (y_pixel, x_pixel, samples)

        tvec : numpy 1d vector
            vector containing times in seconds for each sample within the trial. Just saved in pickle dict for downstream analysis

        start_end_samp : 2-element list
            Element 0: Number of samples before the event onset for trial start
            Element 1: Number of samples after the event onset for trial end

        frame_events : dictionary of np 1d arrays (vectors)
            Dictionary where keys are the conditions in the session and values are numpy 1d vectors that contain
            event occurrences as samples

        conditions : list of strings
            Each entry in the list is a condition to extract trials from; must correspond to keys in frame_events

        Optional Parameters
        -------------------

        baseline_start_end_samp : 2-element list
            Element 0: Number of samples relative to the event onset for baseline epoch start
            Element 1: Number of samples relative the event onset for baseline epoch end
            NOTE: including this variable will generate a z-scored data variable

        Returns
        -------
        data_dict : dictionary
            1st level of dict keys: individual conditions
                2nd level of keys :
                    data : numpy 4d array with dimensions (trials,y,x,samples)
                    num_samples : number of samples (time) in a trial
                    num_trials : total number of trials in the condition

        """

    # create sample vector for baseline epoch if argument exists (for zscoring)
    if baseline_start_end_samp is not None:
        baseline_svec = (np.arange(baseline_start_end_samp[0], baseline_start_end_samp[1] + 1, 1) -
                         baseline_start_end_samp[0]).astype('int')

    data_dict = {}

    for idx, condition in enumerate(conditions):

        data_dict[condition] = {}

        # get rid of trials that are outside of the session bounds with respect to time
        data_end_sample = data.shape[-1]
        cond_frame_events = remove_trials_out_of_bounds(data_end_sample, frame_events[condition], start_end_samp[0], start_end_samp[1])

        # convert window time bounds to samples and make a trial sample vector
        # make an array where the sample indices are repeated in the y axis for n number of trials
        num_trials_cond = len(cond_frame_events)
        if num_trials_cond == 1:
            svec_tile = np.arange(start_end_samp[0], start_end_samp[1] + 1) # just make a 1D vector for svec
            num_trial_samps = len(svec_tile)
        else:
            svec_tile = make_tile(start_end_samp[0], start_end_samp[1], num_trials_cond)
            num_trial_samps = svec_tile.shape[1]

        if num_trials_cond > 0:

            # now make a repeated matrix of each trial's ttl on sample in the x dimension
            ttl_repmat = np.repeat(cond_frame_events[:, np.newaxis], num_trial_samps, axis=1).astype('int')
            # calculate actual trial sample indices by adding the TTL onset repeated matrix and the trial window template
            trial_sample_mat = np.round(ttl_repmat + svec_tile).astype('int')

            # extract frames in trials and reshape the data to be: y,x,trials,samples
            # basically unpacking the last 2 dimensions
            reshape_dim = data.shape[:-1] + (svec_tile.shape)
            extracted_trial_dat = data[..., np.ndarray.flatten(trial_sample_mat)].reshape(reshape_dim)

            # reorder dimensions and put trial as first dim; resulting dims will be [trial, roi, samples]
            # or [trial, y, x, samples]
            if num_trials_cond > 1:
                if len(extracted_trial_dat.shape) :
                    data_dict[condition]['data'] = extracted_trial_dat.transpose((1, 0, 2))
                elif len(extracted_trial_dat.shape) == 4:
                    data_dict[condition]['data'] = extracted_trial_dat.transpose((2, 0, 1, 3))
            else: # dimension order is correct since there's no reshaping done
                data_dict[condition]['data'] = np.expand_dims(extracted_trial_dat, axis=0)

            # save normalized data
            if baseline_start_end_samp is not None:
                # input data dimensions should be (trials, ROI, samples)
                data_dict[condition]['zdata'] = np.squeeze(np.apply_along_axis(zscore_, -1,
                                                                                          data_dict[condition]['data'],
                                                                                          baseline_svec), axis=-1)

            # also save trial-averaged (if there are multiple trials) and z-scored data
            if num_trials_cond > 1: # if more than one trial
                data_dict[condition]['trial_avg_data'] = np.nanmean(data_dict[condition]['data'], axis=0)

                if baseline_start_end_samp is not None:
                    # this can take a while to compute
                    data_dict[condition]['ztrial_avg_data'] = np.squeeze(np.nanmean(data_dict[condition]['zdata'], axis=0))
            else:
                # if there's only one trial, just zscore the raw data
                if baseline_start_end_samp is not None:
                    data_dict[condition]['ztrial_avg_data'] = np.squeeze(np.apply_along_axis(zscore_, -1,
                                                                                              data_dict[condition]['data'],
                                                                                              baseline_svec))

        # save some meta data
        data_dict[condition]['num_samples'] = num_trial_samps
        data_dict[condition]['num_trials'] = num_trials_cond
        data_dict[condition]['tvec'] = tvec

        if save_dir:
            with open(os.path.join(save_dir, 'event_data_dict.pkl'), 'wb') as save_handle:
                pickle.dump(data_dict, save_handle)

    return data_dict


def get_tvec_sample(tvec, time):
    return np.argmin(abs(tvec - time))


def time_to_samples(trial_tvec, analysis_window):
    """

    Parameters
    ----------
    trial_tvec : np 1d vector
        Vector of times in seconds that correspond to the samples in the data

    analysis_window : np 1d vector , entries are floats
        First entry is the window start time in seconds, second entry is the window end time
        in seconds.

    Returns
    -------
    analysis_svec : np 1d vector
        Vector of samples that are the corresponding samples in the trial_tvec between the start and end times

    """
    win_start_end_samp = []
    for window_bounds in analysis_window:
        win_start_end_samp.append(get_tvec_sample(trial_tvec, window_bounds))

    analysis_svec = np.arange(win_start_end_samp[0], win_start_end_samp[1])

    return analysis_svec


def calc_dff(activity_vec):
    """
    Needs to be used with: np.apply_along_axis(calc_dff, 1, roi_signal_sima)
    Alternatively one can apply np.vstack(np.mean(data, axis=1)) onto whole array without needing to apply to each row
    """
    mean_act = np.nanmean(activity_vec)
    return (activity_vec-mean_act)/mean_act


def dict_time_to_samples(dict_in, fs):
    """
    For a dictionary containing lists of times, converts all list entries to frames/samples
    """
    for cond in dict_in:
        dict_in[cond] = [int(entry*fs) for entry in dict_in[cond]]
    return dict_in


def df_to_dict(fpath):
    """
    Turns a csv containing events names (column 0) and frame samples (column 1) into a dictionary where keys are event names
    and values are lists containing each event's frame samples
    """

    event_frames_dict = {}
    event_frames_df = pd.read_csv(fpath)
    for condition in event_frames_df['event'].unique():
        event_frames_dict[condition] = list(event_frames_df[event_frames_df['event'] == condition]['time'])
    return event_frames_dict