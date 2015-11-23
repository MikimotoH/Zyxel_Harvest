#!/usr/bin/env python3
# coding: utf-8
import harvest_utils
from harvest_utils import waitVisible, waitText, getElems, getFirefox,driver,waitTextChanged, getElemText, elemWithText, waitClickable, waitUntilStable, isReadyState,waitUntil,retryStable,getNumElem,goToUrl
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException, WebDriverException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.keys import Keys
import sys
import sqlite3
import re
import time
import datetime
from datetime import datetime
import ipdb
import traceback
from my_utils import uprint,ulog,getFuncName
from contextlib import suppress
import random
import math
import html2text
from urllib import parse
from os import path


driver,conn=None,None
modelName=''
prevTrail=[]
startTrail=[]
rootUrl='http://www2.zyxel.com/us/en/support/download_landing.shtml'
allModels=[]

def glocals()->dict:
    """ globals() + locals()
    """
    import inspect
    ret = dict(inspect.stack()[1][0].f_locals)
    ret.update(globals())
    return ret


def getScriptName():
    from os import path
    return path.splitext(path.basename(__file__))[0]

def getStartIdx():
    global startTrail
    if startTrail:
        return startTrail.pop(0)
    else:
        return 0

def sql(query:str, var=None):
    global conn
    csr=conn.cursor()
    try:
        if var:
            rows = csr.execute(query,var)
        else:
            rows = csr.execute(query)
        if not query.startswith('SELECT'):
            conn.commit()
        if query.startswith('SELECT'):
            return rows.fetchall()
        else:
            return
    except sqlite3.Error as ex:
        print(ex)
        raise ex

def retryUntilTrue(statement, timeOut:float=6.2, pollFreq:float=0.3):
    timeElap=0
    while timeElap<timeOut:
        timeBegin=time.time()
        try:
            r = statement()
            if r==True:
                return r
        except (StaleElementReferenceException,NoSuchElementException, StopIteration):
            pass
        except Exception as ex:
            ulog('raise %s %s'%(type(ex),str(ex)))
            raise ex
        #ulog('sleep %f secs'%pollFreq)
        time.sleep(pollFreq)
        timeElap+=(time.time()-timeBegin)
    raise TimeoutException(getFuncName()+': timeOut=%f'%timeOut)
def retryA(statement, timeOut:float=6.2, pollFreq:float=0.3):
    timeElap=0
    while timeElap<timeOut:
        timeBegin=time.time()
        try:
            return statement()
        except (StaleElementReferenceException,NoSuchElementException, StopIteration):
            pass
        except Exception as ex:
            ulog('raise %s %s'%(type(ex),str(ex)))
            raise ex
        #ulog('sleep %f secs'%pollFreq)
        time.sleep(pollFreq)
        timeElap+=(time.time()-timeBegin)
    raise TimeoutException(getFuncName()+': timeOut=%f'%timeOut)


def guessDate(txt:str)->datetime:
    """ txt = '07-13-2015' """
    try:
        m = re.search(r'\d{2}-\d{2}-\d{4}', txt)
        return datetime.strptime(m.group(0), '%m-%d-%Y')
    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()

def upsertOneVersion(row,imgUrl,prodName):
    global driver,prevTrail,modelName
    try:
        fwVer = row.find_element_by_css_selector('td.versionTd').text.strip()
        pageUrl = driver.current_url
        ulog('row.text="%s"'%repr(row.text))
        fileUrls = [_.get_attribute('data-filelink') for _ in row.find_elements_by_css_selector('td.downloadTd a') if _.is_displayed() ]
        fileUrl = '\n'.join(_ for _ in fileUrls if _)
        relDate = guessDate(row.text)
        trailStr=str(prevTrail)
        sql("INSERT OR REPLACE INTO TFiles(model, prod_name, "
            " fw_ver, rel_date, image_url, page_url, file_url, "
            " tree_trail) VALUES (:modelName,:prodName,"
            " :fwVer,:relDate,:imgUrl,:pageUrl,:fileUrl,"
            " :trailStr)",glocals())
        ulog('UPSERT "%(modelName)s","%(fwVer)s",%(trailStr)s'%glocals())
    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()
        driver.save_screenshot(getScriptName()+'_'+getFuncName()+'_excep.png')

