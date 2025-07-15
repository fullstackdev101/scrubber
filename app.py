from flask import Flask, render_template, request, send_from_directory
import os
import pandas as pd

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
FINAL_FOLDER = 'final_sheets'
ALLOWED_EXTENSIONS = {'xlsx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    message = request.args.get('message', '')
    return render_template('index.html', message=message)

@app.route('/remove_duplicates', methods=['POST'])
def remove():
    if 'file' not in request.files:
        return 'No file part'

    file = request.files['file']
    if file.filename == '':
        return 'No selected file'

    file_path = os.path.join(FINAL_FOLDER, file.filename)
    file.save(file_path)

    df = pd.read_excel(file_path)
    df_no_duplicates = df.drop_duplicates()

    output_excel_file = os.path.join(FINAL_FOLDER, 'output_sheet.xlsx')
    df_no_duplicates.to_excel(output_excel_file, index=False)

    return render_template('index.html', message="✅ Duplicates removed successfully!")

@app.route('/upload', methods=['POST'])
def upload_files():
    uploaded_files = request.files.getlist('files')

    if uploaded_files:
        for file in uploaded_files:
            if file and allowed_file(file.filename):
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
            else:
                return 'Invalid file type. Only .xlsx files are allowed.'

        return render_template('index.html', message="✅ Files uploaded successfully!")
    else:
        return 'No files uploaded'

@app.route('/scrub')
def scrub():
    folder_path = UPLOAD_FOLDER
    output_file = os.path.join(FINAL_FOLDER, "output_sheet.xlsx")

    if not os.path.exists(output_file):
        return render_template('index.html', message="⚠️ No output_sheet.xlsx found. Please remove duplicates first.")

    original_df = pd.read_excel(output_file)
    common_column = "PhoneNumber"

    for file_name in os.listdir(folder_path):
        if file_name.endswith(".xlsx"):
            file_path = os.path.join(folder_path, file_name)
            external_df = pd.read_excel(file_path)

            if common_column not in external_df.columns:
                continue  # Skip files without the common column

            # Keep only the common_column to prevent duplicate columns
            external_df = external_df[[common_column]].drop_duplicates()

            merged_df = pd.merge(original_df, external_df, on=common_column, how="left", indicator=True)
            non_matching_df = merged_df[merged_df["_merge"] == "left_only"].drop(columns=["_merge"])

            # Overwrite the output file
            non_matching_df.to_excel(output_file, index=False)

    return render_template(
        'index.html',
        message="✅ Scrubbed successfully! <a href='/download_output' class='underline text-blue-700'>Download Output Sheet</a>"
    )

@app.route('/download_output')
def download_output():
    path = FINAL_FOLDER
    filename = "output_sheet.xlsx"
    return send_from_directory(path, filename, as_attachment=True)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(FINAL_FOLDER, exist_ok=True)

if __name__ == '__main__':
    app.run(debug=True)

