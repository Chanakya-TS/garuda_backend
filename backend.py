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
# Geotagged data points (latitude, longitude)
data_points = [
    {"lat": 37.7749, "lon": -122.4194},  # San Francisco
    {"lat": 34.0522, "lon": -118.2437},  # Los Angeles
    {"lat": 40.7128, "lon": -74.0060},  # New York
    {"lat": 51.5074, "lon": -0.1278},  # London
    {"lat": 35.6895, "lon": 139.6917},  # Tokyo
    # Add more points here as needed
]
@app.route('/add_point', methods=['POST'])
def add_data_point():
    new_point = request.json
    data_points.append(new_point)
    print(data_points)
    return jsonify({"status": "success", "new_point": new_point}), 200

from collections import defaultdict
import math 
# Function to aggregate and output heatmap data
@app.route('/heatmap', methods=['GET'])
def get_heatmap_data():
    # Define grid size (in degrees)
    grid_size = 0.01  # Adjust this value to change the clustering distance

    # Aggregate data points into grid cells
    aggregated_data = defaultdict(lambda: {"lat_sum": 0, "lon_sum": 0, "count": 0})

    for point in data_points:
        grid_lat = math.floor(point["lat"] / grid_size)
        grid_lon = math.floor(point["lon"] / grid_size)
        key = (grid_lat, grid_lon)
        aggregated_data[key]["lat_sum"] += point["lat"]
        aggregated_data[key]["lon_sum"] += point["lon"]
        aggregated_data[key]["count"] += 1

    # Calculate average location and determine color intensity
    heatmap_data = []
    max_count = max(value["count"] for value in aggregated_data.values()) if aggregated_data else 1
    for key, value in aggregated_data.items():
        avg_lat = value["lat_sum"] / value["count"]
        avg_lon = value["lon_sum"] / value["count"]
        color, radius = determine_color(value["count"], max_count)
        heatmap_data.append({
            "location": {"lat": avg_lat, "lng": avg_lon},
            "count": value["count"],
            "color": color,
            "radius": radius
        })

    return jsonify(heatmap_data)

def determine_color(count, max_count):
    # Normalize the count to a value between 0 and 1
    normalized_count = count / max_count
    # Map the normalized count to a color spectrum
    if normalized_count > 0.75:
        return "red", 20
    elif normalized_count > 0.5:
        return "orange", 15
    elif normalized_count > 0.25:
        return "yellow", 10
    else:
        return ""
if __name__ == '__main__':
    app.run(debug=True)
