#!/usr/bin/python
# Copyright (c) 2014 Khoa Tran. All rights reserved.

import httplib
import re
import collections
import time
import argparse
from CalFord import *

boundaryString = '----'+genRandStr(30)

successCount = 0
errorCount = 0
retryList = collections.deque()
configFile = "calford.conf"
inputListFile = None

waitingPool = collections.deque()
queryPool = {}
maxPoolSize = 6
maxJob = 50

def argsSanityCheck():
   isOk = True
   if not os.path.isfile(inputListFile):
      print "Cannot open query list file: %s"%inputListFile
      isOk = False
   return isOk

def parseArgs():
   global configFile
   global inputListFile
   global maxPoolSize
   global maxJob

   parser = argparse.ArgumentParser(description="Send protein data to NetNGlyc Server to analyze")
   parser.add_argument("--poolSize",help="number of simultaneous queries",
                       nargs=1,type=int)
   parser.add_argument("--maxJob",help="number of job can run",
                       nargs=1,type=int)
   parser.add_argument("--config",help="calford config file",
                       nargs=1)
   parser.add_argument("queryList",help="a file contains list of FASTA file to send")
   args = parser.parse_args()
   inputListFile = args.queryList
   if args.config!=None:
      configFile = args.config[0]
   if args.maxJob!=None:
      maxJob = args.maxJob[0]
   if args.poolSize!=None:
      maxPoolSize = args.poolSize[0]
   if not argsSanityCheck():
      print
      exit(1)

def encodePostData(name,value,additionalKv={},additionalHeaders={}):
   additionalQry = "; ".join("%s=\"%s\""%(k,additionalKv[k]) for k in additionalKv)
   if additionalQry!="":
      additionalQry = "; "+additionalQry
   ret = ["--"+boundaryString,
         'Content-Disposition: form-data; name="%s"%s'%(name,additionalQry)]
   for k in additionalHeaders:
      ret.append("%s: %s"%(k,additionalHeaders[k]))

   ret.append('')
   ret.append(str(value))

   return ret

def prepareQuery(fastaData):
   queryData = []
   queryData.extend(encodePostData('configfile','/usr/opt/www/pub/CBS/services/NetNGlyc-1.0/NetNGlyc.cf'))
   queryData.extend(encodePostData('SEQPASTE',fastaData))
   queryData.extend(encodePostData('SEQSUB','',{'filename':""},{"Content-Type":"application/octet-stream"}))
   queryData.extend(encodePostData('id',''))

   queryData.append("--"+boundaryString+"--")
   queryData.append("")

   return '\r\n'.join(queryData)

def sendQuery(data):
   global boundaryString
   boundaryString = '----'+genRandStr(30)
   headers = {'Pragma':'no-cache',
              'Origin':'http://www.cbs.dtu.dk',
              'Accept-Encoding':' deflate',
              'Accept-Language':'en-US,en;q=0.8,vi;q=0.6',
              'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.42 Safari/537.36',
              'Content-Type':'multipart/form-data; boundary=%s'%boundaryString,
              'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
              'Cache-Control':'no-cache',
              'Referer':'http://www.cbs.dtu.dk/services/NetNGlyc/',
              'Cookie':'__utmz=215717889.1415578563.1.1.utmccn=(direct)|utmcsr=(direct)|utmcmd=(none); '
                       '__utma=215717889.1400914664.1415578563.1416180461.1416190940.5; '
                       '__utmc=215717889; __utmb=215717889; __utmt=1; '
                       '__utma=151498347.573547553.1415578588.1416184437.1416190299.7; '
                       '__utmb=151498347.6.10.1416190299; __utmc=151498347; '
                       '__utmz=151498347.1415578588.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)',
              'Connection':'keep-alive'}
           
   queryString = prepareQuery(data)
   try:
      h = httplib.HTTPConnection(config['netNGlycHost'],timeout=90)
      h.connect()
      queryPath = config['netNGlycPrefix']+'/'+config['netNGlycSelector']
      TRACE9('sendQuery to %s' % queryPath)
      h.putrequest('POST',queryPath,skip_accept_encoding=True)
      for k in headers:
         h.putheader(k,headers[k])
      h.putheader('Content-Length',str(len(queryString)))
      h.endheaders()
      h.send(queryString)
      return h
   except Exception,e:
      TRACE0("Send query error: "+str(e))
      return None

def doQuery(pData):
   # Send a query to the server and get the result URL
   urlRe = re.compile("location.replace\(\"(.*)&opt=wait\"")
   h = sendQuery('\n'.join(pData[k] for k in pData))
   if h==None:
      return (None,True)

   try:
      response = h.getresponse()
      responseStr = response.read()
   except Exception,e:
      TRACE0("Received bad response for query request: "+str(e))
      return (None,True)
   finally:
      h.close()
   
   if response.status!=200:
      TRACE0("Reponse status not OK: %d - %s"%(response.status,response.reason))
      return (None,True)
   
   m = urlRe.search(responseStr)
   if m==None:
      TRACE0("Received bad response")
      TRACE9("Bad response: %s"%responseStr)
      return (None,False)

   return (m.group(1),True)

