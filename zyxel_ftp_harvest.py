#!/usr/bin/env python3
# coding: utf-8
import sqlite3
import ipdb
import traceback
import sys
from ftp_credentials import ftpHostName,ftpUserName,ftpPassword
import ftputil
from os import path
import os
from my_utils import uprint
from web_utils import getFileSha1 
from datetime import datetime
import re

conn=None
dlDir=path.abspath('firmware_files')
zyxel_ftp='ftp2.zyxel.com'
startTrail=[]
prevTrail=[]

def getStartIdx():
    global startTrail
    if startTrail:
        return startTrail.pop(0)
    else:
        return 0

def downloadFile(ftp, model, rfile):
    global prevTrail,conn
    csr = conn.cursor()
    try:
        fname = ftp.path.basename(rfile)
        epoch = ftp.path.getmtime(rfile)
        fwDate = datetime.fromtimestamp(epoch) 
        fileSize = ftp.path.getsize(rfile)
        lfile = path.join(dlDir,fname)
        uprint('download "%s"'%fname)
        ftp.download(rfile, lfile)

        fileSha1=getFileSha1(lfile)
        fileUrl="ftp://"+zyxel_ftp+"/"+rfile
        modelName = model.replace('_',' ')

        trailStr=str(prevTrail)
        csr.execute("INSERT OR REPLACE INTO TFiles (model,"
            "fw_date,file_size,file_sha1,file_url,tree_trail) VALUES "
            "(:modelName,:fwDate,:fileSize,:fileSha1,:fileUrl,:trailStr)",
            locals())
        conn.commit()
        uprint('UPSERT fileSha1=%(fileSha1)s, fileSize=%(fileSize)s'
                ' model="%(modelName)s", trail=%(trailStr)s' %locals())
        with ftputil.FTPHost(ftpHostName,ftpUserName,ftpPassword) as grid:
            grid.upload(lfile, path.basename(lfile))
            uprint('uploaded "%s" to ftp://%s/'
                %(path.basename(lfile), ftpHostName))
        os.remove(lfile)
    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()

def downloadDir(ftp, model, rdir):
    global prevTrail
    try:
        files = ftp.listdir(rdir)
        startIdx = getStartIdx()
        uprint('numFiles=%s'%len(files))
        for idx,fname in enumerate(files[startIdx:], startIdx):
            prevTrail += [idx]
            if ftp.path.isdir(ftp.path.join(rdir, fname)):
                downloadDir(ftp, model, ftp.path.join(rdir, fname))
            else:
                downloadFile(ftp, model, ftp.path.join(rdir, fname))
            prevTrail.pop()
    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()

def main():
    global startTrail,prevTrail,conn
    try:
        startTrail = [int(re.search(r'\d+', _).group(0)) for _ in sys.argv[1:]]
        conn= sqlite3.connect('zyxel.sqlite3')
        csr=conn.cursor()
        csr.execute(
            "CREATE TABLE IF NOT EXISTS TFiles("
            "id INTEGER NOT NULL,"
            "model TEXT,"
            "product_name TEXT,"
            "fw_date DATE,"
            "fw_ver TEXT,"
            "fw_desc TEXT,"
            "file_size INTEGER,"
            "page_url TEXT,"
            "file_url TEXT,"
            "tree_trail TEXT,"
            "file_sha1 TEXT,"
            "PRIMARY KEY (id)"
            "UNIQUE(model,fw_date)"
            ");")

        ftp = ftputil.FTPHost(zyxel_ftp, 'anonymous', '')
        ftp.keep_alive()
        prevTrail=[]
        models = ftp.listdir('.')
        startDIdx = getStartIdx()
        for didx,model in enumerate(models[startDIdx:],startDIdx):
            uprint('didx=%d'%didx)
            prevTrail+=[didx]
            if not ftp.path.isdir(model):
                uprint('"%s" is not directory '%model)
                prevTrail.pop()
                continue
            while True:
                try:
                    dirs = ftp.listdir(model)
                    break
                except ftputil.error.TemporaryError as ex:
                    print(ex)
                    ftp = ftputil.FTPHost(zyxel_ftp, 'anonymous','')
            fw = next((_ for _ in dirs if _.lower().startswith('firmware')),None)
            if not fw:
                uprint('model "%s" has no firmware'%model)
                prevTrail.pop()
                continue
            uprint('model="%s"'%model)
            remoteDir = path.join(model,fw)
            files = ftp.listdir(remoteDir)
            uprint('numFiles=%d'%len(files))
            startFIdx = getStartIdx()
            for fidx,fname in enumerate(files[startFIdx:],startFIdx):
                uprint('fidx = %s,"%s"'%(fidx,fname))
                prevTrail+=[fidx]
                rfile = path.join(remoteDir,fname)
                if ftp.path.isdir(rfile):
                    uprint('"%s" is a directory!'%rfile)
                    downloadDir(ftp, model, rfile)
                else:
                    downloadFile(ftp, model, rfile)
                prevTrail.pop()
            prevTrail.pop()
        ftp.close()
    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()

if __name__=='__main__':
    main()
