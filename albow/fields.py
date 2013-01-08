#
#   Albow - Fields
#

from pygame import draw
import pygame
from pygame.locals import K_LEFT, K_RIGHT, K_TAB, K_c, K_v, SCRAP_TEXT, K_UP, K_DOWN
from widget import Widget, overridable_property
from controls import Control

#---------------------------------------------------------------------------


class TextEditor(Widget):

    upper = False
    tab_stop = True

    _text = u""

    def __init__(self, width, upper=None, **kwds):
        Widget.__init__(self, **kwds)
        self.set_size_for_text(width)
        if upper is not None:
            self.upper = upper
        self.insertion_point = None

    def get_text(self):
        return self._text

    def set_text(self, text):
        self._text = text

    text = overridable_property('text')

    def draw(self, surface):
        frame = self.get_margin_rect()
        fg = self.fg_color
        font = self.font
        focused = self.has_focus()
        text, i = self.get_text_and_insertion_point()
        if focused and i is None:
            surface.fill(self.sel_color, frame)
        image = font.render(text, True, fg)
        surface.blit(image, frame)
        if focused and i is not None:
            x, h = font.size(text[:i])
            x += frame.left
            y = frame.top
            draw.line(surface, fg, (x, y), (x, y + h - 1))

    def key_down(self, event):
        if not (event.cmd or event.alt):
            k = event.key
            if k == K_LEFT:
                self.move_insertion_point(-1)
                return
            if k == K_RIGHT:
                self.move_insertion_point(1)
                return
            if k == K_TAB:
                self.attention_lost()
                self.tab_to_next()
                return
            try:
                c = event.unicode
            except ValueError:
                c = ""
            if self.insert_char(c) != 'pass':
                return
        if event.cmd and event.unicode:
            if event.key == K_c:
                try:
                    pygame.scrap.put(SCRAP_TEXT, self.text)
                except:
                    print "scrap not available"

            elif event.key == K_v:
                try:
                    t = pygame.scrap.get(SCRAP_TEXT).replace('\0', '')
                    self.text = t
                except:
                    print "scrap not available"
                #print repr(t)
            else:
                self.attention_lost()

        self.call_parent_handler('key_down', event)

    def get_text_and_insertion_point(self):
        text = self.get_text()
        i = self.insertion_point
        if i is not None:
            i = max(0, min(i, len(text)))
        return text, i

    def move_insertion_point(self, d):
        text, i = self.get_text_and_insertion_point()
        if i is None:
            if d > 0:
                i = len(text)
            else:
                i = 0
        else:
            i = max(0, min(i + d, len(text)))
        self.insertion_point = i

    def insert_char(self, c):
        if self.upper:
            c = c.upper()
        if c <= "\x7f":
            if c == "\x08" or c == "\x7f":
                text, i = self.get_text_and_insertion_point()
                if i is None:
                    text = ""
                    i = 0
                else:
                    text = text[:i - 1] + text[i:]
                    i -= 1
                self.change_text(text)
                self.insertion_point = i
                return
            elif c == "\r" or c == "\x03":
                return self.call_handler('enter_action')
            elif c == "\x1b":
                return self.call_handler('escape_action')
            elif c >= "\x20":
                if self.allow_char(c):
                    text, i = self.get_text_and_insertion_point()
                    if i is None:
                        text = c
                        i = 1
                    else:
                        text = text[:i] + c + text[i:]
                        i += 1
                    self.change_text(text)
                    self.insertion_point = i
                    return
        return 'pass'

    def allow_char(self, c):
        return True

    def mouse_down(self, e):
        self.focus()
        if e.num_clicks == 2:
            self.insertion_point = None
            return

        x, y = e.local
        i = self.pos_to_index(x)
        self.insertion_point = i

    def pos_to_index(self, x):
        text = self.get_text()
        font = self.font

        def width(i):
            return font.size(text[:i])[0]

        i1 = 0
        i2 = len(text)
        x1 = 0
        x2 = width(i2)
        while i2 - i1 > 1:
            i3 = (i1 + i2) // 2
            x3 = width(i3)
            if x > x3:
                i1, x1 = i3, x3
            else:
                i2, x2 = i3, x3
        if x - x1 > (x2 - x1) // 2:
            i = i2
        else:
            i = i1

        return i

    def change_text(self, text):
        self.set_text(text)
        self.call_handler('change_action')

