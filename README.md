# Knoxify - Text to Speech Web Application

A modern web application that converts text files to natural-sounding speech using AWS Polly. Upload a `.txt` file, select a voice, and download the generated MP3 audio.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)
![AWS](https://img.shields.io/badge/AWS-Polly%20%7C%20S3%20%7C%20Lambda-orange.svg)

## Features

- 📄 Upload `.txt` files (max 50 KB)
- 🎙️ Choose from 8 AI voices (Joanna, Matthew, Ivy, Kendra, etc.)
- ⚡ Automatic text-to-speech conversion via AWS Lambda
- 🎧 Play and download generated MP3 audio
- 🌙 Clean dark theme UI

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Browser   │────▶│   Flask App      │────▶│  S3 Source      │
│             │     │   (Python)       │     │  Bucket         │
└─────────────┘     └──────────────────┘     └────────┬────────┘
                                                      │
                                                      ▼ (S3 Trigger)
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Browser   │◀────│  Pre-signed URL  │◀────│  Lambda + Polly │
│  (Download) │     │                  │     │                 │
└─────────────┘     └──────────────────┘     └────────┬────────┘
                                                      │
                                                      ▼
                                             ┌─────────────────┐
                                             │  S3 Destination │
                                             │  Bucket (.mp3)  │
                                             └─────────────────┘
```

## Project Structure

```
Knoxify-webTTS/
├── app.py                 # Flask backend
├── lambda_function.py     # AWS Lambda function code
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (not in repo)
├── .gitignore
├── templates/
│   └── index.html         # Main UI template
├── static/
│   ├── css/style.css      # Dark theme styles
│   └── js/main.js         # Frontend logic
└── README.md
```

---

## AWS Setup Guide

### Prerequisites

- AWS Account
- AWS CLI configured (optional)

### Step 1: Select AWS Region

Set your region to **us-east-1** (N. Virginia) for all resources.

---

### Step 2: Create S3 Buckets

#### Source Bucket (for uploaded text files)

1. Go to **S3** → **Create bucket**
2. Name: `knoxify-source-bucket`
3. Region: `us-east-1`
4. Keep **Block all public access** enabled
5. Click **Create bucket**

#### Destination Bucket (for generated audio)

1. Go to **S3** → **Create bucket**
2. Name: `knoxify-destination-bucket`
3. Region: `us-east-1`
4. Keep **Block all public access** enabled
5. Click **Create bucket**

---

### Step 3: Create IAM Policy

1. Go to **IAM** → **Policies** → **Create policy**
2. Click **JSON** tab and paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": [
        "arn:aws:s3:::knoxify-source-bucket/*",
        "arn:aws:s3:::knoxify-destination-bucket/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["polly:SynthesizeSpeech"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

3. Name: `KnoxifyLambdaPolicy`
4. Click **Create policy**

---

### Step 4: Create IAM Role for Lambda

1. Go to **IAM** → **Roles** → **Create role**
2. Trusted entity: **AWS service**
3. Use case: **Lambda**
4. Attach policy: `KnoxifyLambdaPolicy`
5. Name: `knoxify-lambda-role`
6. Click **Create role**

---

### Step 5: Create Lambda Function

1. Go to **Lambda** → **Create function**
2. Function name: `knoxify-text-to-speech`
3. Runtime: **Python 3.9**
4. Execution role: **Use existing role** → `knoxify-lambda-role`
5. Click **Create function**

#### Add Environment Variable

1. Go to **Configuration** → **Environment variables**
2. Add:
   - Key: `DESTINATION_BUCKET`
   - Value: `knoxify-destination-bucket`

#### Upload Code

1. Copy the contents of `lambda_function.py` from this repo
2. Paste into the Lambda code editor
3. Click **Deploy**

#### Configure Timeout

1. Go to **Configuration** → **General configuration**
2. Set timeout to **30 seconds**

---

### Step 6: Add S3 Trigger

1. In Lambda → **Configuration** → **Triggers**
2. Click **Add trigger**
3. Select **S3**
4. Bucket: `knoxify-source-bucket`
5. Event type: **PUT**
6. Suffix: `.txt`
7. Click **Add**

---

### Step 7: Create IAM User for Web App

1. Go to **IAM** → **Users** → **Create user**
2. Name: `knoxify-app-user`
3. Click **Next**
4. Select **Attach policies directly**
5. Attach:
   - `AmazonS3FullAccess`
   - `AmazonPollyFullAccess`
6. Click **Create user**

#### Generate Access Keys

1. Select the user → **Security credentials** tab
2. Click **Create access key**
3. Select **Application running outside AWS**
4. Save the **Access Key ID** and **Secret Access Key**

---

## Local Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/Knoxify-webTTS.git
cd Knoxify-webTTS
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1

SOURCE_BUCKET=knoxify-source-bucket
DESTINATION_BUCKET=knoxify-destination-bucket

SECRET_KEY=your-flask-secret-key
```

### 5. Run the Application

```bash
python app.py
```

Open your browser to **http://localhost:5000**

---

## API Endpoints

| Endpoint             | Method | Description                     |
| -------------------- | ------ | ------------------------------- |
| `/`                  | GET    | Homepage                        |
| `/upload`            | POST   | Upload text file + voice        |
| `/status/<job_id>`   | GET    | Check processing status         |
| `/download/<job_id>` | GET    | Download audio (pre-signed URL) |
| `/voices`            | GET    | List available voices           |

---

## Available Voices

| Voice   | Gender | Accent             |
| ------- | ------ | ------------------ |
| Joanna  | Female | US English         |
| Matthew | Male   | US English         |
| Ivy     | Female | US English (Child) |
| Kendra  | Female | US English         |
| Salli   | Female | US English         |
| Joey    | Male   | US English         |
| Justin  | Male   | US English (Child) |
| Kevin   | Male   | US English (Child) |

---

## Tech Stack

- **Frontend**: HTML, CSS, JavaScript (Vanilla)
- **Backend**: Python, Flask
- **Cloud**: AWS S3, Lambda, Polly
- **Auth**: AWS IAM, Pre-signed URLs


