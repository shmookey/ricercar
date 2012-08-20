import cv, pygame, FTGL

from OpenGL.GL import *
from OpenGL.GLU import *

from tracker import NoteMarker, CVMarker
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
		''' Informs the Window of the Tracker from which it will be 
		displaying information. 
		
		Causes the configuration UI elements to be regenerated.
		'''
		self.tracker = tracker
		self.ConfigurationUI = DataTable (
			window = self,
			headers = DATA_TABLE_HEADERS,
			rowData = self.GetConfigurationData (),
			bounds=Rect(0,0,DISPLAY_SIZE[0],250)) # TODO: fix magic number

	def GetConfigurationData (self):
		return [
			[m.name,
			"%.2f" % m.x,
			"%.2f" % m.y,
			"%i-%i" % (m.colourRange.hue[0],m.colourRange.hue[1]),
			"%i-%i" % (m.colourRange.saturation[0],m.colourRange.saturation[1]),
			"%i-%i" % (m.colourRange.value[0],m.colourRange.value[1]),]
			for m in self.tracker.markers]
		'''
			m.xMode,
			m.xMin,
			m.xMax,
			m.xChannel,
			m.yMode,
			m.yMin,
			m.yMax,
			m.yChannel] for m in self.tracker.markers]'''

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

	def Render (self):
		glClear (GL_COLOR_BUFFER_BIT)
		glEnable (GL_TEXTURE_2D)
		glColor4f (1.0,1.0,1.0,1.0)

		# Load new image data into OpenGL textures.
		for i,frame in  enumerate (self.frames):
			mat = cv.GetMat (self.frames[i])
			img = CVGLImage (mat)
			if i!=FRAME_MASKED: img.LoadRGBTexture (int(self.textures[i]))
			else: img.LoadRGBATexture (int(self.textures[i]))

		# Draw image data
		self.DrawFrame (FRAME_GRID,0,0,DISPLAY_SIZE[0],DISPLAY_SIZE[1])
		glColor4f (1.0,1.0,1.0,0.6)
		glDisable (GL_TEXTURE_2D)
		self.DrawFrame (FRAME_NOTEXTURE,0,0,DISPLAY_SIZE[0],DISPLAY_SIZE[1])
		glEnable (GL_TEXTURE_2D)
		glColor4f (1.0,1.0,1.0,1.0)
		self.DrawFrame (FRAME_MASKED,0,0,DISPLAY_SIZE[0],DISPLAY_SIZE[1])
		glDisable (GL_TEXTURE_2D)

		# Annotate scene
		self.DrawMarkerLocations ()
		self.DrawNoteBoundaries ()
		self.DrawFPS ()
		self.ConfigurationUI.rowData = self.GetConfigurationData ()
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
		self.smallFont.Render ("FPS: %i" % self.scheduler.trackerTimer.fps)
		glPopMatrix()

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
				self.DrawFrame (FRAME_NOTEXTURE, 0, y, DISPLAY_SIZE[0], noteSize)


		for marker in self.tracker.markers:
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
		self.ConfigurationUI.Render ()
		self.ConfigurationUI.Redraw ()

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

#
# UIElement GUI Framework
# Methods and classes
#