#---------------------------------------------------------------------------


class Field(Control, TextEditor):
    #  type      func(string) -> value
    #  editing   boolean

    empty = NotImplemented
    format = u"%s"
    min = None
    max = None
    enter_passes = False

    def __init__(self, width=None, **kwds):
        min = self.predict_attr(kwds, 'min')
        max = self.predict_attr(kwds, 'max')
        if 'format' in kwds:
            self.format = kwds.pop('format')
        if 'empty' in kwds:
            self.empty = kwds.pop('empty')
        self.editing = False
        if width is None:
            w1 = w2 = ""
            if min is not None:
                w1 = self.format_value(min)
            if max is not None:
                w2 = self.format_value(max)
            if w2:
                if len(w1) > len(w2):
                    width = w1
                else:
                    width = w2
        if width is None:
            width = 100
        TextEditor.__init__(self, width, **kwds)

    def format_value(self, x):
        if x == self.empty:
            return ""
        else:
            return self.format % x

    def get_text(self):
        if self.editing:
            return self._text
        else:
            return self.format_value(self.value)

    def set_text(self, text):
        self.editing = True
        self._text = text
        if self.should_commit_immediately(text):
            self.commit()

    def should_commit_immediately(self, text):
        return False

    def enter_action(self):
        if self.editing:
            self.commit()
        elif self.enter_passes:
            return 'pass'

    def escape_action(self):
        if self.editing:
            self.editing = False
            self.insertion_point = None
        else:
            return 'pass'

    def attention_lost(self):
        self.commit(notify=True)

    def clamp_value(self, value):
        if self.max is not None:
            value = min(value, self.max)
        if self.min is not None:
            value = max(value, self.min)
        return value

    def commit(self, notify=False):
        if self.editing:
            text = self._text
            if text:
                try:
                    value = self.type(text)
                except ValueError:
                    return
                value = self.clamp_value(value)
            else:
                value = self.empty
                if value is NotImplemented:
                    return
            self.value = value
            self.insertion_point = None
            if notify:
                self.change_text(unicode(value))
            else:
                self._text = unicode(value)
            self.editing = False

        else:
            self.insertion_point = None

#    def get_value(self):
#        self.commit()
#        return Control.get_value(self)
#
#    def set_value(self, x):
#        Control.set_value(self, x)
#        self.editing = False

#---------------------------------------------------------------------------


class TextField(Field):
    type = unicode
    _value = u""


class IntField(Field):
    tooltipText = "Point here and use mousewheel to adjust"

    def type(self, i):
        try:
            return eval(i)
        except:
            try:
                return int(i)
            except:
                return 0

    _shift_increment = 16
    _increment = 1

    @property
    def increment(self):
        if key.get_mods() & KMOD_SHIFT:
            return self._shift_increment
        else:
            return self._increment
        return self._increment

    @increment.setter
    def increment(self, val):
        self._increment = val

    def decrease_value(self):
        self.value = self.clamp_value(self.value - self.increment)

    def increase_value(self):
        self.value = self.clamp_value(self.value + self.increment)

    def mouse_down(self, evt):
        if evt.button == 5:
            self.decrease_value()

            self.change_text(str(self.value))

        elif evt.button == 4:
            self.increase_value()
            self.change_text(str(self.value))

        else:
            Field.mouse_down(self, evt)

    allowed_chars = '-+*/<>()0123456789'

    def allow_char(self, c):
        return c in self.allowed_chars

    def should_commit_immediately(self, text):
        try:
            return str(eval(text)) == text
        except:
            return False


