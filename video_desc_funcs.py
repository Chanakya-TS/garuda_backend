import cv2
import time
import json

# Function to call OpenAI API
def ind_image(image_path, all_responses=None):
    
    # Read the image file in binary
    with open(image_path, 'rb') as image_file:
        image_data = image_file.read()

    prompt = (
        "Based on the image, provide the following information as a JSON object:\n\n"
        "Damage Severity: Describe the severity of the structural damage as 'minor', 'moderate', or 'severe'. "
        "(Optional: Provide a detailed description of the damage).\n"
        "Critical Response Level: Rate the urgency of the response needed on a scale of 1 (low) to 5 (high). "
        "(Optional: Explain why this level of response is needed).\n"
        "Damage Type: Categorize the type of damage as 'structural', 'fire-related', 'flood-related', or 'other'. "
        "(Optional: Further elaborate on the nature of the damage).\n"
        "Infrastructure Affected: List the types of infrastructure affected (choose from 'roads', 'bridges', 'buildings', or 'none'). "
        "(Optional: Give additional details about the extent of damage to each infrastructure type).\n"
        "Rescue Needed: Indicate if there are visible signs of people needing rescue or medical attention as 'yes' or 'no'. "
        "(Optional: Describe the situation in more detail if rescue is needed).\n"
        "Accessibility: State if major roads, highways, or bridges are 'accessible' or 'blocked'. "
        "(Optional: Provide more context about the accessibility issues).\n"
    )

    # Add all previous responses to the prompt if they exist
    if all_responses:
        prompt += f"\nPrevious responses:\n{all_responses}\n"

    # try:
    #     # Call the OpenAI API with the image and set a token limit of 1000
    #     response = openai.ChatCompletion.create(
    #         model="gpt-3.5-turbo",  # Specify your model
    #         messages=[
    #             {"role": "user", "content": prompt},
    #         ],
    #         temperature=0.7,
    #         max_tokens=1000  # Set the token limit to 1000
    #     )

    #     # Return the content of the response
    #     return response['choices'][0]['message']['content']
    
    # except Exception as e:
    #     print(f"Error calling OpenAI API: {e}")
    #     return None
    return prompt

# Function to call OpenAI API for final summary
def call_summary(all_responses):
    # openai.api_key = 'YOUR_API_KEY'  # Replace with your OpenAI API key

    # Prompt for the final summary
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

    # try:
    #     # Call the OpenAI API to generate the final summary
    #     response = openai.ChatCompletion.create(
    #         model="gpt-3.5-turbo",  # Specify your model
    #         messages=[
    #             {"role": "user", "content": prompt},
    #         ],
    #         temperature=0.7,
    #         max_tokens=1500  # Adjust token limit for longer summary
    #     )

        # Return the final summary
    #     return response['choices'][0]['message']['content']

    # except Exception as e:
    #     print(f"Error calling OpenAI API for summary: {e}")
    #     return None
    return prompt

# # Function to process video
# def process_video(video_path):
#     cap = cv2.VideoCapture(video_path)
#     frame_rate = int(cap.get(cv2.CAP_PROP_FPS))  # Get the frame rate of the video
#     frame_interval = frame_rate * 5  # Process every 5 seconds (frame_rate * 5)
#     all_responses = []  # Store responses from each frame

#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break

#         current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))

#         # Process every 5 seconds
#         if current_frame % frame_interval == 0:
#             # Save the frame as an image
#             frame_path = "frame.jpg"
#             cv2.imwrite(frame_path, frame)

#             # Show the frame
#             cv2.imshow('Video Frame', frame)
#             cv2.waitKey(1000)  # Show the frame for 1000 milliseconds (1 second)

#             # Concatenate all previous responses into one string
#             previous_responses_text = "\n".join(all_responses)

#             # Call the OpenAI API for the current frame, passing all previous responses
#             response = call_openai_api(frame_path, previous_responses_text)
#             if response:
#                 print(f"Response for frame {current_frame}: {response}")
#                 all_responses.append(response)  # Store response

#         # Break the loop if 'q' is pressed
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break

#     # After processing the last frame, generate the final summary
#     final_summary = call_openai_summary_api("\n".join(all_responses))
#     if final_summary:
#         print(f"\nFinal AI Summary of the Disaster:\n{final_summary}")

#     cap.release()
#     cv2.destroyAllWindows()  # Close all OpenCV windows
