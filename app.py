from flask import Flask, render_template, request
from plots import generate_graph_tab2, define_params, contour_plot_tab1, time_series_plot_tab1, heatmap_plot_tab1, prep_plotting_rois, define_paths_roi_plots, load_s2p_data_roi_plots, masks_init
from drive import upload, delete_folder

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def photon():
    graphJSON = None
    return render_template('photon.html', graphJSON=graphJSON)

@app.route('/2photon/tab1', methods=['GET', 'POST'])
def photon2_tab1():
    if request.method == "POST":
        #Assigning files from input to variables based on whether they were uploaded individually or if a folder was uploaded
        try:
            ff = request.files["ff"]
            ffneu = request.files["ffneu"]
            fiscell = request.files["fiscell"]
            fops = request.files["fops"]
            fspks = request.files["fspks"]
            fstat = request.files["fstat"]

            if (not ff) or (not ffneu) or (not fiscell) or (not fops) or (not fspks) or (not fstat):
                raise Exception()
        except Exception as e:
            files = request.files.getlist('ffolder')
            files_dict = {}

            for file in files:
                if file:
                    filename = file.filename.lower().split("/")
                    files_dict[filename[len(filename) - 1]] = file

            ff = files_dict["f.npy"]
            ffneu = files_dict["fneu.npy"]
            fiscell = files_dict["iscell.npy"]
            fops = files_dict["ops.npy"]
            fspks = files_dict["spks.npy"]
            fstat = files_dict["stat.npy"]
        
        try:
            file_ids, folder_id = upload([ff, ffneu, fiscell, fops, fspks, fstat])
            file_ids_dict = {
                "f": file_ids[0],
                "fneu": file_ids[1],
                "iscell": file_ids[2],
                "ops": file_ids[3],
                "spks": file_ids[4],
                "stat": file_ids[5]
            }
        except Exception as e:
            print(e)
        
        #Assign user inputs to fparams
        fparams = {
            "tseries_start_end": request.form.get('tseries_start_end'),
            "show_labels": request.form.get('show_labels'),
            "rois_to_plot": request.form.get('rois_to_plot')
        }

        if request.form.get('rois_to_plot') == "None":
            rois_to_plot = None
        elif len(request.form.get('rois_to_plot').split(",")) > 1:
            rois_to_plot_split = request.form.get('rois_to_plot').split(",")
            rois_to_plot = [int(item) for item in rois_to_plot_split]
        else:
            rois_to_plot = int(request.form.get('rois_to_plot'))

        if request.form.get('tseries_start_end') == "None":
            tseries_start_end = None
        else:
            tseries_start_end_split = request.form.get('tseries_start_end').split(",")
            tseries_start_end = [int(item) for item in tseries_start_end_split]

        show_labels = False if request.form.get('show_labels') == "false" else True

        #Generate plots and their respective JSON
        path_dict = {}
        path_dict = define_paths_roi_plots(file_ids_dict, path_dict, tseries_start_end, rois_to_plot)
        s2p_data_dict = load_s2p_data_roi_plots(path_dict)
        plot_vars = prep_plotting_rois(s2p_data_dict, path_dict)
        masks_init(plot_vars, s2p_data_dict)
        
        chart_contour = contour_plot_tab1(s2p_data_dict, path_dict, plot_vars, show_labels_=show_labels, cmap_scale_ratio=3)
        graph1JSON = chart_contour.to_json()

        chart_time = time_series_plot_tab1(s2p_data_dict, path_dict, plot_vars)
        graph2JSON = chart_time.to_json()

        chart_heat = heatmap_plot_tab1(s2p_data_dict, path_dict, plot_vars)
        graph3JSON = chart_heat.to_json()

        #Delete the google drive folder
        delete_folder(folder_id)
    else:
        graph1JSON = None
        graph2JSON = None
        graph3JSON = None
        fparams = {
            "tseries_start_end": "0, 10",
            "show_labels": "true",
            "rois_to_plot": None
        }

    return render_template('2photon/tab1.html', graph1JSON=graph1JSON, graph2JSON=graph2JSON, graph3JSON=graph3JSON, fparams=fparams)

@app.route('/2photon/tab2', methods=['GET', 'POST'])
def photon2_tab2():
    if request.method == "POST":
        fs = int(request.form.get('fs'))
        opto_blank_frame = False if request.form.get('opto_blank_frame') == "false" else True
        num_rois = "all" if request.form.get('num_rois') == "all" else int(request.form.get('num_rois'))
        selected_conditions = None if request.form.get('selected_conditions') == "None" else request.form.get('selected_conditions')
        flag_normalization = request.form.get('flag_normalization')

        #Assigning files from input to variables based on whether they were uploaded individually or if a folder was uploaded
        try:
            fsignal = request.files["fsignal"]
            fevents = request.files["fevents"]

            if (not fsignal) or (not fevents):
                raise Exception()
        except Exception as e:
            files = request.files.getlist('ffolder')
            files_dict = {}

            for file in files:
                if file:
                    filename = file.filename.lower().split("/")
                    files_dict[filename[len(filename) - 1]] = file

            fsignal = files_dict["signals.csv"]
            fevents = files_dict["events.csv"]

        fsignal_name = fsignal.filename
        fevents_name = fevents.filename
        
        try:
            file_ids, folder_id = upload([fsignal, fevents])
        except Exception as e:
            print(e)

        # Generate plots and their JSON files
        fparams = define_params(fs = fs, opto_blank_frame = opto_blank_frame, num_rois = num_rois, selected_conditions = selected_conditions, flag_normalization = flag_normalization, fsignal=fsignal_name, fevents=fevents_name)
        
        chart = generate_graph_tab2(fparams, file_ids)
        graphJSON = chart.to_json()

        delete_folder(folder_id)
    else:
        fparams = define_params()
        graphJSON = None

    return render_template('2photon/tab2.html', graphJSON=graphJSON, fparams=fparams)

if __name__ == '__main__':
    app.run(debug=True)