def upsertOneModel():
    global driver, prevTrail, modelName
    try:
        prodName = [_.text for _ in getElems('div.sectionTitle p.hidden-xs') if _.text.strip()]
        if prodName:
            assert len(prodName)==1
            prodName=prodName[0]
        else:
            prodName=None
        pageUrl=driver.current_url
        try:
            imgUrl=waitVisible('.productPic img.img-responsive',4,1).get_attribute('src')
        except TimeoutException:
            imgUrl=None
        assert imgUrl is None or imgUrl.startswith('http')
        trailStr=str(prevTrail)
        sql("INSERT OR REPLACE INTO TFiles(model,prod_name,page_url,"
            "image_url,tree_trail) VALUES(:modelName, :prodName, :pageUrl,"
            ":imgUrl,:trailStr)", glocals())
        ulog('UPSERT "%(modelName)s" "%(prodName)s",%(trailStr)s,'
            '%(pageUrl)s' %glocals())
    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()
        driver.save_screenshot(getScriptName()+'_'+getFuncName()+'_excep.png')

def versionWalker():
    global driver,prevTrail
    try:
        rows = getElems('#Firmware tr')
        rows = [_ for _ in rows if _.text.startswith('Firmware')]
        if not rows:
            upsertOneModel()
            return
        assert len(rows)==1
        row = rows[0]
        try:
            imgUrl=waitVisible('.productPic img.img-responsive',4,1).get_attribute('src')
        except TimeoutException:
            ulog('no Picture!')
            imgUrl=None
        prodName = [_.text for _ in getElems('div.sectionTitle p.hidden-xs') if _.text.strip()]
        if prodName:
            assert len(prodName)==1
            prodName=prodName[0]
        else:
            prodName=None
        try:
            verBtn = row.find_element_by_css_selector('button')
        except NoSuchElementException:
            idx=0
            ulog('only one version')
            ulog('idx=%s'%idx)
            prevTrail+=[idx]
            upsertOneVersion(row,imgUrl,prodName)
            prevTrail.pop()
            return
        verBtn.click()
        versions = row.find_elements_by_css_selector('ul li a')
        startIdx = getStartIdx()
        numVersions = len(versions)
        ulog('numVersions=%s'%numVersions)
        for idx in range(startIdx, numVersions):
            ulog('idx=%s'%idx)
            ulog('click "%s"'%versions[idx].text.strip())
            versions[idx].click()
            time.sleep(0.1)
            prevTrail+=[idx]
            upsertOneVersion(row,imgUrl,prodName)
            prevTrail.pop()
            if idx < numVersions-1:
                verBtn.click()
                versions = row.find_elements_by_css_selector('ul li a')
    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()
        driver.save_screenshot(getScriptName()+'_'+getFuncName()+'_excep.png')


def modelWalker():
    global driver, prevTrail, modelName
    rootUrl='http://www2.zyxel.com/us/en/support/DownloadLandingSR.shtml?c=us&l=en&md='
    try:
        startIdx = getStartIdx()
        ulog('len(allModels)=%d'%len(allModels))
        for idx in range(startIdx,len(allModels)):
            ulog('idx=%s'%idx)
            modelName=allModels[idx]
            ulog('modelName="%s"'%modelName)
            goToUrl(rootUrl+parse.quote(modelName))
            waitUntil(isReadyState)

            # click "Firmware" tab
            tab = elemWithText('li.resp-tab-item','Firmware')
            if not tab:
                ulog('no Firmware tab,bypass!')
                prevTrail+=[idx]
                upsertOneModel()
                prevTrail.pop()
                continue
            tab.click()
            time.sleep(0.1)
            prevTrail+=[idx]
            versionWalker()
            prevTrail.pop()
    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()
        driver.save_screenshot(getScriptName()+'_'+getFuncName()+'_excep.png')


