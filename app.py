from flask import Flask, render_template, request
from plots import generateGraphTab2, define_params
from drive import upload, delete_folder

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def tab1():
    fparams = define_params()
    graphJSON = None

    return render_template('tab1.html', graphJSON=graphJSON, fparams=fparams)

@app.route('/tab2', methods=['GET', 'POST'])
def index():
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
        
        chart = generateGraphTab2(fparams, file_ids)
        graphJSON = chart.to_json()

        delete_folder(folder_id)
    else:
        fparams = define_params()
        graphJSON = None

    return render_template('tab2.html', graphJSON=graphJSON, fparams=fparams)

if __name__ == '__main__':
    app.run(debug=True)
