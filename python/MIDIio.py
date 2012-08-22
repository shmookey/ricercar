import rtmidi
import time

from MIDIConstants import *
from constants import *
import config

def IfConnected (midiFn):
	''' Just ignore MIDI calls if the interface isn't up. '''
	def MIDIFunction (self, *args, **kwargs):
		if not self.state == MIDIDevice.STATE_CONNECTED:
			return
		midiFn (self, *args, **kwargs)
	return MIDIFunction

class MIDIDevice:
	inPorts = [str(portName) for portName in rtmidi.MidiIn().get_ports ()]
	outPorts = [str(portName) for portName in rtmidi.MidiOut().get_ports ()]
	MODE_INPUT = 0
	MODE_OUTPUT = 1

	STATE_NOTCONNECTED = 0
	STATE_CONNECTED = 1
	STATE_ERROR = 2

	def __init__ (self, mode=MODE_INPUT):
		self.activeNotes = []
		self.tracker = None
		self.deviceID = None
		self.mode = mode
		self.state = MIDIDevice.STATE_NOTCONNECTED
		if mode == MIDIDevice.MODE_OUTPUT:
			self.device = rtmidi.MidiOut ()
			self.Tick = self.TickOutput
		elif mode == MIDIDevice.MODE_INPUT:
			self.device = rtmidi.MidiIn ()
			self.Tick = self.TickInput

	def OpenPort (self, portID):
		if self.state == MIDIDevice.STATE_CONNECTED:
			self.device.close_port ()
		status = False
		if self.mode == MIDIDevice.MODE_INPUT:
			status = self.PrepareOpenInputPort (portID)
		elif self.mode == MIDIDevice.MODE_OUTPUT:
			status = self.PrepareOpenOutputPort (portID)
		if status == False: return False
		self.deviceID = portID
		try:
			self.device.open_port (portID)
		except:
			self.state = MIDIDevice.STATE_ERROR
			return False
		self.state = MIDIDevice.STATE_CONNECTED
		return True

	def PrepareOpenInputPort (self, portID):
		if portID >= len(MIDIDevice.inPorts):
			self.state = MIDIDevice.STATE_ERROR
			return False
		return True

	def PrepareOpenOutputPort (self, portID):
		if portID >= len(MIDIDevice.outPorts):
			self.state = MIDIDevice.STATE_ERROR
			return False
		self.CancelActiveNotes ()
		return True

	@IfConnected
	def CancelActiveNotes (self):
		for note in self.activeNotes[:]:
			self.device.send_message ([note[0], note[1], 0])
			self.activeNotes.remove (note)

	'''def OpenInputPort (self, portID):
		self.deviceID = portID
		self.midiIn.close_port ()
		self.midiIn.open_port (portID)'''

	@IfConnected
	def SendNote (self, note, velocity, duration, channel=0x99):
		self.device.send_message ([channel, note, velocity])
		self.activeNotes.append ([channel, note, velocity, duration, time.time ()])

	@IfConnected
	def NoteOn (self, note, velocity, channel=1):
		self.device.send_message ([channel, note, velocity])

	@IfConnected
	def NoteOff (self, note, channel=1):
		self.device.send_message ([channel, note, 0])

	@IfConnected
	def SendControl (self, value, controller=MODULATION_WHEEL, channel=1):
		msg = [CONTINUOUS_CONTROLLER + channel - 1, controller, value]
		self.device.send_message (msg)

	def SetTracker (self, tracker):
		self.tracker = tracker

	@IfConnected
	def TickOutput (self):
		now = time.time ()
		for note in self.activeNotes[:]:
			if now - note[4] >= note[3]:
				self.device.send_message ([note[0], note[1], 0])
				self.activeNotes.remove (note)

	@IfConnected
	def TickInput (self):
		msg = self.device.get_message ()
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
			msg = self.device.get_message ()
