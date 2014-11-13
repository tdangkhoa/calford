#!/usr/bin/python
# Copyright (c) 2014 Khoa Tran. All rights reserved.

from CalFord import *
import argparse
import sys,os
import re

pmapFile = ""
outputFile = ""
outputHandle = None

def argsSanityCheck():
   isOk = True
   if not os.path.isfile(pmapFile):
      print "Error: cannot find %s"%pmapFile
      isOk = False

   return isOk

def parseArgs():
   global pmapFile
   global outputFile
   parser = argparse.ArgumentParser(description="Check how many proteins in the pmap file have signal peptide")
   parser.add_argument("pmapFile",help="input pmap file to check")
   parser.add_argument("--output",help="write the results to this file",
                       nargs=1,required=True)
   args = parser.parse_args()
   pmapFile = args.pmapFile
   outputFile = args.output[0]
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
      print "Error reading pmap file: %s"%str(e)
      return None
   return pmapData

def writeOutput(msg):
   global outputHandle
   if outputHandle==None:
      try:
         outputHandle = open(outputFile,'w')
      except IOError,e:
         print "Error open output file for writing: %s"%str(e)
         exit(1)

   outputHandle.write(msg+"\n")

def doCheck():
   notRe = re.compile("NOT")
   for p in pmapData:
      if p not in pepSignal:
         writeOutput('%s\t-\t-'%p)
      else:
         s = pepSignal[p]
         m = notRe.search(s)
         if m==None:
            containSignal = "1"
         else:
            containSignal = "0"
         writeOutput('%s\t%s\t%s'%(p,containSignal,s))

parseArgs()
parseConfigFile()
print "Write results to: %s" % outputFile

pepSignal = loadOutput(config['outputSignalFile'])
if pepSignal==None:
   # error
   print "Error: load peptide signal file error"
   exit(1)

pmapData = loadPmap(pmapFile)
if pmapData==None:
   # error
   exit(1)

doCheck()

if outputHandle!=None:
   outputHandle.close()
