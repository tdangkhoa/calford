#!/usr/bin/python
# Copyright (c) 2014 Khoa Tran. All rights reserved.

from CalFord import *
import argparse
import sys,os
import re

configFile = "calford.conf"
outputClassificationFile = None
outputReverseClassificationFile = None

def argsSanityCheck():
   isOk = True

   return isOk

def parseArgs():
   global configFile
   global outputClassificationFile
   global outputReverseClassificationFile

   parser = argparse.ArgumentParser(description="Extract protein classification from FASTA database")
   parser.add_argument("--output",help="write protein classification to this file",
                       nargs=1,required=True)
   parser.add_argument("--outputReverse",help="write reverse protein classification to this file",
                       nargs=1,required=False)
   parser.add_argument("--config",help="calford config file",nargs=1)
   args = parser.parse_args()
   outputClassificationFile = args.output[0]
   if args.outputReverse!=None:
      outputReverseClassificationFile = args.outputReverse[0]
   if args.config!=None:
      configFile = args.config[0]
   if not argsSanityCheck():
      print
      exit(1)

def writeClassificationResult(data):
   TRACE5("Writing classification data with %d entries to %s"%(len(data),outputClassificationFile))
   try:
      outputHandle = open(outputClassificationFile,'a')
      for k,v in data.iteritems():
         outputHandle.write("%s\t%d\t%s\n"%(k,len(v),"\t".join(["\t".join([str(x),str(v[x])]) for x in v])))
   except IOError,e:
      print "Error open output file for writing: %s"%str(e)
      exit(1)

   outputHandle.close()
   TRACE5("Done writing classification data")

def writeReverseClassificationResult(data):
   TRACE5("Writing reverse classification data with %d entries to %s"%(len(data),outputReverseClassificationFile))
   try:
      outputHandle = open(outputReverseClassificationFile,'a')
      for k,v in data.iteritems():
         outputHandle.write("%s\t%s\t%d\n"%(k,v['desc'],len(v['proteins'])))
         for p in v['proteins']:
            outputHandle.write("\t%s\n"%(p))
   except IOError,e:
      print "Error open output file for writing: %s"%str(e)
      exit(1)

   outputHandle.close()
   TRACE5("Done writing reverse classification data")

def extractClassification(fastaData,needReverse):
   iprRe = re.compile("(IPR\d+) (((?!IPR)[^\"])+)")
   result = {}
   reverseResult = {}
   for i in fastaData:
      match = iprRe.findall(fastaData[i])
      if len(match)==0:
         continue

      r = {}
      for m in match:
         cls = m[0].strip()
         desc = m[1].strip()
         # Forward lookup collection
         r[cls] = desc

         if needReverse:
            # Reverse lookup collection
            if cls in reverseResult:
               c = reverseResult[cls]
            else:
               c = {
                      'desc':desc,
                      'proteins':[],
                   }
            c['proteins'].append(i)
            reverseResult[cls] = c

      result[i] = r
   return (result,reverseResult)

parseArgs()
parseConfigFile(configFile)
print "Write classification results to: %s" % outputClassificationFile
if outputReverseClassificationFile:
   print "Write reverse classification results to: %s" % outputReverseClassificationFile
else:
   print "No output for reverse classification"   

fastaData = loadFasta(config['database'])
if fastaData==None:
   # error
   print "Error: load FASTA file error"
   exit(1)

needReverse = (outputReverseClassificationFile!=None)
(cData,rData) = extractClassification(fastaData,needReverse)
writeClassificationResult(cData)
if needReverse:
   writeReverseClassificationResult(rData)
