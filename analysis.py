from drive import upload_to_drive, delete_folder, get_contents_bytefile, get_contents_string
from visualizer.data import ROITraceProcessor, WholeSessionProcessor, EventRelAnalysisProcessor, EventClusterProcessor
from visualizer.plots import S2PROITracePlot, WholeSessionPlot, EventRelAnalysisPlot, EventClusterPlot
from abc import ABC, abstractmethod
from io import BytesIO
import base64
import numpy as np

def checkbox_input(value):
    return True if value else False

def none_or_input(value):
    return None if value == "None" else value

def none_or_stringarray_input(value):
    if value == "None":
        return None
    elif len(value.split(",")) > 1:
        return value.split(",")
    else:
        return [value]
    
def none_or_intarray_input(value):
    if value == "None":
        return None
    elif len(value.split(",")) > 1:
        split_array = value.split(",")
        return [int(item) for item in split_array]
    else:
        return [int(value)]

def get_encoded(chart):
    buf = BytesIO()
    chart.savefig(buf, format="png", bbox_inches='tight', pad_inches=0)
    return base64.b64encode(buf.getbuffer()).decode("ascii")

def upload_inputted_files(request, file_names, file_extension):
    files = []
    try:
        #append each requested file to array
        for file_name in file_names:
            file = request.files[file_name]

            if not file:
                raise Exception()
            
            files.append(file)
    except Exception as e:
        #if file is None, then search for file within uploaded folder
        folder = request.files.getlist('folder')
        files_dict = {}

        for file in folder:
            if file:
                filename = file.filename.lower().split("/")
                files_dict[filename[len(filename) - 1]] = file
        
        for i in range(len(file_names)):
            file = files_dict[file_names[i] + file_extension]
            files.append(file)
    
    #Upload files to Google Drive
    file_ids, folder_id = upload_to_drive(files)

    #Return dictionary with file_names
    file_ids_dict = {}

    for i, file_name in enumerate(file_names):
        file_ids_dict[file_name] = file_ids[i]

    return folder_id, file_ids_dict

class Photon2(ABC):
    def __init__(self, request, file_ids_dict, folder_id):
        self.request = request
        self.file_ids_dict = file_ids_dict
        self.folder_id = folder_id
    
    @abstractmethod
    def generate_params(self):
        pass

    @abstractmethod
    def get_contents(self):
        pass

    @abstractmethod
    def generate_plots(self):
        pass

    @abstractmethod
    def generate_full_output(self):
        pass
    
class Photon2Tab1(Photon2):
    def __init__(self, request, file_ids_dict, folder_id):
        super().__init__(request, file_ids_dict, folder_id)

    def generate_params(self):
        self.fparams = {
            "tseries_start_end": self.request.form.get('tseries_start_end'),
            "show_labels": self.request.form.get('show_labels'),
            "rois_to_plot": self.request.form.get('rois_to_plot')
        }
        
        self.rois_to_plot = none_or_intarray_input(self.request.form.get('rois_to_plot'))
        self.tseries_start_end = none_or_intarray_input(self.request.form.get('tseries_start_end'))
        self.show_labels = checkbox_input('show_labels')
        self.color_all_rois = True

    def get_contents(self):
        self.contents = {}
        self.contents["f"] = get_contents_bytefile(self.file_ids_dict["f"])
        self.contents["fneu"] = get_contents_bytefile(self.file_ids_dict["fneu"])
        self.contents["iscell"] = get_contents_bytefile(self.file_ids_dict["iscell"])
        self.contents["ops"] = get_contents_bytefile(self.file_ids_dict["ops"])
        self.contents["stat"] = get_contents_bytefile(self.file_ids_dict["stat"])

    def generate_plots(self):
        data_processor = ROITraceProcessor(self.tseries_start_end, self.show_labels, self.color_all_rois, self.rois_to_plot)
        data_processor.setup_roi_data(self.contents["f"], self.contents["fneu"], self.contents["iscell"], self.contents["ops"], self.contents["stat"])

        data_plotter = S2PROITracePlot(data_processor)
        
        chart_contour = data_plotter.generate_contour_plot(package="matplotlib")

        chart_time = data_plotter.generate_time_series_plot(package="plotly")
        graph2JSON = chart_time.to_json()

        chart_heat = data_plotter.generate_heatmap_plot(package="plotly")
        graph3JSON = chart_heat.to_json()

        return [chart_contour, graph2JSON, graph3JSON]
    
    def generate_full_output(self):
        self.generate_params()
        self.get_contents()
        jsons = self.generate_plots()

        delete_folder(self.folder_id)

        return self.fparams, jsons
    
