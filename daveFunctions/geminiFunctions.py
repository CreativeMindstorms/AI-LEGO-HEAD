import google.generativeai as genai
from random import choice
from typing import Tuple
import pickle
import json
import re

class GeminiHandler:
    def __init__(self, *functions: callable, verbose: int = None):
        """
        Initializes the gemini_handler class and sets up a chat instance.

        Args:
            verbose (int, optional): The amount it should print. Default is 1. (0 is none, 1 is only function calls, 2 is debugging)
            functions (callable): Any number of functions that Gemini can call.
        """        

        try:
            # Retrieve configuration info from json files
            with open('config/config.json', 'r') as file:
                info = json.load(file)
                GEMINI_API_KEY = info["gemini_api_key"]
                GEMINI_MODEL = info["gemini_model"]
                SAFETY_SETTINGS = info["safety_settings"]
                self.MEMORY_PATH = info["memory_path"]
                self.CONTINUE_CONVERSATION = info["continue_conversation"]

                if verbose == None:
                    self.VERBOSE = info["verbose_level"]
                else:
                    self.VERBOSE = verbose
                
            with open('config/ev3_config.json', 'r') as file:
                info = json.load(file)
                self.EMOTIONS = list(info["emotions"].keys())
            
            # Retrieve prompts for the AI models
            with open('config/prompt.txt', 'r') as file:
                BEHAVIOUR = file.read()
            
            with open('config/vision_prompt.txt', 'r') as file:
                VISION_BEHAVIOUR = file.read()

        except FileNotFoundError as e:
            # Catching FileNotFoundError to handle missing configuration files.
            # Expected behavior is to raise an exception and terminate the initialization.
            raise FileNotFoundError(f"[ERROR] [GEMINI] {e}. Please check if the config files exist in the correct location.")
        
        except Exception as e:
            raise Exception(f"[ERROR] [GEMINI] {e}. Please check if the config files are correctly formatted.")

        # Replace [emotions] in the behaviour by the defined emotions in ev3_config if it is present in the prompt
        BEHAVIOUR = BEHAVIOUR.replace("[emotions]", ", ".join(self.EMOTIONS))

        # Create a list of all callable tools by gemini
        tools = list(functions)
        tools.append(self.get_scene_description)

        # Set API Key
        genai.configure(api_key=GEMINI_API_KEY)

        # Create gemini instance for Dave
        self.DAVE_MODEL = genai.GenerativeModel(model_name=GEMINI_MODEL,
                                system_instruction=BEHAVIOUR,
                                safety_settings=SAFETY_SETTINGS,
                                tools=tools,
                                tool_config={'function_calling_config':'AUTO'})
        
        # Create gemini instance for vision functionality
        self.VISION_MODEL = genai.GenerativeModel(model_name=GEMINI_MODEL,
                                system_instruction=VISION_BEHAVIOUR,
                                safety_settings=SAFETY_SETTINGS)

        # Create chat instance
        self.create_chat()
        
        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [GEMINI] Setup complete.")

    def create_chat(self):
        """
        Sets up a chat instance and optionally loads the previous chat history.

        It is determined whether it imports previous memory by the variable defined in the config file.

        History is stored in a file imported in __init__.
        """

        # Start with empty history
        history = []

        # Check whether to load the memory
        if self.CONTINUE_CONVERSATION:

            # Debug
            if self.VERBOSE == 2:
                print("[DEBUG] [GEMINI] Loading memory...")

            # Retrieve previous chat history from the memory file, deserialized with pickle
            try:
                with open(self.MEMORY_PATH, 'rb') as file:
                    history = pickle.load(file)
            except FileNotFoundError as e:
                if self.VERBOSE > 0:
                    print(f"\033[1;31;40m[ERROR]\033[0m [GEMINI] {e}. Starting fresh. (Check if the memory file exists)")
            
        
        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [GEMINI] Creating chat...")

        # Create the chat
        self.CHAT = self.DAVE_MODEL.start_chat(
            history=history,
            enable_automatic_function_calling=True
        )
            
    def get_chat_response(self, prompt: str, img: object) -> Tuple[str, str]:
        """
        Gets a response from Gemini for a given prompt in the current chat.

        May choose to use the attached image for vision capabilities.

        Args:
            prompt (str): The user's prompt.
            img (PIL.Image): An image portraying what Gemini currently sees.

        Returns:
            str: The response from Gemini.
        """
        
        self.img = img
        
        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [GEMINI] Getting response with prompt: " + prompt)

        # Get a response from the AI model
        response = self.CHAT.send_message(prompt)
        text_response = str(response.text).strip()
        
        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [GEMINI] Response: " + text_response)

        # Filter out abnormal characters and replace enters with spaces
        text_response = re.sub('[^\x20-\x7E]', '', text_response.replace('\n', ' ')).strip()

        # Splitting the emotion from the response
        prompt_words = text_response.split(maxsplit=1)

        # Only keep the letters for the emotion and make them lowercase
        prompt_words[0] = re.sub('[^a-zA-Z]+', '', prompt_words[0]).lower().strip()

        # Check if there is an emotion and if it is valid
        if prompt_words[0] in self.EMOTIONS and len(prompt_words) > 1:
            emotion = prompt_words[0]
            response = prompt_words[1]
        
        # Pick a random emotion if it is invalid
        else:
            emotion = choice(self.EMOTIONS)
            response = text_response
        
        # Debug
        if self.VERBOSE == 2:
            print(f"[DEBUG] [GEMINI] Filtered emotion : {emotion}")
            print(f"[DEBUG] [GEMINI] Filtered response: {response}")

        # Return the response and emotion
        return response, emotion

    def get_scene_description(self, prompt: str) -> str:
        """
        Get a description of what the robot can currently see with its eyes (camera).

        This also includes reading, recognizing, searching and other things.
        Any time something requires the robot to see something, this will give the answer.

        Examples:
        Can give details about how people look, how old they are, what they are wearing etc.
        Can also give information about objects that the user might be talking about.

        Args:
            prompt (str): What you are trying to find out about what you can see or the question you are trying to get information for. This could be directly the prompt that the user gives with potentially some additional information.
        
        Returns:
            str: A description of what you see
        """

        # Debug
        if self.VERBOSE > 0:
            print("| Called the vision function with:", prompt)
            if self.VERBOSE == 2:
                print("[DEBUG] [GEMINI] Evaluating scene...")

        # Use the vision model to get a description of the scene
        try:
            response = self.VISION_MODEL.generate_content([self.img, prompt])
            scene_description = response.text.strip()
        except Exception as e:
            scene_description = "Eyes were closed. Please try again."

            if self.VERBOSE > 0:
                print(f"\033[1;31;40m[ERROR]\033[0m [GEMINI] {e}.")

        # Debug
        if self.VERBOSE == 2:
            if scene_description != "Eyes were closed. Please try again.":
                print(f"[DEBUG] [GEMINI] Scene description: {scene_description}")

        return scene_description

    def save_memory(self):
        """
        Saves the chat history serialized with pickle in the memory file, overwriting the previous memory
        """

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [GEMINI] Saving memory...")

        # Write the history in the file, serialized with pickle
        with open(self.MEMORY_PATH, 'wb') as file:
            pickle.dump(self.CHAT.history, file, protocol=pickle.HIGHEST_PROTOCOL)

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Saves memory upon exit.
        """
        # Save the memory for the next boot
        self.save_memory()

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [GEMINI] Exit.")

        del self

    def __del__(self):
        """
        Saves memory when deleted.
        """
        # Save the memory for the next boot
        self.save_memory()

        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [GEMINI] Exit.")

        del self








# Example usage of the GeminiHandler class
if __name__ == "__main__":
    gh = GeminiHandler(verbose=2)
    print(gh.get_chat_response("Can you see me?", None))