class TimeField(Field):
    allowed_chars = ':0123456789 APMapm'

    def format_value(self, hm):
        format = "%d:%02d"
        h, m = hm
        if h >= 12:
            h -= 12
            return format % (h or 12, m) + " PM"
        else:
            return format % (h or 12, m) + " AM"

    def allow_char(self, c):
        return c in self.allowed_chars

    def type(self, i):
        h, m = 0, 0
        i = i.upper()

        pm = "PM" in i
        for a in "APM":
            i = i.replace(a, "")

        parts = i.split(":")

        if len(parts):
            h = int(parts[0])
        if len(parts) > 1:
            m = int(parts[1])

        if pm and h < 12:
            h += 12
        h %= 24
        m %= 60
        return h, m

    def mouse_down(self, evt):
        if evt.button == 5:
            delta = -1
        elif evt.button == 4:
            delta = 1
        else:
            return Field.mouse_down(self, evt)

        (h, m) = self.value
        pos = self.pos_to_index(evt.local[0])
        if pos < 2:
            h += delta
        elif pos < 5:
            m += delta
        else:
            h = (h + 12) % 24

        self.value = (h, m)

    def set_value(self, v):
        h, m = v
        super(TimeField, self).set_value((h % 24, m % 60))

from pygame import key
from pygame.locals import KMOD_SHIFT


class FloatField(Field):
    type = float
    _increment = 1.0
    _shift_increment = 16.0
    tooltipText = "Point here and use mousewheel to adjust"

    allowed_chars = '-+.0123456789f'

    def allow_char(self, c):
        return c in self.allowed_chars

    @property
    def increment(self):
        if key.get_mods() & KMOD_SHIFT:
            return self._shift_increment
        return self._increment

    @increment.setter
    def increment(self, val):
        self._increment = self.clamp_value(val)

    def decrease_value(self):
        self.value = self.clamp_value(self.value - self.increment)

    def increase_value(self):
        self.value = self.clamp_value(self.value + self.increment)

    def mouse_down(self, evt):
        if evt.button == 5:
            self.decrease_value()

            self.change_text(str(self.value))

        elif evt.button == 4:
            self.increase_value()
            self.change_text(str(self.value))

        else:
            Field.mouse_down(self, evt)

#---------------------------------------------------------------------------


class TextEditorWrapped(Widget):

    upper = False
    tab_stop = True

    _text = u""

    def __init__(self, width, lines, upper=None, **kwds):
        Widget.__init__(self, **kwds)
        self.set_size_for_text(width, lines)
        if upper is not None:
            self.upper = upper
        self.insertion_point = None
        self.insertion_step = None
        self.insertion_line = None
        self.selection_start = None
        self.selection_end = None
        self.topLine = 0
        self.dispLines = lines
        self.textChanged = True

    def get_text(self):
        return self._text

    def set_text(self, text):
        self._text = text
        self.textChanged = True

    text = overridable_property('text')
#Text line list and text line EoL index reference
    textL = []
    textRefList = []
        
    def draw(self, surface):
        frame = self.get_margin_rect()
        frameW, frameH = frame.size
        fg = self.fg_color
        font = self.font
        focused = self.has_focus()
        text, i, il = self.get_text_and_insertion_data()
        ip = self.insertion_point

        self.updateTextWrap()

#Scroll the text up or down if necessary
        if self.insertion_line > self.topLine + self.dispLines - 1:
            self.scroll_down()
        elif self.insertion_line < self.topLine:
            self.scroll_up()

#Draw Border
        draw.rect(surface, self.sel_color, pygame.Rect(frame.left,frame.top,frame.size[0],frame.size[1]), 1)

