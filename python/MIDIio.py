import rtmidi
import time

from MIDIConstants import *
from constants import *
import config

midiInPorts = rtmidi.MidiIn().get_ports ()
midiOutPorts = rtmidi.MidiOut().get_ports ()

class MIDIDevice:
	def __init__ (self, deviceID, useInput=True, useOutput=True):
		self.activeNotes = []
		self.tracker = None
		self.deviceID = deviceID
		self.useInput = useInput
		self.useOutput = useOutput

		if useOutput:
			self.midiOut = rtmidi.MidiOut ()
			self.midiOut.open_port (deviceID)
		if useInput:
			self.midiIn = rtmidi.MidiIn ()
			self.midiIn.open_port (deviceID)

	def SetOutputPort (self, portID):
		self.deviceID = portID
		for note in self.activeNotes[:]:
			self.midiOut.send_message ([note[0], note[1], 0])
			self.activeNotes.remove (note)
		self.midiOut.close_port ()
		self.midiOut.open_port (portID)

	def SetInputPort (self, portID):
		self.deviceID = portID
		self.midiIn.close_port ()
		self.midiIn.open_port (portID)

	def SendNote (self, note, velocity, duration, channel=0x99):
		self.midiOut.send_message ([channel, note, velocity])
		self.activeNotes.append ([channel, note, velocity, duration, time.time ()])

	def NoteOn (self, note, velocity, channel=1):
		self.midiOut.send_message ([channel, note, velocity])

	def NoteOff (self, note, channel=1):
		self.midiOut.send_message ([channel, note, 0])

	def SendControl (self, value, controller=MODULATION_WHEEL, channel=1):
		msg = [CONTINUOUS_CONTROLLER + channel - 1, controller, value]
		self.midiOut.send_message (msg)

	def SetTracker (self, tracker):
		self.tracker = tracker

	def Tick (self):
		now = time.time ()
		for note in self.activeNotes[:]:
			if now - note[4] >= note[3]:
				self.midiOut.send_message ([note[0], note[1], 0])
				self.activeNotes.remove (note)

		if self.useInput:
			msg = self.midiIn.get_message ()
			markers = self.tracker.markers
			while msg != None:
				# this is all specific to my axiom 25...
				if msg[0][0] == 176:
					# A knob
					knobID = msg[0][1] - 102
					direction = msg[0][2] - 64
					if knobID==0: markers[MARKER_BLUE].colourRange.saturation[0] += direction
					if knobID==1: markers[MARKER_BLUE].colourRange.value[0] += direction
					if knobID==2: markers[MARKER_RED].colourRange.saturation[0] += direction
					if knobID==3: markers[MARKER_RED].colourRange.value[0] += direction
					if knobID==4: markers[MARKER_GREEN].colourRange.saturation[0] += direction
					if knobID==5: markers[MARKER_GREEN].colourRange.value[0] += direction
					if knobID==6: markers[MARKER_YELLOW].colourRange.saturation[0] += direction
					if knobID==7: markers[MARKER_YELLOW].colourRange.value[0] += direction
				msg = self.midiIn.get_message ()
