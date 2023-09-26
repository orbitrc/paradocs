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

from paradocs_lib import Markdown, CppCode, MemberType, MemberFunction


class Xml:
    def __init__(self, root):
        self._root = root

    @staticmethod
    def plain_text(tree):
        '''Extract plain text from the tag.'''
        txt = tree.text or ''

        for child in tree:
            txt += Xml.plain_text(child)
            txt += child.tail or ''

        return txt

    @staticmethod
    def find_tag(tree, name):
        '''Return the tag with the given name.'''
        if tree.tag == name:
            return tree
        for child in tree:
            found = Xml.find_tag(child, name)
            if found is not None:
                return found
        return None

    @staticmethod
    def filter_tags(tree, name, attribs=None):
        '''Return the list of the given name tag. Not recursive.'''
        if attribs is None:
            return list(filter(lambda x: x.tag == name, tree))
        else:
            ret = []
            filtered = list(filter(lambda x: x.tag == name, tree))
            for key in attribs:
                value = attribs[key]
                has_attrib_tags = filter(
                    lambda x: key in x.attrib.keys(),
                    filtered
                )
                match_tags = filter(
                    lambda x: x.attrib[key] == value,
                    has_attrib_tags
                )
                ret += list(match_tags)
            return ret


class DoxygenClassXml:
    def __init__(self, namespace, filename):
        self._namespace = namespace
        self._filename = filename
        self._tree_root = ET.parse(filename).getroot()

    @staticmethod
    def _get_text(tree):
        '''Get text from the tag recursively.'''
        if len(tree) == 0:
            if tree.text is None:
                return ''
            return tree.text
        elif len(tree) > 0:
            return DoxygenClassXml._get_text(tree[0])

    @staticmethod
    def _parse_para(para_tree):
        '''Parse <para> tag in the XML file.'''
        txt = para_tree.text or ''
        for tag in para_tree:
            txt += DoxygenClassXml._get_text(tag)
            txt += tag.tail

        return txt

    @staticmethod
    def _get_tag(tree, name):
        '''Return the tag with the given name.'''
        if tree.tag == name:
            return tree
        for child in tree:
            found = DoxygenClassXml._get_tag(child, name)
            if found is not None:
                return found
        return None

    @staticmethod
    def _plain_text(tree):
        txt = tree.text or ''

        for child in tree:
            txt += DoxygenClassXml._plain_text(child)

        txt += tree.tail or ''

        return txt

    @staticmethod
    def template_param(param_tree):
        text = ''
        text += Xml.plain_text(Xml.find_tag(param_tree, 'type'))
        declname = Xml.find_tag(param_tree, 'declname')
        if declname is not None:
            text += ' ' + Xml.plain_text(declname)

        return text

    def class_name(self, prepend_namespace=False):
        root = self._tree_root
        compounddef = root[0]
        compoundname = None
        for child in compounddef:
            if child.tag == 'compoundname':
                compoundname = child
                break
        name = compoundname.text
        if prepend_namespace is False:
            name = name.replace(f'{self._namespace}::', '')

        return name

    def class_brief(self):
        root = self._tree_root
        compounddef = root[0]
        briefdescription = None
        for child in compounddef:
            if child.tag == 'briefdescription':
                briefdescription = child
        if len(briefdescription) == 0:
            return ''
        return self._parse_para(briefdescription[0])

    def class_template_params(self):
        '''None if not a template class.'''
        root = self._tree_root
        compounddef = root[0]
        templateparamlist = Xml.find_tag(compounddef, 'templateparamlist')
        if templateparamlist is None:
            return None

        param_tags = Xml.filter_tags(templateparamlist, 'param')
        l = []
        for param_tag in param_tags:
            l.append(DoxygenClassXml.template_param(param_tag))

        return l

    def class_member_functions(self) -> List[MemberFunction]:
        '''List of `MemberFunction`.'''
        root = self._tree_root
        compounddef = root[0]
        # Find <sectiondef kind="public-func">.
        public_func = None
        sectiondef_tags = Xml.filter_tags(compounddef, 'sectiondef')
        for sectiondef in sectiondef_tags:
            if sectiondef.attrib['kind'] == 'public-func':
                public_func = sectiondef
                break
        if public_func is None:
            return []

        prev_func = None
        member_funcs = []
        for memberdef in public_func:
            attributes = memberdef.attrib
            class_name = self.class_name()
            name = self._get_tag(memberdef, 'name').text
            type_tag = Xml.filter_tags(memberdef, 'type')[0]
            ret_type = self._plain_text(type_tag).strip()
            # Check if template.
            template_params = []
            templateparamlist = Xml.find_tag(memberdef, 'templateparamlist')
            if templateparamlist is not None:
                for param in templateparamlist:
                    p = DoxygenClassXml.template_param(param)
                    template_params.append(p)
            # Get <param> tags.
            param_tags = Xml.filter_tags(memberdef, 'param')
            args = []
            for param in param_tags:
                arg_str = DoxygenClassXml._plain_text(param).strip()
                arg_str = arg_str.replace('\n', '')
                arg_str = CppCode.normalize_param(arg_str)
                args.append(arg_str)

            # Get brief and detail descriptions.
            brief = Xml.filter_tags(memberdef, 'briefdescription')[0]
            brief = DoxygenClassXml._plain_text(brief).strip()
            detail = Xml.filter_tags(memberdef, 'detaileddescription')[0]
            detail = DoxygenClassXml._plain_text(detail).strip()

            member_func = MemberFunction(class_name, name, ret_type, args)
            if attributes['const'] == 'yes':
                member_func.set_const(True)
            if len(template_params) > 0:
                member_func.set_template_params(template_params)
            member_func.set_brief(brief)
            member_func.set_detail(detail)
            # Check overloading.
            if prev_func is not None:
                if prev_func.name == member_func.name:
                    member_func.set_overloading_index(prev_func.overloading_index + 1)
            member_funcs.append(member_func)

            prev_func = member_func

        return member_funcs

    def member_alias_types(self) -> List[MemberType]:
        root = self._tree_root
        compounddef = root[0]
        public_type = Xml.filter_tags(compounddef, 'sectiondef', {
            'kind': 'public-type',
        })
        if len(public_type) == 0:
            return []
        public_type = public_type[0]
        memberdef_typedef_list = Xml.filter_tags(public_type, 'memberdef', {
            'kind': 'typedef',
        })
        ret = []
        for memberdef in memberdef_typedef_list:
            target_type = Xml.plain_text(Xml.find_tag(memberdef, 'type'))
            name = Xml.plain_text(Xml.find_tag(memberdef, 'name'))
            member_type = MemberType(self.class_name(), name, MemberType.KIND_ALIAS)
            member_type.set_type(target_type)
            ret.append(member_type)
        return ret

    def member_enums(self) -> List[MemberType]:
        root = self._tree_root
        compounddef = root[0]
        public_type = Xml.filter_tags(compounddef, 'sectiondef', {
            'kind': 'public-type',
        })
        if len(public_type) == 0:
            return []
        public_type = public_type[0]
        memberdef_enum_list = Xml.filter_tags(public_type,
            'memberdef', { 'kind': 'enum', })
        ret = []
        for memberdef in memberdef_enum_list:
            enum_values = []
            enum_name = Xml.plain_text(Xml.find_tag(memberdef, 'name'))
            enumvalue_list = Xml.filter_tags(memberdef, 'enumvalue')
            for enumvalue in enumvalue_list:
                name = Xml.plain_text(Xml.find_tag(enumvalue, 'name'))
                brief = Xml.plain_text(
                    Xml.find_tag(enumvalue, 'briefdescription'))
                detail = Xml.plain_text(
                    Xml.find_tag(enumvalue, 'detaileddescription'))
                enum_value = {
                    'name': name,
                    'brief': brief.strip(),
                    'detail': detail.strip(),
                }
                enum_values.append(enum_value)
            enum_brief = Xml.plain_text(Xml.filter_tags(memberdef, 'briefdescription')[0])
            enum_detail = Xml.plain_text(Xml.filter_tags(memberdef, 'detaileddescription')[0])
            enum = MemberType(self.class_name(), enum_name, MemberType.KIND_ENUM)
            enum.set_enum_values(enum_values)
            enum.set_brief(enum_brief)
            enum.set_detail(enum_detail)
            ret.append(enum)
        return ret

    def member_types(self):
        return self.member_alias_types() + self.member_enums()


class Class:
    def __init__(self, namespace, name):
        self._namespace = namespace
        self._name = name
        self._include = ''
        self._file = ''
        self._brief = ''
        self._detail = ''
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
    def include(self):
        return self._include

    @property
    def brief(self):
        return self._brief

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

    def h1_table(self):
        txt = '| - | - |\n'
        txt += '|---|---|\n'
        # Escape < and >.
        include = self.include.replace('<', '\\<')
        include = include.replace('>', '\\>')
        txt += f'| Include | {include} |\n'
        return txt

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
        member_types = list(filter(lambda x: x.kind == MemberType.KIND_ENUM, self._member_types))
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
        txt += klass.h1_table()
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
            print(project.index_page())
            print('---------------------------')
            print(project.class_page('EnumTest'))
            print('---------------------------')
            print(project.class_page('TemplateTest'))
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
