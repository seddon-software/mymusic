INSTALATION INSTRUCTIONS
=======================

The music generator software runs in a Python 3 environment.  You will need to 
install the following additional packages.
    pip install ply
    pip install psutil
    pip install midiutil
    pip install pandas

You will also need to install one of the following software synths:
    timidity
    fluidsynth

The software also requires at least one soundfont (*.sf2).  You can download soundfonts from the internet.
The following soundfonts are quite good (http://www.soundfonts.gonet.biz/):
    merlin_gold.sf2
    merlin_vienna.sf2

FILES
=====
    parser.py           This is the parser that reads a "mymidi" file and creates a midifile
    parser.cfg          Contains the information on the synth and soundfont to use
    example.mymidi      Example song file with comments (please read)
    INSTRUMENTS.txt     List of midi instruments
    library/mymidi.py   Library used by parser.py

RUNNING THE SOFTWARE
====================

To run the software use the command:
    python parser.py example

where you can replace "example" with any new file you create based on this file.  Note the song file must have
a ".mymidi" extension.

