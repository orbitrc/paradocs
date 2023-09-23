from typing import List

from .markdown import Markdown

class MemberFunction:
    def __init__(self, class_name, name, type, args) -> None:
        self._class_name = class_name
        self._name = name
        self._type = type
        self._args = args
        self._const = False
        self._overloading_index = 0
        self._brief = ''
        self._detail = ''
        self._template_params = [] # e.g. ['typename T', 'int num']

    def set_const(self, const: bool):
        self._const = const

    def set_overloading_index(self, index):
        self._overloading_index = index

    def set_brief(self, brief):
        self._brief = brief

    def set_detail(self, detail):
        self._detail = detail

    def set_template_params(self, params: List[str]):
        self._template_params = params

    def is_constructor(self) -> bool:
        if self._type == '':
            return True
        return False

    def is_template(self) -> bool:
        return len(self._template_params) > 0

    @property
    def name(self):
        return self._name

    @property
    def overloading_index(self):
        return self._overloading_index

    @property
    def anchor_id(self):
        anchor = self._name.lower()
        if self._overloading_index > 0:
            anchor += str(self._overloading_index)

        return anchor

    @property
    def brief(self):
        return self._brief

    @property
    def detail(self):
        return self._detail

    def table_row(self):
        col1 = self._type
        col2 = Markdown.link(self._name, f'#{self.anchor_id}')
        col2 += '('
        col2 += ', '.join(self._args)
        col2 += ')'
        if self._const is True:
            col2 += ' const'

        return f'| {col1} | {col2} |\n'

    def heading(self, compatible_mode=True):
        text = f'{self._type} {self._class_name}::{self._name}('
        text += ', '.join(self._args)
        text += ')'
        if self._const is True:
            text += ' const'

        ret = ''
        if compatible_mode is True:
            ret = f'<h3 id="{self.anchor_id}">{text}</h3>'
        else:
            ret = f'### {text} {{#{self._anchor_id}}}'

        return ret

    def description(self):
        text = self.brief + '\n\n'
        text += self.detail + '\n'

        return text

    def template_decl(self):
        text = '**template <'
        text += ', '.join(self._template_params)
        text += '>**'

        return text
