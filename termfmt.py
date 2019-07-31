import os
if os.name=='nt':
    os.system('color') # enables coloring

resetAll='\033[0m'
resetIntensity='\033[22m'
resetUnderline='\033[24m'
resetBlink='\033[25m'
resetInverse='\033[27m'
resetFg='\033[39m'
resetBg='\033[49m'

bold='\033[1m'
dim='\033[2m'
underline='\033[4m'
blink='\033[5m'
inverse='\033[7m'


fgDBlack='\033[30m'
fgDRed='\033[31m'
fgDGreen='\033[32m'
fgDYellow='\033[33m'
fgDBlue='\033[34m'
fgDMagenta='\033[35m'
fgDCyan='\033[36m'
fgDWhite='\033[37m'

fgLBlack='\033[90m'
fgLRed='\033[91m'
fgLGreen='\033[92m'
fgLYellow='\033[93m'
fgLBlue='\033[94m'
fgLMagenta='\033[95m'
fgLCyan='\033[96m'
fgLWhite='\033[97m'


bgDBlack='\033[40m'
bgDRed='\033[41m'
bgDGreen='\033[42m'
bgDYellow='\033[43m'
bgDBlue='\033[44m'
bgDMagenta='\033[45m'
bgDCyan='\033[46m'
bgDWhite='\033[47m'

bgLBlack='\033[100m'
bgLRed='\033[101m'
bgLGreen='\033[102m'
bgLYellow='\033[103m'
bgLBlue='\033[104m'
bgLMagenta='\033[105m'
bgLCyan='\033[106m'
bgLWhite='\033[107m'

def fgColor256(n):
    return '\033[38;5;'+str(n)+'m'

def fgClorRGB(r,g,b):
    return '\033[38;2;'+str(r)+';'+str(g)+';'+str(b)+'m'

def bgColor256(n):
    return '\033[48;5;'+str(n)+'m'

def bgColorRGB(r,g,b):
    return '\033[48;2;'+str(r)+';'+str(g)+';'+str(b)+'m'

def fmt(txt, code):
    return code+txt+resetAll
