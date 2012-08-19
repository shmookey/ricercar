import cv, pygame, FTGL

from OpenGL.GL import *
from OpenGL.GLU import *

from tracker import NoteMarker, CVMarker
from music import PITCH_TO_NOTE
from CVGLImage import CVGLImage
from constants import *
from config import *

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

	def InitVideo (self):
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
		self.tracker = tracker

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
			bounds=Rect(20,DISPLAY_SIZE[1]-20,COL_WIDTH*5,0),
			onSelect=SelectInputDevice)
		self.OutputSelector = SelectionGroup (
			label = "MIDI Output",
			window = self,
			options=enumerate(outPorts),
			default=activeIn.deviceID,
			bounds=Rect(400,DISPLAY_SIZE[1]-20,COL_WIDTH*5,0),
			onSelect=SelectOutputDevice)

		#for i,port in enumerate(inPorts):
		#	self.IOSelector.AddOption ("%i: %s" % (i, port),value=i)
		

	def NewRawFrame (self, frame):
		''' Raw frame is BGR 8UC3. '''
		cv.CvtColor (frame, self.frames[FRAME_RAW], cv.CV_BGR2RGB)

	def NewMaskedFrame (self, frame):
		''' Masked frame is RGB 8UC4. '''
		self.frames[FRAME_MASKED] = frame

	def NewGridFrame (self, frame):
		''' Grid frame is BGR 8UC3. '''
		cv.CvtColor (frame, self.frames[FRAME_GRID], cv.CV_BGR2RGB)

	def NewFeatureFrame (self, frame):
		''' Grid frame is BGR 8UC3. '''
		cv.CvtColor (frame, self.frames[FRAME_FEATURES], cv.CV_BGR2RGB)

	def Render (self):
		glClear (GL_COLOR_BUFFER_BIT)
		glEnable (GL_TEXTURE_2D)
		glColor4f (1.0,1.0,1.0,1.0)
	
		for i,frame in  enumerate (self.frames): #[(FRAME_MASKED,self.frames[FRAME_MASKED])]:
			mat = cv.GetMat (self.frames[i])
			img = CVGLImage (mat)
			if i!=FRAME_MASKED: img.LoadRGBTexture (int(self.textures[i]))
			else: img.LoadRGBATexture (int(self.textures[i]))

		self.DrawFrame (FRAME_GRID,0,0,DISPLAY_SIZE[0],DISPLAY_SIZE[1])
		glColor4f (1.0,1.0,1.0,0.6)
		glDisable (GL_TEXTURE_2D)
		self.DrawFrame (FRAME_NOTEXTURE,0,0,DISPLAY_SIZE[0],DISPLAY_SIZE[1])
		glEnable (GL_TEXTURE_2D)
		glColor4f (1.0,1.0,1.0,1.0)
		self.DrawFrame (FRAME_MASKED,0,0,DISPLAY_SIZE[0],DISPLAY_SIZE[1])
		glDisable (GL_TEXTURE_2D)

		self.DrawMarkerLocations ()
		self.DrawNoteBoundaries ()
		
		glPushMatrix ()
		glColor4f (*UI_HUD_TEXT_COLOUR)
		glTranslatef (DISPLAY_SIZE[0]-100.0, DISPLAY_SIZE[1]-ROW_HEIGHT, 0.0)
		self.smallFont.Render ("FPS: %i" % self.scheduler.trackerTimer.fps)
		glPopMatrix()

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

	def DrawMarkerLocations (self):
		for i,marker in enumerate(self.markers):
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
				self.DrawFrame (FRAME_NOTEXTURE, 0, y, DISPLAY_SIZE[0], noteSize)


		for marker in self.tracker.markers:
			color = marker.colour
			glColor3f (color[2],color[1],color[0])
			for i, stringx in enumerate(marker.stringx):
				if not marker.strings[i]: glLineWidth (NOTE_BOUNDARY_THICKNESS)
				else: glLineWidth (NOTE_BOUNDARY_THICKNESS*2)
				glBegin (GL_LINES)
				glVertex2i (int(DISPLAY_SIZE[0]*stringx),0)
				glVertex2i (int(DISPLAY_SIZE[0]*stringx),DISPLAY_SIZE[1])
				glEnd ()

	

	def DrawConfigUI (self):
		glColor4f (*UI_HUD_BG_COLOUR)
		self.DrawFrame (FRAME_NOTEXTURE,0,0,DISPLAY_SIZE[0],130)
		glColor4f (*UI_HUD_TEXT_COLOUR)
		glPushMatrix ()

		# Move to top left hand corner
		glTranslatef (LEFT_PADDING,UI_HEIGHT-TOP_PADDING,0.0)
		
		# Render position heading
		glPushMatrix ()
		glTranslatef (COL_WIDTH,0.0,0.0)
		self.smallFont.Render ("Position")
		glTranslatef (0.0,-ROW_HEIGHT,0.0)
		self.smallFont.Render ("x")
		glTranslatef (COL_WIDTH,0.0,0.0)
		self.smallFont.Render ("y")
		glPopMatrix ()

		# Render colour sensitivity headings
		glPushMatrix ()
		glTranslatef (COL_WIDTH*3,0.0,0.0)
		self.smallFont.Render ("Colour Sensitivity")
		glTranslatef (0.0,-ROW_HEIGHT,0.0)
		self.smallFont.Render ("Hue")
		glTranslatef (COL_WIDTH,0.0,0.0)
		self.smallFont.Render ("Sat")
		glTranslatef (COL_WIDTH,0.0,0.0)
		self.smallFont.Render ("Val")
		glPopMatrix ()

		# Render MIDI output headings
		glPushMatrix ()
		glTranslatef (COL_WIDTH*6,0.0,0.0)
		self.smallFont.Render ("MIDI Mapping")
		glTranslatef (0.0,-ROW_HEIGHT,0.0)
		self.smallFont.Render ("X Mode")
		glTranslatef (COL_WIDTH,0.0,0.0)
		self.smallFont.Render ("X Min")
		glTranslatef (COL_WIDTH,0.0,0.0)
		self.smallFont.Render ("X Max")
		glTranslatef (COL_WIDTH,0.0,0.0)
		self.smallFont.Render ("X Ch")
		glTranslatef (COL_WIDTH,0.0,0.0)
		self.smallFont.Render ("Y Mode")
		glTranslatef (COL_WIDTH,0.0,0.0)
		self.smallFont.Render ("Y Min")
		glTranslatef (COL_WIDTH,0.0,0.0)
		self.smallFont.Render ("Y Max")
		glTranslatef (COL_WIDTH,0.0,0.0)
		self.smallFont.Render ("Y Ch")
		glPopMatrix ()

		# Render marker names
		glPushMatrix ()
		glTranslatef (0.0,-ROW_HEIGHT*2,0.0)
		self.smallFont.Render ("Red")
		glTranslatef (0.0,-ROW_HEIGHT,0.0)
		self.smallFont.Render ("Green")
		glTranslatef (0.0,-ROW_HEIGHT,0.0)
		self.smallFont.Render ("Blue")
		glTranslatef (0.0,-ROW_HEIGHT,0.0)
		self.smallFont.Render ("Yellow")
		glPopMatrix ()

		# Render data
		glPushMatrix ()
		glTranslatef (COL_WIDTH,-ROW_HEIGHT*2,0.0)
		for marker in self.tracker.markers:
			cRange = marker.colourRange
			self.smallFont.Render ("%.2f" % marker.x)
			glTranslatef (COL_WIDTH,0.0,0.0)
			self.smallFont.Render ("%.2f" % marker.y)
			glTranslatef (COL_WIDTH,0.0,0.0)
			self.smallFont.Render ("%i-%i" % (cRange.hue[0],cRange.hue[1]))
			glTranslatef (COL_WIDTH,0.0,0.0)
			self.smallFont.Render ("%i-%i" % (cRange.saturation[0],cRange.saturation[1]))
			glTranslatef (COL_WIDTH,0.0,0.0)
			self.smallFont.Render ("%i-%i" % (cRange.value[0],cRange.value[1]))
			glTranslatef (COL_WIDTH,0.0,0.0)
			if isinstance(marker, NoteMarker):
				self.smallFont.Render ("Note")
				glTranslatef (COL_WIDTH,0.0,0.0)
				self.smallFont.Render ("%i" % marker.xMin)
				glTranslatef (COL_WIDTH,0.0,0.0)
				self.smallFont.Render ("%i" % marker.xMax)
				glTranslatef (COL_WIDTH,0.0,0.0)
				self.smallFont.Render ("%i" % (marker.xCh-144))
				glTranslatef (COL_WIDTH,0.0,0.0)
				self.smallFont.Render ("Velocity")
				glTranslatef (COL_WIDTH,0.0,0.0)
				self.smallFont.Render ("%i" % marker.yMin)
				glTranslatef (COL_WIDTH,0.0,0.0)
				self.smallFont.Render ("%i" % marker.yMax)
				glTranslatef (COL_WIDTH,0.0,0.0)
				self.smallFont.Render ("%i" % (marker.yCh-144))
			if isinstance(marker, CVMarker):
				self.smallFont.Render ("CV")
				glTranslatef (COL_WIDTH,0.0,0.0)
				self.smallFont.Render ("%i" % marker.xMin)
				glTranslatef (COL_WIDTH,0.0,0.0)
				self.smallFont.Render ("%i" % marker.xMax)
				glTranslatef (COL_WIDTH,0.0,0.0)
				self.smallFont.Render ("%i" % (marker.xCh-144))
				glTranslatef (COL_WIDTH,0.0,0.0)
				self.smallFont.Render ("CV")
				glTranslatef (COL_WIDTH,0.0,0.0)
				self.smallFont.Render ("%i" % marker.yMin)
				glTranslatef (COL_WIDTH,0.0,0.0)
				self.smallFont.Render ("%i" % marker.yMax)
				glTranslatef (COL_WIDTH,0.0,0.0)
				self.smallFont.Render ("%i" % (marker.yCh-144))
			glTranslatef (-COL_WIDTH*12,-ROW_HEIGHT,0.0)
		glPopMatrix ()

		glPopMatrix ()

	def DrawIOSelector (self):
		self.InputSelector.Render ()
		self.InputSelector.Redraw ()
		self.OutputSelector.Render ()
		self.OutputSelector.Redraw ()

	def Click (self, x, y):
		invY = DISPLAY_SIZE[1]-y
		for item in self.items:
			if item.bounds.IsPointInside (x,invY): item.Click (x,invY)

	def DrawFrame (self, frameID, x, y, w, h):
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

	def ShowMarkers (self, markers):
		self.markers = markers

