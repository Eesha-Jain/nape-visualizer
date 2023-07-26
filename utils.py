import json
import numpy as np
import pandas as pd
from drive import get_file_by_id
import io

def load_signals(file_id):
    file_obj = get_file_by_id(file_id)

    file_obj.seek(0)
    file_content = file_obj.read()
    csv_string = file_content.decode('utf-8')

    fext = file_obj.content_type

    if 'npy' in fext:
        signals = np.squeeze(np.load(file_obj))
    elif 'csv' in fext:
        df_signals = pd.read_csv(io.StringIO(csv_string), header=None)
        if 'Time(s)/Cell Status' in df_signals.values:
            # for inscopix data, drop first two rows and first column, and transpose
            signals = np.transpose(df_signals.drop([0,1], axis=0).iloc[:, 1:].values.astype(np.float32))
        else:
            signals = df_signals.values

    return signals

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


def df_to_dict(file_id):
    """
    Turns a csv containing events names (column 0) and frame samples (column 1) into a dictionary where keys are event names
    and values are lists containing each event's frame samples
    """

    file_obj = get_file_by_id(file_id)

    file_obj.seek(0)
    file_content = file_obj.read()
    csv_string = file_content.decode('utf-8')

    event_frames_dict = {}
    event_frames_df = pd.read_csv(io.StringIO(csv_string))

    for condition in event_frames_df['event'].unique():
        event_frames_dict[condition] = list(event_frames_df[event_frames_df['event'] == condition]['time'])
    return event_frames_dict

def get_contents(file_id):
    file_obj = get_file_by_id(file_id)
    file_obj.seek(0)
    file_content = file_obj.read()
    return io.BytesIO(file_content)

def open_json(json_fpath):
    with open(json_fpath) as json_file:
        return json.load(json_file)

def get_tvec_sample(tvec, time):
    return np.argmin(abs(tvec - time))