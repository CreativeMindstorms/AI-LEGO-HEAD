from pvrecorder import PvRecorder
import speech_recognition as sr
import sounddevice as sd
import pvporcupine
import numpy as np
import threading
import pyttsx3
import json

class Listening:
    def __init__(self, verbose: int = None):
        """
        Initializes the Listening class.

        Sets up the keyword detection and speech recognition engines.
        Retrieves initial information from config.json

        Args:
            verbose (int, optional): level of debugging (0 = no printing, 1 = errors, 2 = full debugging) (default = None).

        Raises:
            FileNotFoundError: If the config file is not found.
            Exception: If there is an error in the config file format.
        """

        try:
            # Retrieve configuration info from json files
            with open('config/config.json', 'r') as file:
                info = json.load(file)
                PICO_API_KEY = info["pico_api_key"]
                if info["use_external_microphone"]:
                    physical_audio_device = info["external_microphone_name"]
                else: physical_audio_device = info["internal_microphone_name"]
                end_speaking_duration = info["end_speaking_duration"]
                self.non_speaking_duration = info["non_speaking_duration"]
                self.PICO_KEYWORD_PATHS = [info["pico_keyword_path_hey_dave"]]
                self.PICO_KEYWORDS = info["pico_keywords"]

                if verbose == None:
                    self.VERBOSE = info["verbose_level"]
                else:
                    self.VERBOSE = verbose

        except FileNotFoundError as e:
            # Catching FileNotFoundError to handle missing configuration files.
            # Expected behavior is to raise an exception and terminate the initialization.
            raise FileNotFoundError(f"[ERROR] [AUDIO_LISTEN] {e}. Please check if the config files exist.")
        
        except Exception as e:
            # Raise an error if the config file is not correctly formatted
            raise Exception(f"[ERROR] [AUDIO_LISTEN] {e}. Please check if the config files are correctly formatted.")

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [AUDIO_LISTEN] Setting up...")
        
        # Get the index of the microphone device
        self.mic_idx, pv_mic_idx = self.get_microphone_index(physical_audio_device)

        # Set up keyword detection
        try:
            self.ppn = pvporcupine.create(access_key=PICO_API_KEY, keyword_paths=self.PICO_KEYWORD_PATHS)
        except pvporcupine.PorcupineError as e:
            raise Exception(f"[ERROR] [AUDIO_LISTEN] Failed to create Porcupine instance: {e}")
        self.recorder = PvRecorder(device_index=pv_mic_idx,frame_length=self.ppn.frame_length)

        # Set up speech recognition
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = end_speaking_duration

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [AUDIO_LISTEN] Listening for ambient noise (1 sec)...")

        with sr.Microphone(device_index=self.mic_idx) as source:
            self.recognizer.adjust_for_ambient_noise(source=source, duration=1)
        
        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [AUDIO_LISTEN] Setup complete.")

    def get_microphone_index(self, mic_name: str) -> int:
        """
        Retrieves the index of the microphone device.
        
        Args:
            mic_name (str): Name of the microphone to be used.

        Returns:
            int: The index of the microphone device.
        """

        # Retrieve devices
        available_mics = {}
        for i, name in enumerate(sr.Microphone.list_microphone_names()):
            available_mics[i] = name

        # Do the same with PvRecorder
        available_mics_pv = {}
        for i, name in enumerate(PvRecorder.get_available_devices()):
            available_mics_pv[i] = name

        # Get the index of the selected camera
        try:
            mic_idx = list(available_mics.values()).index(mic_name)
        except ValueError:
            # Raise an error if the camera name is not found
            raise ValueError(f"[ERROR] [AUDIO_LISTEN] Microphone '{mic_name}' not found in the list of available cameras: {list(available_mics.values())}")
        
        try:
            for value in available_mics_pv.values():
                if mic_name in value:
                    mic_name = value
                    break
            pv_mic_idx = list(available_mics_pv.values()).index(mic_name)
        except ValueError:
            # Raise an error if the camera name is not found
            raise ValueError(f"[ERROR] [AUDIO_LISTEN] Microphone '{mic_name}' not found in the list of available cameras (pv): {list(available_mics_pv.values())}")

        # Debug
        if self.VERBOSE == 2:
            print(f"[DEBUG] [AUDIO_LISTEN] Index for microphone '{mic_name}': speech: {mic_idx}, keyword: {pv_mic_idx}")

        return mic_idx, pv_mic_idx

    def wait_for_keyword(self, wanted_keyword: str) -> None:
        """
        Waits for a specific keyword to be detected.

        Args:
            wanted_keyword (str): String of the keyword to listen for. (.ppn file must exist and be declared) ("hey dave" or "stop now")

        Raises:
            Exception: If the keyword is not found in the config.json.
        """
        # Get the index of the wanted keyword
        try:
            wanted_keyword_idx = self.PICO_KEYWORDS.index(wanted_keyword.lower())
 
            # Debug
            if self.VERBOSE == 2:
                print(f"[DEBUG] [AUDIO_LISTEN] Retrieved keyword index for '{wanted_keyword.lower()}': {wanted_keyword_idx}")

        except Exception as e:
            # Raise an error if the keyword is not found in the config.json
            raise Exception(f"[ERROR] [AUDIO_LISTEN] {e}. Keyword: '{wanted_keyword}'. Keywords as defined in config.json: {self.PICO_KEYWORDS}")

        # Start listening
        try:
            self.recorder.start()
        except Exception as e:
            raise Exception(f"[ERROR] [AUDIO_LISTEN] Failed to start recorder: {e}")
 
        # Debug
        if self.VERBOSE == 2:
            print(f"[DEBUG] [AUDIO_LISTEN] Started listening...")

        # Wait for the keyword to be detected
        keyword_index = -1
        while keyword_index != wanted_keyword_idx:
            pcm = self.recorder.read()
            keyword_index = self.ppn.process(pcm)

        # Stop listening
        self.recorder.stop()
        
        # Debug
        if self.VERBOSE == 2:
            print(f"[DEBUG] [AUDIO_LISTEN] Keyword '{wanted_keyword.lower()}' detected.")

    def speech_recognition(self) -> tuple[str, bool]:
        """
        Listens and converts speech to text.

        Returns:
            tuple: A tuple containing:
                - str: Transcribed text from the speech input or an error message if the speech is not recognized.
                - bool: Whether the speech recognition was successful or not.
        """
        # Initialize variable
        audible = False

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [AUDIO_LISTEN] Listening for speech...")

        # Listen for speech
        try:
            with sr.Microphone(device_index=self.mic_idx) as source:
                audio = self.recognizer.listen(source, timeout = self.non_speaking_duration)
        except sr.exceptions.WaitTimeoutError as e:
            return e, audible

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [AUDIO_LISTEN] Speech detected. Transcribing...")

        # Attempt to transcribe the speech
        try:
            detectedQuestion = self.recognizer.recognize_google(audio) # Use Google's speech recognition
            audible = True
        except sr.UnknownValueError:
            detectedQuestion = "*Inaudible*" # If the speech is not recognized, set the text to inaudible
        except sr.RequestError as e:
            detectedQuestion = f"Could not request results; {e}" # If there is an error in the request, set the text to the error message
        except Exception as e:
            detectedQuestion = f"An unexpected error occurred; {e}" # If there is an unexpected error, set the text to the error message
            if self.VERBOSE > 0:
                print(f"[ERROR] [AUDIO_LISTEN] An unexpected error occurred during speech recognition: {e}")

        # Debug
        if self.VERBOSE == 2:
            if audible:
                print(f"[DEBUG] [AUDIO_LISTEN] Transcribed: {detectedQuestion}")
            else:
                print(f"[DEBUG] [AUDIO_LISTEN] Speech was unsuccesfully recognized: {detectedQuestion}")

        return detectedQuestion, audible
    
    def __del__(self):
        """
        Cleans up the Listening class.

        Stops the recorder and deletes the class.
        """
        self.recorder.stop()

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [AUDIO_LISTEN] Exit.")

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Cleans up the Listening class.

        Stops the recorder and deletes the class.
        """
        self.recorder.stop()

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [AUDIO_LISTEN] Exit.")

        del self

class Speaking:
    def __init__(self, sync_jaw: callable = None, move_eyebrows: callable = None, move_to_emotion: callable = None, move_to_neutral: callable = None, verbose: int = None):
        """
        Initializes the Speaking class.

        Sets up the pyttsx3 engine and optional robotic actions.
        Retrieves initial information from config.json

        Args:
            sync_jaw (callable, optional): Function to move the mouth during speech (required if use_Mindstorms == True).
            move_eyebrows (callable, optional): Function to move the eyebrows (required if use_Mindstorms == True).
            move_to_emotion (callable, optional): Function to move the mouth and eyebrows to an emotion (required if use_Mindstorms == True).
            move_to_neutral (callable, optional): Function to move the mouth and eyebrows to the neutral position (required if use_Mindstorms == True).
            verbose (int, optional): level of debugging (0 = no printing, 1 = errors, 2 = full debugging) (default = None).
        """

        try:
            # Retrieve configuration info from json files
            with open('config/config.json', 'r') as file:
                info = json.load(file)
                VOICE_ID = info["voice_id"]
                self.use_Mindstorms = info["use_Mindstorms"]
                self.PLAY_INAUDIBLE_TONE = info["play_inaudible_tone"]
                self.INAUDIBLE_TONE_DURATION = info["inaudible_tone_duration"]
                self.VIRTUAL_AUDIO_DEVICE = info["virtual_audio_device"]

                if verbose == None:
                    self.VERBOSE = info["verbose_level"]
                else:
                    self.VERBOSE = verbose

        except FileNotFoundError as e:
            # Catching FileNotFoundError to handle missing configuration files.
            # Expected behavior is to raise an exception and terminate the initialization.
            raise FileNotFoundError(f"[ERROR] [AUDIO_SPEAK] {e}. Please check if the config files exist.")
        
        except Exception as e:
            # Raise an error if the config file is not correctly formatted
            raise Exception(f"[ERROR] [AUDIO_SPEAK] {e}. Please check if the config files are correctly formatted.")
        
        # Save variables
        if self.use_Mindstorms:
            if sync_jaw is None or move_eyebrows is None or move_to_emotion is None or move_to_neutral is None:
                raise Exception("[ERROR] [AUDIO_SPEAK] If use_Mindstorms is True, sync_mouth, move_eyebrows, move_to_emotion, and move_to_neutral must be defined.")
            self.sync_jaw = sync_jaw
            self.move_eyebrows = move_eyebrows
            self.move_to_emotion = move_to_emotion
            self.move_to_neutral = move_to_neutral
        self.stop_talking = False

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [AUDIO_SPEAK] Setting up...")

        # Set up text to speech
        self.engine = pyttsx3.init()
        voices = self.engine.getProperty('voices')
        if self.VERBOSE == 2:
            print("[DEBUG] [AUDIO_SPEAK] Available voices:", [voice.name for voice in voices])
        self.engine.setProperty('voice', voices[VOICE_ID].id)
        if self.VERBOSE == 2:
            print("[DEBUG] [AUDIO_SPEAK] Selected:", voices[VOICE_ID].name)

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [AUDIO_SPEAK] Setup complete.")

    def sync_mouth(self):
        """
        Handles Mindstorms jaw movement during speech in a separate thread.

        This is a loop that uses an ending flag contained within self.
        It continuously calls the sync_jaw function (defined in ev3Functions) to move the jaw, using information from the virtual audio device.
        """

        # Continuously call the sync_jaw function to move the jaw until self.stop_talking is True
        with sd.InputStream(callback=self.sync_jaw, device=self.VIRTUAL_AUDIO_DEVICE):
            while not self.stop_talking:
                sd.sleep(100)
            self.stop_talking = False
            return

    def say(self, text: str, emotion: str = "neutral"):
        """
        Speaks the given text with an optional emotion.

        Also handles robotic actions if Mindstorms is used.
        This includes: moving the mouth and eyebrows, and starting a thread to move the jaw during speech.

        Args:
            text (str): The text to speak.
            emotion (str, optional): The emotion to convey (default "neutral").
        """

        # Play an inaudible tone to wake up a Bluetooth speaker and prevent cutoff
        if self.PLAY_INAUDIBLE_TONE:

            # Debug
            if self.VERBOSE == 2:
                print(f"[DEBUG] [AUDIO_SPEAK] Playing inaudible tone for {self.INAUDIBLE_TONE_DURATION} seconds to wake up Bluetooth speaker...")

            tone = np.sin(2 * np.pi * np.arange(0, self.INAUDIBLE_TONE_DURATION, 1 / 44100))  # generate an inaudible low frequency tone
            sd.play(tone, 44100)  # play it

        # Check if Mindstorms should be used
        if self.use_Mindstorms:

            # Move the mouth and eyebrows to the emotion
            self.move_to_emotion(emotion)

            # Debug
            if self.VERBOSE == 2:
                print("[DEBUG] [AUDIO_SPEAK] Starting jaw syncing thread...")

            # Start a thread to move the jaw during speech
            thread = threading.Thread(target=self.sync_mouth)
            thread.start()

        # wait for it to finish playing the inaudible tone
        sd.wait()

        if self.VERBOSE == 2:
            print("[DEBUG] [AUDIO_SPEAK] Inaudible tone played.")

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [AUDIO_SPEAK] Speaking...")

        # Speak the text
        self.engine.say(text)
        self.engine.runAndWait()

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [AUDIO_SPEAK] Speech complete.")

        # Check if Mindstorms should be used
        if self.use_Mindstorms:

            # Debug
            if self.VERBOSE == 2:
                print("[DEBUG] [AUDIO_SPEAK] Stopping jaw syncing...")

            # Stop moving the jaw
            self.stop_talking = True
            thread.join()

            # Move the mouth and eyebrows back to neutral
            self.move_to_neutral()

    def __del__(self):
        """
        Cleans up the Speaking class.

        Stops the pyttsx3 engine and deletes the class.
        """

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [AUDIO_SPEAK] Exit.")

        try:
            self.engine.stop()
        except:
            pass
    
    def __exit__(self, exc_type, exc_value, traceback):
        """
        Cleans up the Speaking class.

        Stops the pyttsx3 engine and deletes the class.
        """

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [AUDIO_SPEAK] Exit.")

        self.engine.stop()








# Example usage of the Listening and Speaking classes
if __name__ == "__main__":
    def sync_mouth(indata, frames, time, status):
        pass
    def move_eyebrows(position):
        pass
    def move_to_emotion(emotion):
        pass
    def move_to_neutral():
        pass

    # Initialize the classes
    listen = Listening(verbose=2)
    speaking = Speaking(verbose=2, sync_jaw=sync_mouth, move_eyebrows=move_eyebrows, move_to_emotion=move_to_emotion, move_to_neutral=move_to_neutral)

    # Use the listening and speaking classes
    listen.wait_for_keyword("hey dave")
    listen.wait_for_keyword("stop now")
    detectedQuestion, audible = listen.speech_recognition()
    speaking.say("This is a test.", "happy")
