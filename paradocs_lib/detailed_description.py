import xml.etree.ElementTree as ET

from .xml_helper import Xml


class DetailedDescription:
    def __init__(self, tree: ET.Element):
        # tree.tag == 'detaileddescription'
        self._tree = tree

        self._since = ''
        self._params = [] # [['name', 'description'],]
        self._description = ''

        self._parse()

    def _parse(self):
        para = Xml.find_tag(self._tree, 'para')
        if para is None:
            return
        # Since tag.
        simplesect = Xml.find_tag(para, 'simplesect')
        if simplesect is not None and simplesect.attrib['kind'] == 'since':
            self._since = Xml.plain_text(simplesect).strip()

        # Params.
        parameterlist = Xml.find_tag(para, 'parameterlist')
        if parameterlist is not None:
            parameteritem_list = Xml.filter_tags(parameterlist,
                'parameteritem')
            for parameteritem in parameteritem_list:
                parametername = Xml.find_tag(
                    parameteritem, 'parametername')
                parameterdescription = Xml.find_tag(
                    parameteritem, 'parameterdescription')
                if parametername is not None and parameterdescription is not None:
                    param = [
                        Xml.plain_text(parametername).strip(),
                        Xml.plain_text(parameterdescription).strip()
                    ]
                    self._params.append(param)

        # Description.
        desc = Xml.plain_text_exclude(para, ['simplesect', 'parameterlist'])
        self._description = desc

    @property
    def since(self) -> str:
        return self._since

    @property
    def description(self) -> str:
        return self._description

    @property
    def params(self):
        return self._params
