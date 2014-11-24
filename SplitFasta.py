#!/usr/bin/python
# Copyright (c) 2014 Khoa Tran. All rights reserved.

from CalFord import *
import argparse
import sys,os
import re

configFile = "calford.conf"
localConfig = {}

def argsSanityCheck():
   isOk = True
   if 'skippedFile' in localConfig:
      for f in localConfig['skippedFile']:
         if not os.path.isfile(f):
            print "Error: cannot find %s"%f
            isOk = False

   return isOk

def parseArgs():
   global configFile
   global localConfig

   parser = argparse.ArgumentParser(
      description="Split FASTA file into smaller files, with constraints in "\
                  "number of sequences per file, max number of AA, and AA "\
                  "per sequence",
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)
   parser.add_argument("--config",help="calford config file",
                       nargs=1)
   parser.add_argument("--maxSeq",help="max number of sequence per file",
                       nargs=1,
                       type=int,
                       default=2000)
   parser.add_argument("--maxAa",help="max number of amino acid per file",
                       nargs=1,
                       type=int,
                       default=200000)
   parser.add_argument("--maxAaPerSeq",help="max number of amino acid per sequence",
                       nargs=1,
                       type=int,
                       default=4000)
   parser.add_argument("--outputPrefix",help="prefix for output files",
                       nargs=1,
                       required=True)
   parser.add_argument("--skippedFile",help="file contains list of proteins to skip",
                       action='append')
   parser.add_argument("--ignoreRegex",help="ignore proteins match this regex",
                       nargs=1)
   args = parser.parse_args()
   if isinstance(args.maxSeq,int):
      localConfig['maxSeq'] = args.maxSeq
   else:
      localConfig['maxSeq'] = args.maxSeq[0]

   if isinstance(args.maxAa,int):
      localConfig['maxAa'] = args.maxAa
   else:
      localConfig['maxAa'] = args.maxAa[0]

   if isinstance(args.maxAaPerSeq,int):
      localConfig['maxAaPerSeq'] = args.maxAaPerSeq
   else:
      localConfig['maxAaPerSeq'] = args.maxAaPerSeq[0]
   localConfig['outputPrefix'] = args.outputPrefix[0]
   if args.ignoreRegex!=None:
      localConfig['ignoreRegex'] = args.ignoreRegex[0]
   if args.skippedFile!=None:
      localConfig['skippedFiles'] = args.skippedFile
   if args.config!=None:
      configFile = args.config[0]
   if not argsSanityCheck():
      print
      exit(1)

def loadSkippedFile(fileName):
   TRACE5("Loading protein in skipped file %s"%fileName)
   try:
      f = open(fileName,'r')
   except IOError,e:
      print "Error open %s for reading: %s"%(fileName,str(e))
      return None
   result = set()
   pidRe = re.compile('(\S+)')
   for line in f:
      m = pidRe.match(line)
      if m==None:
         continue
      result.add(m.group(1))
   return result

def loadSkippedFiles(skippedFiles):
   result = set()
   for f in skippedFiles:
      r = loadSkippedFile(f)
      result |= r
   TRACE4("Loaded %d skipped proteins"%(len(result)))
   return result

def filterFasta(fastaData,skippedProteins,ignoreStr=""):
   result = {}
   if ignoreStr!="":
      ignoreRe = re.compile(ignoreStr)
      for k in fastaData:
         if not ignoreRe.match(k):
            result[k] = fastaData[k]
   else:
      result = fastaData

   for p in skippedProtein:
      if p in result:
         del result[p]
   return result

def doSplit(fastaData,prefix,maxSeq,maxAa,maxAaPerSeq):
   TRACE5("doSplit with %d items to %s-*.fasta files"%(len(fastaData),prefix))
   outputCnt = 0
   seqCnt = 0
   aaCnt = 0
   outputHandler = None
   for p in fastaData:
      d = fastaData[p]
      desc,seq = d.split('\n')
      seqLen = len(seq)
      if seqLen>maxAaPerSeq:
         TRACE0("Protein '%s' has a sequence longer than permitted length (%d)"%(p,seqLen))
         continue
      if outputHandler==None\
            or (seqCnt+1)>maxSeq\
            or (aaCnt+seqLen)>maxAa:
         if outputHandler:
            outputHandler.close()
         try:
            outputCnt += 1
            fileName = prefix+"-"+str(outputCnt)+".fasta"
            TRACE6("Start writing to %s"%fileName)
            outputHandler = open(fileName,'w')
         except Exception,e:
            TRACE0("Error open file to write: %s"%str(e))
            print "Error open file to write: %s"%str(e)
            exit(1)
         seqCnt = 0
         aaCnt = 0
      seqCnt += 1
      aaCnt += seqLen
      outputHandler.write(d+"\n")
   if outputHandler:
      outputHandler.close()

parseArgs()
parseConfigFile(configFile)
print "Args configuration:"
for k in localConfig:
   print "    %12s: %s"%(k,localConfig[k])
print

fastaData = loadFasta(config['database'])
if fastaData==None:
   # error
   print "Error: load FASTA file error"
   exit(1)

skippedProtein = loadSkippedFiles(localConfig['skippedFiles'])

ignoreStr = ""
if 'ignoreRegex' in localConfig:
   ignoreStr = localConfig['ignoreRegex']
fastaData = filterFasta(fastaData,skippedProtein,ignoreStr)

doSplit(fastaData,localConfig['outputPrefix'],
        localConfig['maxSeq'],
        localConfig['maxAa'],
        localConfig['maxAaPerSeq'])
