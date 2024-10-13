#!/usr/bin/env python3

from flask import Flask, request, jsonify
import cv2
import os
import subprocess

app = Flask(__name__)

# Ensure the tmp directory exists
os.makedirs('tmp', exist_ok=True)

@app.route('/process', methods=['POST'])
def process_video():
    data = request.get_json()
    if not data or 'video_path' not in data:
        return jsonify({'error': 'No video path provided'}), 400

    video_path = data['video_path']
    if not os.path.exists(video_path):
        return jsonify({'error': 'Video file does not exist'}), 400

    cap = cv2.VideoCapture(video_path)
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
    
    # Return JSON data for each frame and the final summary
    result = {
        'frames': all_responses,
        'summary': final_summary
    }
    return jsonify(result), 200


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


if __name__ == '__main__':
    app.run(host='localhost', port=8081)