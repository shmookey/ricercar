import cv
import math
from music import *

from config import *

class HSVColourRange:
	''' Represents a colour range for extraction from an image.
	Supports an additional hue range for red, since it wraps around the spectrum.
	'''
	def __init__ (self, hue, saturation, value, hue2=None):
		self.hue = hue
		self.saturation = saturation
		self.value = value
		self.hue2 = hue2

class String:
	''' A virtual string which may trigger musical notes when "plucked".
	'''
	def __init__ (self, x, noteOffset):
		self.x = x
		self.noteOffset = noteOffset
		self.activeNotes = []
		self.remainingNoteTime = [] # Parallel list to activeNotes containing note trigger times.

class Marker:
	''' An object with a position in a unit square.
	'''

	TYPE_NOTE = 0
	TYPE_CV = 1

	MODE_POLYPHONIC = 0
	MODE_MONOPHONIC = 1

	nMarkers = 0
	def __init__ (self,
			name="Marker",
			x=0,
			y=0,
			colour=None,
			midiOut=None,
			colourRange=None,
			ID = None):
		self.name = name
		self.x = x # Position
		self.y = y
		self.tX = x # Target position
		self.tY = y
		self.vx = 0.0 # Velocity
		self.vy = 0.0
		self.visible = False
		self.justAppeared = True
		self.colour = colour
		self.midiOut = midiOut
		self.colourRange = colourRange
		if ID == None:
			self.ID = Marker.nMarkers
			Marker.nMarkers += 1
		else:
			self.ID = ID

	def Enable (self):
		self.visible = True
		self.justAppeared = True

	def Disable (self):
		self.visible = False

	def Tick (self, timeElapsed):
		if self.justAppeared:
			self.vx = self.vy = self.velocity = 0
			self.x = self.tX
			self.y = self.tY
			self.justAppeared = False
			return
		self.vx = (self.tX - self.x)/timeElapsed
		self.vy = (self.tY - self.y)/timeElapsed
		self.velocity = math.sqrt (self.vx**2 + self.vy**2)
		self.x = self.tX
		self.y = self.tY

	def Target (self, x, y):
		if not self.visible:
			self.Enable ()
		self.tX = x
		self.tY = y

class CVMarker (Marker):
	def __init__ (self,
			name="CVMarker",
			x=0,
			y=0,
			colour=None,
			midiOut=None,
			xController=MARKER_CV_DEFAULT_X_CONTROLLER,
			yController=MARKER_CV_DEFAULT_Y_CONTROLLER,
			xChannel=1,
			yChannel=1,
			xRange=(0,127),
			yRange=(0,127),
			colourRange=None,
			ID = None):
		Marker.__init__ (self,
			name=name,
			x=x,
			y=y,
			colour=colour,
			midiOut=midiOut,
			colourRange=colourRange,
			ID = ID)
		self.xController = xController
		self.yController = yController
		self.xRange = xRange
		self.yRange = yRange
		self.xChannel = xChannel
		self.yChannel = yChannel

	def Tick (self, timeElapsed):
		Marker.Tick (self, timeElapsed)
		if not self.visible: return
		# Generate MIDI output
		mX = int(self.x*127)
		mY = int((1-self.y)*127)
		self.midiOut.SendControl (mX,controller=self.xController,channel=1)
		self.midiOut.SendControl (mY,controller=self.yController,channel=1)

