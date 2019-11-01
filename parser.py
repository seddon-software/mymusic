'''
This parser takes an input file of type *.mymidi and creates a python file temp.py
The program then runs this python file before deleting it
The temp.py file uses one of my libraries <library.myrtmidi> or <library.mymidi> to generate music
See Tracks.play() in <library.mymidi> to see how the midi file is created

This parser accepts <N> notation to select instruments
'''
import os, sys
import ply.lex as lex
import ply.yacc as yacc
import subprocess

####################
# check command line
####################
if len(sys.argv) != 2:
    print("Usage: python parser.py <mymidi-file-name>")
    sys.exit()

# get the name of the "mymidi" source file
INFILE = sys.argv[1]

# strip off ".mymidi" extension if present
if INFILE.endswith(".mymidi"):
    INFILE = INFILE[:-len(".mymidi")]



###################
# setup debug flags
###################
print_tokens = False
code_generation = False
lexer_debug = False
parser_debug = False
BNF_debug = False

############################# PARSER ################################

tempo = ""
sections = 1
startingTrackNo = 0
endingTrackNo = 0
instrumentId = 0
instrumentIds = []
lastTune = 0

def BNF_debugging(name, p=""):
    if BNF_debug: 
#        print(f"{name} : {p}")
#        if name == 'line': print(f"{name} : {p}")
        if name == 'instrument': print(f"{name} : {p}")
#        if name == 'section': print(f"{name} : {p}")
        pass
    
