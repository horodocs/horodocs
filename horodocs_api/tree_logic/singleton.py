class Singleton(type):
    """Single class allows to make a class unique. Has to be used as a metaclass parameter by another class.
    
    Example:

        a = ClassA()

        b = ClassA()
        
    This class makes it that in this example a = b.
    """

    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]