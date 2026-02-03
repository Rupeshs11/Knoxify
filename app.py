"""
Knoxify - Text-to-Speech Web Application
Flask backend with AWS S3 and Polly integration
"""

import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, url_for, redirect
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024

# AWS config
SOURCE_BUCKET = os.getenv('SOURCE_BUCKET')
DESTINATION_BUCKET = os.getenv('DESTINATION_BUCKET')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

# Local folders
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), 'output')
ALLOWED_EXTENSIONS = {'txt'}

AVAILABLE_VOICES = ['Joanna', 'Matthew', 'Ivy', 'Kendra', 'Salli', 'Joey', 'Justin', 'Kevin']

jobs = {}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def get_s3_client():
    return boto3.client(
        's3',
        region_name=AWS_REGION,
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_job_id():
    return str(uuid.uuid4())[:8]


def validate_text_length(text, max_chars=3000):
    return len(text) <= max_chars


@app.route('/')
def index():
    return render_template('index.html', voices=AVAILABLE_VOICES)


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    voice = request.form.get('voice', 'Joanna')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Only .txt files are allowed'}), 400
    
    if voice not in AVAILABLE_VOICES:
        return jsonify({'error': 'Invalid voice selected'}), 400
    
    job_id = generate_job_id()
    filename = secure_filename(file.filename)
    file_content = file.read()
    
    try:
        text_content = file_content.decode('utf-8')
    except UnicodeDecodeError:
        return jsonify({'error': 'File must be valid UTF-8 text'}), 400
    
    if not validate_text_length(text_content):
        return jsonify({'error': 'Text exceeds maximum length (3000 characters)'}), 400
    
    if not text_content.strip():
        return jsonify({'error': 'File is empty'}), 400
    
    jobs[job_id] = {
        'status': 'processing',
        'voice': voice,
        'filename': filename,
        'text_content': text_content,
        'created_at': datetime.now().isoformat(),
        'audio_key': None,
        'error': None
    }
    
    # Upload to S3
    try:
        s3 = get_s3_client()
        s3_key = f"{job_id}/{filename}"
        
        s3.put_object(
            Bucket=SOURCE_BUCKET,
            Key=s3_key,
            Body=file_content,
            ContentType='text/plain',
            Metadata={'voice': voice, 'job_id': job_id}
        )
        
        jobs[job_id]['s3_key'] = s3_key
        
    except ClientError as e:
        jobs[job_id]['status'] = 'error'
        jobs[job_id]['error'] = str(e)
        return jsonify({'error': f'S3 upload failed: {str(e)}'}), 500
    except Exception as e:
        jobs[job_id]['status'] = 'error'
        jobs[job_id]['error'] = str(e)
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500
    
    return jsonify({
        'success': True,
        'job_id': job_id,
        'message': 'File uploaded. Processing started.'
    })


@app.route('/status/<job_id>')
def check_status(job_id):
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    
    # Check if audio exists in destination bucket
    if job['status'] == 'processing':
        try:
            s3 = get_s3_client()
            base_name = job['filename'].rsplit('.', 1)[0]
            audio_key = f"{job_id}/{base_name}.mp3"
            
            s3.head_object(Bucket=DESTINATION_BUCKET, Key=audio_key)
            
            job['status'] = 'ready'
            job['audio_key'] = audio_key
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                pass
            else:
                job['status'] = 'error'
                job['error'] = str(e)
    
    response = {
        'job_id': job_id,
        'status': job['status'],
        'voice': job['voice'],
        'filename': job['filename']
    }
    
    if job['status'] == 'ready':
        response['download_url'] = url_for('download_audio', job_id=job_id)
    
    if job['status'] == 'error':
        response['error'] = job.get('error', 'Unknown error occurred')
    
    return jsonify(response)


@app.route('/download/<job_id>')
def download_audio(job_id):
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    
    if job['status'] != 'ready':
        return jsonify({'error': 'Audio not ready yet'}), 400
    
    try:
        s3 = get_s3_client()
        base_name = job['filename'].rsplit('.', 1)[0]
        audio_key = f"{job_id}/{base_name}.mp3"
        
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': DESTINATION_BUCKET, 'Key': audio_key},
            ExpiresIn=300
        )
        
        return redirect(url)
        
    except ClientError as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500


@app.route('/voices')
def get_voices():
    return jsonify({'voices': AVAILABLE_VOICES})


@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'File size exceeds 50 KB limit'}), 413


@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    print(f"Source: {SOURCE_BUCKET}, Destination: {DESTINATION_BUCKET}")
    app.run(debug=True, host='0.0.0.0', port=5000)
