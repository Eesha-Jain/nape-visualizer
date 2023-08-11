from drive import upload_to_drive, delete_folder, get_contents_bytefile, get_contents_string
from visualizer.data import ROITraceProcessor, WholeSessionProcessor, EventRelAnalysisProcessor
from visualizer.plots import S2PROITracePlot, WholeSessionPlot, EventRelAnalysisPlot
from abc import ABC, abstractmethod
from io import BytesIO
import base64

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

        if self.request.form.get('rois_to_plot') == "None":
            self.rois_to_plot = None
        elif len(self.request.form.get('rois_to_plot').split(",")) > 1:
            rois_to_plot_split = self.request.form.get('rois_to_plot').split(",")
            self.rois_to_plot = [int(item) for item in rois_to_plot_split]
        else:
            self.rois_to_plot = int(self.request.form.get('rois_to_plot'))

        if self.request.form.get('tseries_start_end') == "None":
            self.tseries_start_end = None
        else:
            self.tseries_start_end_split = self.request.form.get('tseries_start_end').split(",")
            self.tseries_start_end = [int(item) for item in self.tseries_start_end_split]

        self.show_labels = True if self.request.form.get('show_labels') else False
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
        self.opto_blank_frame = True if self.request.form.get('opto_blank_frame') else False
        self.num_rois = "all" if self.request.form.get('num_rois') == "all" else int(self.request.form.get('num_rois'))
        self.selected_conditions = None if self.request.form.get('selected_conditions') == "None" else self.request.form.get('selected_conditions')
        self.flag_normalization = self.request.form.get('flag_normalization')

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

        if self.request.form.get('selected_conditions') == "None":
            selected_conditions = None
        else:
            selected_conditions_split = self.request.form.get('selected_conditions').split(",")
            selected_conditions = [int(item) for item in selected_conditions_split]

        self.processor_fparams = {
            'fs': int(self.request.form.get('fs')),
            'selected_conditions': selected_conditions,
            'trial_start_end': [int(item) for item in self.request.form.get('trial_start_end').split(",")],
            'flag_normalization': None if self.request.form.get('flag_normalization') == "None" else self.request.form.get('flag_normalization'),
            'baseline_end': float(self.request.form.get('baseline_end')),
            'event_dur': int(self.request.form.get('event_dur')),
            'event_sort_analysis_win': [int(item) for item in self.request.form.get('event_sort_analysis_win').split(",")],
            'opto_blank_frame': True if self.fparams["opto_blank_frame"] else False,
            'flag_sort_rois': True if self.fparams["flag_sort_rois"] else False,
            'user_sort_method': self.request.form.get('user_sort_method'),
            'roi_sort_cond': self.request.form.get('roi_sort_cond'),
            'flag_roi_trial_avg_errbar': True if self.fparams["flag_roi_trial_avg_errbar"] else False,
            'flag_trial_avg_errbar': True if self.fparams["flag_trial_avg_errbar"] else False,
            'interesting_rois': [int(item) for item in self.request.form.get('interesting_rois').split(",")],
            'data_trial_resolved_key': self.request.form.get('data_trial_resolved_key'),
            'data_trial_avg_key': self.request.form.get('data_trial_avg_key'),
            'cmap_': None if self.request.form.get('cmap_') == "None" else self.request.form.get('cmap_'),
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