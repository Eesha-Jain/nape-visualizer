from drive import upload_to_drive, delete_folder, get_contents_bytefile, get_contents_string
from visualizer.data import ROITraceProcessor, WholeSessionProcessor, EventRelAnalysisProcessor, EventClusterProcessor
from visualizer.plots import S2PROITracePlot, WholeSessionPlot, EventRelAnalysisPlot, EventClusterPlot
from abc import ABC, abstractmethod
from io import BytesIO
import base64
import numpy as np

# Process the inputs from the HTML form
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
    else:
        return [int(item) for item in none_or_stringarray_input(value)]
    
def process_input(value, type):
    if type == "intarray":
        return none_or_intarray_input(value)
    elif type == "stringarray":
        return none_or_stringarray_input(value)
    elif type == "checkbox":
        return True if value else False
    elif type == "int":
        return int(value)
    elif type == "string":
        return value 
    elif type == "nullstring":
        return None if value == "None" else value
    elif type == "allint":
        return "all" if value == "all" else int(value)
    elif type == "float":
        return float(value)
    elif type == "npintarray":
        return np.array(none_or_intarray_input(value))
    
    raise Exception("Type {} not recognized".format(type))

# Convert matplotlib plot into base64 for display
def get_encoded(chart):
    buf = BytesIO()
    chart.savefig(buf, format="png", bbox_inches='tight', pad_inches=0)
    return base64.b64encode(buf.getbuffer()).decode("ascii")

# Find respective files from HTML form and upload to Google Drive
def contains_name(files_dict, name, file_extension):
    for key in files_dict.keys():
        if name in key and any(ext in key for ext in file_extension):
            return files_dict[key]

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
            file = contains_name(files_dict, file_names[i], file_extension)
            files.append(file)
    
    #Upload files to Google Drive
    file_ids, folder_id = upload_to_drive(files)

    #Return dictionary with file_names
    file_ids_dict = {}

    for i, file_name in enumerate(file_names):
        file_ids_dict[file_name] = file_ids[i]

    return folder_id, file_ids_dict

# Parent class for the individual tab analysis
class Photon2(ABC):
    def __init__(self, request, file_ids_dict, folder_id, file_names):
        self.request = request
        self.file_ids_dict = file_ids_dict
        self.folder_id = folder_id
        self.file_names = file_names

        self.fparams = {}
        self.processed_fparams = {}
        self.parameters = {}
        self.contents = {}
    
    def generate_params(self):
        for param in self.parameters.keys():
            self.fparams[param] = self.request.form.get(param)
            self.processed_fparams[param] = process_input(self.request.form.get(param), self.parameters[param])
    
    def generate_params_with_file_ext(self):
        for param in self.parameters.keys():
            self.fparams[param] = self.request.form.get(param)
            self.processed_fparams[param] = process_input(self.request.form.get(param), self.parameters[param])
        self.file_extension = self.request.form.get("file_extension").split(",") if len(self.request.form.get("file_extension").split(",")) > 1 else [self.request.form.get("file_extension")]

    def get_contents(self):
        for i, file_name in enumerate(self.file_names):
            self.contents[file_name] = get_contents_string(self.file_ids_dict[file_name], self.file_extension[i])

    @abstractmethod
    def generate_plots(self):
        pass

    def generate_full_output(self):
        self.generate_params()
        self.get_contents()
        jsons = self.generate_plots()

        delete_folder(self.folder_id)

        return self.fparams, jsons

# Tab 1 image processing class
class Photon2Tab1(Photon2):
    def __init__(self, request, file_ids_dict, folder_id, file_names):
        super().__init__(request, file_ids_dict, folder_id, file_names)

    def generate_params(self):
        self.parameters = {
            "tseries_start_end": "intarray",
            "show_labels": "checkbox",
            "color_all_rois": "checkbox",
            "rois_to_plot": "intarray"
        }

        super().generate_params()

    def get_contents(self):
        for file_name in self.file_names:
            self.contents[file_name] = get_contents_bytefile(self.file_ids_dict[file_name])

    def generate_plots(self):
        params = [self.processed_fparams[item] for item in self.parameters.keys()]
        file_params = [self.contents[item] for item in self.contents.keys()]

        data_processor = ROITraceProcessor(*params)
        data_processor.setup_roi_data(*file_params)

        data_plotter = S2PROITracePlot(data_processor)
        
        chart_contour = data_plotter.generate_contour_plot(package="matplotlib")

        chart_time = data_plotter.generate_time_series_plot(package="plotly")
        graph2JSON = chart_time.to_json()

        chart_heat = data_plotter.generate_heatmap_plot(package="plotly")
        graph3JSON = chart_heat.to_json()

        return [chart_contour, graph2JSON, graph3JSON]

