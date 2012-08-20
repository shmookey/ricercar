''' UIElement.py - UIElement GUI Framework
'''

from OpenGL.GL import *
from OpenGL.GLU import *

from constants import *
from config import *


##
#
# UIElement GUI Framework
# Classes, functions and decorators
#
##

def LazyRender (renderFn):
	''' Indicates that a rendering method should only continue if the
	object has been flagged with requireRedraw, e.g.: because it displays
	data that has changed.
	'''
	def LazilyRenderedFn (self):
		if not self.requireRedraw: return
		renderFn (self)
	return LazilyRenderedFn

def FilterClick (clickFn):
	''' Checks to see if the x and y parameters supplied to a method are
	within the object's bounds before allowing the call to continue.
	'''
	def ClickFilteredFn (self, x, y):
		if not self.bounds.IsPointInside (x, y): return
		clickFn (self, x, y)
	return ClickFilteredFn

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

	def SetWidth (self, w):
		''' Sets the width of the Rect preserving the location of the bottom-left corner.
		'''
		wInt = int(w)
		self.w = wInt
		self.xMax = self.x + wInt

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
			window = None,
			bgColour = UI_HUD_BG_COLOUR):
		self.window = window
		self.requireRedraw = True
		self.bounds = bounds
		self.items = []

	def Tick (self):
		''' Send heartbeat to every UI element contained within this one. '''
		for item in self.items: item.Tick ()

	def Redraw (self):
		''' Marks the selection group and all of its items for redrawing at next frame. '''
		self.requireRedraw = True
		for item in self.items: item.Redraw ()

	@FilterClick
	def Click (self, x, y):
		''' A click event occured within the bounds of the selector. Pass it on to the
		appropriate button. '''
		for item in self.items:
			if item.bounds.IsPointInside (x, y): item.Click (x, y)

	def FitItems (self):
		''' Recalculates the bounds of the element to just fit around the items it contains.

		Does not modify the x or y position of the element.
		'''
		xMax = 0
		yMax = 0
		for item in self.items:
			xMax = max(xMax, item.bounds.xMax)
			yMax = max(yMax, item.bounds.yMax)
		self.bounds.SetWidth (xMax - self.bounds.x)
		self.bounds.SetHeight (yMax - self.bounds.y)

class BasicFrame (UIElement):
	def __init__ (self,
			bounds = None,
			window = None,
			bgColour = UI_HUD_BG_COLOUR):
		UIElement.__init__ (self,
			bounds = bounds,
			window = window)
		self.bgColour = bgColour

	@LazyRender
	def Tick (self):
		if self.bgColour:
			glColor4f (*self.bgColour)
			self.bounds.Render ()
		UIElement.Tick (self)
		self.requireRedraw = False

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
	def Tick (self):
		if self.bounds and not self.bgColour == None:
			glColor4f (*self.bgColour)
			self.bounds.Render ()
		glColor4f (*self.textColour)
		glPushMatrix ()
		glTranslatef (self.bounds.x+UI_HUD_LEFT_PADDING, self.bounds.yMax-UI_TABLE_ROW_HEIGHT+3,0.0)
		self.window.smallFont.Render (self.label)
		glPopMatrix ()
		UIElement.Tick (self)

	def ItemSelected (self, selectedItem):
		for item in self.items:
			item.SetBackgroundColour (UI_HUD_BG_COLOUR)
		selectedItem.SetBackgroundColour (UI_HUD_SELECTED_COLOUR)
		self.onSelect (selectedItem)

class Button (UIElement):
	''' A clickable button. '''
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
	def Tick (self):
		if self.bgColour != None: glColor4f (*self.bgColour)
		self.bounds.Render ()
		glPushMatrix ()
		glTranslatef (self.bounds.x+UI_HUD_LEFT_PADDING,self.bounds.y+UI_HUD_BUTTON_Y_OFFSET,0.0)
		glColor4f (*self.textColour)
		self.window.smallFont.Render (str(self.label))
		glPopMatrix ()
		self.requireRedraw = False
	
	@FilterClick
	def Click (self, x, y):
		if self.onClick: self.onClick (self)

	def SetBackgroundColour (self, bgColour):
		self.bgColour = bgColour
		self.Redraw ()

class CyclicButton (Button):
	''' A button that cycles through a list of values when clicked.
	'''
	def __init__ (self,
			bounds = None,
			labels = ["On","Off"],
			window = None,
			bgColour = UI_HUD_BG_COLOUR,
			textColour = UI_HUD_TEXT_COLOUR,
			onClick = None,
			values = [1,0],
			startIndex = 0):
		Button.__init__ (self,
			label = labels[startIndex],
			bounds = bounds,
			window = window,
			bgColour = bgColour,
			textColour = textColour,
			onClick = onClick,
			value = values[startIndex])
		self.labels = labels
		self.values = values
		self.currentIndex = startIndex

	@FilterClick
	def Click (self, x, y):
		self.currentIndex += 1
		if self.currentIndex >= len(self.labels): self.currentIndex = 0
		self.label = self.labels[self.currentIndex]
		self.value = self.values[self.currentIndex]
		self.Redraw ()
		Button.Click (self, x, y)

class DataTable (UIElement):
	''' A table of values with headings and subheadings.
	
	Overrides the dimensions specified in the bounds it is given to in
	order to accomodate all data in the table.
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
		
		#self.FitItems ()
		fullHeight = UI_TABLE_ROW_HEIGHT*(3+len(rowData))
		fullWidth = UI_TABLE_COLUMN_WIDTH* (len(rowData[0]))
		self.bounds.SetHeight (fullHeight)
		self.bounds.SetWidth (fullWidth)

	@LazyRender
	def Tick (self):
		if self.bgColour:
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
