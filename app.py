from flask import Flask, render_template, request
from plots import generate_graph_tab2, define_params, contour_plot_tab1, time_series_plot_tab1, heatmap_plot_tab1, prep_plotting_rois, define_paths_roi_plots, load_s2p_data_roi_plots, masks_init
from drive import upload, delete_folder

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def tab1():
    if request.method == "POST":
        ff = request.files["ff"]
        ffneu = request.files["ffneu"]
        fiscell = request.files["fiscell"]
        fops = request.files["fops"]
        fspks = request.files["fspks"]
        fstat = request.files["fstat"]
        
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
        
        #USER DEFINDED VARIABLES
        tseries_start_end = [0, 10] # setting None will plot the whole session
        show_labels = True
        """
        define number of ROIs to visualize

        can be: 
        1) a list of select rois, 
        2) an integer (n) indicating n first rois to plot, or 
        3) None which plots all valid ROIs
        """ 
        rois_to_plot = None

        #ACTUAL CODE
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

        delete_folder(folder_id)
    else:
        graph1JSON = None
        graph2JSON = None
        graph3JSON = None

    return render_template('tab1.html', graph1JSON=graph1JSON, graph2JSON=graph2JSON, graph3JSON=graph3JSON)

@app.route('/tab2', methods=['GET', 'POST'])
def tab2():
    if request.method == "POST":
        fs = int(request.form.get('fs'))
        opto_blank_frame = False if request.form.get('opto_blank_frame') == "false" else True
        num_rois = "all" if request.form.get('num_rois') == "all" else int(request.form.get('num_rois'))
        selected_conditions = None if request.form.get('selected_conditions') == "None" else request.form.get('selected_conditions')
        flag_normalization = request.form.get('flag_normalization')

        fsignal = request.files["fsignal"]
        fevents = request.files["fevents"]

        fsignal_name = fsignal.filename
        fevents_name = fevents.filename
        
        try:
            file_ids, folder_id = upload([fsignal, fevents])
        except Exception as e:
            print(e)

        fparams = define_params(fs = fs, opto_blank_frame = opto_blank_frame, num_rois = num_rois, selected_conditions = selected_conditions, flag_normalization = flag_normalization, fsignal=fsignal_name, fevents=fevents_name)
        
        chart = generate_graph_tab2(fparams, file_ids)
        graphJSON = chart.to_json()

        delete_folder(folder_id)
    else:
        fparams = define_params()
        graphJSON = None

    return render_template('tab2.html', graphJSON=graphJSON, fparams=fparams)

if __name__ == '__main__':
    app.run(debug=True)
