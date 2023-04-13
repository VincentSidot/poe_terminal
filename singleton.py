
class _Singleton:
    def __init__(self, obj):
        self.instance = None
        self.obj = obj
    def __call__(self, *args, **kwargs):
        if not self.instance:
            self.instance = self.obj(*args, **kwargs)
        return self.instance

@_Singleton
class SingletonManager:
    def __init__(self) -> None:
        self.obj = {}
    def __getitem__(self, param):
        obj, args, kwargs = param
        if not obj in self.obj:
            self.obj[obj] = obj(*args, **kwargs)
        return self.obj[obj]
    

def Singleton(obj, *args, **kwargs):
    param = (obj, args, kwargs)
    return SingletonManager().__getitem__(param)