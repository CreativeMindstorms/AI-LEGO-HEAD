from google import genai
from google.genai import types
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
                GEMINI_MODEL_NAME = info["gemini_model"]
                SAFETY_SETTINGS = info["safety_settings"]
                self.MEMORY_PATH = info["memory_path"]
                self.CONTINUE_CONVERSATION = info["continue_conversation"]

                if verbose is None:
                    self.VERBOSE = info["verbose_level"]
                else:
                    self.VERBOSE = verbose
            
            with open('config/ev3_config.json', 'r') as file:
                ev3_info = json.load(file) 
                self.EMOTIONS = list(ev3_info["emotions"].keys())
            
            # Retrieve prompts for the AI models
            with open('config/prompt.txt', 'r') as file:
                BEHAVIOUR_PROMPT = file.read()
            
            with open('config/vision_prompt.txt', 'r') as file:
                VISION_BEHAVIOUR_PROMPT = file.read()

        # Catching FileNotFoundError to handle missing configuration files.
        except FileNotFoundError as e:
            raise FileNotFoundError(f"[ERROR] [GEMINI] {e}. Please check if the config files exist in the correct location.")
        except Exception as e:
            raise Exception(f"[ERROR] [GEMINI] {e}. Please check if the config files are correctly formatted.")

        # Replace [emotions] in the behaviour by the defined emotions in ev3_config if it is present in the prompt
        BEHAVIOUR_PROMPT = BEHAVIOUR_PROMPT.replace("[emotions]", ", ".join(self.EMOTIONS))

        # Set API Key and model name
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.gemini_model_name = GEMINI_MODEL_NAME

        # Create a list of all callable tools by gemini
        self.tools_list = list(functions)
        self.tools_list.append(self.get_scene_description)
        
        # Parse safety settings from JSON into SDK objects
        self.parsed_safety_settings = None
        if SAFETY_SETTINGS:
            try:
                self.parsed_safety_settings = [
                    types.SafetySetting(category=s['category'], threshold=s['threshold'])
                    for s in SAFETY_SETTINGS
                ]
            except KeyError as e:
                raise ValueError(f"Invalid safety_settings format in JSON. Missing key: {e}")
            except Exception as e:
                raise ValueError(f"Error parsing safety_settings from JSON into SafetySetting objects: {e}")

        # Create GenerationConfig for the main chat
        try:
            self.dave_generation_config = types.GenerateContentConfig(
                system_instruction=BEHAVIOUR_PROMPT,
                safety_settings=self.parsed_safety_settings,
                tools=self.tools_list
            )

        # Handle potential errors in the response
        except Exception as e:
            if self.VERBOSE > 0:
                print(f"\033[1;31;40m[ERROR]\033[0m [GEMINI] Failed to create dave_generation_config: {e}")
            raise

        # Create GenerationConfig for vision model
        try:
            self.vision_config = types.GenerateContentConfig(
                system_instruction=VISION_BEHAVIOUR_PROMPT, 
                safety_settings=self.parsed_safety_settings
            )
        
        # Handle potential errors in the response
        except Exception as e:
            if self.VERBOSE > 0:
                print(f"\033[1;31;40m[ERROR]\033[0m [GEMINI] Failed to create vision_config: {e}")
            raise 

        # Create the Gemini chat instance
        self.CHAT = None 
        self.create_chat()
        
        # Debug
        if self.VERBOSE == 2:
            print("[DEBUG] [GEMINI] Setup complete. Generation configs created.")

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
            if self.VERBOSE == 2: print("[DEBUG] [GEMINI] Loading memory...")
            
            # Retrieve previous chat history from the memory file, deserialized with pickle
            try:
                with open(self.MEMORY_PATH, 'rb') as file:
                    history = pickle.load(file)
                    if not isinstance(history, list):
                        if self.VERBOSE > 0: print(f"\033[1;33;40m[WARNING]\033[0m [GEMINI] Loaded history is not a list. Starting fresh.")
                        history = []
            except FileNotFoundError:
                if self.VERBOSE > 0: print(f"\033[1;31;40m[ERROR]\033[0m [GEMINI] Memory file {self.MEMORY_PATH} not found. Starting fresh.")
                history = []
            except Exception as e:
                if self.VERBOSE > 0: print(f"\033[1;31;40m[ERROR]\033[0m [GEMINI] Error loading memory: {e}. Starting fresh.")
                history = []
        
        # Debug
        if self.VERBOSE == 2: print("[DEBUG] [GEMINI] Creating chat...")

        # Create the chat
        self.CHAT = self.client.chats.create(
            model=self.gemini_model_name,
            history=history,
            config=self.dave_generation_config
        )
            
    def get_chat_response(self, prompt: str, img: object) -> Tuple[str, str]:
        """
        Gets a response from Gemini for a given prompt in the current chat.

        May choose to use the attached image for vision capabilities.

        Args:
            prompt (str): The user's prompt.
            img (PIL.Image): An image portraying what Gemini currently sees.

        Returns:
            Tuple[str, str]: The response text from Gemini and the determined emotion.
        """
        self.img = img 
        
        # Debug
        if self.VERBOSE == 2:
            print(f"[DEBUG] [GEMINI] Getting response with prompt: {prompt}")

        # Check if the chat is initialized
        if not self.CHAT:
             if self.VERBOSE > 0: print(f"\033[1;31;40m[ERROR]\033[0m [GEMINI] Chat is not initialized. Call create_chat() first.")
             return "Error: Chat not initialized.", choice(self.EMOTIONS)

        # Get a response from the AI model
        response_obj = self.CHAT.send_message(message=prompt)
        
        # Check if the response object is valid and extract the text
        try:
            text_response = str(response_obj.text).strip()
        except AttributeError:
            if self.VERBOSE > 0: print(f"\033[1;31;40m[ERROR]\033[0m [GEMINI] Response object lacks 'text' attribute. Full response: {response_obj}")
            return "Error: Could not get text from response.", choice(self.EMOTIONS)
        except Exception as e:
            if self.VERBOSE > 0: print(f"\033[1;31;40m[ERROR]\033[0m [GEMINI] Error processing response.text: {e}")
            return "Error: Could not process response.", choice(self.EMOTIONS)

        # Debug
        if self.VERBOSE == 2:
            print(f"[DEBUG] [GEMINI] Raw response text: {text_response}")

        # Filter the text response to remove non-ASCII characters and replace newlines with spaces
        text_response_filtered = re.sub(r'[^\x20-\x7E]', '', text_response.replace('\n', ' ')).strip()

        # Split the emotion from the response text
        prompt_words = text_response_filtered.split(maxsplit=1)
        processed_response_text = ""
        emotion = ""

        # Check if there are any words in the prompt
        if prompt_words:
            # Only keep the letters for the emotion and make them lowercase
            potential_emotion = re.sub(r'[^a-zA-Z]+', '', prompt_words[0]).lower().strip()
            
            # If the potential emotion is in the list of known emotions, use it
            if potential_emotion in self.EMOTIONS and len(prompt_words) > 1:
                emotion = potential_emotion
                processed_response_text = prompt_words[1]
            
            # If the potential emotion is not valid, pick a random emotion
            else:
                emotion = choice(self.EMOTIONS)
                processed_response_text = text_response_filtered
        
        # If the prompt was empty or only contained an invalid emotion, pick a random emotion
        else:
            emotion = choice(self.EMOTIONS)

            # Keep filtered text even if empty
            processed_response_text = text_response_filtered

        # Debug
        if self.VERBOSE == 2:
            print(f"[DEBUG] [GEMINI] Filtered emotion : {emotion}")
            print(f"[DEBUG] [GEMINI] Filtered response: {processed_response_text}")

        # Return the response text and the emotion
        return processed_response_text, emotion

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
            print(f"| Called the vision function with: {prompt}")
        if self.VERBOSE == 2:
            print("[DEBUG] [GEMINI] Evaluating scene...")

        # Check if the image is available
        if not hasattr(self, 'img') or self.img is None:
            if self.VERBOSE > 0:
                print("\033[1;33;40m[WARNING]\033[0m [GEMINI] Vision function called (get_scene_description) but no image (self.img) is available.")
            return "Eyes were closed. Please try again."

        # Prepare the contents for the vision model
        contents_for_vision = [prompt, self.img] 
        
        # Use the vision model to get a description of the scene
        try:
            response = self.client.models.generate_content(
                model=self.gemini_model_name,
                contents=contents_for_vision,
                config=self.vision_config
            )
            scene_description = response.text.strip()

        # Handle potential errors in the response
        except AttributeError as e:
             if self.VERBOSE > 0:
                print(f"\033[1;31;40m[ERROR]\033[0m [GEMINI] Vision error (AttributeError, possibly bad image type for API or response structure): {e}.")
             scene_description = "Eyes were closed. Please try again."
        except Exception as e:
            if self.VERBOSE > 0:
                print(f"\033[1;31;40m[ERROR]\033[0m [GEMINI] Vision API error: {e}.")
            scene_description = "Eyes were closed. Please try again."

        # Debug
        if self.VERBOSE == 2:
            if scene_description != "Eyes were closed. Please try again.":
                print(f"[DEBUG] [GEMINI] Scene description: {scene_description}")
        
        # Return the scene description
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
            pickle.dump(self.CHAT.get_history(), file, protocol=pickle.HIGHEST_PROTOCOL)

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
