def main():
    from daveFunctions.ev3Functions import ev3Handler as EV3
    from daveFunctions.threadHandler import threadHandler
    from daveFunctions.audioFunctions import Listening, Speaking
    from daveFunctions.visionFunctions import visionHandler as Vision
    from daveFunctions.geminiFunctions import GeminiHandler as Gemini
    import daveFunctions.featureFunctions as feature

    # Connect to the EV3, initialize the motors, center the eyes and close the jaw
    with EV3() as ev3:

        # Create instances of the classes
        vision = Vision()
        listening = Listening()
        speaking = Speaking(sync_jaw=ev3.sync_jaw, move_eyebrows=ev3.move_eyebrows, move_to_emotion=ev3.move_to_emotion, move_to_neutral=ev3.move_to_neutral) # Give the callable functions to the SpeakingHandler
        gemini = Gemini(vision.set_mode, vision.recognize_face, feature.get_weather_data, feature.get_time_and_date, feature.retrieve_personal_information, feature.play_rock_paper_scissors) # Give the callable functions to the GeminiHandler

        # Define thread handler class and start the threads
        with threadHandler(eye_tracking=ev3.eye_tracking, visualize=vision.visualize, create_centered_window=vision.create_centered_window, face_hand_detection=vision.face_hand_tracking, calculate_relative_coords=vision.calculate_relative_coords, set_random_tracking=vision.set_random_tracking):

            # Pass on functions for minigames
            feature.pass_functions(vision.set_mode, vision.get_fingers_up, speaking.say, vision.get_window_bounding_box())

            # Start main loop
            justTalked = False
            while True:
                if not justTalked:
                    # Waiting for: "Hey dave" if the conversation isn't ongoing
                    print("Say: 'Hey Dave'")
                    listening.wait_for_keyword("hey dave")
                    justTalked = True

                # Listening for question until stopped speaking
                print("Dave is listening...")
                ev3.move_eyebrows("listening")
                prompt, audible = listening.speech_recognition()
                ev3.move_eyebrows("neutral")

                # Returning to beginning of loop if no question detected and print why there was no question
                if not audible:
                    print(prompt)
                    justTalked = False
                    continue

                # Checking if the code should be aborted
                if prompt.lower() == "shut down":
                    print("User > " + prompt+"\nShutting down...")
                    break

                # Sending the detected question and current frame of the vision to Gemini, to get a response
                print("User > " + prompt)
                response, emotion = gemini.get_chat_response(prompt, vision.get_frame())

                # Printing and saying the response
                print("Emotion: " + emotion + "\nDave > " + response)
                speaking.say(response, emotion)
    

if __name__ == "__main__":
    print("Starting...")
    main()