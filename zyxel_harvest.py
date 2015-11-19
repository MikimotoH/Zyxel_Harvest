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
    """ txt = '2015/11/06' """
    try:
        m = re.search(r'\d{4}/\d{2}/\d{2}', txt)
        return datetime.strptime(m.group(0), '%Y/%m/%d')
    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()
def guessFileSize(txt:str)->int:
    """ txt='27.29 MBytes'
    """
    try:
        m = re.search(r'(\d+\.?\d+)\s*(MB|KB)', txt, re.I)
        if not m:
            ulog('error txt="%s"'%txt)
            return 0
        unitDic=dict(MB=1024**2,KB=1024)
        unitTxt = m.group(2).upper()
        return int(float(m.group(1)) * unitDic[unitTxt] )
    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()


def guessVersion(txt:str)->int:
    """ version 3.0.0.4.378.9313 """
    try:
        #m = re.search(r'version:?\s*([\d\.]+)', txt, re.I)
        # if not m:
        m = re.search(r'\d+\.[\d\.]+(_[A-Z]+)?', txt.splitlines()[0], re.I)
        return m.group(0)
    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()


def enterFrame(iframeId:str):
    global driver
    prev_url=driver.current_url
    url=waitVisible('iframe[id=%s]'%iframeId).get_attribute('src')
    ulog('%s => %s'%(prev_url,url))
    driver.get(url)
    try:
        retryUntilTrue(isReadyState, 10, 2)
    except TimeoutException as ex:
        print(ex)
        pass

def fileEnumer():
    global driver,prevTrail,modelName
    CSS=driver.find_element_by_css_selector
    CSSs=driver.find_elements_by_css_selector
    try:
        try:
            waitClickable('#lisupport a',15,1.6).click()
        except TimeoutException:
            driver.save_screenshot('asus_no_firmware_download.png')
            ulog('No firmware download for "%s" !'%modelName)
            return
        enterFrame('ifame_auto_size')
        # click 'Driver & Tools'
        waitClickable('#a_support_tab_Download',40,2).click()
        # switch to frame
        enterFrame('ifame_auto_size')
        # open dropdown list to select "Others" OS
        waitClickable('#mainzone_Download2_btn_select_os',10,1).click()
        retryA(lambda:elemWithText('ul.dropdown-menu.os a', "Others").click())
        try:
            # expand firmware dropdown
            waitClickable('#btn_type_20',20,1).click()
        except TimeoutException:
            driver.save_screenshot('asus_no_firmware_download_2.png')
            ulog('No firmware download for" %s"!'%modelName)
            return
        # retryA(lambda:elemWithText('#download a','Firmware').click(), 20,1)
        waitUntilStable('#div_type_20',3,0.4)
        tables = [_ for _ in CSSs('#div_type_20 table') 
            if getElemText(_).startswith('Description')]
        numTables = len(tables)
        ulog('numTables=%s'%numTables)
        versions = [getElemText(_) for _ in CSSs('#div_type_20 p')]
        assert len(versions)==numTables
        pageUrl=driver.current_url
        startIdx = getStartIdx()
        for idx in range(startIdx, numTables):
            desc = tables[idx].text
            relDate = guessDate(desc)
            fileSize = guessFileSize(desc)
            fwVer = guessVersion(versions[idx])
            fileUrl = tables[idx].find_element_by_css_selector('a').get_attribute('href')
            trailStr=str(prevTrail+[idx])
            sql("INSERT OR REPLACE INTO TFiles("
                " model, fw_ver, rel_date, file_size, fw_desc, "
                " page_url, file_url, tree_trail) VALUES"
                "(:modelName,:fwVer,:relDate, :fileSize, :desc,"
                ":pageUrl, :fileUrl, :trailStr)", glocals())
            ulog('UPSERT "%(modelName)s", "%(fwVer)s", "%(relDate)s", '
                '%(fileSize)s, "%(fileUrl)s", %(trailStr)s '%glocals())
    except Exception as ex:
        ipdb.set_trace()
        traceback.print_exc()
        driver.save_screenshot(getScriptName()+'_'+getFuncName()+'_excep.png')



models=[]
rootUrl='http://www.zyxel.com/us/en/support/support_landing.shtml'

def modelWalker():
    global driver, prevTrail, models
    act=ActionChains(driver)
    try:
        for model in models:
            goToUrl(rootUrl)
            btn=waitVisible('.search-select button')
            act.move_to_element(btn).click(btn).perform()
            inp=waitVisible('.input-block-level')
            act.move_to_element(inp).click(inp).perform()
            act.send_keys(model + Keys.DOWN + Keys.ENTER).perform()
            time.sleep(0.1)
            waitUntil(isReadyState)
            ulog('url='+driver.current_url)
            title = CSS('.lightGrayBg > div > div > div > h2').text
            ulog('title='+title)
            if title.startswith('No Matches Found'):
                continue
            moreBtn=waitVisible('a.moreBtn:nth-child(3)')
            moreBtn.click()

    



def getAllModels():
    global driver, prevTrail, models
    CSSs=driver.find_elements_by_css_selector
    CSS=driver.find_element_by_css_selector
    act=ActionChains(driver)
    numElm=lambda c:driver.execute_script("return $('%s').length"%c)
    try:
        if path.exists('zyxel_models.txt') and path.getsize('zyxel_models.txt')>0:
            with open('zyxel_models.txt','r',encoding='utf-8-sig') as fin:
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
        models = [_.get_attribute('data') for _ in CSSs('#searchDropUl li')]
        models = [_ for _ in models if _]
        uprint('len(models)=%s'%len(models))
        with open('zyxel_models.txt', 'w', encoding='utf-8-sig') as fout:
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
            "product_name TEXT," # 2-Bay Power Media Server
            "fw_ver TEXT," # 4.70(AFO.0)C0
            "rel_date DATE," # 07-18-2014
            "file_size INTEGER," # 
            "page_url TEXT," # http://www.zyxel.com/us/en/support/DownloadLandingSR.shtml?c=us&l=en&kbid=MD09138&md=NSA320#searchZyxelTab4
            "file_url TEXT," # data-filelink="ftp://ftp2.zyxel.com/NSA320/firmware/NSA320_4.70(AFO.1)C0.zip"
            "tree_trail TEXT," # [26, 2, 1, 0, 0]
            "file_sha1 TEXT," # 5d3bc16eec2f6c34a5e46790b513093c28d8924a
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

