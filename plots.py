import os
import numpy as np
import glob
import pickle
import matplotlib.pyplot as plt
import matplotlib
import plotly.graph_objects as go
import utils
from drive import get_file_by_id

#important for text to be detected when importing saved figures into illustrator
matplotlib.rcParams['pdf.fonttype']=42
matplotlib.rcParams['ps.fonttype']=42
plt.rcParams["font.family"] = "Arial"

# method options are 'single', 'f2a', 'root_dir'
def define_params(fs = 5, opto_blank_frame = False, num_rois = 10, selected_conditions = None, flag_normalization = "dff_perc", fsignal = "VJ_OFCVTA_7_260_D6_neuropil_corrected_signals_15_50_beta_0.8.csv", fevents="event_times_VJ_OFCVTA_7_260_D6_trained.csv"):
    
    fparams = {}
    
    fparams['fname_signal'] = fsignal   # 
    fparams['fname_events'] = fevents # can set to None if you want to plot the signals only
    # fdir signifies to the root path of the data. Currently, the abspath phrase points to sample data from the repo.
    # To specify a path that is on your local computer, use this string format: r'your_root_path', where you should copy/paste
    # your path between the single quotes (important to keep the r to render as a complete raw string). See example below:
    # r'C:\Users\stuberadmin\Documents\GitHub\NAPE_imaging_postprocess\napeca_post\sample_data' 
    fparams['fdir'] = os.path.abspath('./sample_data/') 
    fparams['fname'] = os.path.split(fparams['fdir'])[1]

    # set the sampling rate
    fparams['fs'] = fs

    # session info
    fparams['opto_blank_frame'] = opto_blank_frame # if PMTs were blanked during stim, set stim times to nan (instead of 0)
    
    # analysis and plotting arguments
    fparams['num_rois'] = num_rois # set to 'all' if want to show all cells
    fparams['selected_conditions'] = selected_conditions # set to None if want to include all conditions from behav data
    fparams['flag_normalization'] = flag_normalization # options: 'dff', 'zscore', 'dff_perc', None

    return fparams

# functions to normalize traces
def calc_dff_percentile(activity_vec, perc=25):
    perc_activity = np.percentile(activity_vec, perc)
    return (activity_vec-perc_activity)/perc_activity

def calc_zscore(activity_vec, baseline_samples):
    mean_baseline = np.nanmean(data[..., baseline_samples])
    std_baseline = np.nanstd(data[..., baseline_samples])
    return (data-mean_baseline)/std_baseline

def generateGraphTab2(fparams, file_ids):
    cond_colors = ['steelblue', 'crimson', 'orchid', 'gold']

    # load time-series data
    signals = utils.load_signals(file_ids[0])
        
    if fparams['opto_blank_frame']:
        try:
            glob_stim_files = glob.glob(os.path.join(fparams['fdir'], "{}*_stimmed_frames.pkl".format(fparams['fname'])))
            stim_frames = pickle.load( open( glob_stim_files[0], "rb" ) )
            signals[:,stim_frames['samples']] = None # blank out stimmed frames
            flag_stim = True
            print('Detected stim data; replaced stim samples with NaNs')
        except:
            flag_stim = False
            print('Note: No stim preprocessed meta data detected.')

    if fparams['flag_normalization'] == 'dff':
        signal_to_plot = np.apply_along_axis(utils.calc_dff, 1, signals)
    elif fparams['flag_normalization'] == 'dff_perc':
        signal_to_plot = np.apply_along_axis(calc_dff_percentile, 1, signals)
    elif fparams['flag_normalization'] == 'zscore':
        signal_to_plot = np.apply_along_axis(calc_zscore, 1, signals, np.arange(0, signals.shape[1]))
    else:
        signal_to_plot = signals

    min_max = [list(min_max_tup) for min_max_tup in zip(np.min(signal_to_plot,axis=1), np.max(signal_to_plot,axis=1))]
    min_max_all = [np.min(signal_to_plot), np.max(signal_to_plot)]

    if fparams['num_rois'] == 'all':
        fparams['num_rois'] = signals.shape[0]

    total_session_time = signals.shape[1]/fparams['fs']
    tvec = np.round(np.linspace(0, total_session_time, signals.shape[1]), 2)

    #load behavioral data and trial info
    if fparams['fname_events']:
        event_times = utils.df_to_dict(file_ids[1])
        event_frames = utils.dict_time_to_samples(event_times, fparams['fs'])

        event_times = {}
        if fparams['selected_conditions']:
            conditions = fparams['selected_conditions'] 
        else:
            conditions = event_frames.keys()
        for cond in conditions: # convert event samples to time in seconds
                event_times[cond] = (np.array(event_frames[cond])/fparams['fs']).astype('int')
    
    # Create figure
    fig = go.Figure()

    # Add traces, one for each slider step
    for idx_roi in np.arange(fparams['num_rois']):
        fig.add_trace(
            go.Scatter(
                visible=False,
                name='Activity',
                line=dict(color="green", width=1.5),
                x=tvec,
                y=signal_to_plot[idx_roi,:]))

    if fparams['fname_events']:
        # add vertical lines for events 
        for idx_cond, cond in enumerate(conditions):
            for idx_ev, event in enumerate(event_times[cond]):
                # 2nd case used to hide trace duplicates in legend
                if idx_ev==0:
                    fig.add_trace(go.Scatter(x=[event,event],y=[min_max_all[0],min_max_all[1]], visible=True,  
                        mode='lines', 
                        line=dict(color=cond_colors[idx_cond], width=1.5, dash='dash'), showlegend=True, 
                        legendgroup=cond,
                        name='{}'.format(cond)))
                else:
                    fig.add_trace(go.Scatter(x=[event,event], y=[min_max_all[0],min_max_all[1]], visible=True,
                        mode='lines',  
                        showlegend=False, legendgroup=cond,
                        line=dict(color=cond_colors[idx_cond], width=1.5, dash='dash'),
                        name='{} {}'.format(cond, str(idx_ev))))
        

    # make a list of attributes for slider steps
    steps = []
    for iroi in np.arange(fparams['num_rois']): 
        # when ever slider changes, set all roi's to be invisible and all event lines as visible
        step = dict(
            method="restyle",
            # layout attributes
            args=[{"visible": ([False] * fparams['num_rois']) + [True] * (len(fig.data)- fparams['num_rois'])},
                {"title": "Viewing ROI " + str(iroi)},
                ])
        # then make the selected ROI visible
        step["args"][0]["visible"][iroi] = True  # Toggle i'th trace to "visible"
        steps.append(step)

    # create and setup slider 
    sliders = [dict(
        active=0,
        currentvalue={"prefix": "Viewing "},
        pad={"t": 50},
        steps=steps
    )]

    fig.update_layout(
        xaxis_title="Time (s)",
        yaxis_title="Fluorescence ({})".format(fparams['flag_normalization']),
        legend_title="Legend Title",
        font=dict(
            size=12),
        sliders=sliders,
        showlegend=True,
        legend_title_text='Legend',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    # rename slider ticks
    for idx in np.arange(fparams['num_rois']):
        fig['layout']['sliders'][0]['steps'][idx]['label']='ROI ' + str(idx)

    # Make 1st trace visible
    fig.data[0].visible = True

    # Change grid color and axis colors
    fig.update_xaxes(showline=True, linewidth=1.5, linecolor='black')
    fig.update_yaxes(showline=True, linewidth=1.5, linecolor='black')

    return fig