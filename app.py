from flask import Flask, render_template, request
from analysis import upload_inputted_files, get_encoded, Photon2Tab1, Photon2Tab2, Photon2Tab3, Photon2Tab4

# Create a Flask application instance
app = Flask(__name__)

# Route for the main page
@app.route('/', methods=['GET', 'POST'])
def photon():
    graphJSON = None
    return render_template('photon.html', graphJSON=graphJSON)

# Route and logic for the 'Tab 1' of Photon2
@app.route('/photon2/tab1', methods=['GET', 'POST'])
def photon2_tab1():
    if request.method == "POST":
        # Upload inputted files and generate required data
        file_names = ["ff", "fneu", "iscell", "ops", "stat"]
        folder_id, file_ids_dict = upload_inputted_files(request, file_names, ".npy")
        data_generator = Photon2Tab1(request, file_ids_dict, folder_id, file_names)
        fparams, jsons = data_generator.generate_full_output()

        graph1 = get_encoded(jsons[0])
        graph2JSON = jsons[1]
        graph3JSON = jsons[2]
    else:
        # Set default values
        graph1 = ""
        graph2JSON = None
        graph3JSON = None
        fparams = {
            "tseries_start_end": "0, 10",
            "show_labels": "true",
            "rois_to_plot": None,
            "color_all_rois": "true"
        }

    return render_template('photon2/tab1.html', graph1=graph1, graph2JSON=graph2JSON, graph3JSON=graph3JSON, fparams=fparams)

# Route and logic for 'Tab 2' of Photon2
@app.route('/photon2/tab2', methods=['GET', 'POST'])
def photon2_tab2():
    if request.method == "POST":
        # Upload inputted files and generate required data
        file_names = ["signals", "event"]
        file_ext = request.form.get("file_extension").split(",") if len(request.form.get("file_extension").split(",")) > 1 else [request.form.get("file_extension")]
        folder_id, file_ids_dict = upload_inputted_files(request, file_names, file_ext)
        data_generator = Photon2Tab2(request, file_ids_dict, folder_id, file_names)
        fparams, jsons = data_generator.generate_full_output()

        graphJSON = jsons[0]
    else:
        # Set default values
        graphJSON = None
        fparams = {
            "fs": 5,
            "opto_blank_frame": "true",
            "num_rois": 10, 
            "selected_conditions": None,
            "flag_normalization": "dff_perc",
            "file_extension": ".csv"
        }

    return render_template('photon2/tab2.html', graphJSON=graphJSON, fparams=fparams)

# Route and logic for 'Tab 3' of Photon2
@app.route('/photon2/tab3', methods=['GET', 'POST'])
def photon2_tab3():
    if request.method == "POST":
        # Upload inputted files and generate required data
        file_names = ["signals", "event"]
        file_ext = request.form.get("file_extension").split(",") if len(request.form.get("file_extension").split(",")) > 1 else [request.form.get("file_extension")]
        folder_id, file_ids_dict = upload_inputted_files(request, file_names, file_ext)
        data_generator = Photon2Tab3(request, file_ids_dict, folder_id, file_names)
        fparams, matCharts, num_rois = data_generator.generate_full_output()

        graphs = []

        # Generate graphs for different chart types
        for chart in matCharts:
            graphBytes = {}
            
            if "heatmap" in chart and chart["heatmap"]:
                graphBytes["heatmap"] = get_encoded(chart["heatmap"])
            if "linegraph" in chart and chart["linegraph"]:
                graphBytes["linegraph"] = get_encoded(chart["linegraph"])
            if "bargraph" in chart and chart["bargraph"]:
                graphBytes["bargraph"] = get_encoded(chart["bargraph"])
            
            graphs.append(graphBytes)
    else:
        # Set default values
        graphs = None
        num_rois = 0
        fparams = {
            'fs': 5,
            'selected_conditions': "None",
            'trial_start_end': "-2,8",
            'flag_normalization': 'zscore',
            'baseline_end': -0.2,
            'event_dur': 2,
            'event_sort_analysis_win': "0,5",
            'opto_blank_frame': None,
            'flag_sort_rois': "true",
            'user_sort_method': 'max_value',
            'roi_sort_cond': 'plus',
            'flag_roi_trial_avg_errbar': "true",
            'flag_trial_avg_errbar': "true",
            'interesting_rois': "0,1"
        }

        # Adjust default parameters based on normalization type
        if 'zscore' in fparams['flag_normalization']:
            fparams['data_trial_resolved_key'] = 'zdata'
            fparams['data_trial_avg_key'] = 'ztrial_avg_data'
            fparams['cmap_'] = 'None'
            fparams['ylabel'] = 'Z-score Activity'
        else:
            fparams['data_trial_resolved_key'] = 'data'
            fparams['data_trial_avg_key'] = 'trial_avg_data'
            fparams['cmap_'] = 'inferno'
            fparams['ylabel'] = 'Activity'

    return render_template('photon2/tab3.html', graphs=graphs, fparams=fparams, num_rois=num_rois)

# Route and logic for 'Tab 4' of Photon2
@app.route('/photon2/tab4', methods=['GET', 'POST'])
def photon2_tab4():
    if request.method == "POST":
        # Upload inputted files and generate required data
        file_names = ["signals", "event"]
        file_ext = request.form.get("file_extension").split(",") if len(request.form.get("file_extension").split(",")) > 1 else [request.form.get("file_extension")]
        folder_id, file_ids_dict = upload_inputted_files(request, file_names, file_ext)
        data_generator = Photon2Tab4(request, file_ids_dict, folder_id, file_names)
        fparams, jsons = data_generator.generate_full_output()

        graphs = []

        # Generate graphs for different data
        for i, json in enumerate(jsons):
            if i == 0:
                continue
            graphs.append(get_encoded(json))

    else:
        # Set default values
        graphs = None
        jsons = [None]
        fparams = {
            "fs": 5,
            'trial_start_end': "-2,8",
            'baseline_end': -0.2,
            "event_sort_analysis_win": "0,5",
            "pca_num_pc_method": 0,
            "max_n_clusters": 10,
            "possible_n_nearest_neighbors": "3,5,10",
            "selected_conditions": "None",
            "flag_plot_reward_line": None,
            "second_event_seconds": 1,
            "heatmap_cmap_scaling": 1,
            "group_data": None,
            "group_data_conditions": 'cs_plus,cs_minus',
            "sortwindow": "15,100"
        }

    return render_template('photon2/tab4.html', graph1JSON=jsons[0], graphs=graphs, fparams=fparams)

# Run the application if this script is executed directly
if __name__ == '__main__':
    app.run(debug=True)