def doParser():
    
    def p_song(p):
        """
        song : intro sections
        """
        p[0] = 'import sys\n'
        p[0] += 'sys.path.append("..")\n'
        p[0] += 'from library.mymidi import Tracks\n'
        p[0] += f'tracks = Tracks("{INFILE}", {endingTrackNo})\n'
        p[0] += p[2]
        p[0] += '\ntracks.play()\n'
        BNF_debugging("song", p[0])
        
    def p_sections(p):
        """
        sections : sections section
                 | section
        """
        global sections, tempo, instrumentIds, lastTune
        if len(p) == 2: 
            p[0] = p[1]
        if len(p) == 3:
            sections += 1
            p[0] = p[1]
            p[0] += p[2]
        p[0] += tempo

        for i in instrumentIds:
            if i > lastTune:
                p[0] += f'tune{i}(t{i})\n'
                lastTune = i
        BNF_debugging("sections", p[0])
                
    def p_section(p):
        '''section : instruments lines'''
        global startingTrackNo, endingTrackNo
        startingTrackNo = endingTrackNo
        defaults = {'volume' : 100, 'octave' : 0}
        instruments = p[1]
        lines = p[2]
        p[0] = ""
        for instrument in instruments:
            original = lines
            p[0] += f"\n\ndef tune{instrument['id']}(m):\n"
            for line in lines:
                ids = [int(s) for s in line[0]]
                notes_and_durations = line[1]
                for duration, notes in notes_and_durations:
                    durations = [duration for note in notes]    #@UnusedVariable
                    # instrument active
                    if not ids or instrument['id'] in ids:
                        notes = translate(notes)
                    # instrument active
                    else:
                        notes = [0 for note in notes]    #@UnusedVariable
                    p[0] += f'\tm += {notes}, \\\n'
                    p[0] += f'\t     {durations}\n'
            lines = original
        for i, entry in enumerate(p[1]):
            entry = {**defaults, **entry} # combine dictionaries
            instrument = entry['instrument']
            volume = entry['volume']
            octave = entry['octave']
            track = startingTrackNo+i+1
            p[0] += setInstrument(track, instrument, int(octave) * 12, volume)
        endingTrackNo = track
        BNF_debugging("section", p[0])
        
    def p_instruments(p):
        """
        instruments : instruments instrument
                    | instrument
        """
        if len(p) == 2: 
            p[0] = [p[1]]
        if len(p) == 3: 
            p[1].append(p[2])
            p[0] = p[1]
        BNF_debugging("instruments", p[0])
        
    def p_instrument(p):
        """
        instrument : INSTRUMENT '=' NAME_OR_INTEGER ',' ID ':' INTEGER ',' instrument_parts newlines
                   | INSTRUMENT '=' NAME_OR_INTEGER ',' ID ':' INTEGER newlines
                   | INSTRUMENT '=' NAME_OR_INTEGER ',' instrument_parts newlines
                   | INSTRUMENT '=' NAME_OR_INTEGER newlines """
        # if instrument is specified as an integer convert to a name
        try:
            p[3] = instruments[int(p[3])]
            print(p[3])
        except:
            pass
        
        global instrumentId, instrumentIds
        
        if len(p) == 5:
            instrumentId += 1 
            p[0] = {'instrument':p[3], 'id':instrumentId}            
        if len(p) == 7:
            instrumentId += 1 
            p[0] = {**{'instrument':p[3], 'id':instrumentId}, **p[5]} # combine dictionaries
        if len(p) == 9:
            instrumentId = int(p[7])
            p[0] = {'instrument':p[3], 'id':instrumentId}
        if len(p) == 11: 
            instrumentId = int(p[7])
            p[0] = {**{'instrument':p[3], 'id':instrumentId}, **p[9]} # combine dictionaries
        instrumentIds.append(instrumentId)
        
        BNF_debugging("instrument", p[0])
    
    def p_NAME_OR_INTEGER(p):
        """NAME_OR_INTEGER : NAME
                           | INTEGER """
        p[0] = p[1]
    
    def p_instrument_parts(p):
        """
        instrument_parts : instrument_parts ',' instrument_part
                         | instrument_part
        """
        if len(p) == 2: p[0] = p[1]
        if len(p) == 4: p[0] = {**p[1], **p[3]}
        BNF_debugging("instrument_parts", p[0])
    
    def p_instrument_part(p):
        """instrument_part : OCTAVE ':' INTEGER
                           | VOLUME ':' INTEGER"""
        p[0] = {p[1] : p[3]}
        BNF_debugging("instrument_part", p[0])
    
    def p_newlines(p):
        """newlines : newlines NEWLINE
                    | NEWLINE """
        BNF_debugging("newlines")
    
    def p_intro(p):
        """intro : newlines TEMPO '=' '(' INTEGER ',' INTEGER ')' newlines 
                 | TEMPO '=' '(' INTEGER ',' INTEGER ')' newlines""" 
        global tempo
        if len(p) == 10:
            n = int(p[5]) * int(p[7])
        else:
            n = int(p[4]) * int(p[6])
            
        tempo = '\ntracks.setTempo({})\n'.format(n)
        BNF_debugging("intro")

    def p_lines(p):
        '''lines : lines line
                | line'''
        if len(p) == 2: 
            p[0] = [p[1]]
        if len(p) == 3: 
            p[1].append(p[2])
            p[0] = p[1]
        BNF_debugging("lines", p[0])
    
    def p_line(p):
        '''line : selector frames newlines
                | frames newlines'''
        if len(p) == 3:
            p[0] = [(), p[1]]
        else:
            p[0] = [p[1], p[2]]
        BNF_debugging("line", p[0])
    
    def p_frames(p):
        ''' frames : frames frame
                   | frame '''
        if len(p) == 2:
            p[0] = [p[1]]
        else:
            p[1].append(p[2])
            p[0] = p[1]
        BNF_debugging("frames", p[0])
    
    def p_frame(p):
        ''' frame : duration phrases '''
        p[0] = [p[1], p[2]]
        BNF_debugging("frame", p[0])
    
    def p_phrases(p):
        '''phrases : phrases phrase
                   | phrase'''
        if len(p) == 2: 
            p[0] = p[1]
        if len(p) == 3:
            p[1].extend(p[2])
            p[0] = p[1]
        BNF_debugging("phrases", p[0])

    def p_phrase(p):
        '''phrase : chords
                  | notes'''
        p[0] = p[1]
        BNF_debugging("phrase", p[0])
    
    def p_chords(p):
        '''chords : chords chord
                  | chord'''
        if len(p) == 2: p[0] = p[1]
        if len(p) == 3: p[0] = p[1] + p[2]
        BNF_debugging("chords", p[0])
        
    def p_chord(p):
        """chord : '{' notes '}'"""
        p[0] = [p[2]]
        BNF_debugging("chord", p[0])
    
    def p_notes(p):
        ''' notes : notes note
                  | note'''
        if len(p) == 2:
            p[0] = [p[1]]
        if len(p) == 3:
            p[1].append(p[2])
            p[0] = p[1]
        BNF_debugging("notes", p[0])
        
    def p_note(p):
        '''note : INTEGER 
                | REST'''
        if p[1] == '-':      # rest
            p[0] = 0
        else:
            p[0] = int(p[1]) + 60
        BNF_debugging("note", p[0])
        
    def p_duration(p):
        """duration : '[' INTEGER ']'"""
        duration = p[2]     #@UnusedVariable
        p[0] = int(p[2])
        BNF_debugging("duration", p[0])

    def p_selector(p):
        """selector : '<' list_of_integers '>' """
        p[0] = tuple(p[2])
        BNF_debugging("selector", p[0])

    def p_list_of_integers(p):
        """list_of_integers : list_of_integers "," INTEGER
                            | INTEGER """
        if len(p) == 2:
            p[0] = [p[1]]
        else:
            p[1].append(p[3])
            p[0] = p[1]
        BNF_debugging("list_of_integers", p[0])
                        
    def translate(notes):
        result = '['
        for n in notes:
            if type(n) is list:
                try:
                    m = '{}'.format(n)
                    result += '{' + m[1:-1] + '}, '
                except Exception as e:
                    print(e)
            else:
                result += str(n) + ', '
        result = result[:-2] + ']'
        return result
    
    def p_error(x):
        print("ERROR ---", x)
        
    # Build the parser
    parser = yacc.yacc()
    result = parser.parse(data, lexer=getLexer(), debug=parser_debug)
    if code_generation: print(result)
    return result

