''' ui.py - Main window GUI for ricercar
'''

import cv, pygame, FTGL
from OpenGL.GL import *
from OpenGL.GLU import *

from UIElement import *
from tracker import Marker, NoteMarker, CVMarker
from music import PITCH_TO_NOTE
from CVGLImage import CVGLImage
from constants import *
from config import *

#
# Public Service Announcement
# Remember: In OpenGL coordinates the origin (0,0) is at the bottom left.
#

class MainWindow:
	def __init__ (self, scheduler):
		self.midiInPorts = []
		self.midiOutPorts = []
		self.showHUD = False
		self.showIO = False
		self.midiInDevice = None
		self.midiOutDevice = None
		self.frames = []
		self.textures = []
		self.items = []
		self.scheduler = scheduler

		self.trackerConfigurationWindow = None

	def InitVideo (self):
		''' Initialises OpenGL.

		All methods that invoke OpenGL must be made from a single thread.
		'''
		pygame.init ()
		pygame.display.set_mode ((DISPLAY_SIZE[0],DISPLAY_SIZE[1]), pygame.OPENGL|pygame.DOUBLEBUF)
		
		glClearColor(0.0,0.0,0.0,0.0)
		glColor3f (1.0,1.0,1.0)
		glPointSize (4.0)
		glMatrixMode (GL_PROJECTION)
		glLoadIdentity ()
		gluOrtho2D (0.0, DISPLAY_SIZE[0], 0.0, DISPLAY_SIZE[1])
		glEnable (GL_BLEND)
		glBlendFunc (GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

		self.frames.append (cv.CreateMat (STREAM_SIZE[1],STREAM_SIZE[0],cv.CV_8UC3)) # FRAME_RAW
		self.frames.append (cv.CreateMat (GRID_SIZE[1],GRID_SIZE[0],cv.CV_8UC3)) # FRAME_GRID
		self.frames.append (cv.CreateMat (GRID_SIZE[1],GRID_SIZE[0],cv.CV_8UC3)) # FRAME_MASKED
		self.frames.append (cv.CreateMat (STREAM_SIZE[1],STREAM_SIZE[0],cv.CV_8UC3)) # FRAME_FEATURES
		self.frames.append (cv.CreateMat (STREAM_SIZE[1],STREAM_SIZE[0],cv.CV_8UC4)) # FRAME_COMPOSITED

		self.textures = glGenTextures (5)
		for texture in self.textures:
			glBindTexture (GL_TEXTURE_2D, texture)
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
			glTexParameteri (GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
			glTexParameteri (GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
			glTexParameteri (GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
		
		self.largeFont = FTGL.TextureFont (FONT)
		self.largeFont.FaceSize (18)
		self.smallFont = FTGL.TextureFont (FONT)
		self.smallFont.FaceSize (16)


	def SetTracker (self, tracker):
		''' Informs the Window of the Tracker from which it will be 
		displaying information. 
		
		Causes the configuration UI elements to be regenerated. This
		method should only be called once.
		'''
		self.tracker = tracker
		self.trackerConfigurationWindow = TrackerConfigurationWindow (
			tracker = tracker,
			window = self,
			bounds = Rect (0,0,0,0))
		self.items.append (self.trackerConfigurationWindow)

	
	def SetMIDIDeviceList (self, inPorts, outPorts, activeIn, activeOut):
		self.midiInPorts = inPorts
		self.midiOutPorts = outPorts
		self.midiInDevice = activeIn
		self.midiOutDevice = activeOut

		def SelectInputDevice (obj):
			self.midiInDevice.SetInputPort (obj.value)
		def SelectOutputDevice (obj):
			self.midiOutDevice.SetOutputPort (obj.value)

		# Generate IO selector menu items
		self.InputSelector = SelectionGroup (
			label = "MIDI Input",
			window = self,
			options=enumerate(inPorts),
			default=activeIn.deviceID,
			bounds=Rect(20,DISPLAY_SIZE[1]-20,UI_TABLE_COLUMN_WIDTH*5,0),
			onSelect=SelectInputDevice)
		self.OutputSelector = SelectionGroup (
			label = "MIDI Output",
			window = self,
			options=enumerate(outPorts),
			default=activeIn.deviceID,
			bounds=Rect(400,DISPLAY_SIZE[1]-20,UI_TABLE_COLUMN_WIDTH*5,0),
			onSelect=SelectOutputDevice)

	def NewRawFrame (self, frame):
		''' 
		Copies new raw stream data to this Window's frame buffer.
		Also converts it to RGB.

		Raw frame data is expected to be in OpenCV's default of BGR 8UC3. 
		'''
		cv.CvtColor (frame, self.frames[FRAME_RAW], cv.CV_BGR2RGB)

	def NewMaskedFrame (self, frame):
		'''
		Copies new image data masked to reveal important features (the
		'masked frame') to this Window's frame buffer.
		Also converts it to RGB.

		Masked frame data is expected to be in RGB 8UC4. '''
		self.frames[FRAME_MASKED] = frame

	def NewGridFrame (self, frame):
		''' 
		Copies new image data containing the downsampled image used in
		processing.
		Also converts it to RGB.

		Grid frame data is expected to be in OpenCV default BGR 8UC3.
		'''
		cv.CvtColor (frame, self.frames[FRAME_GRID], cv.CV_BGR2RGB)

	def Tick (self):
		''' Renders the next frame.
		
		Must be called from the same thread as InitVideo.'''
		glClear (GL_COLOR_BUFFER_BIT)

		self.LoadVideoTextures ()
		self.DrawVideoStream ()
		self.DrawMarkerLocations ()
		self.DrawNoteBoundaries ()
		self.DrawStrings ()
		self.DrawFPS ()
		if self.showHUD: self.DrawConfigUI ()
		if self.showIO: self.DrawIOSelector ()

		pygame.display.flip ()

	def ToggleHUD (self):
		if self.showHUD: self.showHUD = False
		else:
			self.showHUD = True
			self.showIO = False

	def ToggleIO (self):
		if self.showIO:
			self.items.remove (self.InputSelector)
			self.items.remove (self.OutputSelector)
			self.showIO = False
		else:
			self.items.append (self.InputSelector)
			self.items.append (self.OutputSelector)
			self.showIO = True
			self.showHUD = False

	def DrawFPS (self):
		glPushMatrix ()
		glColor4f (*UI_HUD_TEXT_COLOUR)
		glTranslatef (DISPLAY_SIZE[0]-100.0, DISPLAY_SIZE[1]-UI_TABLE_ROW_HEIGHT, 0.0)
		self.smallFont.Render ("FPS: %i" % self.scheduler.frameTimer.fps)
		glPopMatrix()

	def LoadVideoTextures (self):
		''' Load OpenCV image data into OpenGL textures. '''
		glEnable (GL_TEXTURE_2D)
		for i,frame in  enumerate (self.frames):
			mat = cv.GetMat (self.frames[i])
			img = CVGLImage (mat)
			if i!=FRAME_MASKED: img.LoadRGBTexture (int(self.textures[i]))
			else: img.LoadRGBATexture (int(self.textures[i]))

	def DrawVideoStream (self):
		# Draw image data
		glColor4f (1.0,1.0,1.0,1.0)
		self.DrawTexturedRect (FRAME_GRID,0,0,DISPLAY_SIZE[0],DISPLAY_SIZE[1])
		glColor4f (1.0,1.0,1.0,0.6)
		glDisable (GL_TEXTURE_2D)
		self.DrawTexturedRect (FRAME_NOTEXTURE,0,0,DISPLAY_SIZE[0],DISPLAY_SIZE[1])
		glEnable (GL_TEXTURE_2D)
		glColor4f (1.0,1.0,1.0,1.0)
		self.DrawTexturedRect (FRAME_MASKED,0,0,DISPLAY_SIZE[0],DISPLAY_SIZE[1])
		glDisable (GL_TEXTURE_2D)

	def DrawMarkerLocations (self):
		for i,marker in enumerate(self.tracker.markers):
			if not marker.visible: continue
			markerX = int(marker.x*DISPLAY_SIZE[0])
			markerY = int(marker.y*DISPLAY_SIZE[1])
			colour = [marker.colour[2],marker.colour[1],marker.colour[0],1.0]
			transparent = colour[:]
			transparent[3] = 0.0
			glLineWidth (CROSSHAIR_THICKNESS)
			# Vertical
			glBegin (GL_LINE_STRIP)	
			glColor4f (*transparent)
			glVertex2i (markerX,markerY - CROSSHAIR_SIZE)
			glColor4f (*colour)
			glVertex2i (markerX, markerY)
			glColor4f (*transparent)
			glVertex2i (markerX,markerY + CROSSHAIR_SIZE)
			glEnd ()
			# Horizontal
			glBegin (GL_LINE_STRIP)	
			glColor4f (*transparent)
			glVertex2i (markerX - CROSSHAIR_SIZE,markerY)
			glColor4f (*colour)
			glVertex2i (markerX, markerY)
			glColor4f (*transparent)
			glVertex2i (markerX + CROSSHAIR_SIZE, markerY)
			glEnd ()

	def DrawNoteBoundaries (self):
		glColor4f (1.0,1.0,1.0,0.75)
		glLineWidth (NOTE_BOUNDARY_THICKNESS)
		# For now we'll test by drawing two pentatonic ocatves - 10 notes
		noteSize = int(DISPLAY_SIZE[1] / self.tracker.scale.nNotes)
		scale = self.tracker.scale
		for i, (pitch, relY) in enumerate(self.tracker.scale.notePositions): 
			y = int(relY * DISPLAY_SIZE[1])
			glBegin (GL_LINES)
			glVertex2i (0,y)
			glVertex2i (DISPLAY_SIZE[0],y)
			glEnd ()

			glPushMatrix ()
			glTranslatef (5.0,y+20.0,0.0)
			self.largeFont.Render ("%s" % PITCH_TO_NOTE[pitch])
			glPopMatrix ()

			highlight = scale.highlights[i]
			if highlight:
				glColor4f (*highlight)
				self.DrawTexturedRect (FRAME_NOTEXTURE, 0, y, DISPLAY_SIZE[0], noteSize)

	def DrawStrings (self):
		for marker in self.tracker.markers:
			if not isinstance(marker, NoteMarker): continue
			color = marker.colour
			glColor3f (color[2],color[1],color[0])
			for i, string in enumerate(marker.strings):
				if len(string.activeNotes) == 0: glLineWidth (NOTE_BOUNDARY_THICKNESS)
				else: glLineWidth (NOTE_BOUNDARY_THICKNESS*2)
				glBegin (GL_LINES)
				glVertex2i (int(DISPLAY_SIZE[0]*string.x),0)
				glVertex2i (int(DISPLAY_SIZE[0]*string.x),DISPLAY_SIZE[1])
				glEnd ()

	def DrawConfigUI (self):
		self.trackerConfigurationWindow.Tick ()
		self.trackerConfigurationWindow.Redraw ()

	def DrawIOSelector (self):
		self.InputSelector.Tick ()
		self.InputSelector.Redraw ()
		self.OutputSelector.Tick ()
		self.OutputSelector.Redraw ()

	def Click (self, x, y):
		invY = DISPLAY_SIZE[1]-y
		for item in self.items:
			if item.bounds.IsPointInside (x,invY): item.Click (x,invY)

	def DrawTexturedRect (self, frameID, x, y, w, h):
		if not frameID < 0: glBindTexture (GL_TEXTURE_2D, self.textures[frameID])
		glBegin (GL_QUADS)
		glTexCoord2f (0.0,0.0)
		glVertex2i (x,y)
		glTexCoord2f (1.0,0.0)
		glVertex2i (x+w,y)
		glTexCoord2f (1.0,1.0)
		glVertex2i (x+w,y+h)
		glTexCoord2f (0.0,1.0)
		glVertex2i (x,y+h)
		glEnd ()


class TrackerConfigurationWindow (BasicFrame):
	''' A lean configuration interface for the MIDI output caused by a marker.
	
	Overrides the width and height of the supplied bounds.'''

	def __init__ (self,
			tracker = None,
			bounds = None,
			window = None,
			bgColour = UI_HUD_BG_COLOUR,
			textColour = UI_HUD_TEXT_COLOUR):
		
		BasicFrame.__init__ (self,
			bounds = bounds,
			window = window,
			bgColour = bgColour)
		
		self.tracker = tracker
		self.textColour = textColour
		self.markerSubmenus = [None] * 4

		paramTable = self.paramTable = DataTable (
			window = window,
			headers = DATA_TABLE_HEADERS,
			rowData = self.GetConfigurationData (),
			bounds = Rect(bounds.x+UI_FRAME_PADDING,bounds.y,0,0),
			bgColour = None,
			textColour = textColour)
		self.items.append (paramTable)

		markerTypeButtons = self.markerTypeButtons = [CyclicButton (
			labels = ["Note","CV"],
			values = [Marker.TYPE_NOTE,Marker.TYPE_CV],
			startIndex = 0,
			window = window,
			bounds = Rect (
				self.paramTable.bounds.xMax,
				self.paramTable.bounds.yMax-((i+3)*UI_TABLE_ROW_HEIGHT)-6,
				UI_TABLE_COLUMN_WIDTH,
				UI_TABLE_ROW_HEIGHT),
			onClick = self.GenerateClickHandler (marker),
			) for i, marker in enumerate(tracker.markers)]
		self.items += markerTypeButtons
		
		# Open default menus on initialisation
		for i, marker in enumerate (tracker.markers):
			ID = marker.ID
			button = markerTypeButtons[i]
			newMarkerOpts = NoteMarkerConfigurationStrip (
				marker = marker,
				window = self.window,
				bounds = Rect (button.bounds.xMax, button.bounds.y-1, 0, 0),
				bgColour = None
			)
			self.markerSubmenus[ID] = newMarkerOpts
			self.items.append (newMarkerOpts)

		#self.items = [self.paramTable] + self.markerTypeButtons
		self.FitItems ()

	def GetConfigurationData (self):
		return [
			[m.name,
			"%.2f" % m.x,
			"%.2f" % m.y,
			"%i-%i" % (m.colourRange.hue[0],m.colourRange.hue[1]),
			"%i-%i" % (m.colourRange.saturation[0],m.colourRange.saturation[1]),
			"%i-%i" % (m.colourRange.value[0],m.colourRange.value[1]),]
			for m in self.tracker.markers]

	def Tick (self):
		self.paramTable.rowData = self.GetConfigurationData ()
		BasicFrame.Tick (self)

	def GenerateClickHandler (self, marker):
		def MarkerTypeClick (button):
			newMarkerOpts = None
			newMarker = None
			# Remove old marker options, if any
			oldMarkerOpts = self.markerSubmenus[marker.ID]
			if oldMarkerOpts: self.items.remove (oldMarkerOpts)
			
			if button.value == Marker.TYPE_NOTE:
				# Display new NoteMarker options
				newMarkerOpts = NoteMarkerConfigurationStrip (
					marker = marker,
					window = self.window,
					bounds = Rect (button.bounds.xMax, button.bounds.y-1, 0, 0),
					bgColour = None)
				newMarker = NoteMarker (
					colour = marker.colour,
					colourRange = marker.colourRange,
					midiOut = marker.midiOut,
					channel = marker.xChannel,
					name = marker.name,
					scale = self.tracker.scale,
					mode = MARKER_NOTE_DEFAULT_MODE,
					strings = self.tracker.GenerateStrings ((marker.ID+1)/8+0.5,[0]),
					ID = marker.ID)
			elif button.value == Marker.TYPE_CV:
				# Display CVMarker options
				newMarkerOpts = CVMarkerConfigurationStrip (
					marker = marker,
					window = self.window,
					bounds = Rect (button.bounds.xMax, button.bounds.y-1, 0, 0),
					bgColour = None)
				newMarker = CVMarker (
					colour = marker.colour,
					colourRange = marker.colourRange,
					midiOut = marker.midiOut,
					xChannel = marker.channel,
					yChannel = marker.channel,
					name = marker.name,
					xController = MARKER_CV_DEFAULT_X_CONTROLLER,
					yController = MARKER_CV_DEFAULT_Y_CONTROLLER,
					ID = marker.ID)
			self.items.append (newMarkerOpts)
			self.markerSubmenus[marker.ID] = newMarkerOpts
			idx = self.tracker.markers.index (marker)
			self.tracker.markers[idx] = newMarker

			# Resize to fit new marker options
			self.FitItems ()

		return MarkerTypeClick

class NoteMarkerConfigurationStrip (BasicFrame):
	def __init__ (self,
			marker = None,
			window = None,
			bounds = None,
			bgColour = None):
		BasicFrame.__init__ (self,
			window = window,
			bounds = bounds,
			bgColour = bgColour)

		self.marker = marker
		channelButton = CyclicButton (
			window = self.window,
			bounds = Rect (bounds.x, bounds.y, UI_TABLE_COLUMN_WIDTH, UI_TABLE_ROW_HEIGHT),
			labels = ["Ch: %i" % (i+1) for i in range(16)],
			values = [MIDI_CHANNEL_START + i for i in range(16)],
			startIndex = 0,
			onClick = self.ChannelClick
		)
		markerModeButton = self.markerModeButton = CyclicButton (
			window = self.window,
			bounds = Rect (channelButton.bounds.xMax, bounds.y, UI_TABLE_COLUMN_WIDTH*1.5, UI_TABLE_ROW_HEIGHT),
			labels = ["AutoRelease","Toggle","Legato"],
			values = [NoteMarker.MODE_AUTORELEASE, NoteMarker.MODE_TOGGLE, NoteMarker.MODE_LEGATO],
			startIndex = 0,
			onClick = self.MarkerModeClick
		)
		modeOptions = self.modeOptions = AutoReleaseConfigurationStrip (
			marker = marker,
			window = window,
			bounds = Rect (markerModeButton.bounds.xMax, bounds.y, 0, 0),
			bgColour = None
		)
		self.items = [channelButton, markerModeButton, modeOptions]
		self.FitItems ()

	def MarkerModeClick (self, button):
		self.items.pop () # The last item should always be these options.
		modeOptions = None
		if button.value == NoteMarker.MODE_AUTORELEASE:
			modeOptions = self.modeOptions = AutoReleaseConfigurationStrip (
				marker = self.marker,
				window = self.window,
				bounds = Rect (self.markerModeButton.bounds.xMax, self.bounds.y, 0, 0),
				bgColour = None)
			self.marker.mode = NoteMarker.MODE_AUTORELEASE
		elif button.value == NoteMarker.MODE_LEGATO:
			modeOptions = self.modeOptions = LegatoConfigurationStrip (
				marker = self.marker,
				window = self.window,
				bounds = Rect (self.markerModeButton.bounds.xMax, self.bounds.y, 0, 0),
				bgColour = None)
			self.marker.mode = NoteMarker.MODE_LEGATO
		elif button.value == NoteMarker.MODE_TOGGLE:
			modeOptions = self.modeOptions = ToggleConfigurationStrip (
				marker = self.marker,
				window = self.window,
				bounds = Rect (self.markerModeButton.bounds.xMax, self.bounds.y, 0, 0),
				bgColour = None)
			self.marker.mode = NoteMarker.MODE_TOGGLE
		
		self.items.append (modeOptions)
		self.FitItems ()

	def ChannelClick (self, button):
		self.marker.channel = button.value
		print self.marker.name, self.marker.channel

class CVMarkerConfigurationStrip (BasicFrame):
	def __init__ (self,
			marker = None,
			window = None,
			bounds = None,
			bgColour = None):
		BasicFrame.__init__ (self,
			window = window,
			bounds = bounds,
			bgColour = bgColour)

		self.marker = marker
		xChannelButton = CyclicButton (
			window = self.window,
			bounds = Rect (bounds.x, bounds.y, UI_TABLE_COLUMN_WIDTH, UI_TABLE_ROW_HEIGHT),
			labels = ["X Ch: %i" % (i+1) for i in range(16)],
			values = range(16),
			startIndex = 0,
		)
		yChannelButton = CyclicButton (
			window = self.window,
			bounds = Rect (xChannelButton.bounds.xMax, bounds.y, UI_TABLE_COLUMN_WIDTH, UI_TABLE_ROW_HEIGHT),
			labels = ["Y Ch: %i" % (i+1) for i in range(16)],
			values = range(16),
			startIndex = 0,
		)
		self.items = [xChannelButton, yChannelButton]
		self.FitItems ()

	def XChannelClick (self, button):
		self.marker.xChannel = button.value
	def YChannelClick (self, button):
		self.marker.yChannel = button.value


class AutoReleaseConfigurationStrip (BasicFrame):
	def __init__ (self,
			marker = None,
			window = None,
			bounds = None,
			bgColour = None):
		BasicFrame.__init__ (self,
			window = window,
			bounds = bounds,
			bgColour = bgColour)

		self.marker = marker

		duration = self.durationButton = CyclicButton (
			window = self.window,
			bounds = Rect (bounds.x, bounds.y, UI_TABLE_COLUMN_WIDTH, UI_TABLE_ROW_HEIGHT),
			labels = ["%i00ms" % (i+1) for i in range(10)],
			values = [0.1 * (i+1) for i in range(10)],
			startIndex = 1,
			onClick = self.DurationClick
		)
		polyphonicButton = self.polyphonicButton = CyclicButton (
			window = self.window,
			bounds = Rect (
				duration.bounds.xMax,
				bounds.y,
				UI_TABLE_COLUMN_WIDTH*1.5,
				UI_TABLE_ROW_HEIGHT),
			labels = ["Polyphonic","Monophonic"],
			values = [Marker.MODE_POLYPHONIC, Marker.MODE_MONOPHONIC],
			startIndex = 1,
			onClick = self.PolyphonicClick
		)
		self.items = [duration, polyphonicButton]
		self.FitItems ()
	
	def PolyphonicClick (self, button):
		self.marker.polyphonic = button.value

	def DurationClick (self, button):
		self.marker.duration = button.value

class ToggleConfigurationStrip (BasicFrame):
	def __init__ (self,
			marker = None,
			window = None,
			bounds = None,
			bgColour = None):
		BasicFrame.__init__ (self,
			window = window,
			bounds = bounds,
			bgColour = bgColour)

		# No options yet...
		
		self.items = []

class LegatoConfigurationStrip (BasicFrame):
	def __init__ (self,
			marker = None,
			window = None,
			bounds = None,
			bgColour = None):
		BasicFrame.__init__ (self,
			window = window,
			bounds = bounds,
			bgColour = bgColour)

		self.marker = marker
		polyphonicButton = self.polyphonicButton = CyclicButton (
			window = self.window,
			bounds = Rect (
				bounds.x,
				bounds.y,
				UI_TABLE_COLUMN_WIDTH*1.5,
				UI_TABLE_ROW_HEIGHT),
			labels = ["Polyphonic","Monophonic"],
			values = [Marker.MODE_POLYPHONIC, Marker.MODE_MONOPHONIC],
			startIndex = 1,
			onClick = self.PolyphonicClick
		)
		self.items = [polyphonicButton]
		self.FitItems ()

	def PolyphonicClick (self, button):
		self.marker.polyphonic = button.value
