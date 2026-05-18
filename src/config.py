# Configuration settings for the JW-OBS Monitor application

# Monitor settings
# MONITOR_INDEX is 1-based and refers to entries returned by mss.monitors
MONITOR_INDEX = 2            # set to the JW Library full-screen monitor (1-based)
CAPTURE_SCALE = 0.25         # scale factor for captures to speed up processing

# Image difference / RMS thresholding
RMS_THRESHOLD = 15.0         # RMS threshold to consider that "something" is being displayed
PRESENCE_FRAMES_REQUIRED = 3 # consecutive frames required to declare media present
ABSENCE_FRAMES_REQUIRED = 5  # consecutive frames required to declare media gone
POLL_INTERVAL = 1          # seconds between captures

# OBS WebSocket settings
OBS_HOST = "localhost"
OBS_PORT = 4455              # default port for obs-websocket 5.x; 4444 for older versions
OBS_PASSWORD = ""           # set if your OBS WebSocket uses a password

SCENES = {
    "default": "Default Scene",  # Name of the default scene in OBS
    "media": "Media Scene"       # Name of the scene for media content in OBS
}

MONITOR_DISPLAY_INDEX = 1  # Index of the second display to monitor (0 for primary, 1 for secondary)

# Scene handling
MEDIA_SCENE_NAME = "Media"   # scene to switch to when media is detected
# If MEDIA_SCENE_NAME is None, the application will only store/restore the previous scene