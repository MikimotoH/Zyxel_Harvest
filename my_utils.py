# coding=utf-8
import re
import sys
from collections import OrderedDict

def ci_rm(text:str, *patts:str) -> str:
    for pat in patts:
        text = re.sub(re.escape(pat), '', text, flags=re.IGNORECASE | re.UNICODE)
    return text


def rmBlank(args: [str] ) -> [str]:
    return [_ for _ in args if _ and _.strip() ]


def joinNoBlank2(arg1:str, arg2:str):
    return joinNoBlank((arg1, arg2))

def joinNoBlank(args:str) -> str:
    return " ".join( rmBlank( args ) )

def surrPrth(*args: str) -> str:
    s = joinNoBlank(args).strip()
    return "(" + s + ")" if s else ""


def uniq(args):
    return list(frozenset(args))

def cieq(strA:str, strB:str) -> bool:
    if strA is None and strB is None:
        return True
    elif strA is None or strB is None:
        return False
    return strA.lower() == strB.lower()


def cistartswith(strA:str, strB:str) -> bool:
    return strA.lower().startswith(strB.lower())

def dict_plus(dictA: dict, dictB: dict) -> dict:
    dictC = dictA.copy()
    dictC.update(dictB)
    return dictC


def drop(iterator:iter, count:int ):
    for i in range(count):
        next(iterator)


def bmr_eq_w(brand:str, model:str, revision:str, wikidevi_name:str) -> bool:
    if not model : return False
    esc = re.escape
    bmr = esc(brand)+" "+esc(model)+ ((".*" + esc(revision)) if revision else "")
    return bool( re.match(bmr, wikidevi_name, flags=re.IGNORECASE) )

def norm(s: str) -> str:
    if not s:return ''
    return re.sub(r'\ |\.|\(|\)|-|_|/|\,|\:', '', s).lower()

def normstartswith(strA: str, strB: str) -> bool:
    normA = norm(strA)
    normB = norm(strB)
    return normA.startswith(normB) or normB.startswith(normA)

def normeq(strA: str, strB: str) -> bool:
    return norm(strA)==norm(strB)

def normcontains(strA: str, strB: str) -> bool:
    if not strA or not strB:
        return False
    return norm(strB) in norm(strA)

def parens(r:str) -> str:
    return '('+r+')'

def endotrim(s:str, c:str)->str:
    return ''.join(_ for _ in s if _ not in c)


def movedict(d, *args) -> OrderedDict:
    od = OrderedDict()
    for arg in args:
        od[arg] = d[arg]; del d[arg]
    return od

def mergedict(d,e):
    f= OrderedDict(d); f.update(e)
    return f

def curlyBrace(s)->str:
    return '{'+s+'}'

def tryint(s,defval=None)->int:
    try:
        return int(s)
    except ValueError:
        return defval

def safeFileName(s:str) -> str:
    return parse.quote(s, ' (),$#')

def ierase(A:str,B:str)->str:
    """case insensitive erase
    """
    while True:
        i = A.lower().find(B.lower())
        if i==-1:
            return A
        A = A[0:i] + A[i+len(B):]
def iStartsWith(text:str,prefix:str)->bool:
    return text.lower().startswith(prefix.lower())
def uprint(msg:str)->int:
    return sys.stdout.buffer.write((msg+'\n').encode('utf8'))

def strFindEither(text:str, *args:(str))->int:
    r= min(_ if _>=0 else sys.maxsize for _ in (text.find(_) for _ in args))
    return r if r!=sys.maxsize else -1

def in_ignorecase(pat:str, text:str)->bool:
    return text.lower().find(pat.lower()) != -1
def index_ignorecase(text:str, pat:str)->int:
    return text.lower().index(pat.lower())

def gl(localvars):
    d=globals()
    d.update(localvars)
    return d

def ulog(msg:str)->int:
    import inspect
    callerName=inspect.stack()[1][3]
    return uprint(callerName+': '+msg)

def getFuncName()->str:
    import inspect
    return inspect.stack()[1][3]

def absfloor(x:float)->int:
    import math
    r = int(math.floor(abs(x)))
    return r if x>=0 else r

