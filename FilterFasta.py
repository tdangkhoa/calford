#!/usr/bin/python
# Copyright (c) 2014 Khoa Tran. All rights reserved.

from CalFord import *
import argparse
import sys,os
import re

pmapFile = ""
outputFile = ""
outputHandle = None
configPath = "calford.conf"

def argsSanityCheck():
   isOk = True
   if not os.path.isfile(pmapFile):
      print "Error: cannot find %s"%pmapFile
      isOk = False

   return isOk

def parseArgs():
   global pmapFile
   global outputFile
   global configPath
   parser = argparse.ArgumentParser(description="Filter a subset FASTA file from pmap")
   parser.add_argument("pmapFile",help="input pmap file to check")
   parser.add_argument("--config",help="path to config file",
                       nargs=1)
   parser.add_argument("--output",help="write the subset of FASTA to this file",
                       nargs=1,required=True)
   args = parser.parse_args()
   pmapFile = args.pmapFile
   if args.config!=None:
      configPath = args.config[0]
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
   for p in pmapData:
      if p not in fastaDb:
         TRACE0("Cannot find %s in database"%p)
      else:
         seq = fastaDb[p]
         writeOutput('%s'%seq)

parseArgs()
parseConfigFile(configPath)
print "Write results to: %s" % outputFile

fastaDb = loadFasta(config['database'])
if fastaDb==None:
   # error
   print "Error: load FASTA file error"
   exit(1)

pmapData = loadPmap(pmapFile)
if pmapData==None:
   # error
   exit(1)

doCheck()

if outputHandle!=None:
   outputHandle.close()
