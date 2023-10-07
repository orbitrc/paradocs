import xml.etree.ElementTree as ET

from typing import List

from .xml_helper import Xml
from .member_function import MemberFunction
from .cpp_code import CppCode
from .member_type import MemberType


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
    def template_param(param_tree):
        text = ''
        text += Xml.plain_text(Xml.find_tag(param_tree, 'type'))
        declname = Xml.find_tag(param_tree, 'declname')
        if declname is not None:
            text += ' ' + Xml.plain_text(declname)

        return text

    @staticmethod
    def description_text(tree: ET.Element) -> str:
        '''Get plain text from tree. Keep backticks.'''
        text = tree.text or ''
        text = text.lstrip()
        for child in tree:
            if child.tag == 'computeroutput':
                text += f'`{Xml.plain_text(child)}`'
            else:
                text += DoxygenClassXml.description_text(child)
            text += child.tail or ''
        text = text.strip()

        return text

    @staticmethod
    def description_text_exclude(tree: ET.Element, exclude) -> str:
        '''Get text from tree. Keep backticks. Exclude tags.'''
        text = tree.text or ''
        text = text.lstrip()
        for child in tree:
            if child.tag in exclude:
                pass
            else:
                if child.tag == 'computeroutput':
                    text += f'`{Xml.plain_text(child)}`'
                else:
                    text += DoxygenClassXml.description_text_exclude(
                        child, exclude)
            text += child.tail or ''
        return text.strip()

    def class_name(self, prepend_namespace=False):
        root = self._tree_root
        compounddef = root[0]
        compoundname = Xml.find_tag(compounddef, 'compoundname')
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
        sectiondef_tags = Xml.filter_tags(compounddef, 'sectiondef',
            {'kind': 'public-func'})
        if len(sectiondef_tags) == 0:
            return []
        public_func = sectiondef_tags[0]

        prev_func = None
        member_funcs = []
        for memberdef in public_func:
            attributes = memberdef.attrib
            class_name = self.class_name()
            name = Xml.find_tag_direct(memberdef, 'name').text
            type_tag = Xml.find_tag_direct(memberdef, 'type')
            ret_type = Xml.plain_text(type_tag).strip()
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
                arg_str = Xml.plain_text(param).strip()
                arg_str = arg_str.replace('\n', '')
                arg_str = CppCode.normalize_param(arg_str)
                args.append(arg_str)

            # Get brief and detail descriptions.
            brief = Xml.filter_tags(memberdef, 'briefdescription')[0]
            brief = DoxygenClassXml.description_text(brief)
            detail = Xml.filter_tags(memberdef, 'detaileddescription')[0]
            detail = DoxygenClassXml.description_text(detail)

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


if __name__ == '__main__':
    xml = '''        <detaileddescription>
<para><simplesect kind="since"><para>0.1 </para>
</simplesect>
<parameterlist kind="param"><parameteritem>
<parameternamelist>
<parametername>nested</parametername>
</parameternamelist>
<parameterdescription>
<para>A <computeroutput><ref refid="classmy_1_1Enclosing_1_1Nested" kindref="compound">Nested</ref></computeroutput> object.</para>
</parameterdescription>
</parameteritem>
</parameterlist>
This function do something with `Some` class. but nobody knows what is the something. </para>
        </detaileddescription>'''

    root = ET.fromstring(xml)
    detail = DoxygenClassXml.description_text_exclude(root,
        ['simplesect', 'parameterlist'])
    print(detail)
