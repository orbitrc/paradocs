class Markdown:
    '''Markdown helper class.'''
    @staticmethod
    def table(head, data) -> str:
        '''head: [str, str], data: [[str, str]...]'''
        txt = f'| {head[0]} | {head[1]} |\n'
        txt += '|-----------|-----------|\n'
        for pair in data:
            txt += f'| {pair[0]} | {pair[1]} |\n'

        return txt

    @staticmethod
    def link(text, link) -> str:
        return f'[{text}]({link})'
