import subprocess
import atexit
import queue
import select
import sys

if 'termux' in sys.prefix:

    class AirButton:
        def __init__(self):
            self.process=subprocess.Popen(['termux-sensor','-s','prox','-d','100'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            atexit.register(self.process.terminate)
            self.pushCount=0
            self.releaseCount=0
            self.lastPut=0
            self.lastGet=0
            self.queue=queue.Queue()
            for i in range(20):
                self.queue.put(0)

        def tick(self):
            result=[]
            while select.select([self.process.stdout], [], [], 0)[0] != []:
                line=self.process.stdout.readline().strip()
                if '0'<=line<='9':
                    curGet=self.queue.get()
                    if self.lastGet==0 and curGet==1:
                        self.pushCount-=1
                    elif self.lastGet==1 and curGet==0:
                        self.releaseCount-=1

                    curPut=0
                    if line=='0':
                        curPut=1

                    if self.lastPut==0 and curPut==1:
                        self.pushCount+=1
                    elif self.lastPut==1 and curPut==0:
                        self.releaseCount+=1
                        if self.releaseCount==self.pushCount:
                            result.append(self.releaseCount)

                    self.queue.put(curPut)
                    self.lastGet=curGet
                    self.lastPut=curPut

            return result

else:
    class AirButton:
        def tick(self):
            return []
