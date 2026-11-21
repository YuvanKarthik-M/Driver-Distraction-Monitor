# All tunable thresholds live here.
EAR_THRESHOLD = 0.20        # below this = eye closed
CLOSED_SECONDS = 1.5        # eyes closed this long = drowsy
YAW_LIMIT = 25              # degrees left/right from your normal position
PITCH_LIMIT = 20            # degrees up/down from your normal position
AWAY_SECONDS = 2.0          # looking away this long = alert
CALIBRATION_SECONDS = 2.0   # time spent learning your normal head position
CALIBRATION_MIN_FRAMES = 5  # but never fewer than this many frames