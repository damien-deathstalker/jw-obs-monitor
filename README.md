# JW OBS Monitor

## Overview
JW OBS Monitor is a Python application designed to monitor the JW Library display on a second screen and automatically transition scenes in OBS Studio based on the content being displayed. This tool is particularly useful for streamers and presenters who want to enhance their live broadcasts by seamlessly integrating content from the JW Library.

## Features
- Monitors the JW Library display for images and videos.
- Automatically transitions scenes in OBS Studio based on detected content.
- Configurable settings for OBS WebSocket connection and scene names.
- Includes logging functionality for tracking application events.

## Project Structure
```
jw-obs-monitor
├── src
│   ├── main.py                # Entry point of the application
│   ├── detector.py            # Monitors the JW Library display
│   ├── screen_monitor.py      # Captures screen content from the second display
│   ├── obs_controller.py      # Interfaces with OBS Studio for scene transitions
│   ├── config.py              # Configuration settings for the application
│   └── utils
│       ├── image_processing.py # Utility functions for image processing
│       └── logger.py          # Logging functionality
├── tests/
├── requirements.txt           # Project dependencies
├── pyproject.toml             # Project configuration
└── README.md                  # Project documentation
```

## Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   cd jw-obs-monitor
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage
1. Configure the application by editing the `src/config.py` file to set your OBS WebSocket connection details and scene names.
2. Run the application:
   ```
   python src/main.py
   ```

## Contributing
Contributions are welcome! Please feel free to submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.