from flask import Flask, requests, json

def test_flask():
    video_file_path = "vid_trim.mp4"  # Replace with your video file path
    response = requests.post("http://localhost:8081/process", json=video_file_path)
    print(response)
    return "Hello, World!"

if __name__ == "__main__":
    print('starting test')
    test_flask()
