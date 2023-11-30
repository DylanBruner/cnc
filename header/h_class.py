import inspect

class HeaderClass:
    def __init__(self, header: type):
        self._b_header: type = header
        self._b_child: type = self.__class__

        # make sure that every attribute in the header is in the child including the types
        for attr in header.__annotations__:
            if attr not in self._b_child.__annotations__:
                raise AttributeError(f"Attribute '{attr}' is not in the child class")
            # this code is shit and should be fixed
            elif str(header.__annotations__[attr]).replace('h_', '').split('.')[-1] != str(self._b_child.__annotations__[attr]).replace('h_', '').split('.')[-1]:
                raise AttributeError(f"Attribute '{attr}' in the child class is not the same type as in the header class")

        for item in header.__dict__:
            if item not in self._b_child.__dict__:
                raise AttributeError(f"Attribute '{item}' is not in the child class")
            elif inspect.isfunction(header.__dict__[item]):
                header_func = inspect.getsource(header.__dict__[item]).split('\n')[0]
                child_func = inspect.getsource(self._b_child.__dict__[item]).split('\n')[0]

                # replace anything after the last colon
                header_func = header_func[:header_func.rfind(':') + 1].strip().replace(' ', '')
                child_func = child_func[:child_func.rfind(':') + 1].strip().replace(' ', '')
                
                if header_func.replace('h_','') != child_func.replace('h_', ''):
                    raise AttributeError(f"Function '{item}' in the child class is not the same as in the header class ({header_func} != {child_func})")