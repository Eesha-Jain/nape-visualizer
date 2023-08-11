from flask import Flask, render_template, request
from analysis import upload_inputted_files, get_encoded, Photon2Tab1, Photon2Tab2, Photon2Tab3

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def photon():
    graphJSON = None
    return render_template('photon.html', graphJSON=graphJSON)

@app.route('/photon2/tab1', methods=['GET', 'POST'])
def photon2_tab1():
    if request.method == "POST":
        folder_id, file_ids_dict = upload_inputted_files(request, ["f", "fneu", "iscell", "ops", "spks", "stat"], ".npy")
        data_generator = Photon2Tab1(request, file_ids_dict, folder_id)
        fparams, jsons = data_generator.generate_full_output()

        graph1 = get_encoded(jsons[0])
        graph2JSON = jsons[1]
        graph3JSON = jsons[2]
    else:
        graph1 = ""
        graph2JSON = None
        graph3JSON = None
        fparams = {
            "tseries_start_end": "0, 10",
            "show_labels": "true",
            "rois_to_plot": None
        }

    return render_template('photon2/tab1.html', graph1=graph1, graph2JSON=graph2JSON, graph3JSON=graph3JSON, fparams=fparams)

@app.route('/photon2/tab2', methods=['GET', 'POST'])
def photon2_tab2():
    if request.method == "POST":
        folder_id, file_ids_dict = upload_inputted_files(request, ["signals", "events"], ".csv")
        data_generator = Photon2Tab2(request, file_ids_dict, folder_id)
        fparams, jsons = data_generator.generate_full_output()

        graphJSON = jsons[0]
    else:
        graphJSON = None
        fparams = {
            "fs": 5,
            "opto_blank_frame": "true",
            "num_rois": 10, 
            "selected_conditions": None,
            "flag_normalization": "dff_perc"
        }

    return render_template('photon2/tab2.html', graphJSON=graphJSON, fparams=fparams)

@app.route('/photon2/tab3', methods=['GET', 'POST'])
def photon2_tab3():
    if request.method == "POST":
        folder_id, file_ids_dict = upload_inputted_files(request, ["signals", "events"], ".csv")
        data_generator = Photon2Tab3(request, file_ids_dict, folder_id)
        fparams, matCharts, num_rois = data_generator.generate_full_output()

        graphs = []

        for chart in matCharts:
            graphBytes = {}
            
            if "heatmap" in chart and chart["heatmap"]:
                graphBytes["heatmap"] = get_encoded(chart["heatmap"])
            if "linegraph" in chart and chart["linegraph"]:
                graphBytes["linegraph"] = get_encoded(chart["linegraph"])
            if "bargraph" in chart and chart["bargraph"]:
                graphBytes["bargraph"] = get_encoded(chart["bargraph"])
                print(chart["heatmap"] == chart["bargraph"])
            
            graphs.append(graphBytes)
    else:
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

if __name__ == '__main__':
    app.run(debug=True)
