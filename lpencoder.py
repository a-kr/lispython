# coding: utf-8

"""
    Мегажуткий транслятор из лиспоподобного синтаксиса в питон

    Требует pyparsing
"""

import sys
from pyparsing import (
    Word, alphanums, ZeroOrMore, Literal, Suppress, lineEnd,
    OneOrMore, StringEnd, dblQuotedString, oneOf, Forward
)


def set_parse_action(symbol, action, listicize=True):
    """ облегчалка задания парсер экшенов """
    def inner_action(*args):
        s,l,t = args
        try:
            v = action(*t)
        except Exception as e:
            import traceback; traceback.print_exc()
            print action
            print t
            exit(0)
        if not isinstance(v, list) and listicize:
            v = [v]
        return v
    symbol.setParseAction(inner_action)


class Outputter(object):
    """ Штука, генерирующая результирующий код с учетом вложенности """
    def __init__(self, f):
        self.indent = 0
        self.delta_indent = 4
        self.at_new_line = True
        self.f = f

    def write_literal(self, lit):
        if self.at_new_line:
            self.f.write(' ' * self.indent)
            self.at_new_line = False
        else:
            self.f.write('')
        self.f.write(lit)

    def n(self):
        self.f.write('\n')
        self.at_new_line = True

    def replay(self, recorder):
        for action in recorder.out_actions:
            if action == 'n':
                self.n()
            elif action == 'indent':
                self.indent += 4
            elif action == 'unindent':
                self.indent -= 4
            elif isinstance(action, OutputRecorder):
                self.replay(action)
            elif isinstance(action, list):
                for a in action:
                    if isinstance(a, basestring):
                        self.write_literal(a)
                    elif isinstance(a, OutputRecorder):
                        self.replay(a)
                    else:
                        print a, repr(a), type(a)
                        assert False
            elif isinstance(action, basestring):
                self.write_literal(action)
            else:
                assert False

class OutputRecorder(object):
    """ Штука, записывающая команды для генерации результирующего кода """
    def __init__(self):
        self.out_actions = []

    def __lshift__(self, things):
        self.out_actions.append(things)


class List(object):
    """ Временная штука для хранения списка """
    def __init__(self, orig_repr):
        self.orig = orig_repr
        self.out = OutputRecorder()

def parse_list(*items):
    """ штука, генерящая питоновский код по различным лисповым спискам """
    l = List(items)
    __ = lambda item: item.out if isinstance(item, List) else item
    if len(items) == 0:
        return l
    if items[0] == 'def':
        l.out << ['def ', items[1] + '(' + ', '.join(items[2].orig) + '):']
        l.out << 'n'
        l.out << 'indent'
        if len(items) < 3:
            l.out << ['pass']
        else:
            for item in items[3:]:
                l.out << __(item)
                l.out << 'n'
        l.out << 'unindent'
    elif items[0] == 'lambda':
        l.out << ['lambda ', ', '.join(items[1].orig) + ': ']
        if len(items) < 3:
            l.out << ['None']
        else:
            l.out << __(items[2])
    elif items[0] == 'class':
        l.out << ['class ', items[1] + '(' + ', '.join(items[2].orig) + '):']
        l.out << 'n'
        l.out << 'indent'
        if len(items) < 4:
            l.out << ['pass']
        else:
            for item in items[3:]:
                l.out << __(item)
                l.out << 'n'
        l.out << 'unindent'
    elif items[0] == 'while':
        l.out << ['while ', __(items[1]), ':']
        l.out << 'n'
        l.out << 'indent'
        if len(items) == 1:
            l.out << ['pass']
        else:
            for item in items[2:]:
                l.out << __(item)
                l.out << 'n'
        l.out << 'unindent'
    elif items[0] == 'for':
        l.out << ['for ', ', '.join(items[1].orig), ' in ', __(items[2]), ':']
        l.out << 'n'
        l.out << 'indent'
        if len(items) < 4:
            l.out << ['pass']
        else:
            for item in items[3:]:
                l.out << __(item)
                l.out << 'n'
        l.out << 'unindent'
    elif items[0] == 'if':
        l.out << ['if ', __(items[1]), ':']
        l.out << 'n'
        l.out << 'indent'
        if len(items[2].orig) == 0:
            l.out << ['pass']
        else:
            for item in items[2].orig:
                l.out << __(item)
                l.out << 'n'
        l.out << 'unindent'
        if len(items) > 3:
            l.out << ['else:']
            l.out << 'n'
            l.out << 'indent'
            if len(items[3].orig) == 0:
                l.out << ['pass']
            else:
                for item in items[3].orig:
                    l.out << __(item)
                    l.out << 'n'
            l.out << 'unindent'
    elif items[0] in _Operators:
        l.out << [__(items[1]), ' ', items[0], ' ', __(items[2])]
    elif items[0] in ('return', 'import'):
        l.out << [items[0] + ' ']
        if len(items) > 1:
            l.out << [__(items[1])]
    elif items[0] in ('break', 'continue'):
        l.out << [items[0]]
    else:
        if isinstance(items[0], basestring):
            l.out << [items[0], '(']
        else:
            l.out << ['(', __(items[0]), ')(']
        if len(items) > 1:
            for i in items[1:-1]:
                l.out << [__(i), ', ']
            l.out << [__(items[-1])]
        l.out << [')']
    return l