############################# COMMON ################################

reserved = {
   'tempo'      : 'TEMPO',
   'instrument' : 'INSTRUMENT',
   'octave'     : 'OCTAVE',
   'volume'     : 'VOLUME',
   'id'         : 'ID'
}

tokens = [
    'INTEGER',
    'REST',
    'NEWLINE',
    'NAME'] + list(reserved.values())

literals = [ '(', ')', '{', '}', '[', ']', '=', ',' , ':', '<', '>']

############################# LEXER ################################

def getLexer():
    
    t_REST = r'[-]'     #@UnusedVariable
    
    def t_ID(t):
        r'[a-zA-Z_][ +()\-a-zA-Z_0-9]*'
        t.value = t.value.strip()
        if t.value in reserved:
            t.type = reserved.get(t.value,'ID')    # Check for reserved words
        else:
            t.type = 'NAME'
        return t
    
    
    # lexical rules
    
    # rule to track line numbers
    def t_NEWLINE(t):
        r'\n'
        t.lexer.lineno += len(t.value)
        return t

    # either # (one liner) or /*...*/ (multi liner)
    def t_COMMENT(t):
        r'([/][*](.|\n)*?[*][/]|[#].*\n*?)' 
        return None
                
    def t_INTEGER(t):
        r'[+-]*\d+'
        return t
    
    def t_NAME(t):
        r'[a-zA-Z0-9][ a-zA-Z0-9]*'
        return t
     
    t_ignore  = ' \t'       #@UnusedVariable
    
    # error handling rule
    def t_error(t):
        print("Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)
    
    # Build the lexer
    lexer = lex.lex(debug=lexer_debug)
    lexer.input(data)
    
    # echo the lexical tokens
    if print_tokens:
        while True:
            tok = lexer.token()
            if not tok: break
            print(tok)

############################# MISCELLANEOUS ################################

def setInstrument(i, instrument, pitchShift, volume):
    # max volume = 127
    return f'''
t{instrumentIds[i-1]} = tracks.addTrack("Track {i}")
t{instrumentIds[i-1]}.setInstrument("{instrument}", channel = {i-1}, pitchShift = {pitchShift}, volume = {volume})'''
    

def getFileContents(filename):
    try: 
        f = open(filename, "r")
        allLines = f.readlines()
        return " ".join(allLines)
    except Exception as e:
        print(e)
    finally:
        try:
            f.close()
        except: 
            pass    # can't do anything if close throws

def getInstrumentDictionary(filename):
    d = {}
    try: 
        f = open(filename, "r")
        for line in f:
            instrument, i = line.split(":")
            i = int(i)
            instrument = instrument.strip() 
            d[i] = instrument
        return d
    except Exception as e:
        print(e)
    finally:
        try:
            f.close()
        except: 
            pass    # can't do anything if close throws
    
############################# MAIN ################################

instruments = None

def main():
    result = doParser()
    # execute generated code
    f = open('temp.py', 'w')
    f.writelines(result)
    f.close()
    subprocess.call(f"{sys.executable} temp.py".split())
    os.system("rm temp.py")
    os.system("rm parser.out")
    os.system("rm parsetab.py")
    
try:
    instruments = getInstrumentDictionary('INSTRUMENTS.txt')
    data = getFileContents(INFILE + ".mymidi")
    main()
except Exception as e:
    print(e)
    print("Can't open {}".format(INFILE + ".mymidi"))

