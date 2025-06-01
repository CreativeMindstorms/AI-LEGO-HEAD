# AI-LEGO-HEAD
Python code that allows for a full AI chat assistant experience (optionally with a Lego Mindstorms Robotic Head).

This is the code for my AI Lego robotic head, as seen on my YouTube channel (includes outdated code):
<div align="left">
  <a href="https://www.youtube.com/playlist?list=PLe3o60ftnUstYUnu4vxVhjR4WHe4jSx-d"><img src="https://img.youtube.com/vi/MghrMAWsfi8/0.jpg" alt="AI LEGO HEAD PLAYLIST"></a>
</div>

If you enjoy what I do and would like to support future creations, consider [buying me a coffee](https://buymeacoffee.com/creativemindstorms)!

Every contribution helps fund new machines and videos on YouTube!

## Table of Contents
1. [Introduction](#introduction)
2. [Features](#features)
3. [Installation](#installation)
4. [Usage](#usage)
5. [About The Robot](#about-the-robot)
6. [License](#license)
7. [Contributing](#contributing)
8. [Disclaimer](#disclaimer)

## Introduction
This project uses Python to animate a LEGO Mindstorms robotic head, turning it into a fully functional AI chat assistant with vision capabilities.

## Features
The project includes multiple features that work simultaneously.
- **Interactive AI:** Engage in real-time auditory conversations using Google's Gemini Developer API for the main conversational functionality.
- **Custom Information:** Add custom information that the AI should know (e.g., personal details).
- **Face recognition:** Recognize custom faces from just one sample image using a built-in camera.
- **Object Detection:** Vision capabilities with the Gemini API, using a built-in camera.
- **Live Visual Feedback:** Display a camera feed window containing information used by the AI.
- **Live Data:** Up to date information about local weather and current time and date.
- **Minigame:** Play a game of Rock Paper Scissors using hand detection.
- **Robotic Movements (optional):** Animated head movements powered by LEGO Mindstorms. Including:
	- **Eye Tracking:** For faces and/or hands. Moves the eyes in all directions and the neck sideways.
	- **Idle Eye Movement:** When there is no face or hand visible.
	- **Emotions:** Move the eyebrows and corners of the mouth to convey emotions.
	- **Jaw synchronization:** Synchronizes the jaw with the audio that is being produced.

## Installation
### Requirements
- Python 3 with libraries installed (see requirements.txt)
- Camera (e.g., phone with DroidCam or a webcam)
- Microphone
- Speaker
- Tested on a Windows 10 operating system.

### Optional Requirements
- Lego Robot containing two LEGO Mindstorms EV3 kits
- A Virtual Audio Cable for jaw-synchronization

### Steps
1. Clone this repository:
   ```bash
   git clone https://github.com/CreativeMindstorms/AI-LEGO-HEAD.git
2. Create a virtual environment and install the requirements.
3. Adjust the config files located within `src/config` (for explanation, see `config_explanation.txt`):
	`config.json`, `personal_information.txt`, (optionally `ev3_config.json`, `prompt.txt`, `vision_prompt.txt`)
	Run `src/tools/listAudioDevices.py` to get information about audio devices.
4. Create new face-encodings for your faces:
	- Add pictures of the faces you want to recognize to the `src/faces` folder and update `config.json` accordingly..
	- Run `src/tools/createFaceEncodings.py` to create face-encodings from the images.

### Optional Steps
If you are using a virtual audio cable for jaw synchronization, ensure that your system is set to listen to the virtual audio cable in the sound settings. The code will play the sound into the virtual audio cable specified. This is enough to make the jaw move, but in order to hear the sound too, you need to listen to the recording device too. If not using a virtual audio cable, you can enter your output device in the config file instead.

## Usage
Run `src/main.py` after installation and configuration.

You can start talking after saying the wake words "Hey Dave". It will automatically stop listening once you have stopped speaking and respond.
After it has responded, it will immediately start listening again for a certain amount of time, after which it will go back to waiting for the wake words.

## About The Robot
The robot (which is optional for running this code) uses two Mindstorms EV3 Bricks, of which you need the Bluetooth address.
### Connections

**EV3_SIGHT**:
| PORT | DESCRIPTION |
|------|-------------|
| A    | Eyebrow motor, controlling both eyebrows using predefined positions. |
| B    | Vertical eye motor, controlling the sideways motion of the eyes within a certain range. The motor stalls at its limits. |
| C    | Horizontal eye motor, controlling the up and down motion of the eyes within a certain range. The motor stalls at its limits. |
| D    | Neck motor, controlling the sideways motion of the neck within a certain range. Used when the horizontal eye motor reached its limit. |

**EV3_MOUTH**:
| PORT | DESCRIPTION |
|------|-------------|
| C    | Jaw motor, controlling the up and down movement of the jaw. The motor stalls at its limits, which is also the available range for movement. |
| D    | Mouth motor, controlling the up and dowm movement of the corners of the mouth using predefined positions. |

If you choose to run the code with use_Mindstorms set to false, it will function just fine, but just not send the ev3 commands.

## License
This project is licensed under the [GPLv3 License](LICENSE). Contributions and modifications are welcome, but they must remain open-source and credit the original author.

## Contributing

Contributions are welcome, and I appreciate your interest in improving this project! However, I want to keep this easy to manage, as it is a personal project and a learning experience for me.

If you’d like to suggest changes or improvements, here’s how you can contribute:

1.  **Fork the Repository:** Create a personal copy of the repository by clicking the "Fork" button at the top.
2.  **Make Changes:** Implement your changes in your forked repository. Please keep changes focused and well-documented.
3.  **Submit a Pull Request (PR):** Open a pull request with a clear explanation of your changes. Include why the change is beneficial and how it affects the project.

## Disclaimer

This project is a hobby, and while I enjoy working on it, I can’t provide consistent support or assistance. Please feel free to reach out via email for questions or feedback, but responses may be delayed depending on my availability.
