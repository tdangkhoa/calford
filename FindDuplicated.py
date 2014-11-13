#!/usr/bin/python
# Copyright (c) 2014 Khoa Tran. All rights reserved.

import re
import os,sys

config = {}

def checkConfigSanity():
   # Check if the config file contains valid information
   isValid = True
   if 'database' not in config:
      print "Error: Missing 'database' in the config file"
      isValid = False
   if not os.path.isfile(config['database']):
      print "Error: Cannot find database file at %s"%config['database']
      isValid = False
   if 'outputFile' not in config:
      print "Error: Missing 'outputFile' in the config file"
      isValid = False

   return isValid

def parseConfigFile(configFile='calford.conf'):
   # Read config file
   global config
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

def loadOutput(path):
   proteinSet = set()
   try:
      outHandler = open(path,'r')
      rePid = re.compile('(.*)\t')
      for line in outHandler:
         m = rePid.match(line)
         if m!=None:
            p = m.group(1)
            if p not in proteinSet:
               proteinSet.add(m.group(1))
            else:
               print "Duplication found: %s" % p
         else:
            print "Line read error: %s" % line.strip()
      outHandler.close()
   except Exception,e:
      print "Error: cannot open output file %s for reading"%path
      print e
      exit(1)

parseConfigFile()
loadOutput(config['outputFile'])
