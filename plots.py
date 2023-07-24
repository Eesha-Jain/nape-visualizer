import os
import numpy as np
import glob
import pickle
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import utils
import random

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

def generate_graph_tab2(fparams, file_ids):
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
        sliders=sliders,
        showlegend=True,
        legend_title_text='Legend',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=40)
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

def define_paths_roi_plots(file_ids, path_dict, tseries_start_end, rois_to_plot):

    path_dict['tseries_start_end'] = tseries_start_end
    path_dict['rois_to_plot'] = rois_to_plot
    path_dict['s2p_F_path'] = utils.get_contents(file_ids["f"])
    path_dict['s2p_Fneu_path'] = utils.get_contents(file_ids["fneu"])
    path_dict['s2p_iscell_path'] = utils.get_contents(file_ids["iscell"])
    path_dict['s2p_ops_path'] = utils.get_contents(file_ids["ops"])
    path_dict['s2p_stat_path'] = utils.get_contents(file_ids["stat"])
    path_dict['s2p_spks_path'] = utils.get_contents(file_ids["spks"])
    
    return path_dict

# Takes the path information from path_dict and uses it to load and save the files
# they direct towards


def load_s2p_data_roi_plots(path_dict):
    
    s2p_data_dict = {}
    # load s2p data
    s2p_data_dict['F'] = np.load(path_dict['s2p_F_path'], allow_pickle=True)
    s2p_data_dict['Fneu'] = np.load(path_dict['s2p_Fneu_path'], allow_pickle=True)
    s2p_data_dict['iscell'] = np.load(path_dict['s2p_iscell_path'], allow_pickle=True)
    s2p_data_dict['ops'] = np.load(path_dict['s2p_ops_path'], allow_pickle=True).item()
    s2p_data_dict['stat'] = np.load(path_dict['s2p_stat_path'], allow_pickle=True)

    s2p_data_dict['F_npil_corr'] = s2p_data_dict['F'] - s2p_data_dict['ops']['neucoeff'] * s2p_data_dict['Fneu']

    s2p_data_dict['F_npil_corr_dff'] = np.apply_along_axis(utils.calc_dff, 1, s2p_data_dict['F_npil_corr'])

    return s2p_data_dict

#initializes variables for roi plots
def prep_plotting_rois(s2p_data_dict, path_dict): 
    max_rois_tseries = 10
    plot_vars = {}
    plot_vars['cell_ids'] = np.where( s2p_data_dict['iscell'][:,0] == 1 )[0] # indices of user-curated cells referencing all ROIs detected by s2p
    plot_vars['num_total_rois'] = len(plot_vars['cell_ids'])
    
    # determine if only a subset of cells tseries are to be plotted
    if isinstance(path_dict['rois_to_plot'], list): # if user supplied ROIs
        plot_vars['rois_to_tseries'] = path_dict['rois_to_plot']
        plot_vars['num_rois_to_tseries'] = len(plot_vars['rois_to_tseries'])
    elif plot_vars['num_total_rois'] > max_rois_tseries: # if too many cells to visualize tseries, randomly sample from cells
        plot_vars['rois_to_tseries'] = sorted(random.sample(plot_vars['cell_ids'].tolist(), max_rois_tseries))
        plot_vars['num_rois_to_tseries'] = len(plot_vars['rois_to_tseries'])
    else:
        plot_vars['rois_to_tseries'] = plot_vars['cell_ids']
        plot_vars['num_rois_to_tseries'] = plot_vars['num_total_rois'] 
        
    return plot_vars

# initialize templates for contour map
def masks_init(plot_vars, s2p_data_dict):
    num_rois_to_tseries = plot_vars['num_rois_to_tseries']

    plot_vars['colors_roi'] = [f'rgb{tuple(np.round(np.array(c[:3]) * 254).astype(int))}' for c in plt.cm.viridis(np.linspace(0, 1, num_rois_to_tseries))]
    plot_vars['s2p_masks'] = np.empty([plot_vars['num_total_rois'], s2p_data_dict['ops']['Ly'], s2p_data_dict['ops']['Lx']])
    plot_vars['roi_centroids'] = np.empty([plot_vars['num_total_rois'], 2])

    # loop through ROIs and add their spatial footprints to template
    for idx, roi_id in enumerate(plot_vars['cell_ids']):

        zero_template = np.zeros([s2p_data_dict['ops']['Ly'], s2p_data_dict['ops']['Lx']])
        zero_template[ s2p_data_dict['stat'][roi_id]['ypix'], s2p_data_dict['stat'][roi_id]['xpix'] ] = 1
        plot_vars['s2p_masks'][idx,...] = zero_template

        plot_vars['roi_centroids'][idx,...] = [np.min(s2p_data_dict['stat'][roi_id]['ypix']), np.min(s2p_data_dict['stat'][roi_id]['xpix'])]

        if idx == plot_vars['num_total_rois'] - 1:
            break

    return plot_vars

