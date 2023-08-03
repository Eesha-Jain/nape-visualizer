from flask import Flask, render_template, request
from analysis import upload_inputted_files, Photon2Tab1, Photon2Tab2

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
        
        graph1JSON = jsons[0]
        graph2JSON = jsons[1]
        graph3JSON = jsons[2]
    else:
        graph1JSON = None
        graph2JSON = None
        graph3JSON = None
        fparams = {
            "tseries_start_end": "0, 10",
            "show_labels": "true",
            "rois_to_plot": None
        }

    return render_template('photon2/tab1.html', graph1JSON=graph1JSON, graph2JSON=graph2JSON, graph3JSON=graph3JSON, fparams=fparams)

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
            "opto_blank_frame": True,
            "num_rois": 10, 
            "selected_conditions": None,
            "flag_normalization": "dff_perc"
        }

    return render_template('photon2/tab2.html', graphJSON=graphJSON, fparams=fparams)

if __name__ == '__main__':
    app.run(debug=True)
