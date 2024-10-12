from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, storage
import os
import subprocess
import logging
import traceback

# Initialize Firebase
cred = credentials.Certificate("eagle-d9e67-firebase-adminsdk-nelqz-13125675d2.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'eagle-d9e67.appspot.com'
})

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)

@app.route('/process-video', methods=['POST'])
def process_video():
    # Get the Firebase video link from either JSON body or query parameters
    video_link = request.json.get('video_link') if request.is_json else request.args.get('video_link')
    if not video_link:
        return jsonify({'error': 'No video link provided'}), 400

    try:
        logging.info(f"Received request to process video: {video_link}")

        # Download the video from Firebase
        bucket = storage.bucket()
        blob = bucket.blob(video_link)
        if not blob.exists():
            logging.error(f"File not found in Firebase storage: {video_link}")
            return jsonify({'error': 'Video file not found in Firebase storage'}), 404

        # Define the paths for input and output video files in the current directory
        input_path = os.path.join(os.getcwd(), os.path.basename(video_link))
        output_path = input_path.replace('.mp4', '_processed.mp4')

        # Download the video to the current directory
        logging.info(f"Downloading video to {input_path}")
        blob.download_to_filename(input_path)

        # Process the video using main.py
        logging.info(f"Processing video {input_path} with main.py")
        subprocess.run(['python', 'main.py', input_path, output_path], check=True)

        # Upload the processed video back to Firebase
        output_blob = bucket.blob(f"processed_{os.path.basename(video_link)}")
        logging.info(f"Uploading processed video to Firebase: {output_path}")
        output_blob.upload_from_filename(output_path)
        output_blob.make_public()

        # Generate a public URL for the processed video
        output_url = output_blob.public_url
        logging.info(f"Processed video available at: {output_url}")

        # Clean up files
        # os.unlink(input_path)
        # os.unlink(output_path)

        return jsonify({'processed_video_url': output_url}), 200

    except subprocess.CalledProcessError as e:
        logging.error(f"Error while running main.py: {str(e)}")
        return jsonify({'error': 'Failed to process video'}), 500
    except Exception as e:
        logging.error(f"An error occurred: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