#Draw Selection Highlighting if Applicable
        if focused and ip is None:
            if self.selection_start is None or self.selection_end is None:
                surface.fill(self.sel_color, frame)
            else:
                startLine, startStep = self.get_char_position(self.selection_start)
                endLine, endStep = self.get_char_position(self.selection_end)
                rects = []

                if startLine == endLine:
                    if startStep > endStep:
                        x1, h = font.size(self.textL[startLine][0:endStep])
                        x2, h = font.size(self.textL[startLine][0:startStep])
                        x1 += frame.left
                        x2 += frame.left
                        lineOffset = startLine - self.topLine
                        y = frame.top + lineOffset*h
                        if lineOffset >= 0:
                            selRect = pygame.Rect(x1,y,(x2-x1),h)
                    else:
                        x1, h = font.size(self.textL[startLine][0:startStep])
                        x2, h = font.size(self.textL[startLine][0:endStep])
                        x1 += frame.left
                        x2 += frame.left
                        lineOffset = startLine - self.topLine
                        y = frame.top + lineOffset*h
                        if lineOffset >= 0:
                            selRect = pygame.Rect(x1,y,(x2-x1),h)
                    draw.rect(surface, self.sel_color, selRect)
                elif startLine < endLine:
                    x1, h = font.size(self.textL[startLine][0:startStep])
                    x2, h = font.size(self.textL[endLine][0:endStep])
                    x1 += frame.left
                    x2 += frame.left
                    lineOffsetS = startLine - self.topLine
                    lineOffsetE = endLine - self.topLine
                    lDiff = lineOffsetE - lineOffsetS
                    while lDiff > 1 and lineOffsetS+lDiff >= 0 and lineOffsetS+lDiff < self.dispLines:
                        y = frame.top + lineOffsetS*h + (lDiff-1)*h
                        rects.append(pygame.Rect(frame.left,y,frame.right-frame.left,h))
                        lDiff += -1
                    y = frame.top + lineOffsetS*h
                    if lineOffsetS >= 0:
                        rects.append(pygame.Rect(x1,y,frame.right-x1,h))
                    y = frame.top + lineOffsetE*h
                    if lineOffsetE < self.dispLines:
                        rects.append(pygame.Rect(frame.left,y,x2-frame.left,h))
                    for selRect in rects:
                        draw.rect(surface, self.sel_color, selRect)                            
                elif startLine > endLine:
                    x2, h = font.size(self.textL[startLine][0:startStep])
                    x1, h = font.size(self.textL[endLine][0:endStep])
                    x1 += frame.left
                    x2 += frame.left
                    lineOffsetE = startLine - self.topLine
                    lineOffsetS = endLine - self.topLine
                    lDiff = lineOffsetE - lineOffsetS
                    while lDiff > 1 and lineOffsetS+lDiff >= 0 and lineOffsetS+lDiff < self.dispLines:
                        y = frame.top + lineOffsetS*h + (lDiff-1)*h
                        rects.append(pygame.Rect(frame.left,y,frame.right-frame.left,h))
                        lDiff += -1
                    y = frame.top + lineOffsetS*h
                    if lineOffsetS >= 0:
                        rects.append(pygame.Rect(x1,y,frame.right-x1,h))
                    y = frame.top + lineOffsetE*h
                    if lineOffsetE < self.dispLines:
                        rects.append(pygame.Rect(frame.left,y,x2-frame.left,h))
                    for selRect in rects:
                        draw.rect(surface, self.sel_color, selRect)

# Draw Lines of Text
        h = 0
        for textLine in self.textL[self.topLine:self.topLine + self.dispLines]:
            image = font.render(textLine, True, fg)
            surface.blit(image, frame.move(0,h))
            h += font.size(textLine)[1]

