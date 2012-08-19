import os, sys, time, threading, traceback
from constants import *
import pygame

from config import *
from imgproc import StreamProcessor
from tracker import Marker, Tracker
import MIDIio
from ui import MainWindow

os.environ['SDL_VIDEO_CENTERED'] = '1'

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
	def __init__ (self):
		window = self.window = MainWindow (self)
		midiOut = self.midiOut = MIDIio.MIDIDevice (MIDI_OUT_DEVICE, useInput=False)
		midiIn = self.midiIn = MIDIio.MIDIDevice (MIDI_IN_DEVICE, useOutput=False)
		self.tracker = Tracker (window, self.midiOut)
		self.streamProc = StreamProcessor (window, self.tracker)
		self.midiIn.SetTracker (self.tracker)
		self.window.SetTracker (self.tracker)
		self.window.SetMIDIDeviceList (MIDIio.midiInPorts, MIDIio.midiOutPorts,midiIn,midiOut)

		#self.trackerThread = threading.Thread (target=self.TrackerLoop,name="Tracker")
		#self.imgProcThread = threading.Thread (target=self.ImgProcLoop,name="ImgProc")
		self.imgProcTimer = FrameTimer ()
		self.trackerTimer = FrameTimer ()

		self.running = False

	def Go (self):
		self.running = True
		self.ImgProcLoop ()
		#self.trackerThread.start ()

	def TrackerLoop (self):
		self.imgProcThread.start ()
		while True:
			if not self.running: return

	def ImgProcLoop (self):
		self.window.InitVideo ()
		self.streamProc.InitVideo ()
		lastFPSdisplay = 0
		while True:
			if not self.running: return
			self.streamProc.Tick ()
			self.imgProcTimer.Tick ()
			self.trackerTimer.Tick ()
			self.tracker.Tick (self.trackerTimer.tickTime)
			self.midiOut.Tick ()
			self.midiIn.Tick ()
			self.window.Render ()

			# Input loop
			for event in pygame.event.get ():
				if event.type == pygame.KEYDOWN:
					# Tab toggles HUD display
					if event.key == pygame.K_TAB:
						self.window.ToggleHUD ()
					elif event.key == pygame.K_BACKQUOTE:
						self.window.ToggleIO ()
				elif event.type == pygame.MOUSEBUTTONUP:
					glX, glY = event.pos
					self.window.Click (glX, glY)
				elif event.type == pygame.QUIT:
					sys.exit ()

	def Stop (self):
		self.running = False

s = Scheduler ()
s.Go ()
