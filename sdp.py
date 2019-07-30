import os
import shutil
import time
import subprocess
import random
import math
import signal

from kb import*

playTool="sox"
infoTool="none"
fmtName="notext_tal"
supportedTypes=[".mp3"]

bShuffle=True
bRepeat=True

preloadInfo=False

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

    settingsFile.write('playTool="'+input("Which of these players do you want to use/is installed on your system? [vlc/sox] ")+'"\n')

    answer=None
    try:
        import mutagen as importTest
        settingsFile.write('infoTool="mutagen"\n')
    except:
        print("Mutagen (used to display titles, artists and albums) is not installed.")
        while answer not in ['a','m','n']:
            answer=input("Do you want to :\n- install Automatically (with \"pip install mutagen\") [a]\n- install Manually [m]\n- Not use it [n]\n- if you don't know, use [a].\n? ")
        if answer=='a':
            os.system("pip install mutagen")

        if answer=='n':
            settingsFile.write('infoTool="none"\n')
        else:
            settingsFile.write('infoTool="mutagen"\n')

    settingsFile.write('''\
#fmtName="notext_tal"
#supportedTypes=[".mp3"]

#bShuffle=True
#bRepeat=True

#preloadInfo=False
''')
    print('Finished creating "settings.py", please restart the player now.')
    if answer=='m':
        print("(don't forget to install mutagen before doing so...)")

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

if infoTool=="mutagen":
    from mutagen.id3 import ID3
elif infoTool!="none":
    print("Unsupported metadata listing tool")
    print("Supported: none, mutagen.")
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
playerProcess=subprocess.Popen("true")

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

    def stop(self):
        self.bPaused=True
        self.cur=None
        self.fill()
        playerProcess.terminate()

    def resume(self):
        self.bPaused=False
        playerProcess.send_signal(signal.SIGCONT)

    def pause(self):
        self.bPaused=True
        playerProcess.send_signal(signal.SIGSTOP)
        #self.stop()

    def display(self):
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
        print(txt.strip(), end="", flush=True)
        #if self.cur is not None:
        #    print("# " if self.bPaused else "> ", self.cur, sep="")
        #for i in self.content:
        #    print("  ", i.desc(), sep="")

    def getSize(self):
        return len(self.content)+int(self.cur is not None)

    def fill(self):
        while self.getSize()<100:
            if not rootDir.addToQueue():
                break

class Song:
    def __init__(self, fn=None):
        self.filename=fn
        self.title=None
        self.artist=None
        self.album=None

        self.size=1
        self.gotInfo=False
        if preloadInfo:
            self.getInfo()

    def getInfo(self):
        if self.gotInfo:
            return
        else:
            self.gotInfo=True
        if self.filename is not None:
            # get file info
            if infoTool=="mutagen":
                try:
                    info=ID3(self.filename)
                    if "TIT2" in info:
                        self.title=info["TIT2"].text[0]
                    if "TPE1" in info:
                        self.artist=info["TPE1"].text[0]
                    if "TALB" in info:
                        self.album=info["TALB"].text[0]
                except:
                    None

    def desc(self):
        self.getInfo()
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
            print("loading \"", self.path, "\"...", sep="")
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

### Commands-with-display Classes

class ModePlaylist:
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


class ModeHelp:
    def __init__(self):
        self.display()

    def input(self, c):
        global newMode
        newMode=ModePlaylist

    def display(self):
        clearTerminal()
        print('''\
Help:
- Help    - Display this help page
- <Space> - Play/Pause (Pause=Stop when not available)
- Next    - Skip to next song
- Quit    - Stop and quit SDP
- Stop    - Stop the music
### Press any key to continue ###''')
### UI funcs



kb=KBHit()


rootDir=Directory()
#rootDir.append(Directory("/home/victor/Music/music/SomeRock/Lions in the street/"))
#rootDir.append(Directory("/home/victor/Music/music/SomeRock/Weezer/"))
rootDir.append(Directory(rootPath))

playQueue=PlayQueue()

mode=ModePlaylist()
newMode=None

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
            mode=newMode()
            newMode=None
    playQueue.tick()

    n+=1
    if n<0.2*100: # 0.2s@100Hz
        time.sleep(0.01)
    elif n<0.2*100+2*10: # 2s@10Hz
        time.sleep(0.1)
    else: # 1Hz
        time.sleep(1)
