import re

class CppCode:
    '''C++ header code helper class.'''
    @staticmethod
    def normalize_template(code):
        reg = '([^< ]+) *<(.+)>'

        code = code.strip()
        m = re.search(reg, code)
        if m is None:
            return code
        origin = m.groups()[0].strip()
        return origin + '<' + CppCode.normalize_template(m.groups()[1]) + '>'
    
    @staticmethod
    def normalize_param(code):
        reg_full = '(const)? *([^&]+) *(&)? *([\*]+)? *(.+)'
        reg_template = '<(.+)>'

        code = code.strip()
        m = re.search(reg_full, code)
        is_const = m.groups()[0] is not None
        plain_type = m.groups()[1]
        is_template = re.search(reg_template, plain_type) is not None
        is_ref = m.groups()[2] is not None
        is_ptr = m.groups()[3] is not None
        param_name = m.groups()[4]

        normalized = ''
        if is_const:
            normalized += 'const '
        if is_template:
            normalized += CppCode.normalize_template(plain_type)
        else:
            normalized += plain_type
        if is_ref:
            normalized += '& '
        if is_ptr:
            normalized += ' *'
        normalized += param_name

        return normalized
