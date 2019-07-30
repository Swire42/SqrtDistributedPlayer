import os
import sys
import shutil
import atexit
import time
import subprocess
import random
import math
import signal

import keyboard

fmtName="notext_tal"
supportedTypes=[".mp3"]

bReadMeta=False
bPreloadMeta=False

bShuffle=True
bRepeat=True

bSavePower=False

try:
    from settings import*
    print("Loaded \"settings.py\".")
except:
    print('''\
No "settings.py" file loaded.
Starting "settings.py" assisted-creation :
(Note : you can always change this later by editing "settings.py")
PLEASE NOTE THAT THERE ARE BARELY NO SAFETY CHECKS DONE ON WHAT YOU TYPE, TYPE WISELY''')
    settingsFile=open('settings.py', mode='w')
    settingsFile.write('rootPath="'+input("Where is your music? [full path] ")+'"\n\n')

    playToolChoice=None
    if os.name=='nt':
        playToolChoice="vlc"
    elif 'termux' in sys.prefix:
        playToolChoice="sox"

    while playToolChoice not in ['vlc', 'sox']:
        playToolChoice=input("Which of these players do you want to use/is installed on your system? [vlc/sox] ")
    settingsFile.write('playTool="'+playToolChoice+'"\n')


    settingsFile.write('''\
#fmtName="notext_tal"
#supportedTypes=[".mp3"]

''')


    try:
        import mutagen
        settingsFile.write('bReadMeta=True # enables mutagen\n')
    except:
        failed=False
        if os.system("pip3 install mutagen"):
            if os.name == 'nt':
                if os.system("easy_install pip"):
                    failed=True
                elif os.system("pip3 install mutagen"):
                    failed=True
            else:
                failed=True
        if failed:
            print('''\
Failed to install mutagen.
IF YOU WANT TRACK INFO TO BE DISPLAYED:
1) Install mutagen lib manually
2) set bReadMeta=True in "settings.py"''')
            settingsFile.write('#bReadMeta=False # enables mutagen\n')
        else:
            settingsFile.write('bReadMeta=True # enables mutagen\n')


    settingsFile.write('''\
#bPreloadMeta=False

#bShuffle=True
#bRepeat=True
''')

    if 'termux' in sys.prefix:
        settingsFile.write('bSavePower=True # saves power, at the cost of a less responsing input\n')
    else:
        settingsFile.write('#bSavePower=False # saves power, at the cost of a less responsing input\n')
    print('Finished creating "settings.py", please restart the player now.')

    settingsFile.close()
    exit(0)


# Apply settings
if playTool=="vlc":
    playCmd="vlc --qt-start-minimized --play-and-exit {}"
elif playTool=="sox":
    playCmd="play {}"
else:
    print("Unsupported playing tool.")
    print("Supported: vlc, sox.")
    exit(1)

if fmtName=="text":
    songFmtT="\"{T}\""
    songFmtTA="\"{T}\" by {A}"
    songFmtTAL="\"{T}\" by {A} on {L}"
    songFmtTL="\"{T}\" on {L}"
elif fmtName=="notext_tal":
    songFmtT="\"{T}\""
    songFmtTA="\"{T}\" - {A}"
    songFmtTAL="\"{T}\" - {A} ({L})"
    songFmtTL="\"{T}\" ({L})"
elif fmtName=="notext_atl":
    songFmtT="\"{T}\""
    songFmtTA="{A}: \"{T}\""
    songFmtTAL="{A}: \"{T}\" ({L})"
    songFmtTL="\"{T}\" ({L})"
else:
    print("Unsupported format name")
    print("Supported: text, notext_atl, notext_tal.")
    exit(1)

if bReadMeta:
    from mutagen.id3 import ID3


def scoreFunc(size):
    return round(math.sqrt(size))


