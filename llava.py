from flask import Flask, request, jsonify
import base64
import cv2
import os
import subprocess
import video_desc_funcs

app = Flask(__name__)

# Ensure the tmp directory exists
os.makedirs('tmp', exist_ok=True)

@app.route('/process', methods=['POST'])
def process_video(video_path):
    cap = cv2.VideoCapture(video_path)
    frame_rate = int(cap.get(cv2.CAP_PROP_FPS))  # Get the frame rate of the video
    frame_interval = frame_rate * 5  # Process every 5 seconds (frame_rate * 5)
    all_responses = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))

        # Process every 5 seconds
        if current_frame % frame_interval == 0:
            # Save the frame as an image
            frame_path = "frame.jpg"
            cv2.imwrite(frame_path, frame)

            # Show the frame
            cv2.imshow('Video Frame', frame)
            cv2.waitKey(1000)  # Show the frame for 1000 milliseconds (1 second)

            # Concatenate all previous responses into one string
            previous_responses_text = "\n".join(all_responses)

            # Call the OpenAI API for the current frame, passing all previous responses
            response = process_image_and_prompt(video_desc_funcs.ind_image(frame_path, previous_responses_text))
            if response:
                print(f"Response for frame {current_frame}: {response}")
                all_responses.append(response)  # Store response

        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # After processing the last frame, generate the final summary
    final_summary = process_image_and_prompt(video_desc_funcs.call_summary("\n".join(all_responses)))
    if final_summary:
        print(f"\nFinal AI Summary of the Disaster:\n{final_summary}")

    cap.release()
    cv2.destroyAllWindows()  # Close all OpenCV windows


# Endpoint to receive image and prompt
# @app.route('/process', methods=['POST'])
def process_image_and_prompt(image_data, prompt):
    try:
        # Decode the base64 image and save it to a temporary file
        image_path = 'tmp/image.png'
        with open(image_path, 'wb') as image_file:
            image_file.write(base64.b64decode(image_data))

        # Prepare the command to run Ollama with the Llava model
        command = f'ollama run llava'

        # Create the multi-line prompt
        multi_line_prompt = f"""
        {prompt}
        {image_path}
        """

        # Run the command and capture the output
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
        stdout, stderr = process.communicate(input=multi_line_prompt)

        # Check for errors
        if process.returncode != 0:
            return jsonify({'error': stderr}), 500

        # Return the output from Ollama
        return jsonify({'output': stdout.strip()}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='localhost', port=8081)