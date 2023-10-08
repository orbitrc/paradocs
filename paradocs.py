#!/usr/bin/env python3

# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.
# If not, see <https://www.gnu.org/licenses/>.

import os
import sys
import xml.etree.ElementTree as ET

from typing import List

from paradocs_lib import (
    Markdown, CppCode,
    MemberType, MemberFunction,
    TypeDictionary,
    Xml, DoxygenClassXml,
    DetailedDescription,
)


class Class:
    def __init__(self, namespace, name):
        self._namespace = namespace
        self._name = name
        self._include = ''
        self._file = ''
        self._brief = ''
        self._detail: DetailedDescription = None
        self._member_functions = []
        self._template_params = []

        self._member_types = []

    def set_include(self, include):
        self._include = include

    def set_file(self, filename):
        self._file = filename

    def parse_file(self, docdir):
        filepath = docdir + '/' + self._file
        doxygen_class_xml = DoxygenClassXml(self._namespace, filepath)
        self._brief = doxygen_class_xml.class_brief()
        self._member_functions = doxygen_class_xml.class_member_functions()
        self._template_params = doxygen_class_xml.class_template_params() or []
        self._member_types = doxygen_class_xml.member_types()

    @property
    def name(self) -> str:
        '''Fully qualified name without namespace.'''
        return self._name

    @property
    def relative_name(self) -> str:
        return self.name.rsplit('::', 1)[-1]

    @property
    def include(self) -> str:
        '''Header file for using this class. e.g. "<mylib/obj.h>".'''
        return self._include

    @property
    def brief(self):
        return self._brief

    @property
    def detail(self) -> DetailedDescription:
        return self._detail

    @property
    def member_functions(self):
        return self._member_functions

    @property
    def link(self):
        '''Link to this class.'''
        ret = self._name.lower().replace('::', '')

        return ret

    @property
    def filename(self):
        '''Output filename.'''
        return self.link + '.md'

    @property
    def template_params(self):
        return self._template_params

    @property
    def enclosing_class(self) -> str:
        if self.name.find('::') == -1:
            return ''
        split = self.name.rsplit('::', 1)
        return split[0]

    def member_enums(self) -> List[MemberType]:
        '''Filter member types that kind is enum.'''
        f = filter(lambda x: x.kind == MemberType.KIND_ENUM,
            self._member_types)
        return list(f)

    def h1_table(self, type_dictionary: TypeDictionary | None=None):
        # Escape < and >.
        include = self.include.replace('<', '\\<')
        include = include.replace('>', '\\>')

        head = ['-', '-']
        body = [
            ['Include', f'{include}'],
        ]
        # Class hierarchy.
        if self.enclosing_class != '' and type_dictionary is not None:
            text = self.relative_name
            name = self.enclosing_class
            t = type_dictionary.get_type(name)
            while t is not None:
                linked = Markdown.link(t.relative_name, t.link)
                text = f'{linked}::' + text
                t = type_dictionary.get_type(t.enclosing_class)
            body.append(['Hierarchy', text])

        return Markdown.table(head, body)

    def member_functions_table(self):
        txt = '| Return | Declaration |\n'
        txt += '|-------|-------------|\n'
        for member in self._member_functions:
            txt += member.table_row()
        return txt

    def member_types_section(self):
        if len(self._member_types) == 0:
            return ''

        text = '## Member Types\n\n'
        # Aliases.
        aliases = list(filter(lambda x: x.kind == MemberType.KIND_ALIAS, self._member_types))
        if len(aliases) > 0:
            text += '**Aliases**\n\n'
        for alias in aliases:
            text += f'using {alias.name} = {alias.alias_type}\n\n'
        # Enum classes.
        enums = list(filter(lambda x: x.kind == MemberType.KIND_ENUM, self._member_types))
        if len(enums) != 0:
            text += '**Enums**\n\n'
        for enum in enums:
            link = f'#{enum.anchor_id}'
            text += f'enum class {Markdown.link(enum.name, link)}\n\n'

        return text

    def member_type_details_section(self):
        '''Only KIND_ENUM.'''
        member_types: List[MemberType] = list(filter(
            lambda x: x.kind == MemberType.KIND_ENUM,
            self._member_types
        ))
        if len(member_types) == 0:
            return ''

        text = '## Member Type Details\n\n'

        for member_type in member_types:
            text += member_type.heading() + '\n\n'
            text += member_type.description() + '\n'
            text += member_type.table() + '\n\n'

        return text


