from drive import upload_to_drive, delete_folder, get_contents_bytefile, get_contents_string
from visualizer.data import S2PActivityProcessor, EventTicksProcessor
from visualizer.plots import S2PActivityPlot, EventTicksPlot
from abc import ABC, abstractmethod

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

        self.show_labels = False if self.request.form.get('show_labels') == "false" else True
        self.color_all_rois = True

    def get_contents(self):
        self.contents = {}
        self.contents["f"] = get_contents_bytefile(self.file_ids_dict["f"])
        self.contents["fneu"] = get_contents_bytefile(self.file_ids_dict["fneu"])
        self.contents["iscell"] = get_contents_bytefile(self.file_ids_dict["iscell"])
        self.contents["ops"] = get_contents_bytefile(self.file_ids_dict["ops"])
        self.contents["stat"] = get_contents_bytefile(self.file_ids_dict["stat"])

    def generate_plots(self):
        data_processor = S2PActivityProcessor(self.tseries_start_end, self.show_labels, self.color_all_rois, self.rois_to_plot)
        data_processor.setup_roi_data(self.contents["f"], self.contents["fneu"], self.contents["iscell"], self.contents["ops"], self.contents["stat"])

        data_plotter = S2PActivityPlot(data_processor)
        
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
        self.opto_blank_frame = False if self.request.form.get('opto_blank_frame') == "false" else True
        self.num_rois = "all" if self.request.form.get('num_rois') == "all" else int(self.request.form.get('num_rois'))
        self.selected_conditions = None if self.request.form.get('selected_conditions') == "None" else self.request.form.get('selected_conditions')
        self.flag_normalization = self.request.form.get('flag_normalization')

    def get_contents(self):
        self.contents = {}

        self.contents["signals"] = get_contents_string(self.file_ids_dict["signals"])
        self.contents["events"] = get_contents_string(self.file_ids_dict["events"])

    def generate_plots(self):
        data_processor = EventTicksProcessor(self.fs, self.opto_blank_frame, self.num_rois, self.selected_conditions, self.flag_normalization, self.contents["signals"], self.contents["events"])
        data_processor.generate_all_data()

        data_plotter = EventTicksPlot(data_processor)
        fig = data_plotter.generate_session_plot()
        graphJSON = fig.to_json()

        return [graphJSON]
    
    def generate_full_output(self):
        self.generate_params()
        self.get_contents()
        jsons = self.generate_plots()

        delete_folder(self.folder_id)

        return self.fparams, jsons