class Photon2Tab2(Photon2):
    def __init__(self, request, file_ids_dict, folder_id):
        super().__init__(request, file_ids_dict, folder_id)

    def generate_params(self):
        self.fparams = {
            "fs":self.request.form.get('fs'),
            "opto_blank_frame": self.request.form.get('opto_blank_frame'),
            "num_rois": self.request.form.get('num_rois'), 
            "selected_conditions": self.request.form.get('selected_conditions'),
            "flag_normalization": self.request.form.get('flag_normalization')
        }

        self.fs = int(self.request.form.get('fs'))
        self.opto_blank_frame = checkbox_input(self.request.form.get('opto_blank_frame'))
        self.num_rois = "all" if self.request.form.get('num_rois') == "all" else int(self.request.form.get('num_rois'))
        self.flag_normalization = self.request.form.get('flag_normalization')
        self.selected_conditions = none_or_stringarray_input(self.request.form.get('selected_conditions'))

    def get_contents(self):
        self.contents = {}

        self.contents["signals"] = get_contents_string(self.file_ids_dict["signals"])
        self.contents["events"] = get_contents_string(self.file_ids_dict["events"])

    def generate_plots(self):
        data_processor = WholeSessionProcessor(self.fs, self.opto_blank_frame, self.num_rois, self.selected_conditions, self.flag_normalization, self.contents["signals"], self.contents["events"])
        data_processor.generate_all_data()

        data_plotter = WholeSessionPlot(data_processor)
        fig = data_plotter.generate_session_plot()
        graphJSON = fig.to_json()

        return [graphJSON]
    
    def generate_full_output(self):
        self.generate_params()
        self.get_contents()
        jsons = self.generate_plots()

        delete_folder(self.folder_id)

        return self.fparams, jsons

class Photon2Tab3(Photon2):
    def __init__(self, request, file_ids_dict, folder_id):
        super().__init__(request, file_ids_dict, folder_id)

    def generate_params(self):
        self.fparams = {
            'fs': self.request.form.get('fs'),
            'selected_conditions': self.request.form.get('selected_conditions'),
            'trial_start_end': self.request.form.get('trial_start_end'),
            'flag_normalization': self.request.form.get('flag_normalization'),
            'baseline_end': self.request.form.get('baseline_end'),
            'event_dur': self.request.form.get('event_dur'),
            'event_sort_analysis_win': self.request.form.get('event_sort_analysis_win'),
            'opto_blank_frame': self.request.form.get('opto_blank_frame'),
            'flag_sort_rois': self.request.form.get('flag_sort_rois'),
            'user_sort_method': self.request.form.get('user_sort_method'),
            'roi_sort_cond': self.request.form.get('roi_sort_cond'),
            'flag_roi_trial_avg_errbar': self.request.form.get('flag_roi_trial_avg_errbar'),
            'flag_trial_avg_errbar': self.request.form.get('flag_trial_avg_errbar'),
            'interesting_rois': self.request.form.get('interesting_rois'),
            'data_trial_resolved_key': self.request.form.get('data_trial_resolved_key'),
            'data_trial_avg_key': self.request.form.get('data_trial_avg_key'),
            'cmap_': self.request.form.get('cmap_'),
            'ylabel': self.request.form.get('ylabel')
        }

        self.processor_fparams = {
            'fs': int(self.request.form.get('fs')),
            'selected_conditions': none_or_stringarray_input(self.request.form.get('selected_conditions')),
            'trial_start_end': none_or_intarray_input('trial_start_end'),
            'flag_normalization': none_or_input(self.request.form.get('flag_normalization')),
            'baseline_end': float(self.request.form.get('baseline_end')),
            'event_dur': int(self.request.form.get('event_dur')),
            'event_sort_analysis_win': none_or_intarray_input(self.request.form.get('event_sort_analysis_win')),
            'opto_blank_frame': checkbox_input(self.fparams["opto_blank_frame"]),
            'flag_sort_rois': checkbox_input(self.fparams["flag_sort_rois"]),
            'user_sort_method': self.request.form.get('user_sort_method'),
            'roi_sort_cond': self.request.form.get('roi_sort_cond'),
            'flag_roi_trial_avg_errbar': checkbox_input(self.fparams["flag_roi_trial_avg_errbar"]),
            'flag_trial_avg_errbar': checkbox_input(self.fparams["flag_trial_avg_errbar"]),
            'interesting_rois': none_or_intarray_input(self.request.form.get('interesting_rois')),
            'data_trial_resolved_key': self.request.form.get('data_trial_resolved_key'),
            'data_trial_avg_key': self.request.form.get('data_trial_avg_key'),
            'cmap_': none_or_input(self.request.form.get('cmap_')),
            'ylabel': self.request.form.get('ylabel')
        }

    def get_contents(self):
        self.contents = {}

        self.contents["signals"] = get_contents_string(self.file_ids_dict["signals"])
        self.contents["events"] = get_contents_string(self.file_ids_dict["events"])

    def generate_plots(self):
        data_processor = EventRelAnalysisProcessor(self.processor_fparams, self.contents["signals"], self.contents["events"])
        data_processor.generate_all_data()
        num_rois = data_processor.get_num_rois()

        data_plotter = EventRelAnalysisPlot(data_processor)
        figs = data_plotter.generate_roi_plots()

        return figs, num_rois
    
    def generate_full_output(self):
        self.generate_params()
        self.get_contents()
        figs, num_rois = self.generate_plots()

        delete_folder(self.folder_id)

        return self.fparams, figs, num_rois

