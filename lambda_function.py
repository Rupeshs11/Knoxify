"""
Knoxify Lambda - Converts text files to MP3 using Amazon Polly
"""

import boto3
import os
import urllib.parse

s3 = boto3.client('s3')
polly = boto3.client('polly')

DESTINATION_BUCKET = os.environ.get('DESTINATION_BUCKET')


def lambda_handler(event, context):
    """Triggered when a .txt file is uploaded to source bucket"""
    
    record = event['Records'][0]
    source_bucket = record['s3']['bucket']['name']
    source_key = urllib.parse.unquote_plus(record['s3']['object']['key'])
    
    if not source_key.endswith('.txt'):
        return {'statusCode': 200, 'body': 'Skipped non-txt file'}
    
    try:
        # Get text file from S3
        response = s3.get_object(Bucket=source_bucket, Key=source_key)
        text_content = response['Body'].read().decode('utf-8')
        
        # Get voice from metadata
        metadata = response.get('Metadata', {})
        voice_id = metadata.get('voice', 'Joanna')
        
        # Convert to speech
        polly_response = polly.synthesize_speech(
            Text=text_content,
            OutputFormat='mp3',
            VoiceId=voice_id,
            Engine='neural'
        )
        
        audio_stream = polly_response['AudioStream'].read()
        
        # Save MP3 to destination bucket
        base_name = os.path.splitext(os.path.basename(source_key))[0]
        folder = os.path.dirname(source_key)
        output_key = f"{folder}/{base_name}.mp3" if folder else f"{base_name}.mp3"
        
        s3.put_object(
            Bucket=DESTINATION_BUCKET,
            Key=output_key,
            Body=audio_stream,
            ContentType='audio/mpeg'
        )
        
        return {'statusCode': 200, 'body': f'Converted {source_key}'}
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise e
