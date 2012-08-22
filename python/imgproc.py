import cv, cv2
from constants import *

from config import *

class MarkerNotFound (Exception): pass

class StreamProcessor:
	def __init__ (self, tracker):
		self.tracker = tracker
		
		self.deviceID = None
		self.modeChangeCallback = None

		# Initialise frames used for image processing
		self.gridFrame = cv.CreateImage (GRID_SIZE, 8, 3)
		self.gridFrameHSV = cv.CreateImage (GRID_SIZE, 8, 3)
		self.gridMasked = cv.CreateImage (GRID_SIZE, 8, 4)
		self.gridColours = cv.CreateImage (GRID_SIZE, 8, 3)
		
		# Mask frames
		self.gridMask = cv.CreateImage (GRID_SIZE,8,1)
		self.colourMaskTemp = cv.CreateImage (GRID_SIZE, 8, 1)
		self.colourMaskAll = cv.CreateImage (GRID_SIZE, 8, 1)
		self.colourMask = []
		for i, marker in enumerate(self.tracker.markers):
			self.colourMask.append (cv.CreateImage (GRID_SIZE, 8, 1))
		self.extractedColours = cv.CreateImage (GRID_SIZE, 8, 3)
		self.erodedMask = cv.CreateImage (GRID_SIZE, 8, 1)
		self.markerRegion = cv.CreateImage ((ROI_SIZE,ROI_SIZE),8,1)
		
		self.roughErosion = cv.CreateStructuringElementEx (3,3,0,0,cv.CV_SHAPE_RECT)
		self.fineErosion = cv.CreateStructuringElementEx (2,2,0,0,cv.CV_SHAPE_RECT)

	def Tick (self):
		if not self.capture: return
		# Grab frame and prepare for processing
		frame = cv.QueryFrame (self.capture)
		cv.Flip (frame, self.origFrame,flipMode=-1)
		cv.Resize (self.origFrame, self.gridFrame)
		cv.CvtColor (self.gridFrame, self.gridFrameHSV, cv.CV_BGR2HSV)

		cv.Set (self.colourMaskAll, (0,))
		cv.Set (self.extractedColours, (0,0,0))
		markers = self.tracker.markers
		for i, marker in enumerate (self.tracker.markers):
			cRange = marker.colourRange
			mask = self.colourMask[i]
			# Extract colour map
			cv.InRangeS (
				self.gridFrameHSV,
				(cRange.hue[0],cRange.saturation[0],cRange.value[0]),
				(cRange.hue[1],cRange.saturation[1],cRange.value[1]),
				mask)
			if cRange.hue2 != None:
				cv.InRangeS (
					self.gridFrameHSV,
					(cRange.hue2[0],cRange.saturation[0],cRange.value[0]),
					(cRange.hue2[1],cRange.saturation[1],cRange.value[1]),
					self.colourMaskTemp)
				cv.Add (self.colourMaskTemp, mask, mask)
			
			# First pass: find approximate center to within ROI_SIZE pixels
			cv.Erode (mask, self.erodedMask, element=self.fineErosion, iterations=4)
			try:
				x,y,px,py = self.FindCentre (self.erodedMask)
			except MarkerNotFound:
				marker.Disable ()
				continue

			# Second pass: discard outliers and recalculate centre
			left = max (0, int(px - ROI_SIZE/2))
			top = max (0, int(py - ROI_SIZE/2))
			right = min (GRID_SIZE[0], left+ROI_SIZE)
			bottom = min (GRID_SIZE[1], top+ROI_SIZE)
			rect = (left,top,right-left,bottom-top)
			roi = cv.GetSubRect (
				cv.GetMat(mask),
				rect)
			cv.Erode (roi, roi, element=self.fineErosion, iterations=3)
			cv.Dilate (roi, roi, element=self.fineErosion, iterations=1)
			try:
				subx, suby, subpx, subpy = self.FindCentre (roi)
			except MarkerNotFound:
				marker.Disable ()
				continue
			x = (left + subpx)/GRID_SIZE[0]
			y = (top + subpy)/GRID_SIZE[1]

			marker.Target (x, y) 

			cv.SetImageROI (mask, rect)
			cv.SetImageROI (self.colourMaskAll, rect)
			cv.Add (mask, self.colourMaskAll, self.colourMaskAll)
			cv.ResetImageROI (mask)
			cv.ResetImageROI (self.colourMaskAll)
			cv.Copy (self.gridFrame, self.extractedColours, mask)

		cv.MixChannels ([self.extractedColours,self.colourMaskAll],[self.gridMasked],
				[(0,2),(1,1),(2,0),(3,3)])
		cv.WaitKey (1) # there's gotta be a better way...

	def FindCentre (self, image):
		moments = cv.Moments (cv.GetMat(image))
		central = cv.GetCentralMoment (moments, 0, 0)
		if central == 0: raise MarkerNotFound ()
		else:
			px = cv.GetSpatialMoment (moments, 1, 0)/central
			py = cv.GetSpatialMoment (moments, 0, 1)/central
			x = px/GRID_SIZE[0]
			y = py/GRID_SIZE[1]
		return (x,y,px,py)

	def SetVideoSource (self, deviceID=STREAM_DEVICE, width=STREAM_SIZE[0], height=STREAM_SIZE[1], fps=STREAM_FPS):
		''' Opens a video stream, optionally requesting one or more parameters from
		the driver.'''
		self.deviceID = deviceID
		# Open the stream.
		self.capture = cv.CaptureFromCAM (deviceID)
		# Attempt to set parameters.
		cv.SetCaptureProperty (self.capture, cv.CV_CAP_PROP_FRAME_WIDTH,width)
		cv.SetCaptureProperty (self.capture, cv.CV_CAP_PROP_FRAME_HEIGHT,height)
		#if not fps == None:
		cv.SetCaptureProperty (self.capture, cv.CV_CAP_PROP_FPS,fps)
		# Now get the actual parameters used:
		rwidth = self.streamWidth = int(cv.GetCaptureProperty (self.capture, cv.CV_CAP_PROP_FRAME_WIDTH))
		rheight = self.streamHeight = int(cv.GetCaptureProperty (self.capture, cv.CV_CAP_PROP_FRAME_HEIGHT))
		self.streamFPS = int(cv.GetCaptureProperty (self.capture, cv.CV_CAP_PROP_FPS))
		if rwidth == 0 or rheight == 0:
			self.capture = None
			self.modeChangeCallback ()
			return
		
		dimensions = (rwidth, rheight)
		if not dimensions in STREAM_SIZES:
			STREAM_SIZES.append (dimensions)
			print "Detected unsupported resolution %ix%i" % (width,height)

		# Initialise frame buffer
		self.origFrame = cv.CreateImage (dimensions, 8, 3)
		
		self.modeChangeCallback ()

	def NextVideoSource (self):
		if self.deviceID == None: self.deviceID = 0
		else: self.deviceID += 1
		self.SetVideoSource (deviceID = self.deviceID)

	def PreviousVideoSource (self):
		if self.deviceID == None: self.deviceID = 0
		elif self.deviceID > 0: self.deviceID -= 1
		else: return
		self.SetVideoSource (deviceID = self.deviceID)

	def GetRawFrame (self):
		''' Gets a reference to the current raw unprocessed frame data.

		Not thread safe.'''
		return self.origFrame

	def GetGridFrame (self):
		''' Gets a reference to the current shrunk-for-processing data.

		Not thread safe.'''
		return self.gridFrame

	def GetMaskedFrame (self):
		''' Gets a reference to the current processed, feature-masked data.

		Not thread safe.'''
		return self.gridMasked

	def SetModeChangeCallback (self, callback):
		self.modeChangeCallback = callback