# недограмматика недолиспа

_LP = Suppress(Literal("("))
_RP = Suppress(Literal(")"))
_List = Forward()
_Operators = ('+', '-', '*', '/', '&', '^', '%', '>', '<', '<=', '>=', '=', '==')
_Thingy = Word(alphanums + '_.') ^ oneOf(_Operators) ^ dblQuotedString ^ _List
_List << _LP + ZeroOrMore(_Thingy) + _RP
_LispProgram = OneOrMore(_List) + StringEnd()
set_parse_action(_List, parse_list)

def lisp_to_python(lisp_text):
    """ на входе - код на лиспе, на выходе - код на питоне """
    thing = _LispProgram.parseString(lisp_text)
    from cStringIO import StringIO
    io = StringIO()

    for t in thing:
        writer = Outputter(io)
        writer.replay(t.out)
        io.write('\n')
    return io.getvalue()



test_1 = """
(def test (x)
    (print "hi" (+ x 2))
)
(def mkthing (y)
    (if (>= y 16)
        ((return (/ 2 y)))
    )
    (return (* 2 y))
)
(test (mkthing 25))
"""

test_2 = """
(= s 0)
(= m 1)
(for (i) (xrange 1 10)
    (= s (+ s i))
    (= m (* m i))
)
(print s m)
"""

test_3 = """
((lambda (x) (* x x)) 4)
"""

test_4 = """
(class Quak (object)
    (def __init__ (self x)
        (= self.x x)
    )
    (def quak (self)
        (return (* 2 self.x))
    )
)
(= q (Quak 4))
(print (q.quak))
"""

#=================================================================

# магия кастомного энкодинга

import codecs, cStringIO, encodings
from encodings import utf_8

class StreamReader(utf_8.StreamReader):
    def __init__(self, *args, **kwargs):
        codecs.StreamReader.__init__(self, *args, **kwargs)
        lines = []
        while True:
            line = self.stream.readline()
            if not line:
                break
            lines.append(line)

        data = lisp_to_python(''.join(lines))
        self.stream = cStringIO.StringIO(data)

def search_function(s):
    if s!='lispython': return None
    utf8=encodings.search_function('utf8') # Assume utf8 encoding
    return codecs.CodecInfo(
        name='lispython',
        encode = utf8.encode,
        decode = utf8.decode,
        incrementalencoder=utf8.incrementalencoder,
        incrementaldecoder=utf8.incrementaldecoder,
        streamreader=StreamReader,
        streamwriter=utf8.streamwriter)

codecs.register(search_function)


if __name__ == '__main__':
    # притворяемся что написали тесты
    for src in test_1, test_2, test_3, test_4:
        py = lisp_to_python(src)
        print py
        print '---------------'


