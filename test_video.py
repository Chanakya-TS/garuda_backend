#!/usr/bin/env python3
import requests
import json


def test_flask():
    video_path = "/Users/shiven/Desktop/HackHarvard/test_vid.mp4"  # Replace with your video file path
    data = {'video_path': video_path}
    response = requests.post("http://localhost:8081/process", json=data)
    try:
        print(response.json())
    except requests.exceptions.JSONDecodeError:
        print("Response is not in JSON format")
    return "Hello, World!"

if __name__ == "__main__":
    print('starting test')
    test_flask()
    
