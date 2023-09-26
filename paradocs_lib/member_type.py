from .markdown import Markdown

class MemberType:
    KIND_ALIAS = 0
    KIND_ENUM = 1
    def __init__(self, class_name, name, kind) -> None:
        self._class_name = class_name
        self._name = name
        self._kind = kind
        self._brief = ''
        self._detail = ''

        self._type = '' # Alias type
        # Enum values.
        # [{"name": str, "brief": str, "detail": str}]
        self._enum_values = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def class_name(self) -> str:
        return self._class_name

    @property
    def full_name(self) -> str:
        '''Fully qualified name of the type. Namespace is not included.'''
        return self.class_name + '::' + self.name

    @property
    def kind(self):
        return self._kind

    @property
    def alias_type(self):
        '''Only for KIND_ALIAS.'''
        if self.kind != MemberType.KIND_ALIAS:
            return None
        return self._type

    @property
    def anchor_id(self):
        '''Only for KIND_ENUM.'''
        return f'enum-{self.name.lower()}'

    @property
    def brief(self) -> str:
        return self._brief.strip()

    @property
    def detail(self) -> str:
        return self._detail.strip()

    def set_brief(self, brief: str):
        self._brief = brief

    def set_detail(self, detail: str):
        self._detail = detail

    def set_type(self, alias_type):
        self._type = alias_type

    def set_enum_values(self, enum_values):
        self._enum_values = enum_values

    def heading(self, compatible_mode=True) -> str:
        '''Markdown heading for enum class.'''
        if self.kind == MemberType.KIND_ALIAS:
            return ''
        if compatible_mode == True:
            return f'<h3 id="{self.anchor_id}">{self.name}</h3>'
        else:
            return f'### {self.name} {{#{self._anchor_id}}}'

    def table(self):
        '''Markdown table for values of enum class.'''
        if self.kind == MemberType.KIND_ALIAS:
            return ''
        head = ['Name', 'Description']
        body = []
        for enum_value in self._enum_values:
            name = enum_value['name']
            desc = enum_value['brief']
            if enum_value['detail'] != '':
                desc += '<br />' + enum_value['detail']
            body.append([name, desc])
        return Markdown.table(head, body)

    def description(self):
        '''Brief and detail descriptions for enum class.'''
        text = self.brief + '\n\n'
        text += self.detail + '\n'
        return text