class Rect:
	def __init__ (self,x,y,w,h):
		self.x = int(x)
		self.y = int(y)
		self.w = int(w)
		self.h = int(h)
		self.xMax = int(x+w)
		self.yMax = int(y+h)
	def IsPointInside (self,x,y):
		if x>self.x and x<self.xMax and y>self.y and y<self.yMax: return True
		return False
	def ExtendDownward (self, h):
		hi = int (h)
		self.h += hi
		self.y -= hi
	def ApplyPadding (self, p):
		pi = int(p)
		self.x += pi
		self.y += pi
		self.h -= pi*2
		self.w -= pi*2
		self.xMax = self.x + self.w
		self.yMax = self.y + self.h
	def Render (self):
		glBegin (GL_QUADS)
		glTexCoord2f (0.0,0.0)
		glVertex2i (self.x,self.y)
		glTexCoord2f (1.0,0.0)
		glVertex2i (self.xMax,self.y)
		glTexCoord2f (1.0,1.0)
		glVertex2i (self.xMax,self.yMax)
		glTexCoord2f (0.0,1.0)
		glVertex2i (self.x,self.yMax)
		glEnd ()
	def Clone (self):
		return Rect (self.x,self.y,self.w,self.h)

class UIElement:
	def __init__ (self, window):
		self.window = window
		self.requireRedraw = True
		self.items = []
	def Render (self):
		raise NotImplemented ()
	def Redraw (self):
		''' Marks the selection group and all of its items for redrawing at next frame. '''
		self.requireRedraw = True
		for item in self.items: item.Redraw ()

