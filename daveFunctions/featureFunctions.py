import json
import requests
from datetime import datetime
import random
import cv2

# Get config info from json file
with open('config/config.json') as file:
    info = json.load(file)
    WEATHER_API_KEY = info["weather_api_key"]
    CITY_ID = info["weather_city_id"]
    RPS_FOLDER = info["RPS_location"]
    WEATHERAPI_URL = "https://api.openweathermap.org/data/2.5/weather?"
    VERBOSE = info["verbose_level"]

def pass_functions(choose_eye_mode: callable, hand_detection: callable, talking: callable, window_position: tuple):
    """
    Defines global functions that are used in play_rock_paper_scissors and play_I_spy

    Also uses the window's dimensions to calculate the bounding box of the rock paper scissors images

    Args:
        choose_eye_mode (callable): A function to set the tracking mode for the eyes of the robot
        hand_detection (callable): A function to detect the position of a hand, using the camera
        talking (callable): A function to say any string out loud with an emotion
        window_bounding_box (tuple): The coordinates of the top left of the window for Dave's vision
    """
    # Defining the global variables
    global set_eye_mode, get_fingers_up, say, window_bounding_box
    set_eye_mode = choose_eye_mode
    get_fingers_up = hand_detection
    say = talking

    # Load the rock image to get the proportions of the width and height
    test_img = cv2.imread(RPS_FOLDER+"/rock.jpg")
    img_h, img_w, _ = test_img.shape 
    aspect_ratio = img_h/img_w

    # Calculating the proper window size and location for the rock paper scissor images, based on the size and location of the main vision image
    x, y, w, h = window_position
    new_w = x
    new_h = int(new_w * aspect_ratio)

    # Shrink the image if the height exceeds the vision window's height
    if new_h > h:
        new_h = h
        new_w = int(h / aspect_ratio)
        new_x = x - new_w
    else:
        new_x = 0

    # Set the window bounding box (max width possible and max height possible up against the left side of the vision window)
    window_bounding_box = (new_x, y, new_w, new_h)

    if VERBOSE == 2:
        print(f"[DEBUG] [FEATURE] window bounding box: {window_bounding_box}")

def get_weather_data() -> str:
    """
    Retrieves weather data for the current location.

    Returns:
        str: Weather information including description, temperature and windspeed
    """
    # Debug if necessary
    if VERBOSE > 0:
        print("| Called the weather function returning: ", end="")

    # Define the weather API parameters
    params = {  
        "id": CITY_ID,  
        "units": "metric",  
        "appid": WEATHER_API_KEY
    }  

    # Get the response from the API
    response = requests.get(WEATHERAPI_URL, params=params)  
    weatherdata = response.json()

    # Formulate the weather in a sentence
    weatherstring = "Weather description: " + str(weatherdata["weather"][0]["description"]) + ", Temperature: " + str(round(weatherdata["main"]["temp"],1)) + "°C / " + str(round(float(weatherdata["main"]["temp"])* 9/5 + 32,1)) + "°F, Windspeed: " + str(round(weatherdata["wind"]["speed"],1)) + " meters per second / " + str(round(float(weatherdata["wind"]["speed"])* 2.2369,1)) + " miles per hour"
    
    # Debug if necessary
    if VERBOSE > 0:
        print(weatherstring)
    
    # return the weather
    return weatherstring

def get_time_and_date() -> str:
    """
    Retrieves the current time and date.
    Used to tell time or have context.

    Returns:
        str: Time, day of the week, date and year.
    """
    # Formulate the time
    timestring = "Time: " + datetime.now().strftime("%H:%M:%S") + " | Date: " + datetime.now().strftime('%A, %B %d, %Y')

    # Debug if necessary
    if VERBOSE > 0:
        print("| Called the time and date function returning:", timestring)

    # Return the time
    return timestring

def play_rock_paper_scissors() -> str:
    """
    Play a game of rock paper scissors.
    
    Returns:
        str: Summary of how the game went.
    """
    # Debug if necessary
    if VERBOSE > 0:
        print("| Starting game of Rock, Paper, Scissors")

    # Initialize game variables
    set_eye_mode(mode="hands")  # Switch to hand detection mode
    GameOver = False
    emotion = "neutral"

    # Start a loop for ties
    while not GameOver:

        # Say the line
        say("Ready? Rock, paper, scissors, shoot!", emotion)

        # Start a loop for incorrect detections
        while True:

            # Generate Dave's random choice
            dave_pick = random.choice(["rock", "paper", "scissors"])

            # Get user's hand gesture
            fingers_up = get_fingers_up()

            # Map hand gesture to user's pick
            if fingers_up:
                if fingers_up == [0, 0, 0, 0, 0]:
                    user_pick = "rock"
                    break
                elif fingers_up == [1, 1, 1, 1, 1]:
                    user_pick = "paper"
                    break
                elif fingers_up == [0, 1, 1, 0, 0]:
                    user_pick = "scissors"
                    break

        # Display Dave's pick
        rps_image = cv2.resize(cv2.imread(f"{RPS_FOLDER}/{dave_pick}.jpg"), (window_bounding_box[2], window_bounding_box[3]))
        cv2.imshow("Dave's pick", rps_image)
        cv2.setWindowProperty("Dave's pick", cv2.WND_PROP_TOPMOST, 1)
        cv2.moveWindow("Dave's pick", window_bounding_box[0], window_bounding_box[1])

        # Debug if necessary
        if VERBOSE > 0:
            print(f"| User: {user_pick} | Dave: {dave_pick}")

        # Determine winner
        if user_pick == dave_pick:
            say(f"We both picked {dave_pick}, let's try again!", emotion)
        elif (user_pick, dave_pick) in [("rock", "scissors"), ("scissors", "paper"), ("paper", "rock")]:
            winner = "User"
            GameOver = True
        elif (dave_pick, user_pick) in [("rock", "scissors"), ("scissors", "paper"), ("paper", "rock")]:
            winner = "Dave"
            GameOver = True

        try:
            cv2.waitKey(1000)  # Short delay for results
            cv2.destroyWindow("Dave's pick")
        except:
            pass

    set_eye_mode(mode="face")  # Switch back to face mode

    # Generate response based on winner
    if winner == "User":
        response = f"The match is over. You picked {dave_pick} and the user picked {user_pick}. Respond sad to this, like you're just talking to the user."
    else:
        response = f"The match is over. You picked {dave_pick} and the user picked {user_pick}. Respond happily to this, like you're just talking to the user."

    return response

def retrieve_personal_information() -> str:
    """
    Retrieves custom, additional information about the user.
    This is information that the user decided is good for the AI to know.

    Returns:
      str: Additional information about the user.
    """
    # Debug if necessary
    if VERBOSE > 0:
        print("| Called the retrieve_personal_information function")

    # Return the contents of the personal_information.txt file
    with open("config/personal_information.txt") as file:
        return file.read()