import math
from config import *
from constants import *

PITCH_TO_NOTE = ["%s%i" % (letter,octave-2) for octave in range(10) for letter in KEYS]

class Scale:
	TYPE_PENTATONIC = 0
	TYPE_DIATONIC = 1
	TYPE_CHROMATIC = 2
	def __init__ (self,
			key=0,
			nOctaves=2,
			relativeNotes=None,
			highlight={
				UNITY:[0,0,0,0.75],
				PERFECT_4:[0,0,0,0.25],
				PERFECT_5:[0,0,0,0.5]}):
		self.root = key + ROOT_NOTE_OFFSET
		self.key = key
		self.nOctaves = nOctaves
		self.highlights = []
		self.relativeNotes = relativeNotes
		self.toHighlight = highlight
		self.SetOctaveRange (nOctaves)
	def GetNote (self, position):
		''' Gets the note corresponding to the percentage of the way through the scale. '''
		floorPos = math.floor (position*(self.nNotes))
		return self.notes [int(floorPos)]

	def SetKey (self, key):
		self.root = key + ROOT_NOTE_OFFSET
		self.key = key
		self.SetOctaveRange (self.nOctaves)

	def SetOctaveRange (self, nOctaves):
		root = self.root
		self.nOctaves = nOctaves
		self.notes = [octave*12+interval+root for octave in range(nOctaves) for interval in self.relativeNotes]
		nNotes = self.nNotes = len(self.notes)
		self.notePositions = zip (self.notes, [float(i)/nNotes for i in range(nNotes)])
		for i,note in enumerate(self.relativeNotes*nOctaves):
			if note in self.toHighlight: self.highlights.append (self.toHighlight[note])
			else: self.highlights.append (None)


class PentatonicScale (Scale):
	scaleType = Scale.TYPE_PENTATONIC
	def __init__ (self, key, nOctaves):
		Scale.__init__ (self,
			key = key, 
			nOctaves = nOctaves,
			relativeNotes = (UNITY,MAJOR_2,MAJOR_3,PERFECT_5,MAJOR_6))

class DiatonicScale (Scale):
	scaleType = Scale.TYPE_DIATONIC
	def __init__ (self, key, nOctaves):
		Scale.__init__ (self, 
			key = key, 
			nOctaves = nOctaves, 
			relativeNotes = (UNITY,MAJOR_2,MAJOR_3,PERFECT_4,PERFECT_5,MAJOR_6,MAJOR_7))

class ChromaticScale (Scale):
	scaleType = Scale.TYPE_CHROMATIC
	def __init__ (self, key, nOctaves):
		Scale.__init__ (self,
			key = key,
			nOctaves = nOctaves, 
			relativeNotes = range(12))

class BluesScale (Scale):
	def __init__ (self, root, nOctaves):
		Scale.__init__ (self, root, nOctaves, (0,3,5,6,7,10,12))