class SelectionGroup (UIElement):
	''' Displays a list of items and allows the user to select one. '''
	def __init__ (self,
			label="",
			window=None,
			onSelect=None,
			options=[],
			default=None,
			bounds=None,
			bgColour=UI_HUD_BG_COLOUR,
			textColour=UI_HUD_TEXT_COLOUR):
		UIElement.__init__ (self, window)
		self.onSelect = onSelect
		self.label = label
		self.bounds = bounds
		self.innerBounds = bounds.Clone ()
		self.innerBounds.ApplyPadding (UI_HUD_PADDING)
		self.bgColour = bgColour
		self.textColour = textColour
		for i,option in options: self.AddOption (option,i)
		self.items[default].SetBackgroundColour (UI_HUD_SELECTED_COLOUR)

		# Add some height to the bounding box to accomodate the label
		self.bounds.ExtendDownward (ROW_HEIGHT + UI_HUD_PADDING*2)

	def AddOption (self, label, value):
		nItems = len (self.items)
		newRct = Rect (
			self.innerBounds.x,
			self.innerBounds.yMax - (nItems+2)*ROW_HEIGHT,
			self.innerBounds.w,
			ROW_HEIGHT)
		newBtn = Button (
			bounds = newRct,
			label = label,
			window = self.window,
			onClick = self.ItemSelected,
			value=value)
		self.items.append (newBtn)

		# Extend own bounds downwards to accomodate new item
		if self.bounds:
			self.bounds.ExtendDownward (ROW_HEIGHT)

		self.Redraw ()

	def Render (self):
		if not self.requireRedraw: return
		if self.bounds and not self.bgColour == None:
			glColor4f (*self.bgColour)
			self.bounds.Render ()
		glColor4f (*self.textColour)
		glPushMatrix ()
		glTranslatef (self.bounds.x+UI_HUD_LEFT_PADDING, self.bounds.yMax-ROW_HEIGHT+3,0.0)
		self.window.smallFont.Render (self.label)
		glPopMatrix ()
		for item in self.items:
			item.Render ()
		self.requireRedraw = False

	def ItemSelected (self, selectedItem):
		for item in self.items:
			item.SetBackgroundColour (UI_HUD_BG_COLOUR)
		selectedItem.SetBackgroundColour (UI_HUD_SELECTED_COLOUR)
		self.onSelect (selectedItem)

	def Click (self, x, y):
		''' A click event occured within the bounds of the selector. Pass it on to the
		appropriate button. '''
		if not self.bounds.IsPointInside (x, y): return # Just to be safe...
		for item in self.items:
			if item.bounds.IsPointInside (x, y): item.Click (x, y)

class Button (UIElement):
	def __init__ (self,
			bounds = None,
			label = "",
			window = None,
			bgColour = UI_HUD_BG_COLOUR,
			textColour = UI_HUD_TEXT_COLOUR,
			onClick = None,
			value = None):
		UIElement.__init__ (self, window)
		self.bounds = bounds
		self.bounds.ApplyPadding (UI_HUD_PADDING)
		self.onClick = onClick
		self.label = label
		self.bgColour = bgColour
		self.textColour = textColour
		self.value = value
	def Render (self):
		if not self.requireRedraw: return
		if self.bgColour != None: glColor4f (*self.bgColour)
		self.bounds.Render ()
		glPushMatrix ()
		glTranslatef (self.bounds.x+UI_HUD_LEFT_PADDING,self.bounds.y+UI_HUD_BUTTON_Y_OFFSET,0.0)
		glColor4f (*self.textColour)
		self.window.smallFont.Render (str(self.label))
		glPopMatrix ()
		self.requireRedraw = False
	def Click (self, x, y):
		if not self.bounds.IsPointInside (x, y): return # Just to be safe...
		self.onClick (self)
	def SetBackgroundColour (self, bgColour):
		self.bgColour = bgColour
		self.Redraw ()

