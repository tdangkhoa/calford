#!/usr/bin/python
# Copyright (c) 2014 Khoa Tran. All rights reserved.

import random,string
import datetime,time
import re
import os,sys
import atexit

debugEnabled = {}
debugEnabled[0] = False
debugEnabled[1] = False
debugEnabled[2] = False
debugEnabled[3] = False
debugEnabled[4] = False
debugEnabled[5] = False
debugEnabled[6] = False
debugEnabled[7] = False
debugEnabled[8] = False
debugEnabled[9] = False

debugHandler = None

config = {
   'sigpepQueryHost':'sigpep.services.came.sbg.ac.at',
   'sigpepQueryPrefix':'/cgi-bin',
   'sigpepQuerySelector':'signalblast.cgi',
   'netNGlycHost':'genome.cbs.dtu.dk',
   'netNGlycPrefix':'/cgi-bin',
   'netNGlycSelector':'webface2.fcgi',
   'minBackoff':'2',
   'maxBackoff':'100',
}

backoffTime = 1
minBackoff = 2
maxBackoff = 100

def decreaseBackoff():
   global backoffTime
   dec = int(round(backoffTime/10.0))+1
   backoffTime -= dec
   if backoffTime<minBackoff:
      backoffTime = minBackoff

def increaseBackoff(amount=0):
   global backoffTime
   backoffTime *= 2+amount
   if backoffTime>maxBackoff:
      backoffTime = maxBackoff

def doWaitBackoff():
   minTime = max(minBackoff,backoffTime/5)
   waitTime = random.randint(minTime,backoffTime)
   TRACE1("backoff: wait for %d seconds (%d)"%(waitTime,backoffTime))
   time.sleep(waitTime)

def setupBackoff():
   global minBackoff
   global maxBackoff
   minBackoff = int(float(config['minBackoff']))
   maxBackoff = int(float(config['maxBackoff']))

def debugOutput(msg):
   if debugHandler==None:
      print msg
   else:
      debugHandler.write(msg)
      debugHandler.flush()

def printDebug(level,message):
   # print debug message with a level
   if debugEnabled[level]:
      reFormat = re.compile('(\n|\r\n)')
      formatedStr = reFormat.sub('\n'+(' '*32)+'>> ',message.strip())
      debugOutput("%-30s %-3s %s\n"
                  %(datetime.datetime.now().isoformat(),str(level),formatedStr))

def TRACE0(msg):
   printDebug(0,msg)
def TRACE1(msg):
   printDebug(1,msg)
def TRACE2(msg):
   printDebug(2,msg)
def TRACE3(msg):
   printDebug(3,msg)
def TRACE4(msg):
   printDebug(4,msg)
def TRACE5(msg):
   printDebug(5,msg)
def TRACE6(msg):
   printDebug(6,msg)
def TRACE7(msg):
   printDebug(7,msg)
def TRACE8(msg):
   printDebug(8,msg)
def TRACE9(msg):
   printDebug(9,msg)

def setupDebugPrinting():
   global debugEnabled
   global debugHandler
   if 'debugOutputFile' in config:
      debugFile = config['debugOutputFile']
      if debugFile!="":
         try:
            debugHandler = open(debugFile,'a')
         except IOError,e:
            print "Error open %s for output debug information: %s"%(debugFile,str(e))
   if 'debugSelector' in config:
      dbgSelector = config['debugSelector']
      for i in range(10):
         if dbgSelector=='*' or str(i) in dbgSelector:
            debugEnabled[i] = True

def checkConfigSanity():
   # Check if the config file contains valid information
   isValid = True
   if 'database' not in config:
      print "Error: Missing 'database' in the config file"
      isValid = False
   if not os.path.isfile(config['database']):
      print "Error: Cannot find database file at %s"%config['database']
      isValid = False
   if 'outputSignalFile' not in config:
      print "Error: Missing 'outputSignalFile' in the config file"
      isValid = False

   return isValid

def parseConfigFile(configFile='calford.conf'):
   # Read config file
   global config
   global backoffTime
   try:
      f = open(configFile)

      r = re.compile('([^#=\s]+)\s*=\s*([^#]+)')
      for line in f:
         m = r.match(line)
         if m!=None:
            k = m.group(1).strip()
            v = m.group(2).strip()
            config[k] = v
   except IOError,e:
      print "Error open config file:",e
      exit(1)
   except Exception,e:
      print "Unknown error:",e
      exit(1)

   print "Configuration:"
   for k in sorted(config):
      print "    %-25s: %s"%(k,config[k])
   print

   if not checkConfigSanity():
      exit(1)
   setupDebugPrinting()
   setupBackoff()

def loadFasta(path):
   # read fasta file and justify it
   fasta = {}
   TRACE5("read FASTA file at %s"%path)

   try:
      fastaHandler = open(path,'r')
      curProteinSeq = ""
      curProteinId = ""
      for line in fastaHandler:
         if line[0]=='>':
            # New protein matched
            if curProteinId!="":
               # Save prev protein
               fasta[curProteinId] = curProteinSeq
            reId = re.compile('^>([^\s]*)')
            m = reId.match(line)
            if m==None:
               continue
            curProteinId = m.group(1)
            curProteinSeq = line.strip()+"\n"
         else:
            # Continue on protein sequence
            curProteinSeq += line.strip()
      if curProteinId!="":
         # Save prev protein
         fasta[curProteinId] = curProteinSeq
            
      fastaHandler.close()
   except IOError,e:
      TRACE0("error open FASTA file: %s"%str(e))
      return None

   TRACE5("read %d proteins in FASTA file"%len(fasta))
   return fasta

def loadOutput(path):
   # read output file to see if the proteins have been processed
   output = {}
   TRACE5("read output file at %s"%path)
   try:
      outHandler = open(path,'r')
      rePid = re.compile('([^\t]*)\t(.*)')
      for line in outHandler:
         m = rePid.match(line)
         if m!=None:
            k = m.group(1)
            v = m.group(2)
            if k in output:
               TRACE0("duplication found in output file: %s"%k)
            else:
               output[k] = v
         else:
            TRACE1("unknown format output file: %s"%line.strip())
      outHandler.close()
   except Exception,e:
      TRACE0("error reading output file: %s"%str(e))
      return None

   TRACE5("found %d proteins in output file"%len(output))
   return output

def genRandStr(length):
   boundaryChars = string.ascii_letters+string.digits
   return ''.join(random.choice(boundaryChars) for i in range(length))

def cleanUp():
   if debugHandler:
      debugHandler.close()
   
atexit.register(cleanUp)
