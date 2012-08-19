ricercar
========

Ricercar (pronounced rich-air-kar) turns your webcam into a musical instrument. Use any brightly coloured object to control pitch, volume or any other parameter that can be controlled via MIDI. Use your system's built-in set of MIDI instrument sounds or bring your own synthesiser to create and shape sounds your way. It is free for non-commerical use.

Unlike many other visual-input audio systems, Ricercar is designed to be used in live performance. All aspects of configuration can be bound to knobs and buttons on any MIDI control surface - including Ricercar itself!

Usage
-----

Find some small brightly coloured objects to use as markers. Blue, red, yellow and green items work best (in that order). Bottle caps tend to work well, but experiment with larger or smaller objects if you have trouble with detection. Ricercar will identify these markers and use them to control sounds. The output behaviour for each marker can be configured individually, but you'll need to be comfortable with editing Python source files until GUI controls are hooked up. The default behaviour creates vertical lines called 'strings' that can be turned on and off by swiping past them with a marker. The strings are offset by a configurable number of semitones, similar to a guitar. 

Ricercar works best in a brighly lit, neutrally coloured room. The marker recognition parameters can be tuned with the first 8 continuous controllers on a generic MIDI control surface, or edited manually in config.py. The current values can be viewed by pressing the Tab key. 

If your system has built-in MIDI sounds you can use them with Ricercar by selecting the appropriate device from the Input/Output menu, which can be reached by pressing ` (backtick, usually located above Tab on the keyboard). Otherwise, you'll need to bring your own software synthesiser. A virtual MIDI connection between two programs can be achieved on Windows by using a free tool like LoopMIDI (http://www.tobias-erichsen.de/software/loopmidi.html) to create a MIDI loopback port on Windows, or the built-in MIDI driver configuration tool on OS X.

By default the MIDI output channel for the red and blue markers are 2 and 4 respectively.


Dependencies
------------
Library pack for Windows: http://shmookey.net/ricercar/releases/libs.7z

Python 2.7 (x86) - Python runtime environment
http://www.python.org/getit/releases/2.7/

OpenCV - Computer visualisation library (comes with Python bindings)
http://opencv.willowgarage.com/wiki/

PyFTGL - Python bindings for FTGL (FreeType text rendering in OpenGL)
http://code.google.com/p/pyftgl/

PyCVGL - Fast conversion of OpenCV images to OpenGL textures.
https://code.google.com/p/pycvgl/

python-rtmidi - Python bindings for MIDI I/O library RtMIDI.
http://trac.chrisarndt.de/code/wiki/python-rtmidi

Running the Python version
--------------------------
1. Copy any FreeType-compatible font file (I suggest Microsoft's consola.ttf) into the working directory.
1. Set the FONT variable in config.py to the name of your font file.
1. Run ricercar.py
