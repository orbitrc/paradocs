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
import re
import xml.etree.ElementTree as ET

class Markdown:
    '''Markdown helper class.'''
    @staticmethod
    def table(head, data):
        '''head: [str, str], data: [[str, str]...]'''
        txt = f'| {head[0]} | {head[1]} |\n'
        txt += '|-----------|-----------|\n'
        for pair in data:
            txt += f'| {pair[0]} | {pair[1]} |\n'

        return txt

    @staticmethod
    def link(text, link):
        return f'[{text}]({link})'


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
    def filter_tags(tree, name):
        '''Return the list of the given name tag. Not recursive.'''
        return list(filter(lambda x: x.tag == name, tree))


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

    def class_member_functions(self):
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

    def set_const(self, const):
        self._const = const

    def set_overloading_index(self, index):
        self._overloading_index = index

    def set_brief(self, brief):
        self._brief = brief

    def set_detail(self, detail):
        self._detail = detail

    def set_template_params(self, params):
        self._template_params = params

    def is_constructor(self):
        if self._type == '':
            return True
        return False

    def is_template(self):
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

    @property
    def name(self) -> str:
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


class Project:
    def __init__(self, filename):
        self._filename = filename
        self._name = ''
        self._description = ''
        self._docdir = ''
        self._outdir = 'paradocs'
        self._basepath = '/'
        self._category_trees = []
        self._classes = {} # {"Category": [], ...}

        self._root = ET.parse(filename).getroot()

    @property
    def basepath(self) -> str:
        return self._basepath

    @property
    def outdir(self) -> str:
        return self._outdir

    def parse_metadata(self):
        root = self._root
        project = root[0]
        self._name = Xml.plain_text(Xml.find_tag(project, 'name'))
        self._description = Xml.plain_text(Xml.find_tag(project, 'description'))
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
    def _find_category_name(category_tree):
        '''Extract name tag from the category tag.'''
        for child in category_tree:
            if child.tag == 'name':
                return child.text

        return None

    def index_page(self):
        txt = '# ' + self._name
        txt = txt + '\n\n'
        txt = txt + Markdown.table(['-', '-'],
            [['Version', 'x.y'], ['Namespace', '']])
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

    def class_page(self, class_name):
        # Find class.
        klass = None
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
        txt += '## Member Functions\n\n'
        txt += klass.member_functions_table()
        txt += '\n'
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
    f = open(project.outdir + '/index.md', 'w')
    f.write(project.index_page())
    f.close()
    # Class pages.