def getAllModels():
    global driver, allModels
    try:
        if path.exists('zyxel_models.txt') and \
                path.getsize('zyxel_models.txt')>2 and \
                time.time() - path.getmtime('zyxel_models.txt')<3600*12:
            with open('zyxel_models.txt','r',encoding='utf-8') as fin:
                lines = fin.read()
            allModels=[_ for _ in lines.splitlines()]
            allModels=[_.strip() for _ in allModels if _.strip()]
            return

        # click 'Enter model number here'
        btn = waitClickable('button[data-id=modelName]')
        btn.click()
        time.sleep(0.1)
        inp = waitClickable('.form-control')
        inp.click()
        inp.send_keys(Keys.UP)
        time.sleep(0.1)
        inp.send_keys(Keys.UP)
        oldNumModels = getNumElem('div.dropdown-menu.open ul li a')
        while True:
            inp.send_keys(Keys.UP)
            time.sleep(0.1)
            inp.send_keys(Keys.UP)
            numModels = getNumElem('div.dropdown-menu.open ul li a')
            ulog('numModels=%d'%numModels)
            if numModels == oldNumModels:
                break
            oldNumModels = numModels
        allModels = [_.text for _ in getElems('div.dropdown-menu.open ul li a')]
        allModels = [_.strip() for _ in allModels if _.strip()]
        allModels = [_ for _ in allModels if not _.lower().startswith('enter model ')]
        ulog('len(allModels)=%d'%len(allModels))

        with open('zyxel_models.txt','w',encoding='utf-8') as fout:
            fout.write('\n'.join(_ for _ in allModels))
        btn.click()

    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()
        driver.save_screenshot(getScriptName()+'_'+getFuncName()+'_excep.png')

def main():
    global startTrail, prevTrail,driver,conn
    try:
        startTrail = [int(re.search(r'\d+', _).group(0)) for _ in sys.argv[1:]]
        ulog('startTrail=%s'%startTrail)
        conn=sqlite3.connect('zyxel.sqlite3')
        sql("CREATE TABLE IF NOT EXISTS TFiles("
            "id INTEGER NOT NULL,"
            "model TEXT," # NBG5715
            "prod_name TEXT," # NBG5715
            "fw_ver TEXT," # V1.00(AAAG.8)C0
            "rel_date DATE," # 06-18-2015
            "image_url TEXT," # http://www2.zyxel.com/uploads/images/img_nbg5715_p_01_380.gif
            "page_url TEXT," # http://www2.zyxel.com/us/en/support/DownloadLandingSR.shtml?c=us&l=en&kbid=M-00022&md=NBG5715#searchZyxelTab4
            "file_url TEXT," # ftp://ftp2.zyxel.com/NBG5715/firmware/NBG5715_V1.00(AAAG.8)C0.zip
            "tree_trail TEXT," # [26, 2, 1, 0, 0]
            "file_size INTEGER," # 
            "file_sha1 TEXT," # 5d3bc16eec2f6c34a5e46790b513093c28d8924a
            "PRIMARY KEY (id)"
            "UNIQUE(model,fw_ver)"
            ")")
        driver=harvest_utils.getFirefox()
        # driver.implicitly_wait(2.0)
        harvest_utils.driver=driver
        prevTrail=[]
        goToUrl(rootUrl)
        getAllModels()
        modelWalker()
        driver.quit()
        conn.close()
    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()
        driver.save_screenshot(getScriptName()+'_'+getFuncName()+'_excep.png')

if __name__=='__main__':
    try:
        main()
    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()
        try:
            driver.save_screenshot(getScriptName()+'_excep.png')
            driver.quit()
        except Exception:
            pass
