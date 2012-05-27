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


class Outputter(object):
    """ Умный писатель.

        Воспроизводит команды, записанные в OutputRecorder, и пишет
        результат в файл, следя за отступами строк.
    """
    def __init__(self, f):
        """ f: файлообразный объект, куда будет осуществляться запись результата """
        self.indent = 0
        self.delta_indent = 4
        self.f = f
        self.at_new_line = True
        # ^^^ флаг новой строки.
        # True => мы находимся на новой строке, но еще ничего на ней не написали.
        # Пока флаг == true, можно изменять уровень вложенности.

    def write_literal(self, lit):
        """ пишем строку-литерал без преобразований в файл. """
        if self.at_new_line:
            # если текущая строка в файле пока пуста - запишем в нее отступ
            self.f.write(' ' * self.indent)
            self.at_new_line = False
        self.f.write(lit)

    def n(self):
        """ перевод на новую строку """
        self.f.write('\n')
        self.at_new_line = True

    def replay(self, recorder):
        """ Воспроизведение команд, записанных в recorder.
        """
        assert isinstance(recorder, OutputRecorder)

        for action in recorder.out_actions:
            # три служебные команды
            if action == 'n':
                self.n()
            elif action == 'indent':
                self.indent += 4
            elif action == 'unindent':
                self.indent -= 4
            # вложенный рекордер
            elif isinstance(action, OutputRecorder):
                self.replay(action)
            # вложенный список литералов|рекордеров
            # (зачем он нужен? ну, например, чтобы можно было выводить на печать 
            # литерал "indent" без спец-обработки)
            elif isinstance(action, list):
                for a in action:
                    if isinstance(a, basestring):
                        self.write_literal(a)
                    elif isinstance(a, OutputRecorder):
                        self.replay(a)
                    else:
                        print a, repr(a), type(a)
                        assert False
            # пишем литерал
            elif isinstance(action, basestring):
                self.write_literal(action)
            else:
                assert False

class OutputRecorder(object):
    """ Накопитель команд для генерации питоновского кода.
        
        Команды накапливаются в процессе синтаксического анализа.
        Они потом будут скормлены Outputter'у, и он их воспроизведет и запишет результат в файл.

        Почему нельзя сразу писать в файл в процессе анализа?
        Анализ идет снизу вверх, а уровень вложенности "внизу" неизвестен.
    """
    def __init__(self):
        self.out_actions = []

    def __lshift__(self, things):
        self.out_actions.append(things)


class List(object):
    """ Временный объект для хранения лиспового списка """
    def __init__(self, orig_repr):
        """ orig_repr: узел дерева разбора (список поддеревьев), пришедший из pyparsing """
        self.orig = orig_repr
        self.out = OutputRecorder() # тут запомним генерируемый для этого узла код

def parse_list(*items):
    """ генерирует питоновский код по различным лисповым спискам
        непосредственно в процессе парсинга (parser action).

        Вызывается один раз для каждого лиспового списка.

        items: чайлды узла дерева разбора, соответствующего текущему списку
        (если попроще --- элементы списка)

        Возвращает экземпляр List (и соответственно связанный с ним OutputRecorder,
        в котором накоплен сгенерированный для узла код. Этот List становится узлом дерева
        разбора и снова попадет в parse_list при обработке родительского лисп-списка.
        В итоге будет получено дерево из List (и изоморфное дерево из OutputRecorder);
        итоговый код на Python будет получен обходом этого дерева с воспроизведением
        записанных в узлах-OutputRecorder команд.
    """
    l = List(items)
    __ = lambda item: item.out if isinstance(item, List) else item

    if len(items) == 0:
        return l
    if items[0] == 'def':
        # сгенерим код для определения функции
        # (def имя_фции (список формальных параметров) (оператор1) (оператор2) (оператор3) ...)
        l.out << ['def ', items[1] + '(' + ', '.join(items[2].orig) + '):']
        l.out << 'n' # перевод строки
        l.out << 'indent' # увеличение отступа
        if len(items) < 3:
            l.out << ['pass']
        else:
            for item in items[3:]:
                l.out << __(item)
                l.out << 'n'
        l.out << 'unindent'
    elif items[0] == 'lambda':
        # лямбда-выражение (чисто питоновское, не лисповое)
        # (lambda (список формальных параметров) (выражение))
        l.out << ['lambda ', ', '.join(items[1].orig) + ': ']
        if len(items) < 3:
            l.out << ['None']
        else:
            l.out << __(items[2])
    elif items[0] == 'class':
        # описание класса:
        # (class ИмяКласса (список баз) (def ...) (def ...) (def ...) ...)
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
        # (while (условие) (оператор1) (оператор2) (оператор3) ...)
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
        # (for (список переменных которые перед in) контейнер_или_выражение (оператор2) (оператор3) ...)
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
        # с if чуток посложнее - тело ветви надо еще оборачивать в скобочки, т.к. может быть else
        # (if условие ((оператор1) (оператор2) (оп3)...))
        # (if условие ((оператор1) (оператор2) (оп3)...) ((оп1) (оп2) (оп3) ...))   <--- вот это вариант с else
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
        # меняем префиксную форму на инфиксную
        l.out << [__(items[1]), ' ', items[0], ' ', __(items[2])]
        # кстати тут есть косяк с потерей скобок в исходнике и перепутыванием приоритетов.
        # TODO!! FIXME!!! 
    elif items[0] in ('return', 'import'):
        # после этих ключевых слов может идти аргумент
        l.out << [items[0] + ' ']
        if len(items) > 1:
            l.out << [__(items[1])]
    elif items[0] in ('break', 'continue'):
        # просто ключевые слова
        l.out << [items[0]]
    else:
        # все остальное преобразуем в вызов функции а-ля лисп.
        if isinstance(items[0], basestring):
            # первый элемент списка - имя функции
            l.out << [items[0], '(']
        else:
            # первый элемент списка - неведомая штуковина (лямбда-выражение? другой вызов функции?)
            l.out << ['(', __(items[0]), ')(']
        if len(items) > 1:
            for i in items[1:-1]:
                l.out << [__(i), ', ']
            l.out << [__(items[-1])]
        l.out << [')']
    return l

# ====================================================================
# недограмматика недолиспа

def set_parse_action(symbol, action, listicize=True):
    """ облегчалка задания парсер экшенов """
    def inner_action(*args):
        s,l,t = args
        v = action(*t)
        if not isinstance(v, list) and listicize:
            v = [v]
        return v
    symbol.setParseAction(inner_action)

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

#=================================================================
# магия кастомного энкодинга
# взято с http://stackoverflow.com/questions/214881/can-you-add-new-statements-to-pythons-syntax/215697#215697

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

# =========================================================================
# набор примерчиков

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

if __name__ == '__main__':
    # показываем, что примеры конвертируются в питон
    for src in test_1, test_2, test_3, test_4:
        py = lisp_to_python(src)
        print py
        print '---------------'


