#!/usr/bin/env python3
# coding: utf-8
import harvest_utils
from harvest_utils import waitVisible, waitText, getElems, getFirefox,driver,waitTextChanged, getElemText, elemWithText, waitClickable, waitUntilStable, isReadyState,waitUntil,retryStable,goToUrl
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException, WebDriverException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.action_chains import ActionChains
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
from infix_operator import Infix

css0 = Infix(lambda e,s: e.find_element_by_css_selector(s))
csss = Infix(lambda e,s: e.find_elements_by_css_selector(s))

driver,conn=None,None
category,productName,model='','',''
prevTrail=[]
startTrail=[]

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

def glocals()->dict:
    """ globals() + locals()
    """
    import inspect
    ret = dict(inspect.stack()[1][0].f_locals)
    ret.update(globals())
    return ret

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
    """ txt = '07-18-2014' """
    try:
        m = re.search(r'\d{2}-\d{2}-\d{4}', txt)
        return datetime.strptime(m.group(0), '%m-%d-%Y')
    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()




def upsert(tr:WebElement, fwVer:str):
    global prevTrail,driver
    try:
        trTxt = tr.text
        relDate = guessDate(trTxt)
        downLinks = tr/csss/'td:nth-child(7) div:nth-child(1) > a'
        fileUrls = [_.get_attribute('data-filelink') for _ in downLinks]
        fileUrls = [_ for _ in fileUrls]
        fileUrl = '\n'.join(_ for _ in fileUrls)
        trailStr=str(prevTrail+[idx])
        pageUrl = driver.current_url
        model = waitText('div.container:nth-child(7) > div > div > h2')
        prodName = waitText('div.container:nth-child(7) > div:nth-child(1) > div:nth-child(1) > p:nth-child(2)')
        sql("INSERT OR REPLACE INTO TFiles("
            " model, prod_name, fw_ver, rel_date, "
            " page_url, file_url, tree_trail) VALUES"
            "(:model, :prodName, :fwVer,:relDate, "
            ":pageUrl, :fileUrl, :trailStr)", glocals())
        ulog('UPSERT "%(model)s", "%(fwVer)s", "%(relDate)s", '
            ' "%(fileUrl)s", %(trailStr)s '%glocals())
    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()

def versionWalker(tr:WebElement):
    global driver, prevTrail
    try:
        btn=tr.find_element_by_css_selector('button')
        btn.click()
        time.sleep(0.1)
        waitUnti(lambda:all(_.is_displayed() for _ in tr/csss/'ul li a'))
        versions = tr/csss/'ul li a'
        numVersion = len(versions)
        startIdx = getStartIdx()
        for idx in range(startIdx, numVersions):
            ulog('version idx=%s'%idx)
            fwVer = versions[idx].text.strip()
            versions[idx].click()
            upsert(tr, fwVer)
            if idx < numVersions-1:
                btn.click()
                time.sleep(0.1)
    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()



def rowWalker():
    global driver, prevTrail
    try:
        rows = driver.find_elements_by_css_selector('table.blueTable:nth-child(1) tr')
        waitUntil(lambda:all(_.is_displayed() for _ in rows))
        rows = [_ for _ in rows if _.text.startswith('Firmware')]
        numRows = len(rows)
        startIdx = getStartIdx()
        for idx in range(startIdx, numRows):
            ulog('row idx=%s'%idx)
            if not rows[idx].text.startswith('Firmware\n'):
                continue
            prevTrail += [idx]
            versionWalker(rows[idx])
            prevTrail.pop()
    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()
        

def pageWalker():
    global driver, prevTrail
    try:
        rowWalker()
        nextBtn=waitClickable('.arrowNext')
        nextBtn.click()
        rowWalker()
    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()

def tabWalker():
    global driver, prevTrail
    try:
        tab = elemWithText('li.resp-tab-item', 'DOWNLOAD')
        tab.click()
        time.sleep(0.1)
        numTabs = len(tabs)
        startIdx = getStartIdx()
        for idx in range(startIdx,numTabs):
            ulog('tab idx=%s'%idx)
            if not tabs[idx].text.strip().startswith('DOWNLOAD'):
                continue
            prevTrail+=[idx]
            pageWalker()
    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()


rootUrl='http://www.zyxel.com/us/en/support/download_landing.shtml'
# ALL, Tech Doc, Datasheet, Firmware, Certificate  05-22-2015
rootUrl='http://www.zyxel.com/us/en/support/support_landing.shtml'
# ALL, DOWNLOAD LIBRARY, KNOWLEDGE BASE, 05-22-2015, btn'More'
rootUrl='http://www.zyxel.com/us/en/support/SupportLandingSR.shtml?c=us&l=en'
# ALL, DOWNLOAD LIBRARY, KNOWLEDGE BASE, 05-22-2015, btn'More'
rootUrl='http://www.zyxel.com/support/DownloadLandingSR.shtml?c=gb&l=en&md=NSA325'
# ALL Tech Doc,Datasheet,Firmware,Software,Certificate, May 22,2015, '.fa-angle-right'

