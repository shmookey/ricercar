import cv, cv2
from constants import *

from config import *

class StreamProcessor:
	def __init__ (self, window, tracker):
		# Set up window and video capture
		self.tracker = tracker
		self.window = window

		# Initialise intermediate frames
		self.origFrame = cv.CreateImage (STREAM_SIZE, 8, 3)
		self.gridFrameLarge = cv.CreateImage (STREAM_SIZE, 8, 3)
		self.gridFrame = cv.CreateImage (GRID_SIZE, 8, 3)
		self.gridFrameHSV = cv.CreateImage (GRID_SIZE, 8, 3)
		self.gridMasked = cv.CreateImage (GRID_SIZE, 8, 4)
		self.gridColours = cv.CreateImage (GRID_SIZE, 8, 3)
		self.displayFrame = cv.CreateImage (STREAM_SIZE, 8, 4)

		# Mask frames
		self.gridMask = cv.CreateImage (GRID_SIZE,8,1)
		self.colourMaskTemp = cv.CreateImage (GRID_SIZE, 8, 1)
		self.colourMaskAll = cv.CreateImage (GRID_SIZE, 8, 1)
		self.colourMask = []
		for i, marker in enumerate(self.tracker.markers):
			self.colourMask.append (cv.CreateImage (GRID_SIZE, 8, 1))
		self.extractedColours = cv.CreateImage (GRID_SIZE, 8, 3)

		self.erosionElement = cv.CreateStructuringElementEx (3,3,0,0,cv.CV_SHAPE_RECT)

	def Tick (self):
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
			cv.Erode (mask, mask, element=self.erosionElement, iterations=2)
			# Calculate moments
			moments = cv.Moments (cv.GetMat(mask))
			central = cv.GetCentralMoment (moments, 0, 0)
			if central == 0: marker.Disable ()
			else:
				x = cv.GetSpatialMoment (moments, 1, 0)/central/GRID_SIZE[0]
				y = cv.GetSpatialMoment (moments, 0, 1)/central/GRID_SIZE[1]
				marker.Target (x, y, 0.9) # TODO: Fix this magic number

			cv.Add (mask, self.colourMaskAll, self.colourMaskAll)

			cv.Copy (self.gridFrame, self.extractedColours, mask)

		cv.MixChannels ([self.extractedColours,self.colourMaskAll],[self.gridMasked],
				[(0,2),(1,1),(2,0),(3,3)])
		self.window.NewGridFrame (self.gridFrame)
		self.window.NewMaskedFrame (self.gridMasked)
		cv.WaitKey (1) # there's gotta be a better way...

	def InitVideo (self):
		self.capture = cv.CaptureFromCAM (STREAM_DEVICE)
		cv.SetCaptureProperty (self.capture, cv.CV_CAP_PROP_FPS,STREAM_FPS)
		cv.SetCaptureProperty (self.capture, cv.CV_CAP_PROP_FRAME_WIDTH,STREAM_SIZE[0])
		cv.SetCaptureProperty (self.capture, cv.CV_CAP_PROP_FRAME_HEIGHT,STREAM_SIZE[1])