class NoteMarker (Marker):
	'''
	A marker that triggers notes when it passes by ('plucks') lines called
	strings. A NoteMarker has three modes of operation that affect how it
	triggers notes:
	
	AutoRelease (default): Plucking a string fires a fixed-duration note.
		Iff the 'polyphonic' flag is set, plucking an already-active
		string with a new note does not cause an immediate note-off
		message to be sent for the active notes.
	
	Toggle: Plucking an inactive string activates it and causes a note-on
		message to be sent. Plucking an active string deactivates it
		and causes a note-off message to be sent for the active note.
		The 'polyphonic' flag is ignored.

	Hold: Plucking a string activates it and causes a note-on message to
		be sent. Iff the polyphonic flag is set, no note-off messages
		are triggered. The string can only be deactivated by other
		means, e.g.: a 'marker hidden' event.
	'''
	MODE_AUTORELEASE = 0
	MODE_TOGGLE = 1
	MODE_LEGATO = 2

	def __init__ (self,
			name="NoteMarker",
			x=0,
			y=0,
			colour=None,
			colourRange=None,
			midiOut=None,
			channel=1,
			noteRange=(0,127),
			velocityRange=(0,127),
			scale=None,
			strings=[],
			mode=MODE_AUTORELEASE,
			muteOnHide=False,
			polyphonic=False,
			ID=None,
			duration=MARKER_NOTE_DEFAULT_DURATION):
		Marker.__init__ (self,
			name=name,
			x=x,
			y=y,
			colour=colour,
			midiOut=midiOut,
			colourRange=colourRange,
			ID = ID)
		self.channel = channel
		self.noteRange = noteRange
		self.velocityRange = velocityRange
		self.scale = scale
		self.strings = strings
		self.mode = mode
		self.muteOnHide = muteOnHide
		self.polyphonic = polyphonic
		self.duration = duration
	
	def Disable (self):
		''' The marker was not found in the processed image. '''
		self.visible = False
		if self.muteOnHide: self.MuteActiveNotes ()
	
	def Tick (self, timeElapsed):
		''' Marker heartbeat function. '''
		# Determine which strings have been plucked, if any.
		pluckedStrings = []
		for i, string in enumerate (self.strings):
			if not self.justAppeared:
				crossedLeft = (self.tX < string.x and self.x > string.x)
				crossedRight = (self.tX > string.x and self.x < string.x)
				if crossedLeft or crossedRight:
					pluckedStrings.append (i)

		# Only now do we let the parent class update the marker's position. 
		Marker.Tick (self, timeElapsed)
		
		if self.mode == NoteMarker.MODE_AUTORELEASE:
			# Check if there are any active notes ready to be turned off.
			for string in self.strings:
				if len(string.activeNotes) == 0: continue
				for i in range(len(string.activeNotes)):
					string.remainingNoteTime[i] -= timeElapsed
				while len(string.activeNotes)>0 and string.remainingNoteTime[0] <= 0:
					# Send note-off and remove from active notes.
					self.midiOut.NoteOff (string.activeNotes[0],self.channel)
					string.remainingNoteTime.pop (0)
					string.activeNotes.pop (0)
		
		# Only continue if the marker is visible and a string has been plucked.
		if not self.visible or len(pluckedStrings) == 0: return
	
		# Handle plucked strings
		for stringIndex in pluckedStrings:
			string = self.strings[stringIndex]
			if len(string.activeNotes) > 0:
				if self.mode == NoteMarker.MODE_TOGGLE:
					# Toggle mode: If the string is already activated, deactive it.
					self.midiOut.NoteOff (string.activeNotes[0],self.channel)
					string.activeNotes = []
					continue
				elif not self.polyphonic:
					# Not polyphonic: mute active notes on this string.
					for note in string.activeNotes: self.midiOut.NoteOff (note, self.channel)
					string.activeNotes = []
					string.remainingNoteTime = []

			# Determine note from y position and string offset.
			note = self.scale.GetNote (self.y) + string.noteOffset
			string.activeNotes.append (note)
			if self.mode == NoteMarker.MODE_AUTORELEASE:
				string.remainingNoteTime.append (self.duration)
			velocity = max (64, min (self.velocity*64,127))
			self.midiOut.NoteOn (note, velocity, channel=self.channel)

	def MuteActiveNotes (self):
		''' Sends note-off messages for all active notes on all strings for this marker. '''
		for string in self.strings:
			for note in string.activeNotes: self.midiOut.NoteOff (note, self.channel)
			string.activeNotes = []
			string.remainingNoteTime = []

class Tracker:
	def __init__ (self, midiOut):
		self.midiOut = midiOut

		self.featureFrame = cv.CreateImage (GRID_SIZE, 8, 3)
		self.featureDisplayFrame = cv.CreateImage (STREAM_SIZE, 8, 3)
		self.markers = []

		self.scale = DiatonicScale (48,2)

		redRange = HSVColourRange (hue=SN_RHUE,saturation=SN_RSAT,value=SN_RVAL,hue2=SN_RHUE2)
		blueRange = HSVColourRange (hue=SN_BHUE,saturation=SN_BSAT,value=SN_BVAL)
		greenRange = HSVColourRange (hue=SN_GHUE,saturation=SN_GSAT,value=SN_GVAL)
		yellowRange = HSVColourRange (hue=SN_YHUE,saturation=SN_YSAT,value=SN_YVAL)
		self.markers.append (NoteMarker ( # Red
			name="Red",
			colour=(0,0,255),
			colourRange=redRange,
			midiOut=self.midiOut,
			channel=0x91,
			scale=self.scale,
			mode=NoteMarker.MODE_LEGATO,
			strings=self.GenerateStrings (0.75,GUITAR),
			muteOnHide=True))
		self.markers.append (NoteMarker ( # Green
			name="Green",
			colour=(0,255,0),
			colourRange=greenRange,
			midiOut=self.midiOut,
			channel=0x92,
			scale=self.scale,
			strings=self.GenerateStrings (0.55,[0])))
		self.markers.append (NoteMarker ( # Blue
			name="Blue",
			colour=(255,0,0),
			colourRange=blueRange,
			midiOut=self.midiOut,
			channel=0x90,
			scale=self.scale,
			mode=NoteMarker.MODE_AUTORELEASE,
			strings=self.GenerateStrings (0.25, GUITAR)))
		self.markers.append (NoteMarker ( # Yellow
			name="Yellow",
			colour=(255,255,0),
			colourRange=yellowRange,
			midiOut=self.midiOut,
			channel=0x94,
			scale=self.scale,
			strings=self.GenerateStrings (0.45,[0])))

	def Tick (self, timeElapsed):
		visibleMarkers = []
		for i, marker in enumerate(self.markers):
			# Update marker positions
			marker.Tick (timeElapsed)
			if not marker.visible: continue

	def GenerateStrings (self, centre, offsetPattern, spacing=0.05):
		n = len (offsetPattern)
		width = n * spacing
		left = centre - width/2
		return [String(left+spacing*i, offsetPattern[i]) for i in range(n)]
