from functools import wraps

def without_wraps(func):
    def __wraper(*args, **kwargs):
        '''this is __wraper'''
        return func(*args, **kwargs)
    return __wraper

@without_wraps
def func_1():
    '''this is test!!!'''
    return "Hello"

# words = without_wraps(func_1).__doc__
# print(words)

print(func_1.__doc__)
print(func_1.__name__)

def with_wraps(f):
    @wraps(f)
    def __wraper(*args, **kwargs):
        '''this is __wraper'''
        return f(*args, **kwargs)
    return __wraper

@with_wraps
def func_1():
    '''this is test!!!'''
    return "Hello"

print(func_1.__doc__)
print(func_1.__name__)