class Project:
    def __init__(self, filename: str):
        self._filename = filename
        self._name = ''
        self._description = ''
        self._version = ''
        self._namespace = ''
        self._docdir = ''
        self._outdir = 'paradocs'
        self._basepath = '/'
        self._category_trees: List[ET.Element] = []
        self._classes = {} # {"Category": [], ...}
        self._type_dictionary = TypeDictionary()

        self._root = ET.parse(filename).getroot()

    @property
    def basepath(self) -> str:
        return self._basepath

    @property
    def outdir(self) -> str:
        return self._outdir

    @property
    def version(self) -> str:
        return self._version

    @property
    def namespace(self) -> str:
        return self._namespace

    def classes(self) -> List[Class]:
        '''Return classes in a flat list.'''
        ret: List[Class] = []
        for category in self._classes:
            classes = self._classes[category]
            ret = ret + classes

        return ret

    def type_dictionary(self) -> TypeDictionary:
        '''Return TypeDictionary object.'''
        return self._type_dictionary

    def parse_metadata(self):
        root = self._root
        project = root[0]
        self._name = Xml.plain_text(Xml.find_tag(project, 'name'))
        self._description = Xml.plain_text(Xml.find_tag(project, 'description'))
        # Version and namespace.
        version = Xml.find_tag(project, 'version')
        if version is not None:
            self._version = Xml.plain_text(version)
        namespace = Xml.find_tag(project, 'namespace')
        if namespace is not None:
            self._namespace = Xml.plain_text(namespace)
        # Set docdir.
        self._docdir = Xml.plain_text(Xml.find_tag(project, 'docdir'))
        # Set outdir.
        outdir = Xml.find_tag(project, 'outdir')
        if outdir is not None:
            self._outdir = Xml.plain_text(outdir)
        # Set basepath.
        basepath = Xml.find_tag(project, 'basepath')
        if basepath is None:
            self._basepath = '/'
        else:
            self._basepath = Xml.plain_text(basepath)

    def parse_categories(self):
        project = self._root[0]
        categories = Xml.filter_tags(project, 'category')
        self._category_trees = categories

    def parse_category_trees(self):
        for tree in self._category_trees:
            category_name = self._find_category_name(tree)
            self._classes[category_name] = []
            for klass_tree in tree:
                if klass_tree.tag != 'class':
                    continue
                klass_ns = klass_tree.attrib['namespace']
                klass_file = klass_tree.attrib['file']
                klass_name = ''
                klass_include = ''
                for child in klass_tree:
                    if child.tag == 'name':
                        klass_name = child.text
                    elif child.tag == 'include':
                        klass_include = child.text

                klass = Class(klass_ns, klass_name)
                klass.set_include(klass_include)
                klass.set_file(klass_file)
                klass.parse_file(self._docdir)
                self._classes[category_name].append(klass)

                # Type dictionary.
                t = TypeDictionary.Type(klass.name,
                    TypeDictionary.Type.KIND_CLASS)
                self._type_dictionary.add_type(t)
                for enum in klass.member_enums():
                    t = TypeDictionary.Type(enum.full_name,
                        TypeDictionary.Type.KIND_ENUM)
                    self._type_dictionary.add_type(t)

    @staticmethod
    def _find_category_name(category_tree: ET.Element) -> str:
        '''Extract name tag text from the category tag.'''
        for child in category_tree:
            if child.tag == 'name':
                return child.text

        return None

    def index_page(self) -> str:
        txt = '# ' + self._name
        txt = txt + '\n\n'
        txt = txt + Markdown.table(
            ['-', '-'],
            [['Version', self.version], ['Namespace', self.namespace]]
        )
        txt = txt + '\n'
        txt = txt + self._description
        txt = txt + '\n'
        for category in self._classes:
            txt += f'## {category}\n\n'
            class_summaries = []
            for klass in self._classes[category]:
                basepath = self.basepath
                if basepath.endswith('/'):
                    basepath = basepath.rstrip('/')
                class_summaries.append([
                    Markdown.link(klass.name, f'{basepath}/{klass.link}'),
                    klass.brief
                ])
            txt += Markdown.table(['Name', 'Brief'], class_summaries)
            txt += '\n'

        return txt

    def class_page(self, class_name) -> str:
        # Find class.
        klass: Class | None = None
        for category in self._classes:
            class_list = self._classes[category]
            for cls in class_list:
                if cls.name == class_name:
                    klass = cls
        if klass is None:
            print('Class not found.')
            exit(1)

        txt = '# ' + klass.name
        txt += '\n\n'
        if len(klass.template_params) > 0:
            txt += '**template <'
            txt += ', '.join(klass.template_params)
            txt += '>**'
            txt += '\n\n'
        txt += klass.brief
        txt += '\n\n'
        txt += klass.h1_table(self.type_dictionary())
        txt += '\n\n'
        # "## Member Types"
        txt += klass.member_types_section()
        txt += '## Member Functions\n\n'
        txt += klass.member_functions_table()
        txt += '\n'
        txt += klass.member_type_details_section()
        txt += '## Member Function Details\n\n'
        for func in klass.member_functions:
            txt += func.heading() + '\n\n'
            if func.is_template():
                txt += func.template_decl() + '\n\n'
            txt += func.description() + '\n'

        return txt


if __name__ == '__main__':
    project = Project('paradocs.xml')
    project.parse_metadata()
    project.parse_categories()
    project.parse_category_trees()

    if len(sys.argv) >= 2:
        opt = sys.argv[1]
        if opt == '--test':
            print(project.type_dictionary())
            print(project.index_page())
            print('---------------------------')
            print(project.class_page('EnumTest'))
            print('---------------------------')
            print(project.class_page('TemplateTest'))
            print('---------------------------')
            print(project.class_page('Enclosing::Nested'))
            print('---------------------------')
            print(project.class_page('Enclosing'))
            exit(0)
        elif opt == '--version':
            print('Paradocs v0.1.0')
            exit(0)
        elif opt == '--help':
            print('TODO: Add help')
            exit(0)

    # Make directory.
    os.makedirs(project.outdir, exist_ok=True)
    # Index page.
    print('Writing index file...', end='')
    f = open(project.outdir + '/index.md', 'w')
    f.write(project.index_page())
    f.close()
    print(' Done.')
    # Class pages.
    for klass in project.classes():
        print('Writing class file for ' + klass.name + '...', end='')
        f = open(project.outdir + '/' + klass.link + '.md', 'w')
        f.write(project.class_page(klass.name))
        f.close()
        print(' Done.')
