import ev3_dc as ev3
import json
from time import sleep
import numpy as np

class ev3Handler:
    def __init__(self, verbose: int = None):
        """
        Initializes the EV3_handler class and connects to the robot.

        Sets up motor positions and retrieves any initial information from ev3_config.json.
        Ignores every function call if use_Mindstorms is false in config.json.

        Args:
            verbose (int): level of debugging (0 = no printing, 1 = basic info (ev3 connect), 2 = full debugging) (default = None)
        """

        try:
            # Retrieve configuration info from json files
            with open('config/config.json', 'r') as file:
                info = json.load(file)

                if verbose == None:
                    self.VERBOSE = info["verbose_level"]
                else:
                    self.VERBOSE = verbose

                self.use_Mindstorms = info["use_Mindstorms"]

            # Only continue if the EV3 is being used
            if not self.use_Mindstorms:

                # Debug
                if self.VERBOSE == 2:
                    print("[DEBUG] [EV3] Not using Mindstorms. Ignoring every function call.")

                return
                
            # Continue retrieving configuration info
            with open('config/ev3_config.json', 'r') as file:
                info = json.load(file)
                SIGHT_ADDRESS = info["EV3_SIGHT_ADDRESS"]
                MOUTH_ADDRESS = info["EV3_MOUTH_ADDRESS"]
                SPEEDS = info["speed"]

                self.EYEBROW_LISTENING_POSITION = info["relative_listening_position"]
                self.EYEBROW_RANGE = info["eyebrow_range"]
                self.MOUTH_RANGE = info["mouth_range"]

                self.JAW_DIRECTION = info["jaw_direction"]
                self.JAW_CLOSE_TIME = info["jaw_close_time"]
                self.JAW_SOUND_THRESHOLD = info["jaw_sound_threshold"]

                self.EYE_VERTICAL_AMPLITUDE = info["eye_vertical_amplitude"]
                self.EYE_HORIZONTAL_AMPLITUDE = info["eye_horizontal_amplitude"]
                self.NECK_AMPLITUDE = info["neck_amplitude"]
                self.NECK_EYE_DIFF = info["neck_eye_diff"]

                self.CAM_FOV = info["cam_fov"]
                self.CAM_HEIGHT_DIFF = info["cam_eye_height_diff"]
                self.CAM_ANGLE = info["cam_angle"]

                self.TOLERANCE = info["motor_tolerance"]
                self.EMOTIONS = info["emotions"]

        except FileNotFoundError as e:
            # Catching FileNotFoundError to handle missing configuration files.
            # Expected behavior is to raise an exception and terminate the initialization.
            raise FileNotFoundError(f"[ERROR] [EV3] {e}. Please check if the config files exist.")
        
        except Exception as e:
            # Raise an error if the config file is not correctly formatted
            raise Exception(f"[ERROR] [EV3] {e}. Please check if the config files are correctly formatted.")
        
        # Connect to the EV3
        self.connect(SIGHT_ADDRESS, MOUTH_ADDRESS)

        # Setup motors
        self.setup_motors(SPEEDS)

        # Center the eyes
        self.center_eyes(SPEEDS["eye_vertical_calibrate"], SPEEDS["eye_horizontal_calibrate"])

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [EV3] Closing jaw...")

        # Close the jaw
        self.close_jaw()

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [EV3] EV3 setup complete.")
        
    def connect(self, SIGHT_ADDRESS: str, MOUTH_ADDRESS: str):
        """
        Connects to the two Minstorms EV3 bricks in the robot.

        Args:
            SIGHT_ADDRESS (str): The address of the EV3 robot for the sight motors.
            MOUTH_ADDRESS (str): The address of the EV3 robot for the mouth motors.

        Raises:
            Exception: If the connection to the EV3 robot fails.
        """
        if self.use_Mindstorms:

            # Debug
            if self.VERBOSE == 2:
                print("[DEBUG] [EV3] Attempting to connect to EV3's...")

            # Connect to both EV3's
            self.ev3_sight = ev3.EV3(protocol=ev3.BLUETOOTH, host=SIGHT_ADDRESS)       # SIGHT_EV3
            if self.VERBOSE == 2: print("[DEBUG] [EV3]", end=" ")
            if self.VERBOSE > 0: print(self.ev3_sight)
            self.ev3_mouth = ev3.EV3(protocol=ev3.BLUETOOTH, host=MOUTH_ADDRESS)       # MOUTH_EV3
            if self.VERBOSE == 2: print("[DEBUG] [EV3]", end=" ")
            if self.VERBOSE > 0: print(self.ev3_mouth)

    def setup_motors(self, SPEEDS: dict):
        """
        Sets up the motors for the EV3 robot.

        Sets up the motors for the eyes, neck, eyebrows, jaw, and mouth corners.
        """
        if self.use_Mindstorms:

            # Debug
            if self.VERBOSE == 2:
                print("[DEBUG] [EV3] Setting up motors...")

            # ev3_sight
            self.m_eye_vertical  = ev3.Motor(ev3.PORT_B, ev3_obj=self.ev3_sight)
            self.m_eye_horizontal  = ev3.Motor(ev3.PORT_C, ev3_obj=self.ev3_sight)
            self.m_neck  = ev3.Motor(ev3.PORT_D, ev3_obj=self.ev3_sight)
            self.m_eyebrow  = ev3.Motor(ev3.PORT_A, ev3_obj=self.ev3_sight)

            # ev3_mouth
            self.m_jaw  = ev3.Motor(ev3.PORT_D, ev3_obj=self.ev3_mouth)
            self.m_mouth  = ev3.Motor(ev3.PORT_C, ev3_obj=self.ev3_mouth)

            # Debug
            if self.VERBOSE == 2:
                print("[DEBUG] [EV3] Setting motor speeds...")

            # Defining parameters
            self.m_eye_vertical.speed = SPEEDS["eye_vertical"]
            self.m_eye_horizontal.speed = SPEEDS["eye_horizontal"]
            self.m_neck.speed = SPEEDS["neck"]
            self.m_eyebrow.speed = SPEEDS["eyebrow"]
            self.m_mouth.speed = SPEEDS["mouth"]

            # Set jaw speeds
            self.jaw_speed = SPEEDS["jaw_talk"]
            self.jaw_close_speed = SPEEDS["jaw_close"]

            # Debug
            if self.VERBOSE == 2:
                print("[DEBUG] [EV3] Motors setup complete.")

    def center_eyes(self, vertical_speed: int, horizontal_speed: int):
        """
        Centers the robot's eyes.

        This assumes that the eyes naturally stall at the limits and that the normal (centered) position is in the middle of the limits.

        Args:
            vertical_speed (int): The speed at which the vertical eye motor should move.
            horizontal_speed (int): The speed at which the horizontal eye motor should move.
        """
        if self.use_Mindstorms:

            # Debug
            if self.VERBOSE == 2:
                print("[DEBUG] [EV3] Calibrating eyes...")

            # Center the eyes vertically
            self.m_eye_vertical.start_move(speed=vertical_speed)
            sleep(1)
            point1 = self.m_eye_vertical.position
            self.m_eye_vertical.start_move(direction=-1, speed=vertical_speed)
            sleep(1.5)
            point2 = self.m_eye_vertical.position
            self.m_eye_vertical.start_move_to(int((point1+point2)/2-10), brake=True)
            sleep(1.5)

            # Center the eyes horizontally
            self.m_eye_horizontal.start_move(speed=horizontal_speed)
            sleep(1)
            point1 = self.m_eye_horizontal.position
            self.m_eye_horizontal.start_move(direction=-1, speed=horizontal_speed)
            sleep(1.5)
            point2 = self.m_eye_horizontal.position
            self.m_eye_horizontal.start_move_to(int((point1+point2)/2), brake=True)
            sleep(1.5)

            # Reset the eye positions
            self.m_eye_vertical.position = 0
            self.m_eye_horizontal.position = 0

            # Debug
            if self.VERBOSE == 2:
                print("[DEBUG] [EV3] Eyes calibrated.")

    def close_jaw(self):
        """
        Closes the robot's jaw.

        The jaw will stop by stalling, or after a certain amount of time. but the code will continue immediately.
        This assumes the jaw motor naturally stalls when opening or closing.
        """
        if self.use_Mindstorms:
            self.m_jaw.start_move_for(self.JAW_CLOSE_TIME, speed=self.jaw_close_speed, direction=self.JAW_DIRECTION, brake=True)

    def move_jaw(self, direction: int = 1):
        """
        Starts opening or closing the robot's jaw indefinitely.

        The jaw will only stop by stalling, but the code will continue immediately.
        This assumes the jaw motor naturally stalls when opening or closing.

        Args:
            speed (int): The direction in which the jaw should move (1 = up, -1 = down) (default = 1)
        """
        if self.use_Mindstorms:
            self.m_jaw.start_move(speed=self.jaw_speed, direction=direction*self.JAW_DIRECTION)

    def sync_jaw(self, indata, frames, time, status):
        """
        Opens or Closes the robot's jaw based on audio data.

        The jaw will only stop by stalling, but the code will continue immediately.
        This assumes the jaw motor naturally stalls when opening or closing.

        Calls move_jaw with the direction based on the audio data.

        Args:
            arguments from sound device input stream
        """
        if self.use_Mindstorms:
            # Normalize the volume
            volume_norm = np.linalg.norm(indata)*10

            # If the volume is below the threshold, move the jaw up, otherwise move it down
            if volume_norm < self.JAW_SOUND_THRESHOLD:
                self.move_jaw(direction=1)
            else:
                self.move_jaw(direction=-1)

    def move_eyebrows(self, position: int | str):
        """
        Moves the robot's eyebrows to a specified position if not already within tolerance.
        Can also move the eyebrows to a predefined position for listening or neutral, as defined in ev3_config.json.

        Tolerance is gathered from the ev3_config.json file.
        Must be within the limits of the eyebrows.

        Args:
            position (int): The target position for the eyebrows in degrees.
            Or: position (str): The target position for the eyebrows as defined in config. ("listening" | "neutral")
        """
        if self.use_Mindstorms:

            # Check if the position is a predefined position
            if type(position) == str:
                # Get the predefined position
                if self.EYEBROW_LISTENING_POSITION > 0:
                    position = self.EYEBROW_LISTENING_POSITION * self.EYEBROW_RANGE["high"] if position == "listening" else 0
                else:
                    position = abs(self.EYEBROW_LISTENING_POSITION) * self.EYEBROW_RANGE["low"] if position == "listening" else 0

            # Check if the current position isn't already the target position
            if not self.within_tolerance(position, self.m_eyebrow.position):

                # Debug
                if self.VERBOSE == 2:
                    print(f"[DEBUG] [EV3] Moving eyebrows to position: '{int(position)}'...")

                # Move the eyebrows to the position
                self.m_eyebrow.start_move_to(int(position), brake=True)

            else:
                # Debug
                if self.VERBOSE == 2:
                    print(f"[DEBUG] [EV3] Eyebrows already at target position. ({position})")

    def move_mouth(self, position: int):
        """
        Moves the mouth corner motor to a specified position if not already within tolerance.

        Tolerance is gathered from the ev3_config.json file.
        Must be within the limits of the mouth corners.

        Args:
            position (int): The target position for the mouth corner motor in degrees.
        """
        if self.use_Mindstorms:

            # Check if the current position isn't already the target position
            if not self.within_tolerance(position, self.m_mouth.position):

                # Debug
                if self.VERBOSE == 2:
                    print(f"[DEBUG] [EV3] Moving mouth to position: '{position}'...")

                # Move the eyebrows to the position
                self.m_mouth.start_move_to(int(position), brake=True)

            else:
                # Debug
                if self.VERBOSE == 2:
                    print(f"[DEBUG] [EV3] Mouth already at target position. ({position})")

    def get_motor_positions(self, emotion: str) -> tuple[int, int]:
        """
        Calculates the targeted motor positions based on a given emotion and the values in ev3_config.json file.

        Args:
            emotion (str): One of the emotions in the ev3_config.json file

        Returns:
            tuple: The target positions for the mouth and eyebrow motors in degrees (int).
        """
        if self.use_Mindstorms:
            # Get the relative values for the mouth and eyebrow motors
            rel_mouth, rel_eyebrow = self.EMOTIONS[emotion]["mouth_multiplier"], self.EMOTIONS[emotion]["eyebrow_multiplier"]
            
            # Calculate the target positions based on the relative values
            if rel_mouth < 0:
                mouth = abs(rel_mouth)*self.MOUTH_RANGE["low"]
            else:
                mouth = rel_mouth*self.MOUTH_RANGE["high"]
            if rel_eyebrow < 0:
                eyebrow = abs(rel_eyebrow)*self.EYEBROW_RANGE["low"]
            else:
                eyebrow = rel_eyebrow*self.EYEBROW_RANGE["high"]

            # Return the target positions
            return mouth, eyebrow

    def within_tolerance(self, target: int, current: int) -> bool:
        """
        Checks whether a target position is within a range of the current motor position as defined in ev3_config.json.

        Args:
            target (int): Target motor position in degrees.
            current (int): Current motor position in degrees.

        Returns:
            bool: True if within tolerance, False otherwise.
        """
        if self.use_Mindstorms:
            return abs(target - current) <= self.TOLERANCE

    def convert_to_theoretical_coords(self, bbox: tuple[float, float, float ,float]) -> tuple[float, float, float ,float]:
        """
        Converts bounding box from physical camera to theoretical eye position using normalized coordinates.

        Args:
        bbox (tuple): (x, y, width, height) of bounding box in normalized coordinates (x, y) from -1.0 to 1.0 and (width, height) from 0.0 to 1.0.

        Returns:
        tuple: Transformed bounding box (x, y, width, height) for the theoretical camera in normalized coordinates.
        """
        x, y, w, h = bbox

        # Convert angles from degrees to radians
        tilt_angle_rad = np.radians(self.CAM_ANGLE)
        fov_rad = np.radians(self.CAM_FOV)
        vertical_angle = y * (fov_rad / 2)

        # Corrected vertical angle for the theoretical camera and add compensation for the height difference
        corrected_vertical_angle = vertical_angle - tilt_angle_rad + h * self.CAM_HEIGHT_DIFF

        # Map back to normalized coordinates for the theoretical camera
        corrected_y = corrected_vertical_angle / (fov_rad / 2)

        # Return corrected bounding box and make sure the tracking position is within the bounds
        corrected_box = (x, max(-1.0, min(1.0, corrected_y)), w, h)
        return corrected_box

    def eye_tracking(self, target_position: tuple[float, float, float, float]):
        """
        Moves the robot's eyes and neck to look at a specified bounding box.

        Args:
            target_position (tuple): Target bounding box for eye tracking, containing relative coordinates. (x_left, y_top, width, height)
        """
        if self.use_Mindstorms:

            # Define a function to move the motors for the eyes and neck
            def move_motor_if_needed(motor, target_angle):
                if not self.within_tolerance(target_angle, motor.position):
                    motor.start_move_to(target_angle, brake=True)

            # Calculate center position of target_position
            x = target_position[0] + target_position[2] / 2
            y = target_position[1] + target_position[3] / 2

            # Convert the target position to theoretical coordinates for the eyes
            target_position = self.convert_to_theoretical_coords((x, y, target_position[2], target_position[3]))

            y = target_position[1]

            # Calculate motor angles for vertical eye motor
            vertical_eye_angle = int(y * self.EYE_VERTICAL_AMPLITUDE)

            # Calculate motor angles for horizontal eye motor
            horizontal_angle_combined = int(x * (self.EYE_HORIZONTAL_AMPLITUDE + (self.NECK_AMPLITUDE/self.NECK_EYE_DIFF)))
            if horizontal_angle_combined == 0:
                horizontal_eye_angle = 0
                neck_angle = 0
            else:
                max_horizontal_eye_angle = int(horizontal_angle_combined/abs(horizontal_angle_combined) * self.EYE_HORIZONTAL_AMPLITUDE)
                horizontal_eye_angle = horizontal_angle_combined if abs(horizontal_angle_combined) < self.EYE_HORIZONTAL_AMPLITUDE else max_horizontal_eye_angle
            
                # Calculate motor angles for neck motor
                neck_angle = int((horizontal_angle_combined - horizontal_eye_angle)*self.NECK_EYE_DIFF) if horizontal_eye_angle == max_horizontal_eye_angle else 0

            # Move the motors to the target positions
            move_motor_if_needed(self.m_eye_vertical, vertical_eye_angle)
            move_motor_if_needed(self.m_eye_horizontal, horizontal_eye_angle)
            move_motor_if_needed(self.m_neck, neck_angle)

    def move_to_emotion(self, emotion: str = "neutral"):
        """
        Moves the mouth corners and eyebrows to a specified emotion if not already within tolerance.

        Tolerance is gathered from the ev3_config.json file.
        Uses the built-in function get_motor_positions to get positions and move the mouth and eyes.

        Args:
            emotion (str): The targeted emotion.
        """
        if self.use_Mindstorms:

            # Debug
            if self.VERBOSE == 2:
                print(f"[DEBUG] [EV3] Moving eyebrows and mouth to emotion: '{emotion}'...")

            # Get the target positions
            pos_mouth, pos_eyebrow = self.get_motor_positions(emotion)

            # Move the mouth and eyebrows to the target positions
            self.move_mouth(pos_mouth)
            self.move_eyebrows(pos_eyebrow)

    def move_to_neutral(self):
        """
        Moves the mouth corners and eyebrows to their neutral positions (0) if not already within tolerance.
        Also closes the jaw.

        Tolerance is gathered from the ev3_config.json file.
        Uses built-in functions to move the mouth and eyes to 0 and 0.

        Args:
            emotion (str): The targeted emotion.
        """
        if self.use_Mindstorms:

            # Debug
            if self.VERBOSE == 2:
                print("[DEBUG] [EV3] Moving eyebrows and mouth to neutral positions...")

            # Move the mouth and eyebrows to the neutral positions
            self.move_mouth(0)
            self.move_eyebrows(0)

            # Close the jaw
            self.close_jaw()

    def __enter__(self):
        """
        Starts the EV3 resources on enter.
        """
        return self

    def _cleanup(self):
        """
        Cleans up the EV3 resources.

        Stops the motors and disconnects from the EV3.
        """
        if self.use_Mindstorms:

            # Debug
            if self.VERBOSE == 2:
                print("[DEBUG] [EV3] Resetting motor positions...")

            # Move the motors to neutral positions
            self.move_to_neutral()

            # Wait for the motors to be in position
            sleep(0.5)

            # Move the motors to the center, if not already there
            if not self.within_tolerance(0, self.m_eye_horizontal.position): self.m_eye_horizontal.start_move_to(0, brake=True)
            if not self.within_tolerance(0, self.m_eye_vertical.position): self.m_eye_vertical.start_move_to(0, brake=True)
            if not self.within_tolerance(0, self.m_neck.position): self.m_neck.start_move_to(0, brake=True)

            # Wait for the motors to be in position
            sleep(1.5)

            # Stop the motors
            self.m_eye_vertical.stop(brake=False)
            self.m_eye_horizontal.stop(brake=False)
            self.m_neck.stop(brake=False)
            self.m_eyebrow.stop(brake=False)
            self.m_jaw.stop(brake=False)
            self.m_mouth.stop(brake=False)

            # Debug
            if self.VERBOSE == 2:
                print("[DEBUG] [EV3] EV3 resources cleaned up.")

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Cleans up the EV3 resources on exit.

        Stops the motors and disconnects from the EV3.
        """
        self._cleanup()

    def __del__(self):
        """
        Cleans up the EV3 resources on deletion.

        Stops the motors and disconnects from the EV3.
        """
        self._cleanup()

if __name__ == "__main__":
    # Test the EV3_handler class
    with ev3Handler(verbose=2) as ev3:
        ev3.move_to_emotion("happy")
        sleep(2)
        ev3.move_to_emotion("sad")
        sleep(2)
        ev3.move_to_neutral()

        # Test the eye tracking
        ev3.eye_tracking((-0.125, -0.125, 0.25, 0.25))
        sleep(2)
        ev3.eye_tracking((-0.5, -0.5, 0.25, 0.25))
        sleep(2)
        ev3.eye_tracking((0, 0, 0.5, 0.5))
        sleep(2)
        ev3.eye_tracking((0, 0, 0.1, 0.1))

        # Test the jaw movement
        ev3.move_jaw(-1)
        sleep(2)
        ev3.close_jaw()