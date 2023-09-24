import re

class CppCode:
    '''C++ header code helper class.'''
    @staticmethod
    def normalize_template(code):
        reg_type = '([^< ]+) *<(.+)>'
        reg_brackets = '<(.+)>'

        code = code.strip()
        if code.startswith('<'):
            m = re.search(reg_brackets, code)
            return '<' + CppCode.normalize_template(m.groups()[0]) + '>'
        else:
            m = re.search(reg_type, code)
            if m is None:
                return code
            origin = m.groups()[0].strip()
            return origin + '<' + CppCode.normalize_template(m.groups()[1]) + '>'

    @staticmethod
    def normalize_param(code):
        reg_full = '(const)? *([^& ]+) *(&)? *([\*]+)? *(.+)'
        reg_template = '(<.+>)'

        code = code.strip()
        template_m = re.search(reg_template, code)
        template_brackets = ''
        is_template = False
        if template_m is not None:
            template_brackets = template_m.groups()[0]
            code = code.replace(template_brackets, '')
            template_brackets = CppCode.normalize_template(template_brackets)
            is_template = True
        m = re.search(reg_full, code)
        print(m.groups())
        is_const = m.groups()[0] is not None
        plain_type = m.groups()[1]
        is_ref = m.groups()[2] is not None
        is_ptr = m.groups()[3] is not None
        param_name = m.groups()[4]

        normalized = ''
        if is_const:
            normalized += 'const '
        if is_template:
            print(' - plain_type: "' + plain_type + '"')
            normalized += plain_type + template_brackets
        else:
            normalized += plain_type
        if is_ref:
            normalized += '& '
        if is_ptr:
            normalized += ' *'
        if is_ref or is_ptr:
            normalized += param_name
        else:
            normalized += ' ' + param_name

        return normalized
