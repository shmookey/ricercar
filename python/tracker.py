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

class Marker:
	''' An object with a position in an abstract 3-dimensional space 0->1.
	'''

	def __init__ (self,
			name="Marker",
			x=0,
			y=0,
			colour=None,
			midiOut=None,
			visible=False, 
			xMin=0,
			yMin=0,
			xMax=127,
			yMax=127,
			xChannel=1,
			yChannel=1,
			colourRange=None):
		self.name = name
		self.x = x # Position
		self.y = y
		self.tX = x # Target position
		self.tY = y
		self.vx = 0.0 # Velocity
		self.vy = 0.0
		self.visible = visible
		self.justAppeared = True
		self.colour = colour
		self.midiOut = midiOut
		self.xChannel = xChannel
		self.yChannel = yChannel
		self.xMin = xMin
		self.yMin = yMin
		self.xMax = xMax
		self.yMax = yMax

		# Colour capture parameters - list of (min,max) tuples
		self.colourRange = colourRange

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

	def Target (self, x, y, z):
		# If 'z' (actually brightness) is less than a threshold the marker is invisible.
		if z<BRIGHTNESS_THRESHOLD:
			self.Disable ()
			return
		elif not self.visible:
			self.Enable ()
		self.tX = x
		self.tY = y

class CVMarker (Marker):
	def __init__ (self,
			x=0,
			y=0,
			colour=None,
			midiOut=None,
			visible=False,
			controller=0,
			xChannel=1,
			yChannel=1,
			xMin=0,
			xMax=127,
			yMin=0,
			yMax=127,
			colourRange=None):
		self.controller = controller
		Marker.__init__ (self, x=x,
					y=y,
					colour=colour,
					midiOut=midiOut,
					visible=visible, 
					xMin=xMin,
					yMin=yMin,
					xMax=xMax,
					yMax=yMax,
					xChannel=xChannel,
					yChannel=yChannel,
					colourRange=colourRange)

	def Tick (self, timeElapsed):
		Marker.Tick (self, timeElapsed)
		if not self.visible: return
		# Generate MIDI output
		mX = int(self.x*127)
		mY = int((1-self.y)*127)
		self.midiOut.SendControl (mX,controller=self.controller,channel=1)
		self.midiOut.SendControl (mY,controller=self.controller+1,channel=1)

class NoteMarker (Marker):
	def __init__ (self,
			name="Marker",
			x=0,
			y=0,
			colour=None,
			midiOut=None,
			visible=False, 
			controller=0,
			xChannel=1,
			yChannel=1,
			xMin=0,
			xMax=127,
			yMin=0,
			yMax=127,
			colourRange=None,
			scale=DiatonicScale (60,2),
			stringx=[0.5]):
		self.lastNote = -1
		self.scale = scale
		self.stringx = stringx
		self.strings = {i: False for i,s in enumerate(stringx)}
		self.xMode = "Note"
		self.yMode = "Velocity"
		Marker.__init__ (self,
			name=name,
			x=x,
			y=y,
			colour=colour,
			midiOut=midiOut,
			visible=visible, 
			xMin=xMin,
			yMin=yMin,
			xMax=xMax,
			yMax=yMax,
			xChannel=xChannel,
			yChannel=yChannel,
			colourRange=colourRange)
	
	def Disable (self):
		self.visible = False
		#self.CancelLastNote ()
	
	def Tick (self, timeElapsed):
		triggerNote = None
		for i, stringx in enumerate (self.stringx):
			if not self.justAppeared:
				crossedLeft = (self.tX < stringx and self.x > stringx)
				crossedRight = (self.tX > stringx and self.x < stringx)
				if crossedLeft or crossedRight:
					triggerNote = i
		Marker.Tick (self, timeElapsed)
		if not self.visible:
		#	self.CancelLastNote ()
			self.Disable ()
			return
		if triggerNote == None: return
		
		if self.strings[triggerNote]:
			self.midiOut.NoteOff (self.strings[triggerNote],self.xChannel)
			self.strings[triggerNote] = False
			return
			
		pitch = self.scale.GetNote (self.y) + GUITAR[triggerNote]
		self.strings[triggerNote] = pitch
		velocity = max (64, min (self.velocity*64,127))
		self.lastNote = pitch
		self.midiOut.NoteOn (pitch, velocity, channel=self.yChannel)
	
	def CancelLastNote (self):
		lastNote = self.lastNote
		if lastNote < 1: return
		self.midiOut.NoteOff (lastNote, channel=self.yChannel)
		self.lastNote = -1

class Tracker:
	def __init__ (self, window, midiOut):
		self.midiOut = midiOut
		self.window = window

		self.featureFrame = cv.CreateImage (GRID_SIZE, 8, 3)
		self.featureDisplayFrame = cv.CreateImage (STREAM_SIZE, 8, 3)
		self.markers = []

		self.scale = DiatonicScale (48,2)

		redRange = HSVColourRange (hue=SN_RHUE,saturation=SN_RSAT,value=SN_RVAL,hue2=SN_RHUE2)
		blueRange = HSVColourRange (hue=SN_BHUE,saturation=SN_BSAT,value=SN_BVAL)
		greenRange = HSVColourRange (hue=SN_GHUE,saturation=SN_GSAT,value=SN_GVAL)
		yellowRange = HSVColourRange (hue=SN_YHUE,saturation=SN_YSAT,value=SN_YVAL)
		self.markers.append (NoteMarker ( # Red
			colour=(0,0,255),
			midiOut=self.midiOut,
			#controller=0x01,
			xChannel=0x91,yChannel=0x91,
			colourRange=redRange,
			scale=self.scale,
			stringx=[0.65,0.70,0.75,0.80,0.85]))
		self.markers.append (NoteMarker ( # Green
			colour=(0,255,0),
			midiOut=self.midiOut,
			xChannel=0x92,yChannel=0x92,
			scale=self.scale,
			colourRange=greenRange))
		self.markers.append (NoteMarker ( # Blue
			colour=(255,0,0),
			midiOut=self.midiOut,
			xChannel=0x93,yChannel=0x93,
			colourRange=blueRange,
			scale=self.scale,
			#stringx=[0.25]))
			stringx=[0.15,0.20,0.25,0.30,0.35]))
		self.markers.append (NoteMarker ( # Yellow
			colour=(255,255,0),
			midiOut=self.midiOut,
			xChannel=0x94,yChannel=0x94,
			scale=self.scale,
			colourRange=yellowRange))

	def Tick (self, timeElapsed):
		# Clear feature display
		frame = self.featureFrame

		visibleMarkers = []
		for i, marker in enumerate(self.markers):
			# Update marker positions
			marker.Tick (timeElapsed)
			if not marker.visible: continue

			# Annotate feature chart
			fX = min(marker.x*frame.width,frame.width-1)
			fY = min(marker.y*frame.height,frame.height-1)

			# Send marker positions to main window
			visibleMarkers.append (marker)
		self.window.ShowMarkers (visibleMarkers)


