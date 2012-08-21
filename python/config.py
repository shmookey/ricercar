''' config.py - Global configuration variables for ricercar.
'''

# These next two lines cause the ricercar window to open in the centre of the
# screen.
import os
os.environ['SDL_VIDEO_CENTERED'] = '1'

##
#
# Input/Output
#
##

MIDI_OUT_DEVICE = 2 # Use 0 for the built-in GS MIDI wavetable
MIDI_IN_DEVICE = 0
STREAM_DEVICE = 0
STREAM_FPS = 60

###
#
# Image Processing
#
###

STREAM_SIZE = (320,240) # Webcam stream size.
GRID_SIZE = [320,240] # Image resized to these dimensions for processing.
DISPLAY_SIZE = [1280,960]
STREAM_SIZES = [
	(320,240),
	(640,480)
]
STREAM_RATES = [15,30,60]

ROI_SIZE = 100 # Size of 'region of interest' used to narrow down marker location.


##
#
# Music
#
##

MARKER_NOTE_DEFAULT_MODE = 0
MARKER_NOTE_DEFAULT_DURATION = 0.5
MARKER_CV_DEFAULT_X_CONTROLLER = 10
MARKER_CV_DEFAULT_Y_CONTROLLER = 11

GUITAR = [0,7,12,21,24]

##
#
# User Interface
#
##

FONT = "consola.ttf"
UI_TABLE_COLUMN_WIDTH = 75.0
UI_TABLE_ROW_HEIGHT = 22.0
UI_HEIGHT = 130.0
TOP_PADDING = 20.0
LEFT_PADDING = 10.0
UI_FRAME_PADDING = 10
UI_LABEL_PADDING = 4
UI_BUTTON_BG_COLOUR = (0.0,0.0,0.0,0.6)
UI_HUD_BG_COLOUR = (0.0,0.0,0.0,0.6)
UI_HUD_TEXT_COLOUR = (1.0,1.0,1.0,1.0)
UI_HUD_SELECTED_COLOUR = (0.0,0.25,1.0,0.6)
UI_HUD_PADDING = 1
UI_HUD_BUTTON_Y_OFFSET = 5
UI_HUD_LEFT_PADDING = 5

#
# Specific window settings
#

UI_MIDI_DEVICE_BUTTON_WIDTH = 275
UI_VIDEO_DEVICE_BUTTON_WIDTH = 150

CROSSHAIR_SIZE = 200
CROSSHAIR_THICKNESS = 2.0
NOTE_BOUNDARY_THICKNESS = 1.0

# Colour sensitivities
# Naming convention: [Colour][Parameter][Bound]
# Bounds: L: Lower, U: Upper.
# Colours: B: Blue, G: Green, Y: Yellow, Red (low end), R: Red (high end)
# Parameters: H: Hue, S: Saturation, V: Value
SN_BHUE = [101,132]
SN_BSAT = [72,255]
SN_BVAL = [72,255]
SN_GHUE = [45,67.5]
SN_GSAT = [72,255]
SN_GVAL = [72,255]
SN_YHUE = [25,28]
SN_YSAT = [170,255]
SN_YVAL = [170,255]
SN_RHUE = [0, 12]
SN_RSAT = [80,255]
SN_RVAL = [80,255]
SN_RHUE2 = [173,179]
