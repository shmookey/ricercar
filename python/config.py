#
# Configuration variables
#

MIDI_OUT_DEVICE = 2 # Use 0 for the built-in GS MIDI wavetable
MIDI_IN_DEVICE = 0

# Frame sizes
STREAM_SIZE = (320,240) # Webcam stream size.
GRID_SIZE = [320,240] # Image resized to these dimensions for processing.
DISPLAY_SIZE = [1280,960]
STREAM_FPS = 60
STREAM_DEVICE = 2

FONT = "consola.ttf"

# Marker motion variables
MAX_SPEED = 2.0 # Maximum distance a marker can travel per second in each dimension.
ACCELERATION = 1.0
FRICTION = 0.8

# Marker detection parameters
MARKER_THRESHOLD = 225
BRIGHTNESS_THRESHOLD = 0.90

HUE_SCALE = (180.0/240)

GUITAR = [0,7,12,21,24]


UI_TABLE_COLUMN_WIDTH = 75.0
UI_TABLE_ROW_HEIGHT = 22.0
UI_HEIGHT = 130.0
TOP_PADDING = 20.0
LEFT_PADDING = 10.0

CROSSHAIR_SIZE = 200
CROSSHAIR_THICKNESS = 2.0
NOTE_BOUNDARY_THICKNESS = 1.0

UI_HUD_BG_COLOUR = (0.0,0.0,0.0,0.6)
UI_HUD_TEXT_COLOUR = (1.0,1.0,1.0,1.0)
UI_HUD_SELECTED_COLOUR = (0.0,0.25,1.0,0.6)
UI_HUD_PADDING = 1
UI_HUD_BUTTON_Y_OFFSET = 5
UI_HUD_LEFT_PADDING = 5


UNITY = 0
MINOR_2 = 1
MAJOR_2 = 2
MINOR_3 = 3
MAJOR_3 = 4
PERFECT_4 = 5
TRITONE = 6
PERFECT_5 = 7
MINOR_6 = 8
MAJOR_6 = 9
MINOR_7 = 10
MAJOR_7 = 11
OCTAVE = 12

NOTE_DURATION = 0.5

# Colour sensitivities
# Naming convention: [Colour][Parameter][Bound]
# Bounds: L: Lower, U: Upper.
# Colours: B: Blue, G: Green, Y: Yellow, Red (low end), R: Red (high end)
# Parameters: H: Hue, S: Saturation, V: Value
SN_BHUE = [135*HUE_SCALE,175*HUE_SCALE]
SN_BSAT = [72,255]
SN_BVAL = [72,255]
SN_GHUE = [60*HUE_SCALE,90*HUE_SCALE]
SN_GSAT = [72,255]
SN_GVAL = [72,255]
SN_YHUE = [35*HUE_SCALE,36*HUE_SCALE]
SN_YSAT = [170,255]
SN_YVAL = [170,255]
SN_RHUE = [0, 12]
SN_RSAT = [72,255]
SN_RVAL = [72,255]
SN_RHUE2 = [173,179]
