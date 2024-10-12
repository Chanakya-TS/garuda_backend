from flask import Flask, request, jsonify
import base64
import os
import subprocess

app = Flask(__name__)

# Ensure the tmp directory exists
os.makedirs('tmp', exist_ok=True)

# Endpoint to receive image and prompt
@app.route('/process', methods=['POST'])
def process_image_and_prompt():
    try:
        # Get the image and prompt from the request
        image_data = request.json.get('image')
        prompt = request.json.get('prompt')

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
