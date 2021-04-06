import os
import sys
import shutil
import atexit
import time
import subprocess
import random
import math
import signal
import select

import keyboard
import termfmt as tfmt


fmtName="notext_tal"
supportedTypes=[".mp3", ".wav", ".wma", ".ogg"]

bReadMeta=False
bPreloadMeta=False

bShuffle=True
bRepeat=True

bSavePower=False

bNoAirButton=False

miniSound=False

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

#bNoAirButton=False
''')

    if False:# 'termux' in sys.prefix:
        settingsFile.write('bSavePower=True # saves power, at the cost of a less responsing input\n')
    else:
        settingsFile.write('#bSavePower=False # saves power, at the cost of a less responsing input\n')
    print('Finished creating "settings.py", please restart the player now.')

    settingsFile.close()
    exit(0)


# Apply settings

import airbutton as ab

if rootPath[-1] in ['/', '\\']: rootPath=rootPath[:-1]

if playTool=="vlc":
    playCmd="vlc --qt-start-minimized --play-and-exit {}"
elif playTool=="sox":
    if miniSound:
        playCmd="play -v 0.05 {}"
    else:
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
    #return round(math.sqrt(size))
    #return round(math.sqrt(2*size-3/4))
    return round(math.sqrt(2*size))


### System funcs
def runAlone(fmt, arg=""):
    return subprocess.Popen([arg if i=="{}" else i for i in fmt.split()], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

def runGetOutput(fmt, arg):
    p=subprocess.Popen([arg if i=="{}" else i for i in fmt.split()], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return iter(p.stdout.readline, b'')

def clearTerminal():
    os.system('cls' if os.name == 'nt' else 'clear')

def txt2sec(txt):
    sec=0.
    for part in txt.split(':'):
        try:
            sec=sec*60+float(part)
        except:
            sec=sec*60
    return sec

def sec2txt(sec):
    txt=str(int(sec//3600)).zfill(2)+":"
    sec=sec%3600
    txt+=str(int(sec//60)).zfill(2)+":"
    sec=sec%60
    txt+=str(int(sec//1)).zfill(2)+"."
    sec=sec%1
    txt+=str(int(sec//0.01)).zfill(2)
    return txt

### Playing vars & funcs
if os.name=='nt':
    playerProcess=subprocess.Popen('call', shell=True) # no-op
else:
    playerProcess=subprocess.Popen('true') # no-op

# in case of failure we still want to stop the player.
def killPlayer():
    playerProcess.kill()
atexit.register(killPlayer)

def isSong(filename):
    if filename is None: return False

    for ext in supportedTypes:
        if filename[-len(ext):]==ext:
            return True
    return False

def parent(path):
    sep='\\' if os.name=='nt' else '/'
    i=-1
    for i in range(len(path)-2,-2,-1): # end=-1 : if sep isn't encountered, i==-1
        if path[i]==sep:
            break
    return path[0:i+1]

def cutPath(path):
    sep='\\' if os.name=='nt' else '/'
    i=-1
    for i in range(len(path)-2,-2,-1): # end=-1 : if sep isn't encountered, i==-1
        if path[i]==sep:
            break
    if path[-1]==sep: return path[i+1:-1]
    else: return path[i+1:]

def GCP(a, b): # Greatest Common Parent
    if isSong(a): a=parent(a)
    if isSong(b): b=parent(b)

    if a is None:
        if b is None:
            return ''
        else:
            return b
    elif b is None:
        return a

    if a[0]!=b[0]:
        return ''
    if a==b:
        return a

    sep='\\' if os.name=='nt' else '/'
    if len(a)<len(b):
        if a[-1]!=sep: a+=sep
    else:
        if b[-1]!=sep: b+=sep

    print(1)
    while a!=b:
        if len(a)>len(b):
            a=parent(a)
        else:
            b=parent(b)
        print(a,b)
    print(2)
    return a

### Classes

class Playlist:
    def __init__(self):
        self.include=[]
        self.exclude=[]

    def save(self, name):
        if name[-4:]!=".lst": name+=".lst"
        f=open(name, 'w')
        f.writelines("+%s\n" % i for i in self.include)
        f.writelines("-%s\n" % i for i in self.exclude)
        f.close()

    def load(self, name):
        if name[-4:]!=".lst": name+=".lst"
        self.include=[]
        self.exclude=[]
        with open(name, 'r') as f:
            for line in f:
                if line[0]=='+':
                    self.include.append(line[1:].strip())
                elif line[0]=='-':
                    self.exclude.append(line[1:].strip())

    def rootDir(self):
        ret=None
        for p in self.include:
            ret=GCP(ret, p)
        return ret

    def status(self, path):
        sep='\\' if os.name=='nt' else '/'
        manualAdd=False
        addCause=None
        manualRemove=False
        removeCause=None
        partial=False

        self.include.sort()
        self.exclude.sort()

        for i in self.include:
            if path==i:
                manualAdd=True
            elif path.startswith(i+sep):
                addCause=i
            elif i.startswith(path+sep):
                partial=True

        for i in self.exclude:
            if path==i:
                manualRemove=True
            elif path.startswith(i+sep):
                removeCause=i
            elif i.startswith(path+sep):
                partial=True

        if manualAdd:
            if partial: return '+['
            else:       return '+ '
        elif manualRemove:
            if partial: return '-['
            else:       return '- '
        elif (addCause is not None) and ((removeCause is None) or (removeCause<addCause)):
            if partial: return '.['
            else:       return '. '
        elif (removeCause is not None) and ((addCause is None) or (removeCause>addCause)):
            if partial: return ']['
            else:       return '] '
        else:
            if partial: return ' ['
            else:       return '  '

    def clear(self, path):
        sep='\\' if os.name=='nt' else '/'
        i=0
        while i<len(self.include):
            if self.include[i]==path:
                self.include.pop(i)
            elif self.include[i].startswith(path+sep):
                self.include.pop(i)
            else:
                i+=1
        i=0
        while i<len(self.exclude):
            if self.exclude[i]==path:
                self.exclude.pop(i)
            elif self.exclude[i].startswith(path+sep):
                self.exclude.pop(i)
            else:
                i+=1

    def add(self, path):
        self.clear(path)
        if self.status(path) in ['] ', '  ']:
            self.include.append(path)

    def remove(self, path):
        self.clear(path)
        if self.status(path)=='. ':
            self.exclude.append(path)

class PlayQueue:
    def __init__(self):
        self.content=[]
        self.cur=None
        self.bPaused=False
        self.bShow=False
        self.timeSec=None
        self.lenSec=None
        self.resumeSeek=False
        self.ABRepeat=False
        self.repA=None
        self.repB=None

    def __del__(self):
        playerProcess.terminate()

    def append(self, x):
        self.content.append(x)

    def tick(self):
        if not self.bPaused and playerProcess.poll() is not None: # song ended
            if self.ABRepeat:
                self.seekAbs(self.repA or 0)
            else:
                self.play()

            if self.bShow:
                mode.display()
        if not self.bPaused and playerProcess.poll() is None:
            while select.select([playerProcess.stdout], [], [], 0)[0] != []:
                line=playerProcess.stdout.readline().strip()
                if playTool=="sox":
                    if "Duration: " in line:
                        k=line.index("Duration: ")+10
                        self.lenSec=txt2sec(line[k:k+11])

                    if line[0:1]=='I':
                        i=0
                        while line[i]!='%' and i<len(line):
                            i+=1
                        if i!=len(line):
                            self.timeSec=txt2sec(line[i+2:i+13])
                            if self.ABRepeat and self.repB is not None and self.timeSec>self.repB:
                                self.seekAbs(self.repA or 0)

                            if type(mode)==ModePlayqueue:
                                self.displayStatus()


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
        self.timeSec=None
        self.lenSec=None
        self.repA=None
        self.repB=None
        self.cur=None
        self.fill()
        if len(self.content):
            self.cur=self.content[0]
            self.cur.play()
            self.content.pop(0)
        else:
            self.bPaused=True

    def stop(self):
        self.bPaused=True
        self.timeSec=None
        self.lenSec=None
        self.repA=None
        self.repB=None
        self.cur=None
        self.fill()
        if os.name!='nt':
            playerProcess.send_signal(signal.SIGCONT)
        playerProcess.terminate()

    def seekAbs(self, newTime, pause=False):
        if playTool!="sox":
            return
        if pause:
            self.pause()
        if self.timeSec is not None:
            self.resumeSeek=True
            self.timeSec=newTime
            if self.timeSec<0:
                self.timeSec=0
            elif self.lenSec is not None and self.timeSec>self.lenSec:
                self.timeSec=self.lenSec

            if not self.bPaused:
                self.resume()

            if type(mode)==ModePlayqueue:
                self.displayStatus()

    def seekRel(self, delta, pause=True):
        if self.timeSec is not None:
            self.seekAbs(self.timeSec+delta, pause)

    def resume(self):
        if os.name=='nt':
            return self.play()
        if self.resumeSeek and playTool=="sox" and self.timeSec is not None:
            self.bPaused=False
            self.resumeSeek=False
            self.cur.play(self.timeSec)
        else:
            self.bPaused=False
            playerProcess.send_signal(signal.SIGCONT)

    def pause(self):
        if os.name=='nt':
            return self.stop()
        self.bPaused=True
        playerProcess.send_signal(signal.SIGSTOP)
        #self.stop()

    def setRepA(self):
        if (self.lenSec is not None):
            self.repA=self.timeSec
            if (self.repA or 0)>=(self.repB or self.lenSec):
                self.repB=None
            self.ABRepeat=True
            if type(mode)==ModePlayqueue:
                self.displayStatus()

    def setRepB(self):
        if (self.lenSec is not None):
            self.repB=self.timeSec
            if (self.repA or 0)>=(self.repB or self.lenSec):
                self.repA=None
            self.ABRepeat=True
            if type(mode)==ModePlayqueue:
                self.displayStatus()

    def displayStatus(self):
        if (self.timeSec is not None) and (self.lenSec is not None):
            width, height=shutil.get_terminal_size()
            barLen=width-24
            bar=""
            for k in range(barLen):
                if self.ABRepeat and (k/barLen)<=((self.repA or 0)/self.lenSec)<=((k+1)/barLen):
                    bar+="["
                elif self.ABRepeat and (k/barLen)<=((self.repB or self.lenSec)/self.lenSec)<=((k+1)/barLen):
                    bar+="]"
                elif ((self.repA if self.ABRepeat and self.repA else 0)/self.lenSec)<=(k/barLen)<=(self.timeSec/self.lenSec):
                    bar+="#"
                else:
                    bar+="-"

            print("\r"+sec2txt(self.timeSec)+" "+bar+" "+sec2txt(self.lenSec), end="")

    def display(self):
        if self.getSize()==0:
            return displayStartPage()

        width, height=shutil.get_terminal_size()
        height-=1
        txt=""
        if self.cur is not None:
            line=("# " if self.bPaused else "> ")+self.cur.desc()
            if len(line)>width:
                line=line[:width-3]+"..."
            txt+=line+"\n"
            height-=1
        for i in self.content[:height]:
            line="  "+i.desc()
            if len(line)>width:
                line=line[:width-3]+"..."
            txt+=line+"\n"
        if len(self.content)<height:
            txt+="\n"*(height-len(self.content))
        clearTerminal()
        print(txt, end="", flush=True)
        #if self.cur is not None:
        #    print("# " if self.bPaused else "> ", self.cur, sep="")
        #for i in self.content:
        #    print("  ", i.desc(), sep="")
        self.displayStatus()

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

    def play(self, seek=0):
        if self.filename is None:
            print("Error - no filename")
            playQueue.stop()
            exit(2)
        global playerProcess
        if playerProcess.poll() is None:
            playerProcess.terminate()
        if playTool=="sox" and seek!=0:
            playerProcess=runAlone(playCmd+" trim "+str(seek), self.filename)
        else:
            playerProcess=runAlone(playCmd, self.filename)

    def addToQueue(self):
        playQueue.append(self)
        if not bRepeat:
            self.size=0
        return True


class Directory:
    def __init__(self, p=None, full=True):
        self.path=p
        self.content=[]
        if self.path is not None:
            for i in os.scandir(self.path):
                status=playlist.status(i.path)
                if full or (status[0] in ['+', '.']) or status[1]=='[':
                    if i.is_dir():
                        self.content.append(Directory(i.path, full or status[1]==' '))
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
        global newMode, playQueue, miniSound, playTool, playCmd
        if c=='h':
            newMode=ModeHelp
        elif c==' ':
            playQueue.togglePause()
            self.display()
        elif c=='o' or c=='p':
            newMode=ModeAdd
        elif c=='c':
            global playDir
            global addMode_state
            addMode_state=ModeAdd_state()
            playDir=Directory()
            playQueue=PlayQueue()
            self.display()
        elif c=='l':
            newMode=ModeLoad
        elif c=='m' and playTool=="sox":
            miniSound=not miniSound
            if miniSound:
                playCmd="play -v 0.05 {}"
            else:
                playCmd="play {}"
            playQueue.seekRel(0, False)
        elif c=='n':
            playQueue.play()
            self.display()
        elif c=='q':
            playQueue.stop()
            print("\nQuit")
            exit(0)
        elif c=='s':
            playQueue.stop()
            self.display()
        elif c=='g':
            newMode=ModeSeek
        elif c=='\x1b[C' or c=='\xe0M': # right arrow
            playQueue.seekRel(+5, False)
        elif c=='\x1b[D' or c=='\xe0K': # left arrow
            playQueue.seekRel(-5, False)
        elif c=='r':
            playQueue.ABRepeat=not playQueue.ABRepeat
        elif c=='[':
            playQueue.setRepA()
        elif c==']':
            playQueue.setRepB()

    def display(self):
        playQueue.display()


class ModeAdd_state:
    def __init__(self):
        self.cd(rootPath)
        self.addList=[]

    def add(self, doClear=True):
        global playQueue
        global playDir
        if doClear: playQueue.stop()
        playDir=Directory()
        playDir.append(Directory(playlist.rootDir(), False))
        if doClear:
            playQueue=PlayQueue()
        else:
            playQueue.fill()

    def cd(self, d):
        if d == 1:
            if self.dirList[self.cursor].is_dir():
                self.dir=self.getCursorPath()
        elif d == -1:
            old=cutPath(self.dir)
            self.dir=parent(self.dir)
        else:
            self.dir=d

        self.dirList=list(os.scandir(self.dir))
        self.dirList.sort(key=lambda x: x.name)
        self.idLen=math.ceil(math.log10(len(self.dirList))) if self.dirList else 0
        self.view=0
        self.sId=""
        self.cursor=0
        if d == -1:
            self.find(old)

    def getCursorPath(self):
        return self.dirList[self.cursor].path

    def markAdd(self, path=None):
        if path is None:
            path=self.getCursorPath()
        playlist.add(path)

    def markRemove(self, path=None):
        if path is None:
            path=self.getCursorPath()
        playlist.remove(path)

    def unmark(self, path=None):
        if path is None:
            path=self.getCursorPath()
        playlist.clear(path)

    def toggleMark(self, path=None):
        if path is None:
            path=self.getCursorPath()
        if playlist.status(path)[0] in ['+', '-']:
            self.unmark(path)
        else:
            self.markAdd(path)

    def up(self):
        if self.cursor>0:
            self.cursor-=1
            return True
        else:
            return False

    def down(self):
        if self.cursor<len(self.dirList)-1:
            self.cursor+=1
            return True
        else:
            return False

    def typeNum(self, c):
        if self.idLen==0: return

        if self.sId=='' and int(c)*(10**(self.idLen-1))>=len(self.dirList):
            self.typeNum('0')
        self.sId+=c
        iId=int(self.sId)*(10**(self.idLen-len(self.sId)))
        if iId>=len(self.dirList):
            self.sId=''
            iId=len(self.dirList)-1

        self.cursor=iId+(10**(self.idLen-len(self.sId)))-1
        self.updateView()
        self.cursor=iId

        if len(self.sId)==self.idLen:
            self.sId=''

    def find(self, txt):
        self.cursor=0
        while txt>cutPath(self.getCursorPath()):
            if not self.down():
                self.cursor=0
                return

    def back(self):
        if len(self.sId):
            self.sId=self.sId[:-1]
        else:
            self.cd(-1)

    def updateView(self):
        width, height=shutil.get_terminal_size()
        self.view=min(self.view, max(0, len(self.dirList)-height)) # limit max view pos
        self.view=min(self.view, self.cursor)                      # make sure we see cursor (go up)
        self.view=max(self.view, self.cursor-height+1)             # make sure we see cursor (go down)

    def display(self):
        width, height=shutil.get_terminal_size()
        txt=""

        self.updateView()

        for i in range(self.view, min(self.view+height, len(self.dirList))):
            if i==self.cursor: txt+=tfmt.inverse
            status=playlist.status(self.dirList[i].path)
            if   status[0]=='+': txt+=tfmt.fgLGreen
            elif status[0]=='-': txt+=tfmt.fgLRed
            elif status[0]=='.': txt+=tfmt.fgDGreen
            elif status[0]==']': txt+=tfmt.fgDRed
            elif status[1]=='[': txt+=tfmt.fgLYellow

            curSId=str(i).zfill(self.idLen)
            if curSId.startswith(self.sId):
                curSId=tfmt.underline+self.sId+tfmt.resetUnderline+curSId[len(self.sId):]
            txt+=curSId

            txt+=status


            if self.dirList[i].is_dir(): txt+=tfmt.bgColorRGB(64,64,64)
            elif not isSong(self.dirList[i].name): txt+=tfmt.dim

            name=self.dirList[i].name
            if len(name)>width-2-self.idLen:
                w=width-2-self.idLen
                name=name[:w//2-1]+"..."+name[(-w+4)//2:]

            txt+=name
            if i!=self.view+height-1: txt+='\n'
            txt+=tfmt.resetAll

        clearTerminal()
        print(txt, end="", flush=True)

addMode_state=ModeAdd_state()

class ModeAdd:
    def __init__(self):
        self.display()

    def input(self, c):
        global newMode
        global addMode_state
        global bRepeat
        if c=='h':
            newMode=ModeHelp
        if c=='\x1b': # ESC
            newMode=ModePlayqueue
        elif c=='\x1b[A' or c=='\xe0H': # up arrow
            addMode_state.up()
            addMode_state.display()
        elif c=='\x1b[B' or c=='\xe0P': # down arrow
            addMode_state.down()
            addMode_state.display()
        elif c=='\x1b[C' or c=='\xe0M': # right arrow
            addMode_state.cd(1)
            addMode_state.display()
        elif c=='\x1b[D' or c=='\xe0K': # left arrow
            addMode_state.cd(-1)
            addMode_state.display()
        elif c=='\x7f': # Back
            addMode_state.back()
            addMode_state.display()
        elif c=='\n': # enter
            addMode_state.cd(1)
            addMode_state.display()
        elif c==' ':
            addMode_state.toggleMark()
            addMode_state.display()
        elif len(c)==1 and '0'<=c<='9':
            addMode_state.typeNum(c)
            addMode_state.display()
        elif c=='a':
            addMode_state.toggleMark()
            addMode_state.display()
        elif c=='d':
            addMode_state.markRemove()
            addMode_state.display()
        elif c=='l':
            newMode=ModeLoad
        elif c=='o':
            doClear=bRepeat # if already in no repeat mode, append songs
            bRepeat=False
            addMode_state.add(doClear)
            newMode=ModePlayqueue
        elif c=='p':
            bRepeat=True
            addMode_state.add()
            newMode=ModePlayqueue
        elif c=='q':
            playQueue.stop()
            print("\nQuit")
            exit(0)
        elif c=='s':
            newMode=ModeSave

    def display(self):
        return addMode_state.display()

class ModeSave:
    def __init__(self):
        self.name=""
        self.display()

    def input(self, c):
        global newMode
        if c=='\x7f': # Back
            self.name=self.name[:-1]
            self.display()
        elif c=='\n' and len(self.name)!=0:
            playlist.save(self.name)
            newMode=ModeAdd
        elif c=='\x1b': # ESC
            newMode=ModeAdd
        elif 'a'<=c<='z' or 'A'<=c<='Z' or '0'<=c<='9' or c in ['.']:
            self.name+=c
            self.display()

    def display(self):
        clearTerminal()
        print("Enter playlist name and press [Enter]\n>"+self.name, end="", flush=True)

class ModeLoad:
    def __init__(self):
        self.name=""
        self.view=0
        self.cursor=0
        self.sId=""
        self.saveList=[]
        for f in os.scandir():
            if f.name.endswith(".lst"):
                self.saveList.append(f.name)
        self.saveList.sort()
        self.idLen=math.ceil(math.log10(len(self.saveList))) if self.saveList else 0
        self.display()

    def typeNum(self, c):
        if self.idLen==0: return

        self.sId+=c
        iId=int(self.sId)*(10**(self.idLen-len(self.sId)))
        if iId>=len(self.saveList):
            self.sId=''
            iId=len(self.saveList)-1

        self.cursor=iId+(10**(self.idLen-len(self.sId)))-1
        self.updateView()
        self.cursor=iId

        if len(self.sId)==self.idLen:
            self.load()

    def updateView(self):
        width, height=shutil.get_terminal_size()
        self.view=min(self.view, max(0, len(self.saveList)-height)) # limit max view pos
        self.view=min(self.view, self.cursor)                      # make sure we see cursor (go up)
        self.view=max(self.view, self.cursor-height+1)             # make sure we see cursor (go down)

    def load(self):
        global newMode
        global addMode_state
        playlist.load(self.saveList[self.cursor])
        addMode_state=ModeAdd_state()
        if lastMode==ModePlayqueue:
            addMode_state.add()
        newMode=lastMode

    def input(self, c):
        global newMode
        global addMode_state
        if c=='\x7f': # Back
            self.sId=self.sId[:-1]
            self.display()
        elif c=='\x1b': # ESC
            newMode=ModeAdd
        elif len(c)==1 and '0'<=c<='9':
            self.typeNum(c)
            self.display()
        elif 'a'<=c<='z' or 'A'<=c<='Z' or '0'<=c<='9' or c in ['.']:
            self.name+=c
            self.display()

    def display(self):
        width, height=shutil.get_terminal_size()
        self.updateView()

        txt=""
        for i in range(self.view, min(self.view+height, len(self.saveList))):
            curSId=str(i).zfill(self.idLen)
            if curSId.startswith(self.sId):
                curSId=tfmt.underline+self.sId+tfmt.resetUnderline+curSId[len(self.sId):]
            txt+=curSId+" "+self.saveList[i]
            if i!=self.view+height-1: txt+='\n'
        clearTerminal()
        print(txt, end="", flush=True)

class ModeSeek:
    def __init__(self):
        self.timeTxt=""
        width, height=shutil.get_terminal_size()
        print("\r"+" "*(width), end="")
        self.display()

    def input(self, c):
        global newMode
        if c=='\x7f': # Back
            self.timeTxt=self.timeTxt[:-1]
            self.display()
        elif c=='\n' and len(self.timeTxt)!=0:
            if self.timeTxt[0] in ['+','-']:
                playQueue.seekRel(txt2sec(self.timeTxt), False)
            else:
                playQueue.seekAbs(txt2sec(self.timeTxt))
            newMode=ModePlayqueue
        elif c=='\x1b': # ESC
            newMode=ModePlayqueue
        elif '0'<=c<='9' or c in ['.',':','+','-']:
            self.timeTxt+=c
            self.display()

    def display(self):
        print("\rgoto: >"+self.timeTxt, end="", flush=True)

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
- [h] Help     | Display help page for the current mode.
- [Space]      | Play/Pause (Pause=Stop when not available).
- [p] Playlist | Edit the playlist.
- [o] Once     | Alias for [p].
- [c] Clear    | Clear the playlist.
- [m] Mini     | Toggle low volume. (sox)
- [n] Next     | Skip to next song.
- [q] Quit     | Quit SDP.
- [s] Stop     | Stop the music.
- [g] Goto     | Seek to a given time. (sox)
Goto examples:  0  132.5  00:00:01:11.2  2:  1::  +12  -1.5
- [Left]       | -5 sec. (sox)
- [Right]      | +5 sec. (sox)
- [r]          | Toggle repeat. (sox)
- [Brackets]   | Set repeat points. (sox)
### Press any key to continue ###''')
        elif lastMode==ModeAdd:
            print('''\
### Help - Add ###
- [h] Help  | Display help page for the current mode.
- [Esc]     | Cancel.
- [Up/Down] | Change selected item.
- [Back]    | Erase/parent directory.
- [Left]    | Parent directory.
- [Enter]   | Enter selected directory.
- [Right]   | Enter selected directory.
- [Number]  | Select/Deselect corresponding item.
- [a/Space] | Mark added/unmark.
- [d/Del]   | Mark removed.
- [l] Load  | Load saved playlist.
- [p] Apply | Apply changes and loop play.
- [o] Once  | Apply changes and play once.
- [q] Quit  | Quit SDP.
- [s] Save  | Save playlist.
### Press any key to continue ###''')




### UI funcs



kb=keyboard.KBHit()


playDir=Directory()
#playDir.append(Directory(rootPath))

playlist=Playlist()
playQueue=PlayQueue()
if not bNoAirButton:
    airButton=ab.AirButton()

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
    if not bNoAirButton:
        for i in airButton.tick():
            if i==1:
                mode.input('n')
    playQueue.tick()

    n+=1
    if n<0.2*100: # 0.2s@100Hz
        time.sleep(0.01)
    elif n<0.2*100+2*10: # 2s@10Hz
        time.sleep(0.1)
    else: # 1Hz | 10Hz
        time.sleep(1 if bSavePower else 0.1)
