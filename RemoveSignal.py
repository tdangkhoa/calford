#!/usr/bin/python
# Copyright (c) 2014 Khoa Tran. All rights reserved.

from CalFord import *
import argparse
import sys,os
import re

signalFile = None
configPath = "calford.conf"
noSignalOutputFile = None
removedSignalOutputFile = None

def argsSanityCheck():
   isOk = True
   if not os.path.isfile(signalFile):
      print "Error: cannot find %s"%signalFile
      isOk = False

   return isOk

def parseArgs():
   global configPath
   global signalFile
   global noSignalOutputFile
   global removedSignalOutputFile
   parser = argparse.ArgumentParser(
      description="Read the protein signal file and generate two FASTA file: "\
                  "one file contains proteins without signal, the other one "\
                  "contains processed proteins, whose signal sequence has been "\
                  "truncated.")
   parser.add_argument("signalFile",help="input protein signal analysis result")
   parser.add_argument("--config",help="path to config file",
                       nargs=1)
   parser.add_argument("--outputNoSignal",help="write protein without signal to "\
                       "this file",
                       nargs=1,required=True)
   parser.add_argument("--outputTruncatedSignal",help="write protein with signal "\
                       "sequence truncated to this file",
                       nargs=1,required=True)
   args = parser.parse_args()
   signalFile = args.signalFile
   noSignalOutputFile = args.outputNoSignal[0]
   removedSignalOutputFile = args.outputTruncatedSignal[0]
   if args.config!=None:
      configPath = args.config[0]

   if not argsSanityCheck():
      print
      exit(1)

def loadSignalAnalysis(path):
   TRACE5("Load signal result from %s"%path)
   signalData = {}
   noSignalCount = 0
   noCleaveCount = 0
   truncatedCount = 0
   try:
      f = open(path,'r')
      signalRe = re.compile('(\S+)\s+(Signal .*)')
      cleaveRe = re.compile('after AA (\d+)')
      for line in f:
         m = signalRe.match(line)
         if m==None:
            # no signal found
            noSignalCount += 1
            continue
         pid = m.group(1)
         m2 = cleaveRe.search(m.group(2))
         if m2==None:
            signalData[pid] = 0
            noCleaveCount += 1
         else:
            signalData[pid] = int(m2.group(1))
            truncatedCount += 1

      f.close()
      TRACE9("Found %d proteins with no signal, %d proteins with no cleave location "\
             "and %d proteins has been truncated"\
             %(noSignalCount,noCleaveCount,truncatedCount))
   except IOError,e:
      print "Error reading signal file: %s"%str(e)
      return None
   return signalData

def writeNoSignalProtein(fastaDb,data):
   TRACE5("Writing no signal proteins to output file at %s"%noSignalOutputFile)
   try:
      f = open(noSignalOutputFile,'w')
   except IOError,e:
      print "Error writing no signal output file: %s"%str(e)
      return

   for p in fastaDb:
      if p not in data:
         f.write("%s\n"%fastaDb[p])
   f.close()

def renameProtein(proteinDesc,suffix='.nosignal'):
   proteinIdRe = re.compile('>(\S+)\s+(.*)')
   m = proteinIdRe.match(proteinDesc)
   if m==None:
      TRACE0("Cannot parse protein desc: %s"%proteinDesc)
      return None
   return m.group(1)+suffix

def truncateSignalProtein(fastaDb,data):
   TRACE5("Truncate signal proteins")
   result = {}
   for pid in data:
      loc = data[pid]
      if pid not in fastaDb:
         TRACE0("Error: cannot find %s in FASTA database"%pid)
         continue
      p = fastaDb[pid]
      s = p.split('\n')
      newPid = renameProtein(s[0])
      if newPid==None:
         continue
      seq = s[1]
      if loc>=len(seq):
         TRACE0("Error: cleaved location %d is larger than sequence len (%d)"\
                %(loc,len(seq)))
      seq = seq[loc:]
      result[newPid] = ">"+newPid+"\n"+seq
   return result

def writeTruncatedProtein(data):
   TRACE5("Writing truncated signal proteins to output file at %s"%removedSignalOutputFile)
   try:
      f = open(removedSignalOutputFile,'w')
   except IOError,e:
      print "Error writing truncated signal output file: %s"%str(e)
      return

   for p in data:
      f.write("%s\n"%data[p])
   f.close()

parseArgs()
parseConfigFile(configPath)
print "Write no signal proteins to: %s"%noSignalOutputFile
print "Write truncated signal proteins to: %s"%removedSignalOutputFile

fastaDb = loadFasta(config['database'])
if fastaDb==None:
   # error
   print "Error: load FASTA file error"
   exit(1)

signalData = loadSignalAnalysis(signalFile)
if signalData==None:
   # error
   exit(1)

truncatedDb = truncateSignalProtein(fastaDb,signalData)
writeNoSignalProtein(fastaDb,signalData)
writeTruncatedProtein(truncatedDb)
