import sys, time, threading, traceback
from constants import *
import pygame

from config import *
from imgproc import StreamProcessor
from tracker import Marker, Tracker
from MIDIio import MIDIDevice
from ui import MainWindow

class FrameTimer:
	def __init__ (self):
		self.nFrame = 0
		self.fps = 0
		self.countStart = time.time ()
		self.lastFrame = self.countStart
		self.tickTime = 0.001 # Avoids divide-by-zero errors

	def Tick (self):
		self.nFrame += 1
		now = time.time ()
		self.tickTime = now - self.lastFrame
		self.lastFrame = now
		
		# Recalculate FPS after every 30 frames
		if self.nFrame >= 30:
			elapsed = now - self.countStart
			self.fps = float(self.nFrame)/elapsed
			self.countStart = time.time ()
			self.nFrame = 0

class Scheduler:
	''' Provides the main loop functionality for ricercar. '''
	def __init__ (self):
		# Initialise MIDI
		midiOut = self.midiOut = MIDIDevice (mode=MIDIDevice.MODE_OUTPUT)
		midiIn = self.midiIn = MIDIDevice (mode=MIDIDevice.MODE_INPUT)
		midiOut.OpenPort (MIDI_OUT_DEVICE)
		midiIn.OpenPort (MIDI_IN_DEVICE)
		# GUI, Tracker, Image processing
		tracker = self.tracker = Tracker (midiOut)
		self.midiIn.SetTracker (self.tracker)
		self.streamProc = StreamProcessor (self.tracker)
		window = self.window = MainWindow (
			scheduler = self,
			tracker = self.tracker,
			streamProcessor = self.streamProc,
			midiIn = midiIn,
			midiOut = midiOut)

		#self.imgProcThread = threading.Thread (target=self.ImgProcLoop,name="ImgProc")
		self.frameTimer = FrameTimer ()
		self.running = False

	def Go (self):
		''' Starts ricercar. '''
		# Pre-flight initialisation for non-thread-safe tasks.
		#self.imgProcThread.start ()
		self.window.InitVideo ()
		self.streamProc.SetVideoSource (deviceID=STREAM_DEVICE)
		
		self.running = True
		while self.running:
			# Send heartbeat
			self.frameTimer.Tick ()
			self.streamProc.Tick ()
			self.tracker.Tick (self.frameTimer.tickTime)
			self.midiOut.Tick ()
			self.midiIn.Tick ()
			self.window.Tick ()

			# Input loop
			for event in pygame.event.get ():
				if event.type == pygame.KEYDOWN:
					# Tab toggles HUD display
					if event.key == pygame.K_TAB:
						self.window.ToggleHUD ()
				elif event.type == pygame.MOUSEBUTTONUP:
					glX, glY = event.pos
					self.window.Click (glX, glY)
				elif event.type == pygame.QUIT:
					self.Stop ()

	def Stop (self):
		self.running = False
		print "Stopping ricercar..."
		pygame.display.quit ()
		sys.exit ()

# Start ricercar if this file has been invoked as an application.
if __name__ == "__main__":
	s = Scheduler ()
	s.Go ()