# Draw Cursor if Applicable                
        if focused and ip is not None and i is not None and il is not None:
            if(self.textL):
                x, h = font.size(self.textL[il][:i])
            else:
                x, h = (0, font.size("X")[1])
            x += frame.left
            y = frame.top + h*(il-self.topLine)
            draw.line(surface, fg, (x, y), (x, y + h - 1))

    def key_down(self, event):
        if not (event.cmd or event.alt):
            k = event.key
            if k == K_LEFT:
                self.move_insertion_point(-1)
                return
            if k == K_RIGHT:
                self.move_insertion_point(1)
                return
            if k == K_TAB:
                self.attention_lost()
                self.tab_to_next()
                return
            if k == K_DOWN:
                self.move_insertion_line(1)
                return
            if k == K_UP:
                self.move_insertion_line(-1)
                return
            try:
                c = event.unicode
            except ValueError:
                c = ""
            if self.insert_char(c) != 'pass':
                return
        if event.cmd and event.unicode:
            if event.key == K_c:
                try:
                    pygame.scrap.put(SCRAP_TEXT, self.text)
                except:
                    print "scrap not available"

            elif event.key == K_v:
                try:
                    t = pygame.scrap.get(SCRAP_TEXT).replace('\0', '')
                    if t != None:
                        if self.insertion_point is not None:
                            self.text = self.text[:self.insertion_point] + t + self.text[self.insertion_point:]
                            self.insertion_point += len(t)
                            self.textChanged = True
                            self.sync_line_and_step()
                        elif self.insertion_point is None and (self.selection_start is None or self.selection_end is None):
                            self.text = t
                            self.insertion_point = len(t)
                            self.textChanged = True
                            self.sync_line_and_step()
                        elif self.insertion_point is None and self.selection_start is not None and self.selection_end is not None:
                            self.selection_point = min(self.selection_start,self.selection_end) + len(t)
                            self.text = self.text[:(min(self.selection_start,self.selection_end))] + t + self.text[(max(self.selection_start,self.selection_end)):]
                            self.selection_start = None
                            self.selection_end = None
                            self.textChanged = True
                            self.sync_line_and_step()
                except:
                    print "scrap not available"
                #print repr(t)
            else:
                self.attention_lost()

        self.call_parent_handler('key_down', event)

    def get_text_and_insertion_point(self):
        text = self.get_text()
        i = self.insertion_point
        if i is not None:
            i = max(0, min(i, len(text)))
        return text, i
                
    def get_text_and_insertion_data(self):
        text = self.get_text()
        i = self.insertion_step
        il = self.insertion_line
        if il is not None:
            il = max(0, min(il, (len(self.textL)-1)))
        if i is not None and il is not None and len(self.textL) > 0:
            i = max(0, min(i, len(self.textL[il])-1))
        return text, i, il

    def move_insertion_point(self, d):
        text, i = self.get_text_and_insertion_point()
        if i is None:
            if d > 0:
                i = len(text)
            else:
                i = 0
        else:
            i = max(0, min(i + d, len(text)))
        self.insertion_point = i
        self.sync_line_and_step()

    def sync_line_and_step(self):
        self.updateTextWrap()
        self.sync_insertion_line()
        self.sync_insertion_step()

    def sync_insertion_line(self):
        ip = self.insertion_point
        i = 0

        for refVal in self.textRefList:
            if ip > refVal:
                i += 1
            elif ip <= refVal:
                break
        self.insertion_line = i

    def sync_insertion_step(self):
        ip = self.insertion_point
        il = self.insertion_line

        if ip is None:
            self.move_insertion_point(0)
            ip = self.insertion_point
        if il is None:
            self.move_insertion_line(0)
            il = self.insertion_line

        if il > 0:
            refPoint = self.textRefList[il-1]
        else:
            refPoint = 0
        self.insertion_step = ip - refPoint

    def get_char_position(self, i):
        j = 0

        for refVal in self.textRefList:
            if i > refVal:
                j += 1
            elif i <= refVal:
                break
        line = j

        if line > 0:
            refPoint = self.textRefList[line-1]
        else:
            refPoint = 0
        step = i - refPoint

        return line, step

    def move_insertion_line(self, d):
        text, i, il = self.get_text_and_insertion_data()

        if self.selection_end is not None:
            endLine, endStep = self.get_char_position(self.selection_end)
            il = endLine
            i = endStep
            self.insertion_step = i
            self.selection_end = None
            self.selection_start = None
        if il is None:
            if d > 0:
                if len(self.textL) > 1:
                    self.insertion_line = d
                else:
                    self.insertion_line = 0
            else:
                self.insertion_line = 0
        if i is None:
            self.insertion_step = 0
        elif il+d >= 0 and il+d < len(self.textL):
            self.insertion_line = il+d
        if self.insertion_line > 0:
            self.insertion_point = self.textRefList[self.insertion_line-1] + self.insertion_step
            if self.insertion_point > len(self.text):
                self.insertion_point = len(self.text)
        else:
            if self.insertion_step is not None:
                self.insertion_point = self.insertion_step
            else:
                self.insertion_point = 0
                self.insertion_step = 0

    def insert_char(self, c):
        if self.upper:
            c = c.upper()
        if c <= u"\xff":
            if c == "\x08" or c == "\x7f":
                text, i = self.get_text_and_insertion_point()
                if i is None and (self.selection_start is None or self.selection_end is None):
                    text = ""
                    i = 0
                    self.insertion_line = i
                    self.insertion_step = i
                elif i is None and self.selection_start is not None and self.selection_end is not None:
                    i = min(self.selection_start,self.selection_end)
                    text = text[:(min(self.selection_start,self.selection_end))] + text[(max(self.selection_start,self.selection_end)):]
                    self.selection_start = None
                    self.selection_end = None
                elif i > 0:
                    text = text[:i - 1] + text[i:]
                    i -= 1
                self.change_text(text)
                self.insertion_point = i
                self.sync_line_and_step()
                return
            elif c == "\r" or c == "\x03":
                return self.call_handler('enter_action')
            elif c == "\x1b":
                return self.call_handler('escape_action')
            elif c >= "\x20":
                if self.allow_char(c):
                    text, i = self.get_text_and_insertion_point()
                    if i is None and (self.selection_start is None or self.selection_end is None):
                        text = c
                        i = 1
                    elif i is None and self.selection_start is not None and self.selection_end is not None:
                        i = min(self.selection_start,self.selection_end) + 1
                        text = text[:(min(self.selection_start,self.selection_end))] + c + text[(max(self.selection_start,self.selection_end)):]
                        self.selection_start = None
                        self.selection_end = None
                    else:
                        text = text[:i] + c + text[i:]
                        i += 1
                    self.change_text(text)
                    self.insertion_point = i
                    self.sync_line_and_step()
                    return
        return 'pass'

    def allow_char(self, c):
        return True

    def mouse_down(self, e):
        self.focus()
        if e.button == 1:
            if e.num_clicks == 2:
                self.insertion_point = None
                self.selection_start = None
                self.selection_end = None
                return

            x, y = e.local
            i = self.pos_to_index(x,y)
            self.insertion_point = i
            self.selection_start = None
            self.selection_end = None
            self.sync_line_and_step()

        if e.button == 5:
