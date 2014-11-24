#!/usr/bin/python
# Copyright (c) 2014 Khoa Tran. All rights reserved.

from CalFord import *
import argparse
import sys,os
import re

pmapFile = ""
outputResultFile = ""
outputHistogramFile = ""
configFile = "calford.conf"
outputHandle = None

def argsSanityCheck():
   isOk = True
   if not os.path.isfile(pmapFile):
      print "Error: cannot find %s"%pmapFile
      isOk = False

   return isOk

def parseArgs():
   global pmapFile
   global outputResultFile
   global outputHistogramFile
   global configFile
   parser = argparse.ArgumentParser(description="Check how many proteins in the pmap file have signal peptide")
   parser.add_argument("pmapFile",help="input pmap file to check")
   parser.add_argument("--outputResult",help="write the results to this file",
                       nargs=1,required=True)
   parser.add_argument("--outputHistogram",help="write the histogram to this file",
                       nargs=1,required=True)
   parser.add_argument("--config",help="config file",nargs=1)
   args = parser.parse_args()
   pmapFile = args.pmapFile
   outputResultFile = args.outputResult[0]
   outputHistogramFile = args.outputHistogram[0]
   if args.config:
      configFile = args.config[0]
   if not argsSanityCheck():
      print
      exit(1)

def loadPmap(path):
   pmapData = []
   try:
      f = open(path,'r')
      proteinRe = re.compile('(\S+) -')
      for line in f:
         match = proteinRe.match(line)
         if match==None:
            continue
         pmapData.append(match.group(1))
      f.close()
   except IOError,e:
      return None
   return pmapData

def writeOutput(msg):
   global outputHandle
   if outputHandle==None:
      try:
         outputHandle = open(outputResultFile,'w')
      except IOError,e:
         print "Error open output file for writing: %s"%str(e)
         exit(1)

   outputHandle.write(msg+"\n")

def countC(seqString):
   # count how many C in the sequence
   return seqString.lower().count('c')

def doCheck():
   notRe = re.compile("NOT")
   signalLocation = re.compile("after AA (\d+)")
   haveSignalHistogram = {}
   noSignalHistogram = {}

   for p in pmapData:
      if p not in pepSignal:
         writeOutput('%s\t-\t-\t-'%p)
      else:
         s = pepSignal[p]
         m = notRe.search(s)
         if m==None:
            containSignal = "1"
            seq = fastaData[p]
            m = signalLocation.search(s)
            if m==None:
               loc = 0
            else:
               loc = int(m.group(1))
            c = countC(seq[loc:])
            if c in haveSignalHistogram:
               haveSignalHistogram[c] += 1
            else:
               haveSignalHistogram[c] = 1
         else:
            containSignal = "0"
            c = countC(fastaData[p])
            if c in noSignalHistogram:
               noSignalHistogram[c] += 1
            else:
               noSignalHistogram[c] = 1
         writeOutput('%s\t%s\t%s\t%d'%(p,containSignal,s,c))
   maxKey = max(max(haveSignalHistogram.keys()),max(noSignalHistogram.keys()))
   minKey = min(min(haveSignalHistogram.keys()),min(noSignalHistogram.keys()))

   try:
      outputHistogramHandle = open(outputHistogramFile,'w')
   except IOError,e:
      print "Error open histogram file to write: %s"%str(e)
      return
   outputHistogramHandle.write("C count\tW/Signal peptide\tNon-signal peptide"\
                               "\tW/Signal %\tNon-signal %\n")
   sigCount = sum(haveSignalHistogram.values())
   nonSigCount = sum(noSignalHistogram.values())
   for i in range(minKey,maxKey+1):
      if i in haveSignalHistogram:
         sc = haveSignalHistogram[i]
         scp = float(sc)/sigCount*100
      else:
         sc = 0
         scp = 0
      if i in noSignalHistogram:
         nsc = noSignalHistogram[i]
         nscp = float(nsc)/nonSigCount*100
      else:
         nsc = 0
         nscp = 0
      outputHistogramHandle.write("%d\t%d\t%d\t%.2f\t%.2f\n"%(i,sc,nsc,scp,nscp))

   outputHistogramHandle.close()

parseArgs()
parseConfigFile(configFile)
print "Write results to: %s" % outputResultFile
print "Write histogram to: %s" % outputHistogramFile

pepSignal = loadOutput(config['outputSignalFile'])
if pepSignal==None:
   # error
   print "Error: load peptide signal file error"
   exit(1)

fastaData = loadFasta(config['database'])
if fastaData==None:
   # error
   print "Error: load FASTA file error"
   exit(1)

pmapData = loadPmap(pmapFile)
if pmapData==None:
   # error
   print "Error: reading pmap file error: %s"%str(e)
   exit(1)

doCheck()

if outputHandle!=None:
   outputHandle.close()
