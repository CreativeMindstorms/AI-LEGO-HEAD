import threading
from time import sleep
import json
from random import randint

class threadHandler:
    def __init__(self, eye_tracking: callable, visualize: callable, create_centered_window: callable, face_hand_detection: callable, calculate_relative_coords: callable, set_random_tracking: callable,verbose: int = None) -> None:
        """
        Initializes the ThreadHandler class.

        Args:
            eye_tracking (callable): Function for eye tracking.
            visualize (callable): Function for visualization.
            face_hand_detection (callable): Function for face and hand detection.
            calculate_relative_coords (callable): Function to transform absolute coordinates of bounding boxes to relative coordinates (-1 to 1)
            verbose (int, optional): Verbosity level. Defaults to None.
        """

        try:
            # Retrieve configuration info from json files
            with open('config/config.json', 'r') as file:
                info = json.load(file)

                self.RANDOM_EYES_INTERVAL = info["random_eyes_interval"]

                if verbose == None:
                    self.VERBOSE = info["verbose_level"]
                else:
                    self.VERBOSE = verbose

        except FileNotFoundError as e:
            # Catching FileNotFoundError to handle missing configuration files.
            # Expected behavior is to raise an exception and terminate the initialization.
            raise FileNotFoundError(f"[ERROR] [THREADHANDLER] {e}. Please check if the config files exist in the correct location.")
        
        except Exception as e:
            raise Exception(f"[ERROR] [THREADHANDLER] {e}. Please check if the config files are correctly formatted.")
        
        self.eye_tracking = eye_tracking
        self.visualize = visualize
        self.face_hand_detection = face_hand_detection
        self.create_centered_window = create_centered_window
        self.calculate_relative_coords = calculate_relative_coords
        self.set_random_tracking = set_random_tracking
        self.end_thread = False
        self.vision_thread = None
        self.track_thread = None

        if self.VERBOSE == 2:
            print("[DEBUG] [THREADHANDLER] Initialized.")

    def start_threads(self) -> None:
        """
        Starts the necessary threads for tracking and visualization.
        """

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [THREADHANDLER] Starting threads...")

        # Start the threads
        self.vision_thread = threading.Thread(target=self.vision_handler)
        self.vision_thread.start()
        self.track_thread = threading.Thread(target=self.tracking_handler)
        self.track_thread.start()

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [THREADHANDLER] Threads started.")

    def vision_handler(self) -> None:
        """
        Continuously handles the vision functions (face and hand tracking and visualization).
        """

        # Create a window in the middle of the screen        
        self.create_centered_window()

        while not self.end_thread:
            # Visualize the vision
            self.visualize()

            # Add a small sleep interval to reduce CPU usage
            sleep(0.01)

    def tracking_handler(self) -> None:
        """
        Continuously tracks the eye position.
        """
        while not self.end_thread:
            try:
                # Track the position of the face/hand and determine if successful
                success, position = self.face_hand_detection()

                # Only track if face/hand was detected or when randomly looking at something
                if success or randint(0, self.RANDOM_EYES_INTERVAL) == 1:

                    # Calculate the coordinates (for success or random position)
                    position = self.calculate_relative_coords(
                        position if success else self.set_random_tracking()
                    )

                    if not success and self.VERBOSE == 2:
                        print(f"[DEBUG] [THREADHANDLER] Looking at random position: {position}")

                    # Move the eyes to the calculated position
                    self.eye_tracking(position)
            except Exception as e:
                if self.VERBOSE > 0:
                    print(f"[ERROR] [THREADHANDLER] {e}")

            # Add a small sleep interval to reduce CPU usage
            sleep(0.01)

    def __enter__(self):
        """
        Starts the threads when entering the context.
        """
        self.start_threads()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """
        Cleans up thread resources on exit.
        """
        self.end_thread = True
        if self.vision_thread is not None:
            self.vision_thread.join()
        if self.track_thread is not None:
            self.track_thread.join()

    def __del__(self):
        """
        Cleans up thread resources on deletion.
        """
        self.end_thread = True
        if self.vision_thread is not None:
            self.vision_thread.join()
        if self.track_thread is not None:
            self.track_thread.join()


# Thread handler class

# args: eye_tracking, visualize, face_hand_detection in __init__

# start_threads Starts eye_tracking and show_vision thread

# eye_tracking Thread that calls the face_hand_detection function, retrievs a position and then calls the track position function continuously until self.end_thread

# show_vision Thread that calls the visualize function

# Sets self.end_thread to True in __exit__ and __delete__