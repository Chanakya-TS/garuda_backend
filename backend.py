from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, storage
import os
import subprocess
import logging
import traceback
import cv2
from collections import defaultdict
import math

# Initialize Firebase
cred = credentials.Certificate("eagle-d9e67-firebase-adminsdk-nelqz-13125675d2.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'eagle-d9e67.appspot.com'
})

app = Flask(__name__)

# Ensure the tmp directory exists
os.makedirs('tmp', exist_ok=True)

# Set up logging
logging.basicConfig(level=logging.INFO)

@app.route('/process-video', methods=['POST'])
def process_video_drowning():
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

@app.route('/process', methods=['POST'])
def process_video_summary():
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

        # Define the path for the input video file in the current directory
        input_path = os.path.join(os.getcwd(), os.path.basename(video_link))

        # Download the video to the current directory
        logging.info(f"Downloading video to {input_path}")
        blob.download_to_filename(input_path)

        # Process the video
        cap = cv2.VideoCapture(input_path)
        frame_rate = int(cap.get(cv2.CAP_PROP_FPS))  # Get the frame rate of the video
        frame_interval = frame_rate * 5  # Process every 5 seconds (frame_rate * 5)
        all_responses = []
        frame_index = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))

            # Process every 5 seconds
            if current_frame % frame_interval == 0:
                # Save the frame as an image
                frame_path = f"tmp/frame_{frame_index}.jpg"
                cv2.imwrite(frame_path, frame)
                frame_index += 1

                # Concatenate all previous responses into one string
                previous_responses_text = "\n".join(all_responses)

                # Call the OpenAI API for the current frame, passing all previous responses for chain-of-thought reasoning
                prompt = create_chain_of_thought_prompt(frame_path, previous_responses_text)
                response = process_image_and_prompt(frame_path, prompt)
                if response:
                    print(f"Response for frame {current_frame}: {response}")
                    all_responses.append(response)  # Store response

        # After processing the last frame, generate the final summary
        final_summary_prompt = create_final_summary_prompt("\n".join(all_responses))
        final_summary = process_image_and_prompt(None, final_summary_prompt)
        cap.release()

        # Upload the final summary to Firebase
        summary_blob = bucket.blob(f"summary_{os.path.basename(video_link)}.txt")
        logging.info(f"Uploading summary to Firebase")
        summary_blob.upload_from_string(final_summary)
        summary_blob.make_public()

        # Generate a public URL for the summary
        summary_url = summary_blob.public_url
        logging.info(f"Summary available at: {summary_url}")

        # Clean up files
        # os.unlink(input_path)

        # Return JSON data for each frame and the final summary URL
        result = {
            'frames': all_responses,
            'summary_url': summary_url
        }
        return jsonify(result), 200

    except Exception as e:
        logging.error(f"An error occurred: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

def process_image_and_prompt(image_path, prompt):
    try:
        # Prepare the command to run Ollama with the Llava model
        command = f'ollama run llava'

        # Create the multi-line prompt
        multi_line_prompt = f"""
        {prompt}
        """
        if image_path:
            # If there's an image, add the image path to the prompt
            multi_line_prompt += f"\n{image_path}"

        # Run the command and capture the output
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
        stdout, stderr = process.communicate(input=multi_line_prompt)

        # Check for errors
        if process.returncode != 0:
            return f'Error: {stderr}'

        # Return the output from Ollama
        return stdout.strip()

    except Exception as e:
        return f'Error: {str(e)}'

def create_final_summary_prompt(all_responses):
    # Chain of thought prompt for the final summary
    prompt = (
        "You are given a sequence of observations about a disaster scene, where structural damage, infrastructure damage, "
        "accessibility, rescue needs, and other information have been reported frame by frame. Based on these observations, "
        "generate a comprehensive AI summary of the disaster, including:\n\n"
        "1. Overall damage severity and critical response level.\n"
        "2. Types of damage observed and affected infrastructure.\n"
        "3. Rescue needs observed throughout the video.\n"
        "4. Accessibility issues and areas of concern.\n"
        "5. Any other key aspects that require attention.\n\n"
        f"Here is the information collected from the video:\n{all_responses}\n"
    )
    return prompt

def create_chain_of_thought_prompt(image_path, all_responses=None):
    # Create a chain of thought prompt for processing an individual image
    prompt = (
        "Analyze the image and provide the following details as a JSON object:\n"
        "1. Damage Severity: ('minor', 'moderate', or 'severe').\n"
        "2. Critical Response Level: (1 to 5, where 5 is most urgent).\n"
        "3. Damage Type: ('structural', 'fire-related', 'flood-related', or 'other').\n"
        "4. Infrastructure Affected: (list of 'roads', 'bridges', 'buildings', or 'none').\n"
        "5. Rescue Needed: ('yes' or 'no').\n"
        "6. Accessibility: ('accessible' or 'blocked').\n"
        "\nExpected Output:\n"
        "{\n"
        "  \"damage_severity\": \"\",\n"
        "  \"critical_response_level\": 0,\n"
        "  \"damage_type\": \"\",\n"
        "  \"infrastructure_affected\": [],\n"
        "  \"rescue_needed\": \"\",\n"
        "  \"accessibility\": \"\"\n"
        "}"
    )

    # Add all previous responses to the prompt if they exist for chain of thought
    if all_responses:
        prompt += f"\nPrevious responses:\n{all_responses}"

    return prompt





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
        return "green", 5

if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=8081)