def LazyRender (renderFn):
	''' Indicates that a rendering method should only continue if the
	object has been flagged with requireRedraw, e.g.: because it displays
	data that has changed.
	'''
	def LazilyRenderedFn (self):
		if not self.requireRedraw: return
		renderFn (self)
	return LazilyRenderedFn

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

	# The 'extend' methods change the relative dimensions of the Rect.
	def ExtendDownward (self, h):
		hi = int (h)
		self.h += hi
		self.y -= hi
	def ExtendUpward (self, h):
		hInt = int (h)
		self.h += hInt
		self.yMax += hInt

	def SetHeight (self, h):
		''' Sets the height of the Rect preserving the location of the bottom-left corner.
		'''
		hInt = int(h)
		self.h = hInt
		self.yMax = self.y + hInt

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
	def __init__ (self,
			bounds = None,
			window = None):
		self.window = window
		self.requireRedraw = True
		self.bounds = bounds
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
		UIElement.__init__ (self,
			bounds = bounds,
			window = window)
		self.onSelect = onSelect
		self.label = label
		self.innerBounds = bounds.Clone ()
		self.innerBounds.ApplyPadding (UI_HUD_PADDING)
		self.bgColour = bgColour
		self.textColour = textColour
		for i,option in options: self.AddOption (option,i)
		self.items[default].SetBackgroundColour (UI_HUD_SELECTED_COLOUR)

		# Add some height to the bounding box to accomodate the label
		self.bounds.ExtendDownward (UI_TABLE_ROW_HEIGHT + UI_HUD_PADDING*2)

	def AddOption (self, label, value):
		nItems = len (self.items)
		newRct = Rect (
			self.innerBounds.x,
			self.innerBounds.yMax - (nItems+2)*UI_TABLE_ROW_HEIGHT,
			self.innerBounds.w,
			UI_TABLE_ROW_HEIGHT)
		newBtn = Button (
			bounds = newRct,
			label = label,
			window = self.window,
			onClick = self.ItemSelected,
			value=value)
		self.items.append (newBtn)

		# Extend own bounds downwards to accomodate new item
		if self.bounds:
			self.bounds.ExtendDownward (UI_TABLE_ROW_HEIGHT)

		self.Redraw ()

	@LazyRender
	def Render (self):
		if self.bounds and not self.bgColour == None:
			glColor4f (*self.bgColour)
			self.bounds.Render ()
		glColor4f (*self.textColour)
		glPushMatrix ()
		glTranslatef (self.bounds.x+UI_HUD_LEFT_PADDING, self.bounds.yMax-UI_TABLE_ROW_HEIGHT+3,0.0)
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
		UIElement.__init__ (self,
			bounds = bounds,
			window = window)
		self.bounds.ApplyPadding (UI_HUD_PADDING)
		self.onClick = onClick
		self.label = label
		self.bgColour = bgColour
		self.textColour = textColour
		self.value = value

	@LazyRender
	def Render (self):
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

class DataTable (UIElement):
	''' A table of values with headings and subheadings.
	
	Overrides the height specified in the bounds it is given to in order
	to accomodate all data in the table.
	'''
	def __init__ (self,
			bounds = None,
			window = None,
			headers = None,
			rowData = [],
			textColour = UI_HUD_TEXT_COLOUR,
			bgColour = UI_HUD_BG_COLOUR):
		''' headers is a list of tuples of the form ("Heading",["Subheading 1","Subheading 2"]) '''
		UIElement.__init__ (self,
			bounds = bounds,
			window = window)
		self.headers = headers
		self.textColour = textColour
		self.bgColour = bgColour
		self.rowData = rowData
		
		fullHeight = UI_TABLE_ROW_HEIGHT*(3+len(rowData))
		self.bounds.SetHeight (fullHeight)

	@LazyRender
	def Render (self):
		glColor4f (*self.bgColour)
		self.bounds.Render ()
		glPushMatrix ()

		glTranslatef (self.bounds.x, self.bounds.y+self.bounds.h, 0.0)
		glTranslatef (0.0, -UI_TABLE_ROW_HEIGHT, 0.0)
		glColor4f (*self.textColour)

		# Render headers
		cumulativeColumnOffset = 0 # Keeps track of left offset for current header group.
		for i, (header,subheaders) in enumerate (self.headers):
			glPushMatrix ()
			glTranslatef (cumulativeColumnOffset, 0.0, 0.0)
			# Render top-level header
			self.window.smallFont.Render ("%s" % str(header))
			# Render subheaders
			glTranslatef (0.0, -UI_TABLE_ROW_HEIGHT, 0.0)
			for subheader in subheaders:
				self.window.smallFont.Render ("%s" % str(subheader))
				glTranslatef (UI_TABLE_COLUMN_WIDTH,0.0,0.0)
			# Keep track of how far left we are.
			cumulativeColumnOffset += len(subheaders) * UI_TABLE_COLUMN_WIDTH
			glPopMatrix ()

		# Render data
		for i, row in enumerate (self.rowData):
			glPushMatrix ()
			glTranslatef (0.0, -UI_TABLE_ROW_HEIGHT*(i+2), 0.0)
			for cell in row:
				self.window.smallFont.Render ("%s" % str(cell))
				glTranslatef (UI_TABLE_COLUMN_WIDTH, 0.0, 0.0)
			glPopMatrix ()
		glPopMatrix ()
