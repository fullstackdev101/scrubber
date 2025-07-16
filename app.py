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
        return render_template('index.html', message="❌ No file part.")

    file = request.files['file']
    if file.filename == '':
        return render_template('index.html', message="❌ No file selected.")

    file_path = os.path.join(FINAL_FOLDER, file.filename)
    file.save(file_path)

    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        return render_template('index.html', message=f"❌ Failed to read Excel file: {str(e)}")

    if 'PhoneNumber' not in df.columns:
        os.remove(file_path)  # Clean up
        return render_template('index.html', message="❌ The uploaded file does not contain a 'PhoneNumber' column.")

    df_no_duplicates = df.drop_duplicates()
    output_excel_file = os.path.join(FINAL_FOLDER, 'output_sheet.xlsx')
    df_no_duplicates.to_excel(output_excel_file, index=False)

    return render_template('index.html', message="✅ Duplicates removed successfully!")

@app.route('/upload', methods=['POST'])
def upload_files():
    uploaded_files = request.files.getlist('files')

    accepted_files = []
    rejected_files = []

    if not uploaded_files:
        return render_template('index.html', message="❌ No files uploaded.")

    for file in uploaded_files:
        if not (file and allowed_file(file.filename)):
            rejected_files.append(f"{file.filename} (invalid file type)")
            continue

        try:
            df = pd.read_excel(file)
            if 'PhoneNumber' not in df.columns:
                rejected_files.append(f"{file.filename} (missing 'PhoneNumber' column)")
                continue

            # Save only if valid
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.seek(0)  # Reset stream before saving
            file.save(file_path)
            accepted_files.append(file.filename)

        except Exception as e:
            rejected_files.append(f"{file.filename} (read error: {str(e).splitlines()[0]})")
            continue

    # Compose HTML message
    message_parts = []

    if accepted_files:
        uploaded_list = "<br>".join([f"✅ <b>{fname}</b>" for fname in accepted_files])
        message_parts.append(f"<div class='text-green-700 font-medium'>Uploaded:</div>{uploaded_list}")

    if rejected_files:
        rejected_list = "<br>".join([f"⚠️ <b>{fname}</b>" for fname in rejected_files])
        message_parts.append(f"<div class='text-red-700 font-medium mt-2'>Rejected:</div>{rejected_list}")

    final_message = "<br>".join(message_parts)

    return render_template('index.html', message=final_message)




@app.route('/scrub')
def scrub():
    folder_path = UPLOAD_FOLDER
    output_file = os.path.join(FINAL_FOLDER, "output_sheet.xlsx")

    if not os.path.exists(output_file):
        return render_template('index.html', message="⚠️ No output_sheet.xlsx found. Please remove duplicates first.")

    try:
        original_df = pd.read_excel(output_file)
    except Exception as e:
        return render_template('index.html', message=f"❌ Failed to read output sheet: {str(e)}")

    common_column = "PhoneNumber"
    skipped_files = []

    for file_name in os.listdir(folder_path):
        if file_name.endswith(".xlsx"):
            file_path = os.path.join(folder_path, file_name)

            try:
                external_df = pd.read_excel(file_path)
            except Exception:
                skipped_files.append(f"{file_name} (read error)")
                continue

            if common_column not in external_df.columns:
                skipped_files.append(f"{file_name} (missing 'PhoneNumber')")
                continue

            external_df = external_df[[common_column]].drop_duplicates()

            try:
                merged_df = pd.merge(original_df, external_df, on=common_column, how="left", indicator=True)
                non_matching_df = merged_df[merged_df["_merge"] == "left_only"].drop(columns=["_merge"])
                original_df = non_matching_df
            except Exception:
                skipped_files.append(f"{file_name} (merge error)")
                continue

    try:
        original_df.to_excel(output_file, index=False)
    except Exception as e:
        return render_template('index.html', message=f"❌ Failed to write output sheet: {str(e)}")

    # ✅ Delete all files from uploads folder
    for f in os.listdir(folder_path):
        try:
            os.remove(os.path.join(folder_path, f))
        except Exception:
            continue  # Avoid crash if file is in use or locked

    # 📨 Generate message
    if skipped_files:
        skipped_html = "<br>".join([f"⚠️ <b>{fname}</b> skipped" for fname in skipped_files])
        return render_template(
            'index.html',
            message=f"✅ Scrubbed successfully! <a href='/download_output' class='underline text-blue-700'>Download Output Sheet</a><br>{skipped_html}"
        )
    else:
        return render_template(
            'index.html',
            message="✅ Scrubbed successfully! <a href='/download_output' class='underline text-blue-700'>Download Output Sheet</a>"
        )


@app.route('/download_output')
def download_output():
    path = FINAL_FOLDER
    filename = "output_sheet.xlsx"
    return send_from_directory(path, filename, as_attachment=True)

@app.route('/check_output_ready')
def check_output_ready():
    output_file_exists = os.path.exists(os.path.join(FINAL_FOLDER, "output_sheet.xlsx"))
    uploads_exist = any(f.endswith(".xlsx") for f in os.listdir(UPLOAD_FOLDER))
    return {"ready": output_file_exists and uploads_exist}


os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(FINAL_FOLDER, exist_ok=True)

if __name__ == '__main__':
    app.run(debug=True)