# Tab 2 image processing class
class Photon2Tab2(Photon2):
    def __init__(self, request, file_ids_dict, folder_id, file_names):
        super().__init__(request, file_ids_dict, folder_id, file_names)

    def generate_params(self):
        self.parameters = {
            "fs": "int",
            "opto_blank_frame": "checkbox",
            "num_rois": "allint",
            "selected_conditions": "stringarray",
            "flag_normalization": "string"
        }
        
        super().generate_params_with_file_ext()

    def generate_plots(self):
        params = [self.processed_fparams[item] for item in self.parameters.keys()]
        file_params = [self.contents[item] for item in self.contents.keys()]

        data_processor = WholeSessionProcessor(*params, *file_params, file_extension=self.file_extension)
        data_processor.generate_all_data()

        data_plotter = WholeSessionPlot(data_processor)
        fig = data_plotter.generate_session_plot()
        graphJSON = fig.to_json()

        return [graphJSON]

# Tab 3 imaging processing class
class Photon2Tab3(Photon2):
    def __init__(self, request, file_ids_dict, folder_id, file_names):
        super().__init__(request, file_ids_dict, folder_id, file_names)

    def generate_params(self):
        self.parameters = {
            "fs": "int",
            "selected_conditions": "stringarray",
            "trial_start_end": "intarray",
            "baseline_end": "float",
            "event_dur": "int",
            "event_sort_analysis_win": "intarray",
            "opto_blank_frame": "checkbox",
            "flag_sort_rois": "checkbox",
            "user_sort_method": "string",
            "roi_sort_cond": "string",
            "flag_roi_trial_avg_errbar": "checkbox",
            "flag_trial_avg_errbar": "checkbox",
            "interesting_rois": "intarray",
            "data_trial_resolved_key": "string",
            "data_trial_avg_key": "string",
            "cmap_": "nullstring",
            "ylabel": "string",
            "flag_normalization": "nullstring"
        }

        super().generate_params_with_file_ext()

    def generate_plots(self):
        file_params = [self.contents[item] for item in self.contents.keys()]
    
        data_processor = EventRelAnalysisProcessor(self.processed_fparams, *file_params, file_extension=self.file_extension)
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

# Tab 4 imaging processing class
class Photon2Tab4(Photon2):
    def __init__(self, request, file_ids_dict, folder_id, file_names):
        super().__init__(request, file_ids_dict, folder_id, file_names)

    def generate_params(self):
        self.parameters = {
            "fs": "int",
            "trial_start_end": "intarray",
            "baseline_end": "float",
            "event_sort_analysis_win": "intarray",
            "pca_num_pc_method": "int",
            "max_n_clusters": "int",
            "possible_n_nearest_neighbors": "npintarray",
            "selected_conditions": "stringarray",
            "flag_plot_reward_line": "nullstring",
            "second_event_seconds": "int",
            "heatmap_cmap_scaling": "int",
            "group_data": "nullstring",
            "group_data_conditions": "stringarray",
            "sortwindow": "intarray"
        }

        super().generate_params_with_file_ext()

    def generate_plots(self):
        params = [self.processed_fparams[item] for item in self.parameters.keys()]
        file_params = [self.contents[item] for item in self.contents.keys()]

        data_processor = EventClusterProcessor(*file_params, *params, file_extension=self.file_extension)
        data_processor.generate_all_data()

        data_plotter = EventClusterPlot(data_processor)

        return [data_plotter.generate_scree_plot(package="plotly").to_json(), data_plotter.generate_heatmap_zscore(), data_plotter.generate_pca_plot(), data_plotter.generate_cluster_condition_plots(), data_plotter.generate_fluorescent_graph(), data_plotter.generate_cluster_plot()]