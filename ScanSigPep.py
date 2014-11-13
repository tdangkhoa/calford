#!/usr/bin/python
# Copyright (c) 2014 Khoa Tran. All rights reserved.

import httplib
import re
import collections
from CalFord import *

boundaryString = '----'+genRandStr(30)

successCount = 0
errorCount = 0
retryList = collections.deque()

outputHandler = None

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

def prepareQuery(proteinId,proteinData):
   organism = '1'
   if proteinId.startswith("PSPTO"):
      organism = '2'
   queryData = []
   queryData.extend(encodePostData('organism',organism))
   queryData.extend(encodePostData('parameter','1'))
   queryData.extend(encodePostData('parameter2','0.5'))
   queryData.extend(encodePostData('output','1'))
   queryData.extend(encodePostData('pred','true'))
   queryData.extend(encodePostData('configfile','signalblast-uniprot2014.05.cfg'))
   queryData.extend(encodePostData('sigth','0.0'))
   queryData.extend(encodePostData('data',proteinData))
   queryData.extend(encodePostData('datafile','',{'filename':""},{"Content-Type":"application/octet-stream"}))
   queryData.append("--"+boundaryString)
   queryData.append("")

   return '\r\n'.join(queryData)

def sendQueryRequest(proteinId,proteinData):
   global boundaryString
   boundaryString = '----'+genRandStr(30)
   headers = {'Pragma':'no-cache',
              'Origin':'http://sigpep.services.came.sbg.ac.at',
              'Accept-Encoding':' deflate',
              'Accept-Language':'en-US,en;q=0.8,vi;q=0.6',
              'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.42 Safari/537.36',
              'Content-Type':'multipart/form-data; boundary=%s'%boundaryString,
              'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
              'Cache-Control':'no-cache',
              'Referer':'http://sigpep.services.came.sbg.ac.at/signalblast.html',
              'Connection':'keep-alive'}
           
   queryString = prepareQuery(proteinId,proteinData)
   try:
      h = httplib.HTTPConnection(config['sigpepQueryHost'],timeout=60)
      h.connect()
      queryPath = config['sigpepQueryPrefix']+'/'+config['sigpepQuerySelector']
      TRACE9('sendQueryRequest to %s' % queryPath)
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

def sendGetRequest(location):
   headers = {'Pragma':'no-cache',
              'Accept-Encoding':' deflate',
              'Accept-Language':'en-US,en;q=0.8,vi;q=0.6',
              'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.42 Safari/537.36',
              'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
              'Cache-Control':'no-cache',
              'Referer':'http://sigpep.services.came.sbg.ac.at/signalblast.html',
              'Connection':'keep-alive'}
   h = httplib.HTTPConnection(config['sigpepQueryHost'],timeout=60)
   h.connect()
   TRACE9("sendGetRequest to %s"%location)
   h.putrequest('GET',location,skip_accept_encoding=True)
   for k in headers:
      h.putheader(k,headers[k])
   h.endheaders()
   return h

def queryProteinSignal(proteinId,proteinStr):
   h = sendQueryRequest(proteinId,proteinStr)
   if h==None:
      # may be server error
      increaseBackoff(amount=60)
      return None
   try:
      response = h.getresponse()
   except Exception,e:
      TRACE0("Received bad response for query request: "+str(e))
      return None
   finally:
      h.close()
   responseStr = ""
   while response.status==302:
      hdrs = response.getheaders()
      location = ""
      for h in hdrs:
         if h[0]=='location':
            location = h[1]
            break
      if location=="":
         TRACE0("error redirection. Headers: %d"%"\n".join("%s: %s"%(x[0],x[1]) for x in hdrs))
         return None
      TRACE8("received redirection to %s"%location)
      if location[0]!='/':
         location = config['sigpepQueryPrefix']+"/"+location
      h = sendGetRequest(location)
      try:
         response = h.getresponse()
         responseStr = response.read()
      except Exception,e:
         TRACE0("Received bad response redirection request: "+str(e))
         return None
      finally:
         h.close()

   if response.status!=200:
      TRACE0("request error: %d - %s"%(response.status,response.reason))
      return None

   return responseStr

def writeOutput(proteinId,result):
   global outputHandler
   if outputHandler==None:
      try:
         outputHandler = open(config['outputSignalFile'],'a')
      except Exception,e:
         print "Error: cannot open output file",config['outputSignalFile']
         print e
         exit(1)
   TRACE5("writing output for %s"%proteinId)
   outputHandler.write("%s\t%s\n"%(proteinId,result))
   outputHandler.flush()

def doScanProtein(proteinId):
   global successCount
   global errorCount
   global retryList

   queryStr = queryProteinSignal(proteinId,fasta[proteinId])
   if queryStr==None:
      # Retry
      retryList.append(proteinId)
      errorCount += 1
      increaseBackoff()
      doWaitBackoff()
      return
   reResult = re.compile("Result:\s*([^\r\n]*)")
   m = reResult.search(queryStr)
   if m==None:
      TRACE0("matching error: %s"%queryStr)
   writeOutput(proteinId,m.group(1))
   successCount += 1
   decreaseBackoff()

parseConfigFile()
fasta = loadFasta(config['database'])
if fasta==None:
   # error
   print "Error: load FASTA file error"
   exit(1)
processedOutput = loadOutput(config['outputSignalFile'])
if processedOutput==None:
   # error
   print "Error: load output file error"
   exit(1)

for p in processedOutput:
   if p in fasta:
      del fasta[p]
TRACE4("Proteins remains after filtering: %d"%len(fasta))

for i in fasta:
   TRACE5("scanning protein %s (%d/%d,%d)"%(i,successCount,len(fasta),errorCount))
   doScanProtein(i)

while len(retryList)>0:
   i = retryList.popleft()
   TRACE5("retry scanning protein %s (%d/%d,%d)"%(i,successCount,len(fasta),errorCount))
   doScanProtein(i)

if outputHandler:
   outputHandler.close()

print "All done!"
