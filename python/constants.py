DATA_TABLE_HEADERS = [
	("Marker",
		["ID"]),
	("Position",
		["X",
		"Y"]),
	("Colour Sensitivity",
		["Hue",
		"Sat",
		"Val"]),
#	("MIDI Mapping",
#		["X Mode",
#		"X Min",
#		"X Max",
#		"X Ch",
#		"Y Mode",
#		"Y Min",
#		"Y Max",
#		"Y Ch"])
]

#
# Enumerated values
#

# Marker IDs
MARKER_RED = 0
MARKER_GREEN = 1
MARKER_BLUE = 2
MARKER_YELLOW = 3

# Colour channel codes
RED = 2
GREEN = 1
BLUE = 0

# Pixel spec array index
X = 0
Y = 1
C = 2 # Colour


# Frame IDs
FRAME_NOTEXTURE = -1
FRAME_RAW = 0
FRAME_GRID = 1
FRAME_MASKED = 2
FRAME_FEATURES = 3
FRAME_COMPOSITED = 4
