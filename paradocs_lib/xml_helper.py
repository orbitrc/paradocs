import xml.etree.ElementTree as ET

class Xml:
    def __init__(self, root):
        self._root = root

    @staticmethod
    def plain_text(tree: ET.Element):
        '''Extract plain text from the tag.'''
        txt = tree.text or ''

        for child in tree:
            txt += Xml.plain_text(child)
            txt += child.tail or ''

        return txt

    @staticmethod
    def find_tag(tree: ET.Element, name: str):
        '''Return the tag with the given name. Recursive.'''
        if tree.tag == name:
            return tree
        for child in tree:
            found = Xml.find_tag(child, name)
            if found is not None:
                return found
        return None

    @staticmethod
    def filter_tags(tree: ET.Element, name: str, attribs=None):
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
