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
            self.pushTime=0
            self.last=0

        def tick(self):
            result=[]
            while select.select([self.process.stdout], [], [], 0)[0] != []:
                line=self.process.stdout.readline().strip()
                if '0'<=line<='9':
                    self.pushTime+=1

                    cur=0
                    if line=='0':
                        cur=1

                    if self.last==0 and cur==1:
                        self.pushTime=0
                    elif self.last==1 and cur==0:
                        if self.pushTime<10:
                            result.append(1)
                    self.last=cur

            return result

else:
    class AirButton:
        def tick(self):
            return []