### System funcs
def runAlone(fmt, arg):
    return subprocess.Popen([arg if i=="{}" else i for i in fmt.split()], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

def runGetOutput(fmt, arg):
    p=subprocess.Popen([arg if i=="{}" else i for i in fmt.split()], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return iter(p.stdout.readline, b'')

def clearTerminal():
    os.system('cls' if os.name == 'nt' else 'clear')

### Playing vars & funcs
if os.name=='nt':
    playerProcess=subprocess.Popen('call', shell=True) # no-op
else:
    playerProcess=subprocess.Popen('true') # no-op

# in case of failure we still want to stop the player.
def termPlayer():
    playerProcess.terminate()
atexit.register(termPlayer)

playQueue=[]

def isSong(filename):
    for ext in supportedTypes:
        if filename[-len(ext):]==ext:
            return True
    return False

### Classes

class PlayQueue:
    def __init__(self):
        self.content=[]
        self.cur=None
        self.bPaused=False
        self.bShow=False

    def append(self, x):
        self.content.append(x)

    def tick(self):
        if not self.bPaused and playerProcess.poll() is not None:
            self.play()
            if self.bShow:
                mode.display()

    def togglePause(self):
        if self.bPaused:
            if self.cur is None:
                self.play()
            else:
                self.resume()
        else:
            self.pause()

    def play(self):
        self.bPaused=False
        self.cur=None
        self.fill()
        if len(self.content):
            self.cur=self.content[0].desc()
            self.content[0].play()
            self.content.pop(0)
        else:
            self.bPaused=True

    def stop(self):
        self.bPaused=True
        self.cur=None
        self.fill()
        playerProcess.terminate()

    def resume(self):
        if os.name=='nt':
            return self.play()
        self.bPaused=False
        playerProcess.send_signal(signal.SIGCONT)

    def pause(self):
        if os.name=='nt':
            return self.stop()
        self.bPaused=True
        playerProcess.send_signal(signal.SIGSTOP)
        #self.stop()

    def display(self):
        if self.getSize()==0:
            return displayStartPage()

        width, height=shutil.get_terminal_size()
        txt=""
        if self.cur is not None:
            line=("# " if self.bPaused else "> ")+self.cur
            if len(line)>width:
                line=line[:width-3]+"..."
            txt+=line+"\n"
            height-=1
        for i in self.content[:height]:
            line="  "+i.desc()
            if len(line)>width:
                line=line[:width-3]+"..."
            txt+=line+"\n"
        clearTerminal()
        print(txt.strip('\n'), end="", flush=True)
        #if self.cur is not None:
        #    print("# " if self.bPaused else "> ", self.cur, sep="")
        #for i in self.content:
        #    print("  ", i.desc(), sep="")

    def getSize(self):
        return len(self.content)+int(self.cur is not None)

    def fill(self):
        while self.getSize()<100:
            if not playDir.addToQueue():
                break

class Song:
    def __init__(self, fn=None):
        self.filename=fn
        self.title=None
        self.artist=None
        self.album=None

        self.size=1
        self.gotMeta=False
        if bPreloadMeta:
            self.getMeta()

    def getMeta(self):
        if self.gotMeta:
            return
        else:
            self.gotMeta=True
        if self.filename is not None:
            # get file info
            if bReadMeta:
                try:
                    info=ID3(self.filename)
                    if "TIT2" in info:
                        self.title=info["TIT2"].text[0]
                    if "TPE1" in info:
                        self.artist=info["TPE1"].text[0]
                    if "TALB" in info:
                        self.album=info["TALB"].text[0]
                except:
                    pass

    def desc(self):
        self.getMeta()
        if self.filename is None:
            return "Error - no filename"
        elif self.title is None:
            return self.filename
        else:
            # build using best format
            if self.artist is None and self.album is None:
                fmt=songFmtT
            elif self.album is None:
                fmt=songFmtTA
            elif self.artist is None:
                fmt=songFmtTL
            else:
                fmt=songFmtTAL
            return fmt.replace("{T}", str(self.title)).replace("{A}", str(self.artist)).replace("{L}", str(self.album))

    def play(self):
        if self.filename is None:
            print("Error - no filename")
            playQueue.stop()
            exit(2)
        global playerProcess
        if playerProcess.poll() is None:
            playerProcess.terminate()
        playerProcess=runAlone(playCmd, self.filename)

    def addToQueue(self):
        playQueue.append(self)
        if not bRepeat:
            self.size=0
        return True


class Directory:
    def __init__(self, p=None):
        self.path=p
        self.content=[]
        if self.path is not None:
            for i in os.scandir(self.path):
                if i.is_dir():
                    self.content.append(Directory(i.path))
                    if self.content[-1].size==0:
                        self.content.pop()
                elif i.is_file():
                    if isSong(i.name):
                        self.content.append(Song(i.path))
        self.update()

    def append(self, x):
        self.content.append(x)
        if self.content[-1].size==0:
            self.content.pop()
        self.update()

    def update(self):
        self.size=self.calcSize()
        self.shuffler=list(range(0,len(self.content)))
        if bShuffle:
            random.shuffle(self.shuffler)

    def calcSize(self):
        return sum([i.size for i in self.content])

    def addToQueue(self): # adds a child song to queue
        if len(self.content):
            maxi=(len(self.content))//2
            tmp=[]
            for i in self.shuffler[:maxi+1]:
                for j in range(scoreFunc(self.content[i].size)):
                    tmp.append(i)
            i=random.choice(tmp)
            self.shuffler.append(self.shuffler.pop(self.shuffler.index(i)))
            result=self.content[i].addToQueue()
            if not bRepeat:
                if self.content[i].size==0:
                    self.content.pop(i)
                self.update()
            return result
        return False

### Start page

startLogo=[
    [
        '''                               <QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQ''',
        '''                               mQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQ''',
        '''                              ]QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQ''',
        '''                              QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQ''',
        '''                             ]QQQQQ@                                 ''',
        '''                             QQQQQQ'                                 ''',
        '''                            jQQQQQP                                  ''',
        '''                           .QQQQQQ(                                  ''',
        '''                           jQQQQQE     aQmw,                         ''',
        '''                          .QQQQQQ'    jQQQQQmc                       ''',
        '''                          jQQQQQF     dQQQQQQQQw,                    ''',
        '''                         _QQQQQW'     dQQQQQQQQQQgc                  ''',
        '''                         jQQQQQF      dQQQQQQQQQQQQQa,               ''',
        '''                        _QQQQQW'      dQQQQQQQQQQQQQQQg,             ''',
        '''mmmmmmmmmmw             jQQQQQf       dQQQQQQQQQQQQQQQQQma.          ''',
        '''QQQQQQQQQQQ/           _QQQQQQ`       dQQQQQQQQQQQQQQQQQQQQw,        ''',
        '''QQQQQQQQQQQm.          dQQQQQf        dQQQQQQQQQQQQQQQQQQQQQQma.     ''',
        '''?!!!!!4QQQQQL         _QQQQQ@         dQQQQQQQQQQQQQQQQQQQQQQQQQ/    ''',
        '''      -QQQQQQ,        yQQQQQ[         dQQQQQQQQQQQQQQQQQQQQQQQQQQ    ''',
        '''       ]QQQQQ6       <QQQQQ@          dQQQQQQQQQQQQQQQQQQQQQQQQQP    ''',
        '''        4QQQQQc      mQQQQQ(          dQQQQQQQQQQQQQQQQQQQQQQQ@!     ''',
        '''        +QQQQQQ     ]QQQQQ@           dQQQQQQQQQQQQQQQQQQQQWD^       ''',
        '''         4QQQQQL    mQQQQQ(           dQQQQQQQQQQQQQQQQQQW?'         ''',
        '''          QQQQQQ,  ]QQQQQE            dQQQQQQQQQQQQQQQQD"            ''',
        '''          ]WQQQQk  mQQQQQ'            dQQQQQQQQQQQQQWY'              ''',
        '''           4QQQQQc]QQQQQP             dQQQQQQQQQQQ@!                 ''',
        '''           -QQQQQQWQQQQQ'             dQQQQQQQQQP^                   ''',
        '''            ]QQQQQQQQQQF              3QQQQQQ@?                      ''',
        '''             $QQQQQQQQQ'              +QQQQP^                        ''',
        '''             )WQQQQQQQf                 !"`                          ''',
        '''              4QQQQQQW`                                              ''',
        '''              -QQQQQQf                                               '''
    ],[
        '''                       _QQQQQQQQQQQQQQQQQQQQQQQQQQQQ''',
        '''                       dQQQQQQQQQQQQQQQQQQQQQQQQQQQQ''',
        '''                      <QQQQQQQQQQQQQQQQQQQQQQQQQQQQQ''',
        '''                      dQQQW`                        ''',
        '''                     <QQQQ[                         ''',
        '''                     mQQQ@                          ''',
        '''                    ]QQQQ(   jgga,                  ''',
        '''                   .mQQQD   :WQQQQg,.               ''',
        '''                   ]QQQQ(   =QQQQQQQma,             ''',
        '''                   mQQQP    =QQQQQQQQQQw,.          ''',
        '''asasasas          jQQQQ'    =QQQQQQQQQQQQma.        ''',
        '''QQQQQQQWc        .QQQQF     =QQQQQQQQQQQQQQQw,      ''',
        '''QQQQQQQQQ,       jQQQQ'     =QQQQQQQQQQQQQQQQQma    ''',
        '''    -QQQQL      .QQQQF      =QQQQQQQQQQQQQQQQQQQk   ''',
        '''     )WQQQ/     jQQQW`      =QQQQQQQQQQQQQQQQQQQD   ''',
        '''      4QQQm.   _QQQQf       =QQQQQQQQQQQQQQQQQW?    ''',
        '''      -QQQQL   jQQQ@`       =QQQQQQQQQQQQQQWV"      ''',
        '''       ]QQQQ, _QQQQf        =QQQQQQQQQQQQ@?`        ''',
        '''        $QQQk jQQQW         =QQQQQQQQQWD"           ''',
        '''        )WQQQaQQQQ[         =QQQQQQQ@Y~             ''',
        '''         4QQQQQQQD          :QQQQQD"-               ''',
        '''         -QQQQQQQ(           4$BT^                  ''',
        '''          ]WQQQQD                                   ''',
        '''           4QQQQ(                                   '''
    ],[
        '''               <QQQQQQQQQQQQQQQQQQ''',
        '''               mQQQQQQQQQQQQQQQQQQ''',
        '''              ]WQD                ''',
        '''              mQQ(                ''',
        '''             ]QQP  jQw,.          ''',
        '''             QQQ'  WQQQma.        ''',
        '''            ]QQF   WQQQQQQw,      ''',
        '''QQQQQ[     .QQQ'   WQQQQQQQQma    ''',
        '''T??QQQ,    jQQF    WQQQQQQQQQQQw. ''',
        '''   ]WQk   .QQW`    WQQQQQQQQQQQW[ ''',
        '''    4QQc  jQQf     WQQQQQQQQQQP"  ''',
        '''    -QQQ .QQW      WQQQQQQQWT`    ''',
        '''     ]QQLjQQ[      WQQQQQ@"       ''',
        '''      $QQQQ@       $QQWT'         ''',
        '''      )QQQQ[       "T!`           ''',
        '''       4QQ@                       '''
    ],[
        '''       _QQQQQQQQQ''',
        '''       j@        ''',
        '''      _Q[_Qw,    ''',
        '''aaa   dD ]QQQga  ''',
        '''"?Q/ <Q( ]QQQQQQ/''',
        '''  4m mP  ]QQQQD" ''',
        '''  -QgQ'  )QWT`   ''',
        '''   ]WF    "      '''
    ],[
        '''    ___''',
        '''   /a. ''',
        '''\ / WQD''',
        ''' V  4' ''',
    ],[
        ''' _''',
        '''V>'''
    ]
]

startText=[
    [
        'SqrtDistributedPlayer',
        'by Victor Miquel',
        'press [h] for Help',
        'Playlist empty'
    ],[
        'SqrtDistributedPlayer, by Victor Miquel, press [h] for Help, Playlist empty'
    ],[
        'SDP, Empty, [h]'
    ]
]

def centered(txt, width):
    return "".join([" " for i in range((width-len(txt))//2)])+txt

def displayStartPage():
    width, height=shutil.get_terminal_size()
    txt=""

    if width<len(startText[2][0]): #too small
        clearTerminal()
        print("...", end="", flush=True)
        return

    iText=0
    if height<8+1+4: # text-only, 1 line
        iText=1
    while len(startText[iText][0])>width:
        iText+=1

    iLogo=0
    height-=len(startText[iText])

    while iLogo<len(startLogo) and (len(startLogo[iLogo])>height-1 or len(startLogo[iLogo][0])>width):
        iLogo+=1

    if iLogo!=len(startLogo):
        height-=len(startLogo[iLogo])+1

    for i in range(height//2):
        txt+='\n'
    height-=height//2

    if iLogo!=len(startLogo):
        for line in startLogo[iLogo]:
            txt+=centered(line, width)+'\n'
        txt+='\n'

    iLine=0
    for line in startText[iText]:
        iLine+=1
        if iLine<len(startText[iText]):
            txt+=centered(line, width)+'\n'
        else:
            txt+=centered(line, width)

    for i in range(height):
        txt+='\n'

    clearTerminal()
    print(txt, end="", flush=True)

### UI Classes


class ModePlayqueue:
    def __init__(self):
        playQueue.bShow=True
        self.display()

    def __del__(self):
        playQueue.bShow=False

    def input(self, c):
        global newMode
        if c=='h':
            newMode=ModeHelp
        if c==' ':
            playQueue.togglePause()
            self.display()
        if c=='a':
            newMode=ModeAdd
            addMode_state=ModeAdd_state()
        if c=='n':
            playQueue.play()
            self.display()
        if c=='q':
            playQueue.stop()
            print("\nQuit")
            exit(0)
        if c=='s':
            playQueue.stop()
            self.display()

    def display(self):
        playQueue.display()


class ModeAdd_state:
    def __init__(self):
        self.cd(rootPath)
        self.addList=[]

    def cd(self, d):
        self.dir=d
        self.dirList=list(os.scandir(self.dir))
        self.dirList.sort(key=lambda x: x.name)
        self.idLen=math.ceil(math.log10(len(self.dirList)))
        self.view=0
        self.cursor=0
        self.sId=""

    def getCursorPath(self):
        return self.dirList[self.cursor].path

    def isSelected(self, path=None):
        if path is None:
            path=self.getCursorPath()
        return path in self.addList

    def select(self, path=None):
        if path is None:
            path=self.getCursorPath()
        if not self.isSelected(path):
            self.addList.append(path)

    def deselect(self, path=None):
        if path is None:
            path=self.getCursorPath()
        if self.isSelected(path):
            self.addList.remove(path)

    def toggleSelect(self, path=None):
        if self.isSelected(path):
            self.deselect(path)
        else:
            self.select(path)

    def up(self):
        if self.cursor>0:
            self.cursor-=1

    def down(self):
        if self.cursor<len(self.dirList)-1:
            self.cursor+=1

    def typeNum(self, c):
        self.sId+=c
        if len(self.sId)==self.idLen:
            self.cursor=int(self.sId)
            self.toggleSelect()
            self.sId=""
        else:
            self.cursor=int(self.sId)*(10**(self.idLen-len(self.sId)))
            self.view=self.cursor

    def display(self):
        width, height=shutil.get_terminal_size()
        txt=""

        # update view
        self.view=min(self.view, max(0, len(self.dirList)-height)) # limit max view pos
        self.view=min(self.view, self.cursor)                      # make sure we see cursor (go up)
        self.view=max(self.view, self.cursor-height+1)             # make sure we see cursor (go down)

        for i in range(self.view, min(self.view+height, len(self.dirList))):
            txt+='+' if self.dirList[i].path in self.addList else ' '
            txt+=format(i, '0'+str(self.idLen)+'d')
            txt+='>' if i==self.cursor else ' '
            txt+=self.dirList[i].name
            if i!=self.view+height-1:
                txt+='\n'

        clearTerminal()
        print(txt, end="", flush=True)

addMode_state=ModeAdd_state()

class ModeAdd:
    def __init__(self):
        self.display()

    def input(self, c):
        global newMode
        if c=='\x1b': # ESC
            newMode=ModePlayqueue
        elif c=='\x1b[A' or c=='\xe0H': # up arrow
            addMode_state.up()
            addMode_state.display()
        elif c=='\x1b[B' or c=='\xe0P': # down arrow
            addMode_state.down()
            addMode_state.display()
        elif c==' ':
            addMode_state.toggleSelect()
            addMode_state.display()
        elif len(c)==1 and '0'<=c<='9':
            addMode_state.typeNum(c)
            addMode_state.display()
        elif c=='a':
            addMode_state.add()
            newMode=ModePlayqueue
        elif c=='q':
            playQueue.stop()
            print("\nQuit")
            exit(0)

    def display(self):
        return addMode_state.display()

class ModeHelp:
    def __init__(self):
        self.display()

    def input(self, c):
        global newMode
        newMode=lastMode

    def display(self):
        clearTerminal()
        if lastMode==ModePlayqueue:
            print('''\
### Help - Playqueue ###
Playqueue:
- [Space]   | Play/Pause (Pause=Stop when not available)
- [n] Next  | Skip to next song
- [Q] Quit  | Stop and quit SDP
- [s] Stop  | Stop the music
''')
        else:
            print('### UNKWOWN HELP ###')

        print('''\
Modes:
- [h] Help  | Display help page for the current mode
- [a] Add   | Add a directory/file to the playlist
- [q] Queue | Display playqueue
### Press any key to continue ###''')




### UI funcs



kb=keyboard.KBHit()


playDir=Directory()
#playDir.append(Directory(rootPath))

playQueue=PlayQueue()

mode=ModePlayqueue()
newMode=None
lastMode=None

lastSize=shutil.get_terminal_size()

playQueue.tick()

n=0

while True:
    if lastSize!=shutil.get_terminal_size():
        lastSize=shutil.get_terminal_size()
        mode.display()
    if kb.kbhit():
        n=0
        mode.input(kb.getch())
        if newMode is not None:
            lastMode=type(mode)
            mode=newMode()
            newMode=None
    playQueue.tick()

    n+=1
    if n<0.2*100: # 0.2s@100Hz
        time.sleep(0.01)
    elif n<0.2*100+2*10: # 2s@10Hz
        time.sleep(0.1)
    else: # 1Hz | 10Hz
        time.sleep(1 if bSavePower else 0.1)