#            self.scroll_down()
            self.move_insertion_line(1)

        if e.button == 4:
#            self.scroll_up()
            self.move_insertion_line(-1)

    def mouse_drag(self, e):
        x, y = e.local
        i = self.pos_to_index(x,y)

        if self.insertion_point is not None:
            if i != self.insertion_point:
                if self.selection_start is None:
                    self.selection_start = self.insertion_point
                self.selection_end = i
                self.insertion_point = None
        else:
            if self.selection_start is None:
                self.selection_start = i
            else:
                if self.selection_start == i:
                    self.selection_start = None
                    self.selection_end = None
                    self.insertion_point = i
                else:
                    self.selection_end = i
                

    def pos_to_index(self, x, y):
        text = self.get_text()
        textL = self.textL
        textRef = self.textRefList
        topLine = self.topLine
        dispLines = self.dispLines
        font = self.font

        if textL:
            h = font.size("X")[1]
            line = y//h

            if line >= dispLines:
                line = dispLines - 1

            line = line + topLine

            if line >= len(textL):
                line = len(textL) - 1
                
            if line < 0:
                line = 0

            def width(i):
                return font.size(textL[line][:i])[0]

            i1 = 0
            i2 = len(textL[line])
            x1 = 0
            x2 = width(i2)
            while i2 - i1 > 1:
                i3 = (i1 + i2) // 2
                x3 = width(i3)
                if x > x3:
                    i1, x1 = i3, x3
                else:
                    i2, x2 = i3, x3
            if x - x1 > (x2 - x1) // 2:
                i = i2
            else:
                i = i1
            if line > 0:
                i = i + textRef[line-1]
        else:
            i = 0
        return i

    def change_text(self, text):
        self.set_text(text)
        self.textChanged = True
        self.updateTextWrap()
        self.call_handler('change_action')
                
    def scroll_up(self):
        if self.topLine-1 >= 0:
            self.topLine += -1
    
    def scroll_down(self):
        if self.topLine+1 < len(self.textL)-self.dispLines + 1:
            self.topLine += 1
            
    def updateTextWrap(self):
        # Update text wrapping for box
        font = self.font
        frame = self.get_margin_rect()
        frameW, frameH = frame.size
        if(self.textChanged):
            ix = 0
            iz = 0
            textLi = 0
            text = self.text
            textL = []
            textR = []
            while ix < len(text):
                ix += 1
                if ix == '\r' or ix == '\x03' or ix == '\n':
                    print("RETURN FOUND")
                    if len(textL) > textLi:
                        textL[textLi] = text[iz:ix]
                        textR[textLi] = ix
                    else:
                        textL.append(text[iz:ix])
                        textR.append(ix)
                    iz = ix + 1
                    textLi += 1
                segW = font.size(text[iz:ix])[0]
                if segW > frameW:
                    if len(textL) > textLi:
                        textL[textLi] = text[iz:ix-1]
                        textR[textLi] = ix-1
                    else:
                        textL.append(text[iz:ix-1])
                        textR.append(ix-1)
                    iz = ix-1
                    textLi += 1
            if iz < ix:
                if len(textL) > textLi:
                    textL[textLi] = text[iz:ix]
                    textR[textLi] = ix
                else:
                    textL.append(text[iz:ix])
                    textR.append(ix)
                iz = ix
                textLi += 1                             
            textL = textL[:textLi]
            textR = textR[:textLi]
            self.textL = textL
            self.textRefList = textR
            self.textChanged = False

            i = 0
            
