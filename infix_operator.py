# definition of an Infix operator class                                                                                                                                
# this recipe also works in jython
# calling sequence for the infix is either:
#  x /op/ y
# or
#  x |op| y
# or:
# x <<op>> y

class Infix:
    def __init__(self, function):
        self.function = function
    def __ror__(self, other):
        return Infix(lambda x, self=self, other=other: self.function(other, x))
    def __or__(self, other):
        return self.function(other)
    def __rtruediv__(self, other):
        return Infix(lambda x, self=self, other=other: self.function(other, x))
    def __truediv__(self, other):
        return self.function(other)
    def __rlshift__(self, other):
        return Infix(lambda x, self=self, other=other: self.function(other, x))
    def __rshift__(self, other):
        return self.function(other)
    def __call__(self, value1, value2):
        return self.function(value1, value2)


"""
def regex_group(sent,pat) -> str:
    import re
    m = re.search(pat,sent, re.IGNORECASE)
    return m.group(0) if m else None

rg = Infix(regex_group)
print( 'cve-2002' /rg/ r'\d{4}' )
print( 'cve-2002' /rg/ r'\w+' )
print( 'cve-2002' /rg/ r'\w{9}' )

"""