# plot contours and cell numbers on projection image
def contour_plot_tab1(s2p_data_dict, path_dict, plot_vars, show_labels_=True, cmap_scale_ratio=1):
    if 'threshold_scaling_value' in path_dict:
        tsv = path_dict['threshold_scaling_value']

    to_plot = s2p_data_dict['ops']['meanImg']

    fig = go.Figure()

    # Add the image as a heatmap trace
    heatmap_trace = go.Heatmap(z=to_plot,
                               colorscale='gray',
                               zmin=np.min(to_plot) * (1.0 / cmap_scale_ratio),
                               zmax=np.max(to_plot) * (1.0 / cmap_scale_ratio),
                               showscale=False)  # Set showscale to False to hide the colorbar
    fig.add_trace(heatmap_trace)

    # Create a scatter trace for each contour
    for idx, roi_id in enumerate(plot_vars['cell_ids']):
        if roi_id in plot_vars['rois_to_tseries']:
            this_roi_color = plot_vars['colors_roi'][idx]
        else:
            this_roi_color = 'grey'

        # Find the contour points for this ROI
        contours = np.where(plot_vars['s2p_masks'][idx] > 0)

        # Create scatter trace with mode 'lines' to draw contour lines
        contour_trace = go.Scatter(x=contours[1],
                                   y=contours[0],
                                   mode='lines',
                                   line=dict(color=this_roi_color))
        fig.add_trace(contour_trace)

        # Add the ROI label
        if show_labels_ and roi_id in plot_vars['rois_to_tseries']:
            fig.add_annotation(text=str(roi_id),
                               x=plot_vars['roi_centroids'][idx][1] - 1,
                               y=plot_vars['roi_centroids'][idx][0] - 1,
                               font=dict(family="Arial", size=18, color=this_roi_color),
                               showarrow=False)

    # Remove axis ticks and labels
    fig.update_xaxes(showticklabels=False)
    fig.update_yaxes(showticklabels=False)

    # Adjust margins and size
    fig.update_layout(margin=dict(l=10, b=10, t=30), font=dict(family="Arial", size=18))

    return fig

# initialize variables for plotting time-series
def time_series_plot_tab1(s2p_data_dict, path_dict, plot_vars):
    if 'threshold_scaling_value' in path_dict:
        tsv = path_dict['threshold_scaling_value']

    fs = s2p_data_dict['ops']['fs']
    num_samps = s2p_data_dict['ops']['nframes']
    total_time = num_samps / fs
    tvec = np.linspace(0, total_time, num_samps)

    # F_npil_corr_dff contains all s2p-detected cells
    trace_data_selected = s2p_data_dict['F_npil_corr_dff'][plot_vars['rois_to_tseries']]

    # Cut data and tvec to start/end if user defined
    if path_dict['tseries_start_end']:
        sample_start = utils.get_tvec_sample(tvec, path_dict['tseries_start_end'][0])
        sample_end = utils.get_tvec_sample(tvec, path_dict['tseries_start_end'][1])
        tvec = tvec[sample_start:sample_end]
        trace_data_selected = trace_data_selected[:, sample_start:sample_end]

    # Create a list of traces for each ROI
    traces = []
    for idx in range(plot_vars['num_rois_to_tseries']):
        to_plot = trace_data_selected[idx]
        roi_trace = go.Scatter(x=tvec, y=to_plot, mode='lines', line=dict(color=plot_vars['colors_roi'][idx]))
        traces.append(roi_trace)

    # Create the figure
    fig = go.Figure(data=traces)
    # Update layout
    fig.update_layout(
        margin=dict(t=40),
        xaxis_title="Time (s)",
        yaxis_title="Fluorescence Level",
        showlegend=False,
        font=dict(family="Arial", size=15),
        height=54  # Set the height to 54 pixels
    )

    # Add titles to each subplot
    for idx in range(plot_vars['num_rois_to_tseries']):
        fig.update_layout(title=f"ROI {plot_vars['rois_to_tseries'][idx]}", yaxis=dict(domain=[idx * 0.2, (idx + 1) * 0.2]))

    return fig

def heatmap_plot_tab1(s2p_data_dict, path_dict, plot_vars):
    if 'threshold_scaling_value' in path_dict:
        tsv = path_dict['threshold_scaling_value']

    fs = s2p_data_dict['ops']['fs']
    num_samps = s2p_data_dict['ops']['nframes']
    total_time = num_samps / fs
    tvec = np.linspace(0, total_time, num_samps)

    # F_npil_corr_dff contains all s2p-detected cells; cell_ids references those indices
    trace_data_selected = s2p_data_dict['F_npil_corr_dff'][plot_vars['cell_ids']]

    # Cut data and tvec to start/end if user defined
    if path_dict['tseries_start_end']:
        sample_start = utils.get_tvec_sample(tvec, path_dict['tseries_start_end'][0])
        sample_end = utils.get_tvec_sample(tvec, path_dict['tseries_start_end'][1])
        tvec = tvec[sample_start:sample_end]
        trace_data_selected = trace_data_selected[:, sample_start:sample_end]

    # Create a heatmap trace
    trace = go.Heatmap(z=trace_data_selected, x=tvec, y=plot_vars['cell_ids'])

    # Create the figure
    fig = go.Figure(data=trace)

    # Update layout
    fig.update_layout(
        margin=dict(l=60, b=50, t=40),
        xaxis_title="Time (s)",
        yaxis_title="ROI",
        font=dict(family="Arial", size=15)
    )

    return fig