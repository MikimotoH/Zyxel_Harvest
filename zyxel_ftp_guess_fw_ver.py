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


def main():
    global conn
    try:
        startIdx = int(sys.argv[1]) if len(sys.argv)>1 else 0
        conn= sqlite3.connect('zyxel_ftp.sqlite3')
        csr=conn.cursor()
        rows = csr.execute(
            "SELECT id,model, file_url FROM TFiles ORDER BY id "
            "LIMIT -1 OFFSET %d"%startIdx).fetchall()
        for row in rows:
            devId,model,file_url = row
            fileName = path.basename(file_url)
            uprint('devId=%d, model="%s",fileName="%s"'%(devId,model,fileName))
            ftitle,fext = path.splitext(fileName)
            fext=fext.lower()
            if fext == '.pdf' or fext=='.txt' or fileName.endswith('_info'):
                uprint('bypass txt/pdf')
                continue
            try:
                fnModel, fwVer = ftitle.split('_',1)
            except ValueError:
                fwVer = ftitle
            uprint('fwVer="%s"'%fwVer)
            if '_' in fwVer:
                idx = fwVer.find(model) 
                if idx != -1:
                    fwVer = fwVer[idx+len(model):]
                    fwVer = fwVer.strip()
                    uprint('fwVer="%s"'%fwVer)
                else:
                    ipdb.set_trace()
            csr.execute(
                "UPDATE TFiles SET fw_ver=:fwVer WHERE id=:devId"
                ,locals())
            conn.commit()
    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()

if __name__=='__main__':
    main()
