# coding: utf-8
from collections import OrderedDict
from urllib import request, parse
import urllib


def firefox_url_req(url: str) -> request.Request:
    headers = OrderedDict([
        ('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:34.0) Gecko/20100101 Firefox/34.0'),
        ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
        ('Accept-Language', 'en-us,en;q=0.8,zh-tw;q=0.5,zh;q=0.3'),
        ('Accept-Encoding', 'gzip, deflate'),
        ('Connection', 'keep-alive'),
        ('Pragma', 'no-cache'),
        ('Cache-Control', 'no-cache')
    ])
    return request.Request(url, headers=headers)

"""
def get_http_resp_content(url:str) -> str:
    req = firefox_url_req(url)
    with request.urlopen(req) as fin:
        content_encoding = fin.info().get("Content-Encoding").lower().strip()
        content_type = fin.info().get("Content-Type")
        content_charset = next(( _ for _ in content_type.split(';') if _.startswith("charset=")),
                                "charset=UTF-8" )
        content_charset = content_charset.split(sep='=', maxsplit=1)[1]
        if 'gzip' in content_encoding:
            from io import BytesIO
            import gzip
            gzdata = BytesIO(fin.readall())
            gzfile = gzip.GzipFile(fileobj=gzdata)
            data = gzfile.read()
        else:
            data = fin.readall()
        return data.decode(content_charset)
"""

def get_http_resp_content(url:str) -> str:
    data, content_charset, _ =  get_http_resp_content_bin(url)
    if not data:
        return ""
    return data.decode(content_charset)



def get_http_resp_content_bin(url:str) -> (bytes, str, str):
    """
    returns (content:bytes, char_set, content_type)
    """
    req = firefox_url_req(url)
    try:
        with request.urlopen(req) as resp:
            content_encoding = resp.info().get("Content-Encoding", failobj="").lower().strip()
            content_type = resp.info().get("Content-Type", failobj="")
            content_charset = next(( _ for _ in content_type.split(';') if _.startswith("charset=")),
                                    "charset=UTF-8" )
            content_charset = content_charset.split(sep='=', maxsplit=1)[1]
            if 'gzip' in content_encoding:
                from io import BytesIO
                import gzip
                gzdata = BytesIO(resp.readall())
                gzfile = gzip.GzipFile(fileobj=gzdata)
                return gzfile.read(), content_charset, content_type
            else:
                return resp.readall(), content_charset, content_type
    except Exception as ex:
        import traceback
        traceback.print_exc()
        print(ex)
        return None,None,None

def urlFileName(url:str)->str:
    from os import path
    r = path.basename(parse.urlsplit(url).path)
    if r:
        return r
    r = path.basename(parse.urlsplit(url).query)
    assert r
    return r


class MyHTTPRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        self.location = ""
    def http_error_302(self, req, fp, code, msg, headers):
        """store "Location" HTTP response header
        :return: http
        """
        self.location = headers.get('Location', '')
        uprint("headers['Location']=" + self.location)
        def squote(s):
            return urllib.parse.quote(s, ';/?:&=+,$[]%^')
        try:
            self.location.encode('ascii')
        except UnicodeEncodeError:
            scheme, netloc, path, params, query, fragment = \
                urllib.parse.urlparse(self.location)
            self.location = urllib.parse.urlunparse((
                scheme, netloc, urllib.parse.quote(path), squote(params), squote(query),
                fragment))
            headers.replace_header('Location', self.location)
            uprint("pquoted headers['Location']=" + self.location)
        return urllib.request.HTTPRedirectHandler.http_error_302(
            self, req, fp, code, msg, headers)
    http_error_301 = http_error_303 = http_error_307 = http_error_302


def downloadFile(url:str, fname:str, timeOut:int=10, chunkSize:int=2*1024*1024,
        timeOutInterval:int=3):
    """ download file from url to fname (abspath)
        Keyword arguments:
        url -- source url from where to download
        fname -- target file path
        timeOut -- timeOut for downloading each chunk
        chunkSize -- chunk size in bytes
        timeOutInterval -- if timeOut happens, sleep N seconds and then try again
    """
    import socket
    opener = urllib.request.build_opener(MyHTTPRedirectHandler)
    urllib.request.install_opener(opener)
    while True:
        try:
            with request.urlopen(firefox_url_req(url),
                timeout=timeOut) as resp:
                uprint("resp_headers=%s"%(resp.info().items()))
                with open(fname+".part", mode='wb') as fout:
                    while True:
                        data=resp.read(chunkSize)
                        print('.',end='',flush=True)
                        if not data:
                            print('',flush=True)
                            import os
                            os.rename(fname+".part", fname)
                            return
                        fout.write(data)
                        fout.flush()
                import pdb; pdb.set_trace()
        except socket.timeout as ex:
            print('socket.timeout, sleep %d seconds'%timeOutInterval)
            import time
            time.sleep(timeOutInterval)

def safeUrl(url:str)->str:
    from urllib import parse
    pr = parse.urlparse(url)
    pr2 = parse.ParseResult(scheme=pr.scheme, netloc=pr.netloc,
            path=parse.quote(pr.path,'/%'), params=pr.params,
            query=pr.query, fragment=pr.fragment)
    return parse.urlunparse(pr2)


def safeFileName(name:str)->str:
    def pq(x):
        return ''.join('%%%02X'%_ for _ in x.encode('utf-8'))
    import re
    bb =re.compile(r"[a-z0-9\-_.]",flags=re.IGNORECASE)
    return ''.join(_ if bb.match(_) else pq(_) for _ in name)

def uprint(msg:str):
    import sys
    sys.stdout.buffer.write((msg+'\n').encode('utf8'))


def getFileSha1(fileName)->str:
    import hashlib
    def sha1(data)->str:
        return hashlib.sha1(data).hexdigest()
    with open(fileName,mode='rb') as fin:
        data = fin.read()
        return sha1(data)