class Photon2Tab4(Photon2):
    def __init__(self, request, file_ids_dict, folder_id):
        super().__init__(request, file_ids_dict, folder_id)

    def generate_params(self):
        self.fparams = {
            "fs":self.request.form.get('fs'),
            "trial_start_end": self.request.form.get('trial_start_end'),
            "baseline_end": self.request.form.get('baseline_end'), 
            "event_sort_analysis_win": self.request.form.get('event_sort_analysis_win'),
            "pca_num_pc_method": self.request.form.get('pca_num_pc_method'),
            "max_n_clusters": self.request.form.get('max_n_clusters'),
            "possible_n_nearest_neighbors": self.request.form.get('possible_n_nearest_neighbors'),
            "selected_conditions": self.request.form.get('selected_conditions'),
            "flag_plot_reward_line": self.request.form.get('flag_plot_reward_line'),
            "second_event_seconds": self.request.form.get('second_event_seconds'),
            "heatmap_cmap_scaling": self.request.form.get('heatmap_cmap_scaling'),
            "group_data": self.request.form.get('group_data'),
            "group_data_conditions": self.request.form.get('group_data_conditions'),
            "sortwindow": self.request.form.get('sortwindow'),
        }

        self.fs = int(self.request.form.get('fs'))
        self.trial_start_end = none_or_intarray_input(self.request.form.get('trial_start_end'))
        self.baseline_end = float(self.request.form.get('baseline_end'))
        self.event_sort_analysis_win = none_or_intarray_input(self.request.form.get('event_sort_analysis_win'))
        self.pca_num_pc_method = int(self.request.form.get('pca_num_pc_method'))
        self.max_n_clusters = int(self.request.form.get('max_n_clusters'))
        self.possible_n_nearest_neighbors = np.array([int(item) for item in self.request.form.get('possible_n_nearest_neighbors').split(",")])
        self.selected_conditions = none_or_stringarray_input(self.request.form.get('selected_conditions'))
        self.flag_plot_reward_line = none_or_input(self.request.form.get('flag_plot_reward_line'))
        self.second_event_seconds = int(self.request.form.get('second_event_seconds'))
        self.heatmap_cmap_scaling = int(self.request.form.get('heatmap_cmap_scaling'))
        self.group_data = none_or_input(self.request.form.get('group_data'))
        self.group_data_conditions = none_or_stringarray_input(self.request.form.get('group_data_conditions'))
        self.sortwindow = none_or_intarray_input(self.request.form.get('sortwindow').split(","))

    def get_contents(self):
        self.contents = {}

        self.contents["signals"] = get_contents_string(self.file_ids_dict["signals"])
        self.contents["events"] = get_contents_string(self.file_ids_dict["events"])

    def generate_plots(self):
        data_processor = EventClusterProcessor(self.contents["signals"], self.contents["events"], self.fs, self.trial_start_end, self.baseline_end, self.event_sort_analysis_win, self.pca_num_pc_method, self.max_n_clusters, self.possible_n_nearest_neighbors, self.selected_conditions, self.flag_plot_reward_line, self.second_event_seconds, self.heatmap_cmap_scaling, self.group_data, self.group_data_conditions, self.sortwindow)
        data_processor.generate_all_data()

        data_plotter = EventClusterPlot(data_processor)

        return [data_plotter.generate_heatmap_zscore(), data_plotter.generate_scree_plot(), data_plotter.generate_pca_plot(), data_plotter.generate_cluster_condition_plots(), data_plotter.generate_fluorescent_graph(), data_plotter.generate_cluster_plot()]
    
    def generate_full_output(self):
        self.generate_params()
        self.get_contents()
        jsons = self.generate_plots()

        delete_folder(self.folder_id)

        return self.fparams, jsons