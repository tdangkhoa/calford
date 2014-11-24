#!/usr/bin/python
# Copyright (c) 2014 Khoa Tran. All rights reserved.

from CalFord import *
import argparse
import sys,os
import re

outputPosFile = None
outputFastaFile = None
nGlycFile = None
configFile = "calford.conf"

def argsSanityCheck():
   isOk = True
   if not os.path.isfile(nGlycFile):
      print "Error: cannot find %s"%nGlycFile
      isOk = False

   return isOk

def parseArgs():
   global nGlycFile
   global outputPosFile
   global outputFastaFile
   global configFile

   parser = argparse.ArgumentParser(description="Extract N-Glyc position from protein and replace N with D")
   parser.add_argument("nGlycFile",help="input N-Glyc analysis result file to extract")
   parser.add_argument("--outputPos",help="write the peptide location to this file",
                       nargs=1,required=True)
   parser.add_argument("--outputFasta",help="write modified protein sequence this file",
                       nargs=1,required=True)
   parser.add_argument("--config",help="calford config file",
                       nargs=1)
   args = parser.parse_args()
   nGlycFile = args.nGlycFile
   outputPosFile = args.outputPos[0]
   outputFastaFile = args.outputFasta[0]
   if args.config!=None:
      configFile = args.config[0]
   if not argsSanityCheck():
      print
      exit(1)

def writeOutputPos(data):
   TRACE5("Writing position data with %d entries to %s"%(len(data),outputPosFile))
   try:
      outputPosHandle = open(outputPosFile,'a')
      for k,v in data.iteritems():
         outputPosHandle.write("%s\t%s\n"%(k,",".join([str(x) for x in v])))
   except IOError,e:
      print "Error open output file for writing: %s"%str(e)
      exit(1)

   outputPosHandle.close()
   TRACE5("Done writing position data")

def renameProtein(proteinDesc):
   # rename protein by adding a prefix "D."
   pnRe = re.compile("(\S+)(.*)")
   m = pnRe.match(proteinDesc)
   if m==None:
      TRACE0("Parsing error when renaming protein: %s"%proteinDesc)
      return proteinDesc
   newDesc = "D."+m.group(1)+str(m.group(2))
   return newDesc

def transformProtein(proteinId,seq,positions):
   # transform N protein at positions to D
   outputSeq = seq
   for p in positions:
      if outputSeq[p-1]!="N":
         TRACE0("Invalid peptide at position %d in protein %s: %s"%(p,proteinId,outputSeq[p-1]))
      else:
         if p==1:
            outputSeq = "D"+outputSeq[1:]
         elif p==len(outputSeq):
            outputSeq = outputSeq[:-1]+"D"
         else:
            outputSeq = outputSeq[:(p-1)]+"D"+outputSeq[p:]
   return outputSeq

def writeOutputFasta(data,fd):
   try:
      outputFastaHandle = open(outputFastaFile,'a')
      for k,v in data.iteritems():
         f = fd[k].split('\n')
         desc = renameProtein(f[0])
         outputFastaHandle.write(desc+"\n")
         newSeq = transformProtein(k,f[1],v)
         outputFastaHandle.write(newSeq+"\n")
   except IOError,e:
      print "Error open output file for writing: %s"%str(e)
      exit(1)

   outputFastaHandle.close()

def loadNGlyc(path):
   nGlycData = {}
   try:
      f = open(path,'r')
   except IOError,e:
      print "Error reading pmap file: %s"%str(e)
      return None

   curProtein = None
   curPos = []
   newProteinRe = re.compile("Output for '(\S*)'")
   seqnameRe = re.compile("SeqName")
   posRe = None
   seqnameFound = False
   TRACE5("Reading N-Glyc file: %s"%path)
   for line in f:
      npm = newProteinRe.search(line)
      if npm!=None:
         # Found next protein
         if curProtein!=None:
            # write prev protein info
            nGlycData[curProtein] = curPos
            curPos = []
            seqnameFound = False
            posRe = None
         curProtein = npm.group(1)
      if not seqnameFound:
         # look for "SeqName"
         sm = seqnameRe.match(line)
         if sm!=None:
            seqnameFound = True
      else:
         # look for position
         if posRe==None:
            posRe = re.compile(curProtein+"\s+([0-9]+).*\+")
         l = line.strip()
         while len(l)>0 and l[-1]=="=":
            # concat with next string
            nextline = f.next()
            if nextline=="":
               break
            l = l[:-1]+nextline.strip()
         pm = posRe.match(l)
         if pm!=None:
            curPos.append(int(pm.group(1)))
   if curProtein!=None:
      nGlycData[curProtein] = curPos

   TRACE5("Found %d proteins in the result file"%len(nGlycData))
   f.close()
   return nGlycData

parseArgs()
parseConfigFile(configFile)
print "Write position results to: %s" % outputPosFile
print "Write modified fasta to: %s" % outputFastaFile
print "Read N-Glyc result from: %s" % nGlycFile

ngData = loadNGlyc(nGlycFile)
if ngData==None:
   # error
   print "Error: load N-Glyc result file error"
   exit(1)

fastaData = loadFasta(config['database'])
if fastaData==None:
   # error
   print "Error: load FASTA file error"
   exit(1)

writeOutputPos(ngData)
writeOutputFasta(ngData,fastaData)
