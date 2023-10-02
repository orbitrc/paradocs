from typing import List

class TypeDictionary:
    class Type:
        KIND_ENUM = 'KIND_ENUM'
        KIND_CLASS = 'KIND_CLASS'
        def __init__(self, name: str, kind: str):
            self._name = name
            self._kind = kind

        @property
        def name(self) -> str:
            '''Full name of the type.'''
            return self._name

        @property
        def kind(self):
            return self._kind

        @property
        def enclosing_class(self):
            '''Enclosing class name if the type is nested type.'''
            if self.name.find('::') == -1:
                return ''
            split = self.name.rsplit('::', 1)
            return split[0]

        @property
        def relative_name(self) -> str:
            split = self.name.split('::')
            return split[-1]

        @property
        def link(self) -> str:
            '''Link to other page. Must prepend basepath when using.'''
            if self.kind == self.KIND_CLASS:
                link_name = self.name.lower().replace('::', '')
                return f'/{link_name}'
            else:
                enclosing = self.enclosing_class.lower().replace('::', '')
                anchor = f'enum-{self.relative_name.lower()}'
                link = f'/{enclosing}#{anchor}'
                return link

    def __init__(self):
        self._types: List[TypeDictionary.Type] = []

    def add_type(self, type):
        self._types.append(type)

    def get_type(self, full_type):
        '''Get the type from fully qualified type name.'''
        found = None
        try:
            found = next(filter(lambda x: x.name == full_type, self._types))
        except StopIteration:
            pass
        return found

    def find_types(self, type):
        '''List of relative types.'''
        l = []
        for t in self._types:
            if t.relative_name == type:
                l.append(t)
        return l

    def __str__(self):
        text = '{\n'
        for t in self._types:
            kind = 'Class'
            if t.kind == self.Type.KIND_ENUM:
                kind = 'Enum'
            text += f'  {t.name} -> {kind}\n'
        text += '}'
        return text
