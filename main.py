from flask import Flask, render_template, request, jsonify
import pytesseract
from PIL import Image
import difflib
import os
import base64
import time
import threading
import uuid

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

progress = {}

def extract_text_from_file(file_path, task_id):
    global progress
    progress[task_id]['step'] = f'Processing {os.path.basename(file_path)}'

    file_extension = os.path.splitext(file_path)[1].lower()

    if file_extension in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            # Add name matching logic here
            name_list = ["Alice", "Bob", "Charlie", "David", "Eve"]  # Sample name list
            matched_name = None
            for name in name_list:
                if text.startswith(name[:2]):
                    matched_name = name
                    break
            if matched_name:
                progress[task_id]['step'] += f' - Matched Name: {matched_name}'
        except Exception as e:
            text = f"Error processing image: {str(e)}"
    elif file_extension == '.pdf':
        text = "PDF text extraction not available. File treated as binary."
    else:
        text = f"Unsupported file type: {file_extension}"

    # Simulate progress for demonstration purposes
    for i in range(1, 11):
        time.sleep(0.5)  # Simulate processing time
        progress[task_id]['progress'] += 2  # Increase by 2% for each file (assuming max 5 files)

    return text.strip()

def compare_texts(texts, task_id):
    global progress
    progress[task_id]['step'] = 'Comparing files'
    results = []
    base_text = texts[0]  # Use the first text as the base for comparison
    for i, text in enumerate(texts[1:], start=1):
        matcher = difflib.SequenceMatcher(None, base_text, text)
        similarity = matcher.ratio() * 100
        results.append({
            'file1': 'Base File',  # Label the base file
            'file2': f'File {i+1}',
            'similarity': f"{similarity:.2f}%"
        })
        progress[task_id]['progress'] += 2  # Increase progress for each comparison
        # NEW CODE: Check for matching letters (2 or more)
        matching_letters = []
        for k in range(len(base_text)):
            if k < len(text) and base_text[k] == text[k]:
                matching_letters.append(base_text[k])
        if len(matching_letters) >= 2:
            results.append({
                'file1': 'Base File',  # Label the base file
                'file2': f'File {i+1}',
                'matching_letters': ''.join(matching_letters)
            })

    return results

def process_files(file_paths, task_id):
    global progress
    progress[task_id] = {'step': 'Starting', 'progress': 0}

    texts = []
    for file_path in file_paths:
        text = extract_text_from_file(file_path, task_id)
        texts.append(text)

    comparison_results = compare_texts(texts, task_id)

    file_contents = []
    for file_path in file_paths:
        with open(file_path, "rb") as file:
            file_content = base64.b64encode(file.read()).decode('utf-8')
            file_contents.append({
                'name': os.path.basename(file_path),
                'content': file_content
            })

    progress[task_id] = {
        'step': 'Completed',
        'progress': 100,
        'result': {
            'texts': texts,
            'comparisons': comparison_results,
            'files': file_contents
        }
    }

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/compare', methods=['POST'])
def compare_files():
    if 'files[]' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    files = request.files.getlist('files[]')
    if not files or files[0].filename == '':
        return jsonify({'error': 'No selected file'}), 400

    task_id = str(uuid.uuid4())
    file_paths = []

    for file in files:
        filename = file.filename
        file_path = os.path.join(UPLOAD_FOLDER, f'{task_id}_{filename}')
        file.save(file_path)
        file_paths.append(file_path)

    threading.Thread(target=process_files, args=(file_paths, task_id)).start()

    return jsonify({'task_id': task_id})

@app.route('/progress/<task_id>', methods=['GET'])
def get_progress(task_id):
    global progress
    return jsonify(progress.get(task_id, {'step': 'Not found', 'progress': 0}))

if __name__ == '__main__':
    app.run(debug=True)