models=[]
def modelWalker():
    global driver, prevTrail, models
    act=ActionChains(driver)
    CSSs = driver.find_elements_by_css_selector
    try:
        startIdx = getStartIdx()
        for idx, model in enumerate(models[startIdx:],len(models)):
            ulog('idx=%s, model="%s"'%(idx,model))
            goToUrl(rootUrl)
            btn=waitClickable('.search-select button')
            act.move_to_element(btn).click(btn).perform()
            inp=waitClickable('.input-block-level')
            act.move_to_element(inp).click(inp).perform()
            act.send_keys(model + Keys.DOWN + Keys.ENTER).perform()
            time.sleep(0.1)
            waitUntil(isReadyState)
            ulog('url='+driver.current_url)
            title = waitText('.lightGrayBg > div > div > div > h2')
            ulog('title='+title) 
            # 'Search by Model Number' or 'No Matches Found'
            if title.startswith('No Matches Found'):
                continue
            prevTrail+=[idx]
            tabWalker()
            prevTrail.pop()
    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()
    



def getAllModels():
    global driver, models
    act=ActionChains(driver)
    numElm=lambda c:driver.execute_script("return $('%s').length"%c)
    try:
        if path.exists('zyxel_models.txt') and \
                path.getsize('zyxel_models.txt')>0 and \
                time.time()-path.getmtime('zyxel_models.txt') < 3600*24*7:
            with open('zyxel_models.txt','r',encoding='utf-8') as fin:
                models=[]
                for _ in fin:
                    models += [_]
            return
        goToUrl(rootUrl)
        btn=waitVisible('.search-select button')
        act.move_to_element(btn).click(btn).perform()
        inp=waitVisible('.input-block-level')
        act.move_to_element(inp).click(inp).perform()
        act.send_keys(Keys.DOWN).perform()
        time.sleep(0.1)
        act.send_keys(Keys.LEFT_CONTROL + Keys.END).perform()
        time.sleep(0.1)
        numModels = numElm('#searchDropUl li')
        uprint('numModels=%s'%numModels)
        while True:
            act.send_keys(Keys.LEFT_CONTROL + Keys.END).perform()
            time.sleep(0.1)
            numModels2 = numElm('#searchDropUl li')
            if numModels == numModels2:
                break
            numModels = numModels2
            uprint('numModels=%s'%numModels)
        uprint('numModels=%s'%numModels)
        models = [_.get_attribute('data') for _ in getElems('#searchDropUl li')]
        models = [_ for _ in models if _]
        uprint('len(models)=%s'%len(models))
        with open('zyxel_models.txt', 'w', encoding='utf-8') as fout:
            for m in models:
                fout.write(m + '\n')
    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()
        driver.save_screenshot(getScriptName()+'_'+getFuncName()+'_excep.png')


def main():
    global startTrail, prevTrail,driver,conn,models
    try:
        startTrail = [int(re.search(r'\d+', _).group(0)) for _ in sys.argv[1:]]
        ulog('startTrail=%s'%startTrail)
        conn=sqlite3.connect('zyxel.sqlite3')
        sql("CREATE TABLE IF NOT EXISTS TFiles("
            "id INTEGER NOT NULL,"
            "model TEXT," # NSA320
            "prod_name TEXT," # 2-Bay Power Media Server
            "fw_ver TEXT," # 4.70(AFO.0)C0
            "rel_date DATE," # '07-18-2014' or 'Jul 18, 2014'
            "file_size INTEGER," # 
            "page_url TEXT," 
            # http://www.zyxel.com/us/en/support/DownloadLandingSR.shtml?c=us&l=en&kbid=MD09138&md=NSA320#searchZyxelTab4
            # http://www.zyxel.com/support/DownloadLandingSR.shtml?c=gb&l=en&kbid=MD09138&md=NSA320
            "file_url TEXT," # data-filelink="ftp://ftp2.zyxel.com/NSA320/firmware/NSA320_4.70(AFO.1)C0.zip"
            "tree_trail TEXT," # [26, 2, 1, 0, 0]
            "file_sha1 TEXT," # 
            "PRIMARY KEY (id)"
            "UNIQUE(model,fw_ver)"
            ")")
        driver=harvest_utils.getFirefox()
        # driver.implicitly_wait(2.0)
        harvest_utils.driver=driver
        prevTrail=[]
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

