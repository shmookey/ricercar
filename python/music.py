import math
from config import *

PITCH_TO_NOTE = ["%s%i" % (letter,octave-2) for octave in range(10) for letter in ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]]

class Scale:
	def __init__ (self,
			root,
			nOctaves,
			relativeNotes,
			highlight={
				UNITY:[0,0,0,0.75],
				PERFECT_4:[0,0,0,0.25],
				PERFECT_5:[0,0,0,0.5]}):
		self.root = root
		self.nOctaves = nOctaves
		self.notes = [octave*12+interval+root for octave in range(nOctaves) for interval in relativeNotes]
		nNotes = self.nNotes = len(self.notes)
		self.notePositions = zip (self.notes, [float(i)/nNotes for i in range(nNotes)])
		self.highlights = []
		for i,note in enumerate(relativeNotes*nOctaves):
			if note in highlight: self.highlights.append (highlight[note])
			else: self.highlights.append (None)
		print self.highlights
	def GetNote (self, position):
		''' Gets the note corresponding to the percentage of the way through the scale. '''
		floorPos = math.floor (position*(self.nNotes))
		return self.notes [int(floorPos)]
		


class PentatonicScale (Scale):
	def __init__ (self, root, nOctaves):
		Scale.__init__ (self, root, nOctaves, (0,2,4,7,9))

class DiatonicScale (Scale):
	def __init__ (self, root, nOctaves):
		Scale.__init__ (self, 
				root, 
				nOctaves, 
				(UNITY,MAJOR_2,MAJOR_3,PERFECT_4,PERFECT_5,MAJOR_6,MAJOR_7))
		'''self.notePositions[0][2][3] = 0.75 # TODO: get rid of this
		self.notePositions[3][2][3] = 0.25 # TODO: get rid of this
		self.notePositions[4][2][3] = 0.5 # TODO: get rid of this
		self.notePositions[8][2][3] = 0.75 # TODO: get rid of this
		self.notePositions[11][2][3] = 0.5 # TODO: get rid of this'''

class ChromaticScale (Scale):
	def __init__ (self, root, nOctaves):
		Scale.__init__ (self, root, nOctaves, range(12))

class BluesScale (Scale):
	def __init__ (self, root, nOctaves):
		Scale.__init__ (self, root, nOctaves, (0,3,5,6,7,10,12))

