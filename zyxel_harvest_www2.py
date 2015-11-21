#!/usr/bin/env python3
# coding: utf-8
import harvest_utils
from harvest_utils import waitVisible, waitText, getElems, getFirefox,driver,waitTextChanged, getElemText, elemWithText, waitClickable, waitUntilStable, isReadyState,waitUntil,retryStable
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


driver,conn=None,None
modelName=''
prevTrail=[]
startTrail=[]

def goToUrl(url:str):
    global driver
    ulog('%s'%url)
    driver.get(url)
    waitUntil(isReadyState)

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


def versionWalker():
    global driver,prevTrail,modelName
    try:
        rows = getElems('#Firmware tr')
        rows = [_ for _ in rows if _.text.startswith('Firmware')]
        assert len(rows)==1
        row = rows[0]
        verBtn = row.find_element_by_css_selector('button')
        verBtn.click()
        versions = row.find_elements_by_css_selector('ul li a')
        pageUrl = driver.current_url
        imageUrl=waitVisible('.productPic img.img-responsive').get_attribute('src')
        prodName = [_.text for _ in CSSs('div.sectionTitle p.hidden-xs') if _.text.strip()]
        assert len(prodName)==1
        prodName=prodName[0]
        startIdx = getStartIdx()
        numVersions = len(versions)
        for idx in range(startIdx, numVersions):
            ulog('idx=%s'%idx)
            fwVer = versions[idx].text.strip()
            ulog('click "%s"'%fwVer)
            versions[idx].click()
            time.sleep(0.1)
            ulog('row.text="%s"'%row.text)
            fileUrls = [_.get_attribute('data-filelink') for _ in row.find_elements_by_css_selector(' td:nth-child(7) > a') if _.is_displayed()]
            fileUrl = '\n'.join(_ for _ in fileUrls if _)
            relDate = guessDate(row.text)
            prevTrail+=[idx]
            trailStr=str(prevTrail)
            sql("INSERT OR REPLACE INTO TFiles(model, prod_name, "
                " fw_ver, rel_date, image_url, page_url, file_url, "
                " tree_trail) VALUES (:modelName,:prodName,"
                " :fwVer,:relDate,:imageUrl,:pageUrl,:fileUrl,"
                " :trailStr)",locals())
            ulog('UPSERT "%(modelName)s","%(fwVer)s",%(trailStr)s'%locals())
            prevTrail.pop()
            if idx < numVersions-1:
                verBtn.click()
                versions = row.find_elements_by_css_selector('ul li a')
    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()
        driver.save_screenshot(getScriptName()+'_'+getFuncName()+'_excep.png')



rootUrl='http://www2.zyxel.com/us/en/support/download_landing.shtml'
def modelWalker():
    global driver, prevTrail, modelName
    numElm=lambda c:len(CSSs(c))
    try:
        startIdx = getStartIdx()
        for idx in range(startIdx,sys.maxsize):
            ulog('idx=%s'%idx)
            goToUrl(rootUrl)
            # click 'Enter model number here'
            btn = waitClickable('button[data-id=modelName]')
            btn.click()
            time.sleep(0.1)
            inp = waitClickable('.form-control')
            inp.click()
            for _ in range(idx+1):
                inp.send_keys(Keys.DOWN)
            inp.send_keys(Keys.ENTER)
            time.sleep(0.1)
            newModelName = btn.get_attribute('title')
            if newModelName == modelName:
                break
            modelName = newModelName
            ulog('modelName="%s"'%modelName)

            waitClickable('#searchBtn').click()
            time.sleep(0.1)
            waitUntil(isReadyState)
            # click "Firmware" tab
            tab = elemWithText('li.resp-tab-item','Firmware')
            if not tab:
                ulog('no Firmware tab,bypass!')
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

def main():
    global startTrail, prevTrail,driver,conn
    try:
        startTrail = [int(re.search(r'\d+', _).group(0)) for _ in sys.argv[1:]]
        ulog('startTrail=%s'%startTrail)
        conn=sqlite3.connect('asus.sqlite3')
        sql("CREATE TABLE IF NOT EXISTS TFiles("
            "id INTEGER NOT NULL,"
            "model TEXT," # NBG5715
            "prod_name TEXT," # NBG5715
            "fw_ver TEXT," # V1.00(AAAG.8)C0
            "rel_date DATE," # 06-18-2015
            "image_url TEXT," http://www2.zyxel.com/uploads/images/img_nbg5715_p_01_380.gif
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
