from flask import Flask, render_template, request
from analysis import upload_inputted_files, get_encoded, Photon2Tab1, Photon2Tab2, Photon2Tab3, Photon2Tab4, Photon2Tab5

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
        folder_id, file_ids_dict = upload_inputted_files(request, file_names, [".npy", ".npy", ".npy", ".npy", ".npy"])
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
        folder_id, file_ids_dict = upload_inputted_files(request, file_names, [request.form.get("signals_file_extension"), request.form.get("event_file_extension")])
        data_generator = Photon2Tab2(request, file_ids_dict, folder_id, file_names)
        fparams, jsons = data_generator.generate_full_output()

        graphJSON = jsons[0]
    else:
        # Set default values
        graphJSON = None
        fparams = {
            "fs": 5,
            "opto_blank_frame": None,
            "num_rois": 10, 
            "selected_conditions": None,
            "flag_normalization": "dff_perc",
            "signals_file_extension": ".csv",
            "event_file_extension": ".csv"
        }

    return render_template('photon2/tab2.html', graphJSON=graphJSON, fparams=fparams)

# Route and logic for 'Tab 3' of Photon2
@app.route('/photon2/tab3', methods=['GET', 'POST'])
def photon2_tab3():
    if request.method == "POST":
        # Upload inputted files and generate required data
        file_names = ["signals", "event"]
        folder_id, file_ids_dict = upload_inputted_files(request, file_names, [request.form.get("signals_file_extension"), request.form.get("event_file_extension")])
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
            'interesting_rois': "0,1",
            "signals_file_extension": ".csv",
            "event_file_extension": ".csv"
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
        folder_id, file_ids_dict = upload_inputted_files(request, file_names, [request.form.get("signals_file_extension"), request.form.get("event_file_extension")])
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
            "sortwindow": "15,100",
            "signals_file_extension": ".csv",
            "event_file_extension": ".csv"
        }

    return render_template('photon2/tab4.html', graph1JSON=jsons[0], graphs=graphs, fparams=fparams)

# Route and logic for 'Tab 5' of Photon5
@app.route('/photon2/tab5', methods=['GET', 'POST'])
def photon2_tab5():
    if request.method == "POST":
        # Upload inputted files and generate required data
        file_names = ["signals", "event", "sima_mc", "sima_masks"]
        folder_id, file_ids_dict = upload_inputted_files(request, file_names, [request.form.get("signals_file_extension"), request.form.get("event_file_extension"), ".h5", ".npy"])
        data_generator = Photon2Tab5(request, file_ids_dict, folder_id, file_names)
        fparams, jsons, conditions = data_generator.generate_full_output()

        graphs = []
        graphs.append(get_encoded(jsons[0]))

        graphs_sub = []
        for graph in jsons[1]:
            json = {}
            json["contour"] = get_encoded(graph["contour"])
            json["linegraph"] = get_encoded(graph["linegraph"])
            graphs_sub.append(json)
        
        graphs.append(graphs_sub)

        graphs_sub = []
        for graph in jsons[2]:
            graphs_sub.append(get_encoded(graph))
        
        graphs.append(graphs_sub)
    else:
        # Set default values
        graphs = [None, None, None]
        conditions = None
        fparams = {
            "fs": 5,
            'trial_start_end': "-2,8",
            'baseline_end': -0.2,
            "selected_conditions": "None",
            'opto_blank_frame': None,
            "rois_to_plot": None,
            "activity_name": None,
            "raw_npilCorr": None,
            "analysis_win": "0,None"
        }

    return render_template('photon2/tab5.html', graphs1=graphs[0], graphs2=graphs[1], graphs3=graphs[2], fparams=fparams, conditions=conditions)

# Run the application if this script is executed directly
if __name__ == '__main__':
    app.run(debug=True)
