# All tunable thresholds live here.
EAR_THRESHOLD = 0.20        # below this = eye closed
CLOSED_SECONDS = 1.5        # eyes closed this long = drowsy
YAW_LIMIT = 25              # degrees left/right from your normal position
PITCH_LIMIT = 20            # degrees up/down from your normal position
AWAY_SECONDS = 2.0          # looking away this long = alert
CALIBRATION_SECONDS = 2.0   # time spent learning your normal head position
CALIBRATION_MIN_FRAMES = 5  # but never fewer than this many frames

# Phone detection
PHONE_CONFIDENCE = 0.3      # minimum detector confidence to count a phone (lower = catches more, more false alarms)
PHONE_SECONDS = 1.0         # phone present this long = "Using phone"
PHONE_HOLD_SECONDS = 1.5    # a phone seen once stays "present" this long (helps when only caught now and then)
PHONE_EVERY_N_FRAMES = 1    # run phone detection on every Nth frame (1 = every frame; use 2 on a slow server)

# Hand-at-ear detection (catches a phone held sideways to the ear)
HAND_EAR_ENABLED = True
HAND_EAR_DISTANCE = 0.8     # hand centre within this many face-widths of the side of the face
HAND_SECONDS = 2.0         # hand beside the face this long = "Using phone"
HAND_HOLD_SECONDS = 1.0     # a hand seen once stays "present" this long