def sendGetRequest(url):
   headers = {'Pragma':'no-cache',
              'Accept-Encoding':' deflate',
              'Accept-Language':'en-US,en;q=0.8,vi;q=0.6',
              'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
              'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_0) AppleWebKit/537.36 (KHTML,'
                           ' like Gecko) Chrome/39.0.2171.42 Safari/537.36',
              'Cache-Control':'no-cache',
              'Referer':'http://www.cbs.dtu.dk/services/NetNGlyc/',
              'Cookie':'__utmz=215717889.1415578563.1.1.utmccn=(direct)|utmcsr=(direct)|utmcmd=(none); '
                       '__utma=215717889.1400914664.1415578563.1416180461.1416190940.5; '
                       '__utmc=215717889; __utmb=215717889; __utmt=1; '
                       '__utma=151498347.573547553.1415578588.1416184437.1416190299.7; '
                       '__utmb=151498347.6.10.1416190299; __utmc=151498347; '
                       '__utmz=151498347.1415578588.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)',
              'Connection':'keep-alive'}

   h = httplib.HTTPConnection(config['netNGlycHost'],timeout=60)
   h.connect()
   TRACE9("sendGetRequest to %s"%url)
   h.putrequest('GET',url,skip_accept_encoding=True)
   for k in headers:
      h.putheader(k,headers[k])
   h.endheaders()
   return h


def doPoll(url):
   # Check if the result is shown and download it
   foundRe = re.compile("prediction results")
   processingRe = re.compile("is being processed")
   h = sendGetRequest(url)

   try:
      response = h.getresponse()
      responseStr = response.read()
   except Exception,e:
      TRACE0("Received bad response message: "+str(e))
      return (None,True)
   finally:
      h.close()

   if response.status!=200:
      TRACE0("request error: %d - %s"%(response.status,response.reason))
      return (None,True)

   m = foundRe.search(responseStr)
   if m==None:
      m2 = processingRe.search(responseStr)
      if m2:
         TRACE9("result is not available")
         return (None,True)
      else:
         TRACE0("Polling for result, unknown error (%s): %s"%(url,responseStr))
         return (None,False)
   return (responseStr,True)
   
def writeResult(outFile,result):
   # Write result to output file
   TRACE5("writing result to %s, len=%d"%(outFile,len(result)))
   try:
      f = open(outFile,'w')
   except IOError,e:
      TRACE0("Error open %s for writing result: %s",(outFile,str(e)))
      return False

   f.write(result)
   f.close()
   return True

def doQueryLoop():
   global queryPool
   global waitingPool

   errorCount = 0
   finishCount = 0
   querySentCount = 0
   while (len(waitingPool)>0 and querySentCount<maxJob) or len(queryPool)>0:
      TRACE9("doQueryLoop: waitingPool(%d), queryPool(%d/%d), querySent(%d/%d), finishCount(%d), errorCount(%d)"
             %(len(waitingPool),len(queryPool),maxPoolSize,querySentCount,maxJob,finishCount,errorCount))
      while len(queryPool)<maxPoolSize and len(waitingPool)>0 and querySentCount<maxJob:
         # Fill the query pool
         inFile = waitingPool.pop()
         pData = loadFasta(inFile)
         if pData==None:
            TRACE0("Error loading protein data in %s"%inFile)
            errorCount += 1
            continue

         (resultUrl,recoverable) = doQuery(pData)
         if not resultUrl:
            increaseBackoff()
            doWaitBackoff()
            errorCount += 1
            if recoverable:
               TRACE0("Hit an recoveable error for %s. Scheduled for retrying."%inFile)
               waitingPool.appendLeft(inFile)
            else:
               TRACE0("Hit an unrecoverable error for %s. Ignored."%inFile)
               print "Request error: %s"%inFile
            continue
         queryPool[inFile] = resultUrl
         querySentCount += 1
         TRACE9("Result url for %s: %s"%(inFile,resultUrl))

      if len(queryPool)>0:
         for inFile in queryPool.keys():
            TRACE8("polling result for %s"%inFile)
            result,recoverable = doPoll(queryPool[inFile])
            if result!=None:
               rv = writeResult(inFile+".mhtml",result)
               if rv==True:
                  del queryPool[inFile]
                  finishCount += 1
               else:
                  print "Writing result to %s error"%(inFile+".mhtml")
                  errorCount += 1
            else:
               if not recoverable:
                  TRACE0("Hit an unrecoverable error for %s at %s. Ignored."
                         %(inFile,queryPool[inFile]))
                  print "Reading result error: %s"%inFile
                  del queryPool[inFile]
                  errorCount += 1

      if len(queryPool)<maxPoolSize and len(waitingPool)>0 and querySentCount<maxJob:
         pass
      else:
         # Finish a polling iteration. Wait.
         TRACE9("Suspend for %s seconds"%config['pollingInterval'])
         time.sleep(int(config["pollingInterval"]))

def loadFileList(fileName):
   global waitingPool
   try:
      f = open(fileName,'r')
   except IOError,e:
      TRACE0("Error loading %s for reading list of input files: %s"%(fileName,str(e)))
      return

   for line in f:
      fName = line.strip()
      if not os.path.isfile(fName):
         TRACE0("loadFileList: invalid file at %s"%fName)
         continue
      if os.path.isfile(fName+".mhtml"):
         TRACE1("loadFileList: skipped %s because it has been processed"%fName)
         continue
      waitingPool.appendleft(fName)
   f.close()
   TRACE4("found %d files in input file list %s"%(len(waitingPool),fileName))

parseArgs()
parseConfigFile(configFile)
print "Read list of fasta files in: %s" % inputListFile
print "Max pool size: %s" % maxPoolSize
print "Max jobs: %s" % maxJob
loadFileList(inputListFile)

if len(waitingPool)==0:
   print "No file to send"
   exit(0)

doQueryLoop()
