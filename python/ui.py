''' ui.py - Main window GUI for ricercar
'''

import cv, pygame, FTGL
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GL.ARB.framebuffer_object import *
from OpenGL.GL.EXT.framebuffer_object import *
from ctypes import *

from UIElement import *
from tracker import Marker, NoteMarker, CVMarker
from music import *
from CVGLImage import CVGLImage
from MIDIio import MIDIDevice
from constants import *
from config import *

#
# Public Service Announcement
# Remember: In OpenGL coordinates the origin (0,0) is at the bottom left.
#

class MainWindow:
	def __init__ (self,
			scheduler = None,
			tracker = None,
			streamProcessor = None,
			midiIn = None,
			midiOut = None):

		self.scheduler = scheduler
		self.streamProcessor = streamProcessor
		self.tracker = tracker
		self.midiIn = midiIn
		self.midiOut = midiOut

		self.frames = []
		self.items = []
		self.fonts = [None] * 2

		trackerConf = self.trackerConfigurationWindow = TrackerConfigurationWindow (
			tracker = tracker,
			window = self,
			bounds = Rect (0,0,0,0))
		globalConf = self.globalConfigurationWindow = GlobalConfigurationWindow (
			tracker = tracker,
			window = self,
			bounds = Rect (0,300,0,0))
		self.midiConfigurationWindow = MIDIConfigurationWindow (
			midiIn = midiIn,
			midiOut = midiOut,
			window = self,
			bounds = Rect (0, DISPLAY_SIZE[1]-UI_TABLE_ROW_HEIGHT, 0, 0))
		self.videoConfigurationWindow = VideoConfigurationWindow (
			streamProcessor = streamProcessor,
			window = self,
			bounds = Rect (0,trackerConf.bounds.yMax,0,0))
		self.menuButton = Button (
			label = "Show/Hide Menus (TAB)",
			window = self,
			bounds = Rect (800,DISPLAY_SIZE[1]-UI_TABLE_ROW_HEIGHT+1, UI_SHOW_MENU_WIDTH, UI_TABLE_ROW_HEIGHT),
			onClick = self.ToggleHUD,
			bgColour = UI_BUTTON_BG_COLOUR
		)
		self.exitButton = Button (
			label = "Exit",
			window = self,
			bounds = Rect (700,DISPLAY_SIZE[1]-UI_TABLE_ROW_HEIGHT+1, UI_EXIT_WIDTH, UI_TABLE_ROW_HEIGHT),
			onClick = self.Exit,
			bgColour = UI_BUTTON_BG_COLOUR
		)
		self.items.append (self.trackerConfigurationWindow)
		self.items.append (self.globalConfigurationWindow)
		self.items.append (self.videoConfigurationWindow)
		self.items.append (self.midiConfigurationWindow)
		self.items.append (self.menuButton)
		self.items.append (self.exitButton)
		streamProcessor.SetModeChangeCallback (self.VideoModeChanged)

	def InitVideo (self):
		''' Initialises OpenGL.

		All methods that invoke OpenGL must be made from a single thread.
		'''
		w, h = DISPLAY_SIZE
		pygame.init ()
		pygame.display.set_mode ((w,h), pygame.OPENGL|pygame.DOUBLEBUF)
		pygame.display.set_caption (WINDOW_TITLE)
		
		glClearColor(0.0,0.0,0.0,0.0)
		glColor3f (1.0,1.0,1.0)
		glPointSize (4.0)
		glMatrixMode (GL_PROJECTION)
		glLoadIdentity ()
		gluOrtho2D (0.0, w, 0.0, h)
		glEnable (GL_BLEND)
		glBlendFunc (GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

		# Create FBO object
		#self.uiFBO = glGenFramebuffers(1)
		#glBindFramebuffer(GL_FRAMEBUFFER, self.uiFBO)
		# Set FBO texture parameters
		#self.uiTexture = glGenTextures (1)
		#glBindTexture (GL_TEXTURE_2D, self.uiTexture)
		#glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
		#glTexParameteri (GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
		#glTexParameteri (GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
		#glTexParameteri (GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
		#glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,w,h,0,GL_RGBA,GL_UNSIGNED_INT,None)
		# Set up FBO colour buffer
		#color = glGenRenderbuffers(1)
                #glBindRenderbuffer( GL_RENDERBUFFER, color )
                #glRenderbufferStorage( GL_RENDERBUFFER, GL_RGB, w, h)
                #glFramebufferRenderbuffer( GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_RENDERBUFFER, color )
                #glBindRenderbuffer( GL_RENDERBUFFER, 0 )
		# Configure other FBO options
		#glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0_EXT, GL_TEXTURE_2D, self.uiTexture, 0)
		# Unbind FBO
		#glBindFramebuffer (GL_FRAMEBUFFER, 0)

		
		#glFramebufferTexture2D(
                #	GL_FRAMEBUFFER,
                #	GL_DEPTH_ATTACHMENT,
                #	GL_TEXTURE_2D,
                #	self.uiTexture,
                #	0 #mip-map level...
            	#)

		self.frameTextures = glGenTextures (2)
		for texture in self.frameTextures:
			glBindTexture (GL_TEXTURE_2D, texture)
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
			glTexParameteri (GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
			glTexParameteri (GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
			glTexParameteri (GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
		
		self.fonts[FONT_LARGE] = FTGL.TextureFont (FONT)
		self.fonts[FONT_LARGE].FaceSize (18)
		self.fonts[FONT_SMALL] = FTGL.TextureFont (FONT)
		self.fonts[FONT_SMALL].FaceSize (16)

	def Exit (self, button=None):
		self.scheduler.Stop ()

	def VideoModeChanged (self):
		sp = self.streamProcessor
		self.videoConfigurationWindow.VideoModeChanged ()
		if sp.capture == None: return
		self.gridFrame  = (cv.CreateMat (GRID_SIZE[1],GRID_SIZE[0],cv.CV_8UC3)) # FRAME_GRID
		self.maskedFrame = (cv.CreateMat (GRID_SIZE[1],GRID_SIZE[0],cv.CV_8UC3)) # FRAME_MASKED

	def Tick (self):
		''' Renders the next frame.
		
		Must be called from the same thread as InitVideo.'''
		#glClear (GL_COLOR_BUFFER_BIT)

		glColor4f (1.0,1.0,1.0,1.0)
		if self.streamProcessor.capture:
			self.LoadVideoTextures ()
			self.DrawVideoStream ()
	
		#glBindTexture (GL_TEXTURE_2D, self.uiTexture)
		#self.DrawTexturedRect (FRAME_NOTEXTURE, 0, 0, DISPLAY_SIZE[0], DISPLAY_SIZE[1])
		self.DrawMarkerLocations ()
		self.DrawNoteBoundaries ()
		self.DrawStrings ()
		
		self.DrawFPS ()
		
		for item in self.items:
			if not item.visible: continue
			item.Tick ()
			item.Redraw () # Until we have lazy rendering with VBOs

		pygame.display.flip ()

	def ToggleHUD (self, button=None):
		for item in self.items:
			item.visible = not item.visible
		self.menuButton.visible = True

	def DrawFPS (self):
		glPushMatrix ()
		glColor4f (*UI_HUD_TEXT_COLOUR)
		glTranslatef (DISPLAY_SIZE[0]-100.0, DISPLAY_SIZE[1]-UI_TABLE_ROW_HEIGHT, 0.0)
		self.fonts[FONT_SMALL].Render ("FPS: %i" % self.scheduler.frameTimer.fps)
		glPopMatrix()

	def LoadVideoTextures (self):
		# Raw frame data is expected to be in OpenCV's default of BGR 8UC3. 
		#frame = self.streamProcessor.GetRawFrame ()
		#cv.CvtColor (frame, self.frames[FRAME_RAW], cv.CV_BGR2RGB)
		# Masked frame data is expected to be in RGB 8UC4. 
		maskedFrame = self.streamProcessor.GetMaskedFrame ()
		# Grid frame data is expected to be in OpenCV default BGR 8UC3.
		frame = self.streamProcessor.GetGridFrame ()
		cv.CvtColor (frame, self.gridFrame, cv.CV_BGR2RGB)
		''' Load OpenCV image data into OpenGL textures. '''
		glEnable (GL_TEXTURE_2D)
		mat = cv.GetMat (self.gridFrame)
		img = CVGLImage (mat)
		img.LoadRGBTexture (int(self.frameTextures[FRAME_GRID]))
		mat = cv.GetMat (maskedFrame)
		img = CVGLImage (mat)
		img.LoadRGBATexture (int(self.frameTextures[FRAME_MASKED]))

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
		# Set up rendering to framebuffer
		#glBindTexture (GL_TEXTURE_2D, 0)
		#glBindFramebuffer(GL_FRAMEBUFFER, self.uiFBO )
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
			self.fonts[FONT_LARGE].Render ("%s" % PITCH_TO_NOTE[pitch])
			glPopMatrix ()

			highlight = scale.highlights[i]
			if highlight:
				glColor4f (*highlight)
				self.DrawTexturedRect (FRAME_NOTEXTURE, 0, y, DISPLAY_SIZE[0], noteSize)
		# Done rendering to framebuffer
		#glBindFramebuffer(GL_FRAMEBUFFER, 0)	

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

	def Click (self, x, y):
		invY = DISPLAY_SIZE[1]-y
		for item in self.items:
			if not item.visible: continue
			if item.bounds.IsPointInside (x,invY): item.Click (x,invY)

	def DrawTexturedRect (self, frameID, x, y, w, h):
		if not frameID < 0: glBindTexture (GL_TEXTURE_2D, self.frameTextures[frameID])
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


class MIDIConfigurationWindow (BasicFrame):
	def __init__ (self,
			midiIn = None,
			midiOut = None,
			bounds = None,
			window = None,
			bgColour = UI_HUD_BG_COLOUR,
			textColour = UI_HUD_TEXT_COLOUR):
		BasicFrame.__init__ (self,
			bounds = bounds,
			window = window,
			bgColour = bgColour)

		self.midiIn = midiIn
		self.midiOut = midiOut
		inputMode = SelectionGroup.MODE_NORMAL
		outputMode = SelectionGroup.MODE_NORMAL
		if midiIn.state == MIDIDevice.STATE_ERROR: inputMode = SelectionGroup.MODE_ERROR
		if midiOut.state == MIDIDevice.STATE_ERROR: outputMode = SelectionGroup.MODE_ERROR
		# Generate IO selector menu items
		self.inputSelector = SelectionGroup (
			label = "MIDI Input",
			window = window,
			options=enumerate(midiIn.inPorts),
			default=midiIn.deviceID,
			bounds=Rect(bounds.x,bounds.y,UI_MIDI_DEVICE_BUTTON_WIDTH,0),
			onSelect=self.OnSelectInputDevice,
			mode = inputMode)
		self.outputSelector = SelectionGroup (
			label = "MIDI Output",
			window = window,
			options=enumerate(midiOut.outPorts),
			default=midiOut.deviceID,
			bounds=Rect(self.inputSelector.bounds.xMax,bounds.y,UI_MIDI_DEVICE_BUTTON_WIDTH,0),
			onSelect=self.OnSelectOutputDevice,
			mode = outputMode)

		self.items.append (self.inputSelector)
		self.items.append (self.outputSelector)
		self.FitItems (preserve=False)

	def OnSelectInputDevice (self, obj):
		self.midiIn.OpenPort (obj.value)
		if self.midiIn.state == MIDIDevice.STATE_ERROR:
			self.inputSelector.SetMode (SelectionGroup.MODE_ERROR)
		else:
			self.inputSelector.SetMode (SelectionGroup.MODE_NORMAL)
	def OnSelectOutputDevice (self, obj):
		self.midiOut.OpenPort (obj.value)
		if self.midiOut.state == MIDIDevice.STATE_ERROR:
			self.outputSelector.SetMode (SelectionGroup.MODE_ERROR)
		else:
			self.outputSelector.SetMode (SelectionGroup.MODE_NORMAL)

class VideoConfigurationWindow (BasicFrame):
	def __init__ (self,
			streamProcessor = None,
			bounds = None,
			window = None,
			bgColour = UI_HUD_BG_COLOUR,
			textColour = UI_HUD_TEXT_COLOUR):
		BasicFrame.__init__ (self,
			bounds = bounds,
			window = window,
			bgColour = bgColour)

		self.streamProcessor = streamProcessor

		titleLabel = Label (
			text = "Video Source",
			bounds = Rect (
				bounds.x,
				bounds.y + UI_TABLE_ROW_HEIGHT*4,
				UI_VIDEO_DEVICE_BUTTON_WIDTH,
				UI_TABLE_ROW_HEIGHT),
			window = window,
			bgColour = None)
		self.items.append (titleLabel)
		previousVideoSource = Button (
			label = "Previous",
			bounds = Rect (
				bounds.x,
				titleLabel.bounds.y - UI_TABLE_ROW_HEIGHT,
				UI_VIDEO_DEVICE_BUTTON_WIDTH,
				UI_TABLE_ROW_HEIGHT),
			window = window,
			onClick = self.PreviousVideoSourceClick)
		self.items.append (previousVideoSource)
		nextVideoSource = Button (
			label = "Next",
			bounds = Rect (
				previousVideoSource.bounds.xMax,
				titleLabel.bounds.y - UI_TABLE_ROW_HEIGHT,
				UI_VIDEO_DEVICE_BUTTON_WIDTH,
				UI_TABLE_ROW_HEIGHT),
			window = window,
			onClick = self.NextVideoSourceClick)
		self.items.append (nextVideoSource)
		idLabel = Label (
			text = "ID:",
			bounds = Rect (
				bounds.x,
				nextVideoSource.bounds.y - UI_TABLE_ROW_HEIGHT,
				UI_VIDEO_DEVICE_BUTTON_WIDTH,
				UI_TABLE_ROW_HEIGHT),
			window = window)
		self.items.append (idLabel)
		idValue = self.idValue = Label (
			text = "(no video)",
			bounds = Rect (
				idLabel.bounds.xMax,
				nextVideoSource.bounds.y - UI_TABLE_ROW_HEIGHT,
				UI_VIDEO_DEVICE_BUTTON_WIDTH,
				UI_TABLE_ROW_HEIGHT),
			window = window)
		self.items.append (idValue)
		resolutionLabel = Label (
			text = "Resolution:",
			bounds = Rect (
				bounds.x,
				idLabel.bounds.y - UI_TABLE_ROW_HEIGHT,
				UI_VIDEO_DEVICE_BUTTON_WIDTH,
				UI_TABLE_ROW_HEIGHT),
			window = window)
		self.items.append (resolutionLabel)
		resolutionButton = self.resolutionButton = Button (
			label = "(no video)",
			bounds = Rect (
				resolutionLabel.bounds.xMax,
				idLabel.bounds.y - UI_TABLE_ROW_HEIGHT,
				UI_VIDEO_DEVICE_BUTTON_WIDTH,
				UI_TABLE_ROW_HEIGHT),
			window = window,
			onClick = self.VideoResolutionClick)
		self.items.append (resolutionButton)
		fpsLabel = Label (
			text = "FPS:",
			bounds = Rect (
				bounds.x,
				resolutionLabel.bounds.y - UI_TABLE_ROW_HEIGHT,
				UI_VIDEO_DEVICE_BUTTON_WIDTH,
				UI_TABLE_ROW_HEIGHT),
			window = window)
		self.items.append (fpsLabel)
		fpsButton = self.fpsButton = Button (
			label = "-",
			bounds = Rect (
				resolutionLabel.bounds.xMax,
				resolutionLabel.bounds.y - UI_TABLE_ROW_HEIGHT,
				UI_VIDEO_DEVICE_BUTTON_WIDTH,
				UI_TABLE_ROW_HEIGHT),
			window = window,
			onClick = self.FPSClick)
		self.items.append (fpsButton)
		
		self.FitItems ()

	def NextVideoSourceClick (self, button):
		self.streamProcessor.NextVideoSource ()
	
	def PreviousVideoSourceClick (self, button):
		self.streamProcessor.PreviousVideoSource ()

	def VideoModeChanged (self):
		sp = self.streamProcessor
		self.idValue.text = str(sp.deviceID)
		if sp.capture == None:
			self.resolutionButton.SetLabel ("(no video)")
			self.fpsButton.SetLabel ("-")
			self.resolutionButton.onClick = None
			self.fpsButton.onClick = None
		else:
			label = "%ix%i" % (sp.streamWidth, sp.streamHeight)
			self.resolutionButton.SetLabel (label)
			if sp.streamFPS > 0:
				self.fpsButton.SetLabel (str(sp.streamFPS))
			else:
				self.fpsButton.SetLabel ("-")
			self.resolutionButton.onClick = self.VideoResolutionClick
			self.fpsButton.onClick = self.FPSClick

	def VideoResolutionClick (self, button):
		currentRes = (self.streamProcessor.streamWidth, self.streamProcessor.streamHeight)
		resIdx = STREAM_SIZES.index (currentRes)
		resIdx += 1
		if resIdx >= len(STREAM_SIZES): resIdx = 0
		newRes = STREAM_SIZES [resIdx]
		print "Attempting to switch to %ix%i" % newRes
		fps = self.streamProcessor.streamFPS
		if fps > 0:
			self.streamProcessor.SetVideoSource (
				deviceID = self.streamProcessor.deviceID,
				rWidth = newRes[0],
				rHeight = newRes[1],
				rFPS = self.streamProcessor.streamFPS)
		else:
			self.streamProcessor.SetVideoSource (
				deviceID = self.streamProcessor.deviceID,
				rWidth = newRes[0],
				rHeight = newRes[1])
	
	def FPSClick (self, button):
		currentFPS = self.streamProcessor.streamFPS
		if currentFPS == 0: return # Driver doesn't support setting resolution.
		fpsIdx = STREAM_RATES.index (currentFPS)
		fpsIdx += 1
		if fpsIdx >= len(STREAM_RATES): fpsIdx = 0
		newFPS = STREAM_RATES [fpsIdx]
		self.streamProcessor.SetVideoSource (
			deviceID = self.streamProcessor.deviceID,
			rWidth = self.streamProcessor.streamWidth,
			rHeight = self.streamProcessor.streamHeight,
			rFPS = newFPS)

class GlobalConfigurationWindow (BasicFrame):
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

		titleLabel = Label (
			text = "Global Settings",
			bounds = Rect (
				bounds.x,
				bounds.y + UI_TABLE_ROW_HEIGHT*3,
				UI_GLOBAL_CONFIG_COLUMN_WIDTH,
				UI_TABLE_ROW_HEIGHT),
			window = window,
			bgColour = None)
		self.items.append (titleLabel)
		octavesLabel = Label (
			text = "Octaves",
			bounds = Rect (
				bounds.x,
				titleLabel.bounds.y - UI_TABLE_ROW_HEIGHT,
				UI_GLOBAL_CONFIG_COLUMN_WIDTH,
				UI_TABLE_ROW_HEIGHT),
			window = window)
		self.items.append (octavesLabel)
		octavesButton = CyclicButton (
			labels = ["%i" % i for i in OCTAVE_DISPLAY_RANGE],
			values = OCTAVE_DISPLAY_RANGE,
			startIndex = OCTAVE_DISPLAY_RANGE.index(tracker.scale.nOctaves),
			bounds = Rect (
				titleLabel.bounds.xMax,
				titleLabel.bounds.y - UI_TABLE_ROW_HEIGHT,
				UI_GLOBAL_CONFIG_COLUMN_WIDTH,
				UI_TABLE_ROW_HEIGHT),
			window = window,
			onClick = self.OctavesClick)
		self.items.append (octavesButton)
		scaleLabel = Label (
			text = "Scale",
			bounds = Rect (
				bounds.x,
				octavesLabel.bounds.y - UI_TABLE_ROW_HEIGHT,
				UI_GLOBAL_CONFIG_COLUMN_WIDTH,
				UI_TABLE_ROW_HEIGHT),
			window = window)
		self.items.append (scaleLabel)
		scaleButton = self.scaleButton = CyclicButton (
			labels = ["Pentatonic","Diatonic","Chromatic"],
			values = [Scale.TYPE_PENTATONIC, Scale.TYPE_DIATONIC, Scale.TYPE_CHROMATIC],
			startIndex = tracker.scale.scaleType,
			bounds = Rect (
				scaleLabel.bounds.xMax,
				octavesLabel.bounds.y - UI_TABLE_ROW_HEIGHT,
				UI_GLOBAL_CONFIG_COLUMN_WIDTH,
				UI_TABLE_ROW_HEIGHT),
			window = window,
			onClick = self.ScaleClick)
		self.items.append (scaleButton)
		keyLabel = Label (
			text = "Key:",
			bounds = Rect (
				bounds.x,
				scaleLabel.bounds.y - UI_TABLE_ROW_HEIGHT,
				UI_GLOBAL_CONFIG_COLUMN_WIDTH,
				UI_TABLE_ROW_HEIGHT),
			window = window)
		self.items.append (keyLabel)
		keyButton = self.keyButton = CyclicButton (
			labels = KEYS,
			values = [i for i in range(len(KEYS))],
			bounds = Rect (
				keyLabel.bounds.xMax,
				scaleLabel.bounds.y - UI_TABLE_ROW_HEIGHT,
				UI_GLOBAL_CONFIG_COLUMN_WIDTH,
				UI_TABLE_ROW_HEIGHT),
			window = window,
			onClick = self.KeyClick)
		self.items.append (keyButton)
		
		self.FitItems ()

	def ScaleClick (self, button):
		oldScale = self.tracker.scale
		newScale = None
		if button.value == Scale.TYPE_DIATONIC:
			newScale = DiatonicScale (oldScale.key, oldScale.nOctaves)
		elif button.value == Scale.TYPE_PENTATONIC:
			newScale = PentatonicScale (oldScale.key, oldScale.nOctaves)
		elif button.value == Scale.TYPE_CHROMATIC:
			newScale = ChromaticScale (oldScale.key, oldScale.nOctaves)
		self.tracker.SetScale (newScale)

	def OctavesClick (self, button):
		self.tracker.scale.SetOctaveRange (button.value)

	def KeyClick (self, button):
		self.tracker.scale.SetKey (button.value)

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
			startIndex = marker.typeID,
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
			if isinstance(marker,NoteMarker):
				newMarkerOpts = NoteMarkerConfigurationStrip (
					marker = marker,
					window = self.window,
					bounds = Rect (button.bounds.xMax, button.bounds.y-1, 0, 0),
					bgColour = None
				)
			elif isinstance(marker,CVMarker):
				newMarkerOpts = CVMarkerConfigurationStrip (
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
				newMarker = NoteMarker (
					colour = marker.colour,
					colourRange = marker.colourRange,
					midiOut = marker.midiOut,
					channel = marker.xChannel,
					name = marker.name,
					scale = self.tracker.scale,
					mode = MARKER_NOTE_DEFAULT_MODE,
					stringOffset=marker.stringOffset,
					tuning=GUITAR,
					#strings = self.tracker.GenerateStrings ((marker.ID+1)/8+0.5,[0]),
					ID = marker.ID)
				newMarkerOpts = NoteMarkerConfigurationStrip (
					marker = newMarker,
					window = self.window,
					bounds = Rect (button.bounds.xMax, button.bounds.y-1, 0, 0),
					bgColour = None)
			elif button.value == Marker.TYPE_CV:
				# Display CVMarker options
				newMarker = CVMarker (
					colour = marker.colour,
					colourRange = marker.colourRange,
					midiOut = marker.midiOut,
					xChannel = marker.channel,
					yChannel = marker.channel,
					name = marker.name,
					stringOffset=marker.stringOffset,
					xController = MARKER_CV_DEFAULT_X_CONTROLLER,
					yController = MARKER_CV_DEFAULT_Y_CONTROLLER,
					ID = marker.ID)
				newMarkerOpts = CVMarkerConfigurationStrip (
					marker = newMarker,
					window = self.window,
					bounds = Rect (button.bounds.xMax, button.bounds.y-1, 0, 0),
					bgColour = None)
			self.items.append (newMarkerOpts)
			self.markerSubmenus[marker.ID] = newMarkerOpts
			idx = self.tracker.markers.index (marker)
			self.tracker.markers[idx] = newMarker
			button.onClick = self.GenerateClickHandler (newMarker)

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
			values = [i for i in range(16)],
			startIndex = marker.channel,
			onClick = self.ChannelClick
		)
		muteHideStatus = 0
		if marker.muteOnHide == True: muteHideStatus = 1
		muteHideButton = CyclicButton (
			window = self.window,
			bounds = Rect (channelButton.bounds.xMax, bounds.y, UI_TABLE_COLUMN_WIDTH, UI_TABLE_ROW_HEIGHT),
			labels = ["Hold","Mute"],
			values = [False, True],
			startIndex = muteHideStatus,
			onClick = self.MuteHideClick
		)
		octaveTransposeButton = CyclicButton (
			window = self.window,
			bounds = Rect (muteHideButton.bounds.xMax, bounds.y, UI_TABLE_COLUMN_WIDTH, UI_TABLE_ROW_HEIGHT),
			labels = ["Oct: %i" % i for i in MARKER_TRANSPOSE_OCTAVE_RANGE],
			values = MARKER_TRANSPOSE_OCTAVE_RANGE,
			startIndex = MARKER_TRANSPOSE_OCTAVE_RANGE.index(marker.transposeOctaves),
			onClick = self.OctaveTransposeClick
		)
		semitoneTransposeButton = CyclicButton (
			window = self.window,
			bounds = Rect (octaveTransposeButton.bounds.xMax, bounds.y, UI_TABLE_COLUMN_WIDTH, UI_TABLE_ROW_HEIGHT),
			labels = ["Semi: %i" % i for i in MARKER_TRANSPOSE_SEMITONE_RANGE],
			values = MARKER_TRANSPOSE_SEMITONE_RANGE,
			startIndex = MARKER_TRANSPOSE_SEMITONE_RANGE.index(marker.transposeSemitones),
			onClick = self.SemitoneTransposeClick
		)
		stringConf = StringConfigurationStrip (
			marker = self.marker,
			window = self.window,
			bounds = Rect (semitoneTransposeButton.bounds.xMax,
				bounds.y,
				UI_TABLE_COLUMN_WIDTH*1.5,
				UI_TABLE_ROW_HEIGHT),
			bgColour = None)
		markerModeButton = self.markerModeButton = CyclicButton (
			window = self.window,
			bounds = Rect (stringConf.bounds.xMax, bounds.y, UI_TABLE_COLUMN_WIDTH*1.5, UI_TABLE_ROW_HEIGHT),
			labels = ["AutoRelease","Toggle","Legato"],
			values = [NoteMarker.MODE_AUTORELEASE, NoteMarker.MODE_TOGGLE, NoteMarker.MODE_LEGATO],
			startIndex = marker.mode,
			onClick = self.MarkerModeClick
		)
		if marker.mode == NoteMarker.MODE_AUTORELEASE:
			modeOptions = self.modeOptions = AutoReleaseConfigurationStrip (
				marker = self.marker,
				window = self.window,
				bounds = Rect (self.markerModeButton.bounds.xMax, self.bounds.y, 0, 0),
				bgColour = None)
			self.marker.mode = NoteMarker.MODE_AUTORELEASE
		elif marker.mode == NoteMarker.MODE_LEGATO:
			modeOptions = self.modeOptions = LegatoConfigurationStrip (
				marker = self.marker,
				window = self.window,
				bounds = Rect (self.markerModeButton.bounds.xMax, self.bounds.y, 0, 0),
				bgColour = None)
			self.marker.mode = NoteMarker.MODE_LEGATO
		elif marker.mode == NoteMarker.MODE_TOGGLE:
			modeOptions = self.modeOptions = ToggleConfigurationStrip (
				marker = self.marker,
				window = self.window,
				bounds = Rect (self.markerModeButton.bounds.xMax, self.bounds.y, 0, 0),
				bgColour = None)
			self.marker.mode = NoteMarker.MODE_TOGGLE
		self.items = [
			channelButton,
			muteHideButton,
			octaveTransposeButton,
			semitoneTransposeButton,
			stringConf,
			markerModeButton,
			modeOptions]
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

	def MuteHideClick (self, button):
		self.marker.muteOnHide = button.value

	def OctaveTransposeClick (self, button):
		self.marker.Transpose (octave=button.value)
	
	def SemitoneTransposeClick (self, button):
		self.marker.Transpose (semitones=button.value)

	def ChannelClick (self, button):
		self.marker.channel = button.value

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
			labels = ["X Ch: %i" % (i) for i in range(16)],
			values = range(16),
			startIndex = marker.xChannel,
			onClick = self.XChannelClick,
		)
		xControllerButton = CyclicButton (
			window = self.window,
			bounds = Rect (xChannelButton.bounds.xMax, bounds.y, UI_CV_CTRL_WIDTH, UI_TABLE_ROW_HEIGHT),
			labels = ["X Ctrl: %i" % (i) for i in MARKER_CONTROLLER_ID_RANGE],
			values = range(16),
			startIndex = marker.xController,
			onClick = self.XControllerClick,
		)
		yChannelButton = CyclicButton (
			window = self.window,
			bounds = Rect (xControllerButton.bounds.xMax, bounds.y, UI_TABLE_COLUMN_WIDTH, UI_TABLE_ROW_HEIGHT),
			labels = ["Y Ch: %i" % (i) for i in range(16)],
			values = range(16),
			startIndex = marker.yChannel,
			onClick = self.YChannelClick
		)
		yControllerButton = CyclicButton (
			window = self.window,
			bounds = Rect (yChannelButton.bounds.xMax, bounds.y, UI_CV_CTRL_WIDTH, UI_TABLE_ROW_HEIGHT),
			labels = ["Y Ctrl: %i" % (i) for i in MARKER_CONTROLLER_ID_RANGE],
			values = range(16),
			startIndex = marker.yController,
			onClick = self.YControllerClick,
		)
		self.items = [xChannelButton, xControllerButton, yChannelButton, yControllerButton]
		self.FitItems ()

	def XChannelClick (self, button):
		self.marker.xChannel = button.value
	def YChannelClick (self, button):
		self.marker.yChannel = button.value
	def XControllerClick (self, button):
		self.marker.xController = button.value
	def YControllerClick (self, button):
		self.marker.yController = button.value


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

		isMonophonic = 0
		if marker.polyphonic == True: isMonophonic = 1
		durationIndex = int((marker.duration * 10)-1)
		duration = self.durationButton = CyclicButton (
			window = self.window,
			bounds = Rect (bounds.x, bounds.y, UI_TABLE_COLUMN_WIDTH, UI_TABLE_ROW_HEIGHT),
			labels = ["%i00ms" % (i+1) for i in range(10)],
			values = [0.1 * (i+1) for i in range(10)],
			startIndex = durationIndex,
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
			startIndex = isMonophonic,
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

class StringConfigurationStrip (BasicFrame):
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
		tuningButton = self.tuningButton = CyclicButton (
			window = self.window,
			bounds = Rect (
				bounds.x,
				bounds.y,
				UI_TABLE_COLUMN_WIDTH*1.5,
				UI_TABLE_ROW_HEIGHT),
			labels = TUNING_NAMES,
			values = TUNING_OFFSETS,
			startIndex = TUNING_OFFSETS.index(marker.tuning),
			onClick = self.TuningClick
		)
		self.items = [tuningButton]
		self.FitItems ()

	def TuningClick (self, button):
		self.marker.SetTuning (button.value)
