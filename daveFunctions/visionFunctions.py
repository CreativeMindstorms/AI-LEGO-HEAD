
from cvzone.HandTrackingModule import HandDetector
from pygrabber.dshow_graph import FilterGraph
from screeninfo import get_monitors
from random import randint
import face_recognition
from time import time
import numpy as np
import PIL.Image
import json
import cv2

# This class does not include the Gemini Vision. For that, go to geminiFunctions.py
class visionHandler:
    def __init__(self, verbose: int = None):
        """
        Initializes the vision_handler class and sets up the camera.

        It selects the camera by name, initializes the capture and positions a window in the middle of the screen.

        Args:
            verbose (int, optional): level of debugging (0 = no printing, 1 = errors, 2 = full debugging)
        """

        try:
            # Retrieve configuration info from json files
            with open('config/config.json', 'r') as file:
                info = json.load(file)
                use_external_camera = info['use_external_camera']
                if use_external_camera:
                    camera_name = info['external_camera_name']
                else:
                    camera_name = info['internal_camera_name']
                haar_face_path = info['haar_face_path']
                face_encodings_path = info["face_encodings_path"]
                self.display_monitor_idx = info['display_monitor_idx']
                self.scale_factor = info['display_window_scale_factor']
                self.WINDOW_NAME = info['window_name']
                self.SHOW_FPS = info['show_fps']
                self.MIRROR_HANDS = info['mirror_hands']
                self.KNOWN_FACE_NAMES = info["face_names"]

                if verbose == None:
                    self.VERBOSE = info["verbose_level"]
                else:
                    self.VERBOSE = verbose

        except FileNotFoundError as e:
            # Catching FileNotFoundError to handle missing configuration files.
            # Expected behavior is to raise an exception and terminate the initialization.
            raise FileNotFoundError(f"[ERROR] [VISION] {e}. Please check if the config files exist.")
        
        except Exception as e:
            # Raise an error if the config file is not correctly formatted
            raise Exception(f"[ERROR] [VISION] {e}. Please check if the config files are correctly formatted.")
        
        self.mode = "face"
        self.label = "Unknown"
        self.face_names = []
        self.is_tracking = False
        self.is_locked = False
        self.track_position = None

        # used to calculate fps
        if self.SHOW_FPS:
            self.prev_frame_time = time()
            self.new_frame_time = time()

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [VISION] Setting up capture...")

        # Set up video capture
        camera_idx = self.get_camera(camera_name)
        self.capture = cv2.VideoCapture(camera_idx)
        _, self.img = self.capture.read()

        # Debug
        if self.VERBOSE == 2:
            print(f"[DEBUG] [VISION] Camera capture created for '{camera_name}'.")
            print("[DEBUG] [VISION] Setting up face detection...")

        # Set up face tracking
        self.haar_cascade = cv2.CascadeClassifier(haar_face_path)

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [VISION] Setting up hand detection...")

        # Set up hand tracking
        self.hand = None
        self.hand_detector = HandDetector(maxHands=2, detectionCon=0.80)

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [VISION] Setting up face recognition...")

        # Loading the face encodings.
        face_encodings_file = open(face_encodings_path, "r")
        self.KNOWN_FACE_ENCODINGS = eval(face_encodings_file.read().replace('array', 'np.array'), {'np': np})

        # Determine the bounding box for the camera window
        self.calculate_window_bbox()

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [VISION] Setup complete.")

    def get_camera(self, camera_name):
        """
        Retrieves the camera index based on the given camera name.
        
        Args:
            camera_name (str): Name of the camera to be used.

        Returns:
            int: Camera index.
        """

        # Retrieve devices
        devices = FilterGraph().get_input_devices()

        # Create a dictionary of available cameras
        available_cameras = {}
        for device_index, device_name in enumerate(devices):
            available_cameras[device_index] = device_name

        # Debug
        if self.VERBOSE == 2:
            print(f"[DEBUG] [VISION] Available cameras: {list(available_cameras.values())}")

        # Get the index of the selected camera
        try:
            camera_idx = list(available_cameras.values()).index(camera_name)

        except ValueError:
            # Raise an error if the camera name is not found
            raise ValueError(f"[ERROR] [VISION] Camera '{camera_name}' not found in the list of available cameras: {list(available_cameras.values())}")

        # Debug
        if self.VERBOSE == 2:
            print(f"[DEBUG] [VISION] Index for camera '{camera_name}': {camera_idx}")

        return camera_idx

    def calculate_window_bbox(self):
        """
        Calculates the bounding box for the centered window based on the configuration and camera capture
        """
        # Get monitor information
        monitors = get_monitors()

        # Debug
        if self.VERBOSE == 2:
            print(f"[DEBUG] [VISION] Detected monitors: {monitors}")

        # Check if the display monitor index is out of range
        if self.display_monitor_idx >= len(monitors):
            raise ValueError(f"Monitor index {self.display_monitor_idx} is out of range. {len(monitors)} monitor(s) detected.")

        # Get the display monitors information
        monitor = monitors[self.display_monitor_idx]
        monitor_width, monitor_height = monitor.width, monitor.height

        # Debug
        if self.VERBOSE == 2:
            print(f"[DEBUG] [VISION] Display monitor: {monitor.name} ({monitor_width}x{monitor_height})")

        # Check if the capture is opened
        if not self.capture.isOpened():
            raise ValueError(f"Unable to open video: {self.capture}")

        # Capture video dimensions
        video_width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        video_height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Scale video dimensions
        window_width = int(video_width * self.scale_factor)
        window_height = int(video_height * self.scale_factor)

        # Ensure window size does not exceed monitor size
        self.WINDOW_WIDTH = min(window_width, monitor_width)
        self.WINDOW_HEIGHT = min(window_height, monitor_height)

        # Calculate top-left corner for centering
        self.x_offset = monitor.x + (monitor_width - self.WINDOW_WIDTH) // 2
        self.y_offset = monitor.y + (monitor_height - self.WINDOW_HEIGHT) // 2

    def create_centered_window(self):
        """
        Creates a window in the middle of the screen based on the given monitor index and scale factor.

        Raises:
            ValueError: If the monitor index is out of range or if the video capture is not opened.
        """

        # Debug
        if self.VERBOSE == 2:
            print(f"[DEBUG] [VISION] Creating window...")
            print(f"[DEBUG] [VISION] Window size: {self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")
            print(f"[DEBUG] [VISION] Window position: ({self.x_offset}, {self.y_offset})")

        # Create a named window
        cv2.namedWindow(self.WINDOW_NAME)
        cv2.setWindowProperty(self.WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)

        # Move the window to the desired position
        cv2.moveWindow(self.WINDOW_NAME, self.x_offset, self.y_offset)

        # Resize the window
        cv2.resizeWindow(self.WINDOW_NAME, self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

    def get_window_bounding_box(self):
        """
        Get the window position of Dave's video

        Returns:
            tuple: x and y coordinate in pixels of the top right corner of the window and width and height of the frame
        """
        return (self.x_offset, self.y_offset, self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

    def visualize(self):
        """
        Displays the camera feed with overlaid bounding boxes and labels in a cv2 window.

        This function is also responsible for capturing the current frame.
        """

        # Capture the current frame
        _, self.img = self.capture.read()
        display_img = self.img.copy()

        # Set the thickness of the bounding boxes and labels
        thickness = int(2/self.scale_factor) if 2/self.scale_factor > 0.5 else 1

        # Overlaying bounding boxes and labels
        if self.is_tracking:
            try:
                cv2.rectangle(display_img, (self.track_position[0], self.track_position[1]), (self.track_position[0]+self.track_position[2], self.track_position[1]+self.track_position[3]), (0, 255, 0), 2)
                cv2.putText(display_img, self.label, (int(self.track_position[0]+10/self.scale_factor), int(self.track_position[1]+30/self.scale_factor)), cv2.FONT_HERSHEY_SIMPLEX, 1/self.scale_factor, (0, 255, 0), thickness, cv2.LINE_AA)
            except: pass
            
        if self.SHOW_FPS:
            # Calculate the FPS
            self.new_frame_time = time() 
            fps = str(int(1/(self.new_frame_time-self.prev_frame_time)))
            self.prev_frame_time = self.new_frame_time

            # putting the FPS count on the frame
            cv2.putText(display_img, "fps: "+fps, (int(10/self.scale_factor), int(30/self.scale_factor)), cv2.FONT_HERSHEY_SIMPLEX, 1/self.scale_factor, (0, 255, 0), thickness, cv2.LINE_AA)

        # Resize the image to fit the window
        display_img = cv2.resize(display_img, (self.WINDOW_WIDTH, self.WINDOW_HEIGHT))

        # Display the camera feed
        cv2.imshow(self.WINDOW_NAME, display_img)

        # Wait for a key press for 1 ms (to update the window)
        cv2.waitKey(1)

    def face_hand_tracking(self) -> tuple[bool, tuple[float, float, float, float]]:
        """
        Tracks faces or hands based on the current mode.

        Checks the current mode and calls the corresponding tracking function.
        If the mode is set to "face", it tracks faces.
        If the mode is set to "right hand", "left hand" or "hands", it tracks hands.
        If no hands are detected, it tracks faces.

        Also sets the label based on the tracking result.

        Returns:
            tuple:
                bool: True if a face or hand is detected, False otherwise.
                tuple: Absolute pixel coordinates of the detected face or hand. (x, y, w, h)
        """
        is_tracking = False
        # If the mode is set to "right hand", "left hand" or "hands", track hands
        if self.mode.lower() in ["right hand", "left hand", "hands"]:
            is_tracking, track_position = self.hand_tracking()

            # If a hand is detected, set the label to the hand type
            if is_tracking:
                self.label = self.mode.split()[0].capitalize() if self.mode != "hands" else "Hand"

        # If no hands are detected or the mode is set to "face", track faces
        if self.mode == "face" or not is_tracking:
            is_tracking, track_position = self.face_tracking()

            # If a face is detected, set the label to the first name in the list
            if is_tracking:
                self.label = self.face_names[0].split()[0] if self.face_names else "Unknown"

        if is_tracking:
            # Update the variables and unlock tracking
            self.track_position = track_position
            self.is_tracking = True
            self.is_locked = False

            # Return the tracking status and the relative coordinates
            return True, self.track_position
        
        else:
            # Update the local variable if it isn't locked (looking at random other position)
            if not self.is_locked: self.is_tracking = False

            # Return False and None
            return False, None

    def set_random_tracking(self):
        """
        Function that can be called to create a random bounding box to track, within the frame.

        Will update the self.track_position, set the self.is_tracking to true and self.label to "Focus"
        Will also lock the self.is_tracking with self.is_locked

        Returns:
            tuple: Absolute pixel coordinates of the random box. (x, y, w, h)
        """
        # Determine random bounding box
        # Size between 5% and 40% of the smalles dimension of the window
        # Then x and y random within the available space
        size = int(min(self.WINDOW_WIDTH/self.scale_factor, self.WINDOW_HEIGHT/self.scale_factor) * (randint(5, 40)/100))
        x = randint(0, self.WINDOW_WIDTH/self.scale_factor-size)
        y = randint(0, self.WINDOW_HEIGHT/self.scale_factor-size)

        # Set the tracking to true and set correct label
        self.is_tracking = True
        self.is_locked = True
        self.label = "Focus"

        self.track_position = (x, y, size, size)

        return self.track_position

    def calculate_relative_coords(self, track_position):
        """
        Transfers the track_position with pixel coordinates in the image to relative coordinates

        Args:
            track_position (tuple): Absolute pixel coordinates of the detected face or hand. (x, y, w, h)

        Returns:
            tuple: Relative coordinates of the detected face or hand. (x, y, w, h) (x, y ranging from -1.0 to 1.0 and w, h from 0.0 to 1.0)
        """

        # Calculate the relative coordinates of the detected bbox
        x, y, w, h = track_position
        x = x / (self.img.shape[1]//2) - 1
        y = y / (self.img.shape[0]//2) - 1
        w /= self.img.shape[1]
        h /= self.img.shape[0]
        track_position = (x, y, w, h)

        # Make sure the tracking position is within the bounds
        track_position = tuple(max(-1.0, min(1.0, i)) for i in track_position)

        # Return the tracking status and the relative coordinates
        return track_position

    def face_tracking(self) -> tuple[bool, tuple]:
        """
        Tracks the coordinates of any face.

        Returns:
            tuple:
                bool: True if a face is detected, False otherwise.
                tuple: Coordinates of the detected face. (None if no hand is detected)
        """
        # Convert the image to grayscale
        face_img = cv2.cvtColor(self.img.copy(), cv2.COLOR_BGR2GRAY)

        # Detect faces in the image
        faces_rect = self.haar_cascade.detectMultiScale(face_img, scaleFactor=1.1, minNeighbors=10)

        # Check if any faces are detected
        if len(faces_rect) > 0:

            # Update the track position
            track_position = (faces_rect[0][0], faces_rect[0][1], faces_rect[0][2], faces_rect[0][3])

            # Return True if a face is detected and the coordinates of the face
            return True, track_position
        
        # Return False if no faces are detected
        else:
            return False, None

    def hand_tracking(self) -> tuple[bool, tuple]:
        """
        Tracks the coordinates of hands.

        Returns:
            tuple:
                bool: True if a hand is detected, False otherwise.
                tuple: Coordinates of the detected hand. (None if no hand is detected)
        """
        # Copy the current frame
        hand_img = self.img.copy()

        # Detect hands in the image
        hands, _ = self.hand_detector.findHands(hand_img, draw=False, flipType=self.MIRROR_HANDS)

        # Check if any hands are detected
        if hands:

            # If the mode is set to "hands", track the first hand detected
            if self.mode == "hands":
                track_position = hands[0]["bbox"]
                self.hand = hands[0]
            
            # Otherwise, check which hand to track
            else:
                if self.mode == "right hand":
                    search = "Right"
                elif self.mode == "left hand":
                    search = "Left"
                else:
                    return False, None

                # Get the coordinates of the hand
                for hand in hands:
                    if hand['type'] == search:
                        track_position = hand["bbox"]
                        self.hand = hand
                        break


            # Return True if a hand is detected and the coordinates of the hand
            try:
                return True, track_position

            # Return False if the correct side (left or right) is not detected
            except: 
                pass
        
        # Return False if no hands are detected
        self.hand = None
        return False, None

    def recognize_face(self) -> list:
        """
        Recognizes faces in the current frame.

        Let's the robot know who is in front of it by recognizing faces.

        Returns:
            list: List of recognized faces.
        """

        # Resize frame of video to 1/4 size for faster face recognition
        small_frame = cv2.resize(self.img.copy(), (0, 0), fx=0.25, fy=0.25)

        # Convert the image from BGR  to RGB color
        rgb_small_frame = np.ascontiguousarray(small_frame[:, :, ::-1])

        # Find all the faces and face encodings in the current frame of video
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        # Initialize the list of recognized faces
        self.face_names = []

        for face_encoding in face_encodings:

            # See if the face is a match for the known face(s)
            matches = face_recognition.compare_faces(self.KNOWN_FACE_ENCODINGS, face_encoding)
            name = "Unknown"

            # Use the known face with the smallest distance to the new face
            face_distances = face_recognition.face_distance(self.KNOWN_FACE_ENCODINGS, face_encoding)
            best_match_index = np.argmin(face_distances)

            # If a match is found, set the name to the known face
            if matches[best_match_index]:
                name = self.KNOWN_FACE_NAMES[best_match_index]

            # Append the name to the list of recognized faces
            self.face_names.append(name)

        # Debug
        if self.VERBOSE > 0:
            print(f"| Called the face recognition function returning: {self.face_names}")

        return self.face_names

    def get_fingers_up(self) -> list:
        """
        Count the numbers of fingers raised for the currently tracked hand in the current frame

        Returns:
            list: The fingers that are currently up (0 or 1 for: [thumb - pinky]) or None if unsuccesful
        """
        if self.hand:

            # Try to detect the fingers
            try:
                fingers_up = self.hand_detector.fingersUp(self.hand)

                # Debug if necessary
                if self.VERBOSE == 2:
                    print(f"[DEBUG] [VISION] Checking fingers up for the hand: {fingers_up}")

                return fingers_up
            
            except:
                # Debug if necessary
                if self.VERBOSE == 2:
                    print(f"[DEBUG] [VISION] No fingers found.")

        # Debug if necessary
        if self.VERBOSE == 2:
            print(f"[DEBUG] [VISION] No hand detected.")

        return None

    def set_mode(self, mode: str) -> bool:
        """
        Set what the lego robotic head should be looking at.
        Set the mode for eye tracking.

        Args:
            mode (str): What to be looking at.(One of the following: "right hand", "left hand", "hands" or "face")

        Returns:
            bool: True if the given mode is valid and therefore if the mode selection was succesful, False otherwise.
        """

        # Debug
        if self.VERBOSE > 0:
            print(f"| Called the eye-mode function with mode: '{mode}'")

        # Check if the mode is valid and set it
        if mode in ["right hand", "left hand", "hands", "face"]:
            self.mode = mode
            return True
        else:
            return False

    def get_frame(self) -> object:
        """
        Retrieve the current frame.

        Returns:
            PIL.Image.Image: Current frame converted from a numpy.ndarray
        """
        
        # Convert the image from BGR to RGB
        img = cv2.cvtColor(self.img.copy(), cv2.COLOR_BGR2RGB)

        # Mirror the image if the hands are mirrored
        if self.MIRROR_HANDS:
            img = cv2.flip(img, 1)

        # Convert the numpy array to a PIL image
        return PIL.Image.fromarray(img)
    
    def __del__(self):
        """
        Destructor for the visionHandler class.

        Releases the camera and closes the cv2 windows.
        """

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [VISION] Exit.")

        # Release the camera and close the cv2 windows
        self.capture.release()
        cv2.destroyAllWindows()
    
    def __exit__(self):
        """
        Exit function for the visionHandler class.
        
        Releases the camera and closes the cv2 windows.
        """

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [VISION] Exit.")

        # Release the camera and close the cv2 windows
        self.capture.release()
        cv2.destroyAllWindows()








# Example usage of the vision_handler class
if __name__ == "__main__":
    # Create an instance of the vision_handler class
    vision = visionHandler(verbose=1)

    # Create a window in the middle of the screen
    vision.create_centered_window()

    # Retrieve the bounding box of the window
    vision.get_window_bounding_box()

    # Main loop
    while True:

        # Set the mode to track faces if the user presses 'f'
        if cv2.waitKey(1) & 0xFF == ord('f'):
            vision.set_mode("face")

        # Set the mode to track the right hand if the user presses 'r'
        if cv2.waitKey(1) & 0xFF == ord('r'):
            vision.set_mode("right hand")

        # Set the mode to track the left hand if the user presses 'l'
        if cv2.waitKey(1) & 0xFF == ord('l'):
            vision.set_mode("left hand")

        # Set the mode to track both hands if the user presses 'h'
        if cv2.waitKey(1) & 0xFF == ord('h'):
            vision.set_mode("hands")

        # Track faces and hands
        face_hand_tracking = vision.face_hand_tracking()

        # Recognize faces if user presses 'd'
        if cv2.waitKey(1) & 0xFF == ord('d'):
            faces = vision.recognize_face()

        # Visualize the camera feed
        vision.visualize()