#---------------------------------------------------------------------------

class FieldWrapped(Control, TextEditorWrapped):
    #  type      func(string) -> value
    #  editing   boolean

    empty = NotImplemented
    format = u"%s"
    min = None
    max = None
    enter_passes = False

    def __init__(self, width=None, lines=1, **kwds):
        min = self.predict_attr(kwds, 'min')
        max = self.predict_attr(kwds, 'max')
        if 'format' in kwds:
            self.format = kwds.pop('format')
        if 'empty' in kwds:
            self.empty = kwds.pop('empty')
        self.editing = False
        if width is None:
            w1 = w2 = ""
            if min is not None:
                w1 = self.format_value(min)
            if max is not None:
                w2 = self.format_value(max)
            if w2:
                if len(w1) > len(w2):
                    width = w1
                else:
                    width = w2
        if width is None:
            width = 100
        if lines is None:
            lines = 1
        TextEditorWrapped.__init__(self, width, lines, **kwds)

    def format_value(self, x):
        if x == self.empty:
            return ""
        else:
            return self.format % x

    def get_text(self):
        if self.editing:
            return self._text
        else:
            return self.format_value(self.value)

    def set_text(self, text):
        self.editing = True
        self._text = text
        if self.should_commit_immediately(text):
            self.commit()

    def should_commit_immediately(self, text):
        return False

    def enter_action(self):
        if self.editing:
            self.commit()
        elif self.enter_passes:
            return 'pass'

    def escape_action(self):
        if self.editing:
            self.editing = False
            self.insertion_point = None
        else:
            return 'pass'

    def attention_lost(self):
        self.commit(notify=True)

    def clamp_value(self, value):
        if self.max is not None:
            value = min(value, self.max)
        if self.min is not None:
            value = max(value, self.min)
        return value

    def commit(self, notify=False):
        if self.editing:
            text = self._text
            if text:
                try:
                    value = self.type(text)
                except ValueError:
                    return
                value = self.clamp_value(value)
            else:
                value = self.empty
                if value is NotImplemented:
                    return
            self.value = value
            self.insertion_point = None
            if notify:
                self.change_text(unicode(value))
            else:
                self._text = unicode(value)
            self.editing = False

        else:
            self.insertion_point = None

#    def get_value(self):
#        self.commit()
#        return Control.get_value(self)
#
#    def set_value(self, x):
#        Control.set_value(self, x)
#        self.editing = False

#---------------------------------------------------------------------------

class TextFieldWrapped(FieldWrapped):
    type = unicode
    _value = u""
