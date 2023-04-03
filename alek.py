#! /bin/python3
##############################################################################
#
#  ALEK - Assembly Learning Emulator for Kids
#
#  Copyright (c) 2023, Christoph Feck <cfeck@kde.org>
#
#  This is free software released under GPL license, either version 3,
#  or (at your option) any later version.
#

from PyQt5.QtCore import Qt, QSize, QPoint, QRect, QLine, pyqtSignal
from PyQt5.QtGui import (QPainter, qRgb, qGray, QColor,
    QPen, QFont, QImage, QPalette, QPolygon)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget,
    QTableWidget, QTableWidgetItem, QTableWidgetSelectionRange,
    QHeaderView, QTabBar, QToolButton, QMenu, QAction, QFrame,
    QStackedWidget)


##############################################################################
#
#  global tables
#

Map = list(range(1000))
Mem = [0] * 1000

NumToChar = [""] * 1000
CharToNum = [4] * 128

NumToBits = [0] * 1000
BitsToNum = [0] * 1000


##############################################################################

def initTables():
    initCharTables()
    initBitsTables()

def initCharTables():
    cmap = (
        "\0\t\n\r\x04 .,!?"
        "+-*:;\"'(/)"
        "#$%&^_~<=>"
        "0123456789"
        "@ABCDEFGHI"
        "JKLMNOPQRS"
        "TUVWXYZ[\\]"
        "`abcdefghi"
        "jklmnopqrs"
        "tuvwxyz{|}"
    )
    for x in range(100):
        char = cmap[x]
        NumToChar[x] = char;
        if ord(char) < 128:
            CharToNum[ord(char)] = x

def initBitsTables():
    for d2 in range(8):
        for d1 in range(8):
            v8 = (d2 * 8 + d1) * 8
            v10 = (d2 * 10 + d1) * 10
            for d0 in range(8):
                bits = v8 + d0
                num = v10 + d0
                NumToBits[num] = bits
                BitsToNum[bits] = num


##############################################################################
#
#  virtual GPU (graphics processing unit)
#

class VirtualGPU:
    def __init__(self):
        self.reset()

    def reset(self):
        self.ColorMap = [0] * 1000
        self.bg_rgb = int("112")
        self.fg_rgb = int("889")
        self.initColorMap()
        self.setVideoMode()
        self.clearVideo()

    def initColorMap(self):
        cmap = []
        for v in range(10):
            u = int(230 * ((v / 8) ** 0.85))
            if u > 255: u = 255
            cmap.append(u)
#        print(cmap)
        for R in range(10):
            for G in range(10):
                for B in range(10):
                    i = 100 * R + 10 * G + B
                    self.ColorMap[i] = qRgb(cmap[R], cmap[G], cmap[B])

    def setVideoMode(self):
        self.vid_w = 10
        self.vid_h = 10
        self.txtmem = 700
        self.txtwide = True
        self.layers = [self.paintSolidBackground, self.paintText]

    def clearVideo(self):
        a = Map[self.txtmem]
        for y in range(self.vid_h):
            for x in range(self.vid_w):
                Mem[a] = 0
                a += 1

    def paintVideo(self, painter, rect):
        for paintLayer in self.layers:
            paintLayer(painter, rect)


##############################################################################
#
#  video layers
#

    def paintSolidBackground(self, painter, rect):
        bg_rgb = self.ColorMap[self.bg_rgb]
        painter.fillRect(rect, QColor(bg_rgb))

    def paintText(self, painter, rect):
        painter.save()
        painter.translate(rect.x(), rect.y())
        font = QFont("Courier")
        cw = rect.width() // self.vid_w
        ch = rect.height() // self.vid_h
        font.setPixelSize((ch * 5) // 6)
        if self.txtwide:
            painter.scale(2, 1)
            cw //= 2
        painter.setFont(font)
        fg_rgb = self.ColorMap[self.fg_rgb]
        painter.setPen(QColor(fg_rgb))
        a = Map[self.txtmem]
        for y in range(self.vid_h):
            for x in range(self.vid_w):
                char = Mem[a]
                a += 1
                if char > 4:
                    crect = QRect(cw * x, ch * y, cw, ch)
                    painter.drawText(crect, Qt.AlignCenter, NumToChar[char])
        painter.restore()


##############################################################################
#
#  virtual CPU (central processing unit)
#

class VirtualCPU:
    class State:
        Error = -1
        Idle = 0
        Running = 1
        Waiting = 2

    class Reg:
        SP = 0
        # 1..8 are R1...R8
        IP = 9
        Zero = 10
        Flags = 11
        Rand = 12
        Clk = 13
        Ver = 14
        Rem = 15
        MHi = 16
        DHi = 17
        T1 = 18
        T2 = 19

    class ComparisonResult:
        LessThan = 1
        GreaterThan = 2
        EqualTo = 4

    def __init__(self):
        self.reset()

    def reset(self):
        self.reg = [0] * 20     # SP, A, B, C, D, R5, R6, R7, R8, IP
                                # 0, SR, RAND, CLK, VER, REM, MHI, DHI, T1, T2
        self.reg[self.Reg.Flags] = self.ComparisonResult.EqualTo
        self.reg[self.Reg.Ver] = 1      # VER
        self.state = self.State.Idle
        self.op = [0] * 10

    def fetch(self):
        ip = self.reg[self.Reg.IP]
        for i in range(10):
            self.op[i] = Mem[Map[ip + i]]
#        print("Fetch", self.op, "from", self.reg[self.Reg.IP])
        self.reg[self.Reg.IP] += self.decode()

    # decode helpers
    def digitX00(self, i): return self.op[i] // 100
    def digit0X0(self, i): return (self.op[i] % 100) // 10
    def digit00X(self, i): return self.op[i] % 10

    # FIXME: this isn't really correct
    def decode(self):
        size = 1
        imm = False
        destEA = False
        srcEA = False
        op = self.op[0]
        if op == 990:
            size += 1
            op = self.op[1]
            if op // 100 in [1, 2, 3, 4, 5, 6]:
                destEA = True
                srcEA = True
                imm = True
        elif op == 890:
            size += 1
            op = self.op[1]
            if op in [1]:
                destEA = True
                srcEA = True
                imm = True
        else:
            if op // 100 in [1, 2, 3, 4, 5, 6]:
                destEA = True
                srcEA = True
            if op // 100 in [7]:
                srcEA = True
            if op // 100 in [1, 2, 3, 4, 5, 6, 7]:
                imm = True  # ADD, SUB, MUL, DIV, MOV, CMP, JMP can have immediate
            elif op // 10 in [94, 96, 97]:
                imm = True  # OUT, PUSH, CALL can have immediate
                srcEA = True
            elif op // 10 in [91, 92, 93]:
                srcEA = True # INC, DEC, IN have an argument (FIXME: but not src?)
            elif op in [987, 989]:
                return 2    # LIB and SYS always have immediate
        if srcEA and op % 10 == 9:
            size += 1
        if destEA and (op // 10) % 10 == 9:
            size += 1
        if imm and op % 10 == 0:
            size += 1
        return size

    def execute(self):
#        print("CPU state:", self.state, "Registers:", self.reg)
        if self.state != self.State.Running:
            return
        self.md = -1
        self.i = 1
        self.execA()
        if self.md != -1:
#            print("Memory dirty at", self.md)
            pass    # check memory updates


##############################################################################
#
#  addressing modes
#

    def ea(self):
        #return self.reg[self.Reg.SP]
        v = self.op[self.i]
        self.i += 1
        # disable advanced modes
        return v
        if v < 900:
            disp = v % 100
            base = self.reg[v / 100]
            if disp == 0:
                # (Indirect)
                return base
            # (Relative)
            base += offset
        else:
            v -= 900
            if v < 90:
                b = v / 10
                i = v % 10
                base = self.reg[b]
                if b == i:
                    # (Streaming)
                    self.reg[b] = (self.reg[b] + 1) % 1000
                    return base
                if b == 0 and i == 9:
                    base = 0
                if i == 0 or i == 9:
                    base += self.op[self.i]
                    self.i += 1
                # (Indexed)
                base += self.reg[i]
            else:
                # (Absolute)
                base = self.op[self.i]
                self.i += 1
                return base
        return base % 1000

    def rs(self, m):                # read src
        if m == 0:
            v = self.op[self.i]     # immediate
            self.i += 1
            return v
        elif m < 5:
            return self.reg[m]
        elif m < 9:
            a = self.reg[m - 4]
            return Mem[Map[a]]
        else:
            a = self.ea()
            return Mem[Map[a]]

    def rd(self, m):                # read dst
        if m < 5:
            return self.reg[m]
        elif m < 9:
            a = self.reg[m - 4]
            return Mem[Map[a]]
        else:
            a = self.ea()
            return Mem[Map[a]]

    def wd(self, m, v):             # write dst
        if m < 5:
            self.reg[m] = v
        elif m < 9:
            a = self.reg[m - 4]
            self.md = a             # memory dirty
            Mem[Map[a]] = v
        else:
            a = self.ea()
            self.md = a
            Mem[Map[a]] = v


##############################################################################
#
#  instruction set A tables
#

    def execA(self):
        [
            self.execX0,
            self.execADD,
            self.execSUB,
            self.execMUL,
            self.execDIV,
            self.execMOV,
            self.execCMP,
            self.execJMPcc,
            self.execA8,
            self.execA9,
        ][self.digitX00(0)]()

    def execA9(self):
        [
            self.execX0, #self.execC90,
            self.execINC,
            self.execDEC,
            self.execX0, #self.execIN,
            self.execX0, #self.execOUT,
            self.execPOP,
            self.execPUSH,
            self.execCALL,
            self.execX0, #self.execA98,
            self.execA99,
        ][self.digit0X0(0)]()

    def execA99(self):
        [
            self.execB990,
            self.execX0, #
            self.execX0, #
            self.execX0, #
            self.execX0, #self.execOUTZ,
            self.execX0, #
            self.execPUSHZ,
            self.execRET,
            self.execNOP,
            self.execHLT,
        ][self.digit00X(0)]()

    def execA8(self):
        [
            self.execX0, #self.execC80,
            self.execX0, #self.execLEA,
            self.execNEG,
            self.execX0, #self.execSI,
            self.execX0, #self.execSO,
            self.execMOVZ,
            self.execCMPZ,
            self.execRETcc,
            self.execX0, #self.execA88,
            self.execX0, #self.execA89,
        ][self.digit0X0(0)]()

    def execA89(self):
        [
            self.execB890,
            self.execX0, #self.execPEA,
            self.execX0,
            self.execX0, #self.execRI,
            self.execX0, #self.execRO,
            self.execX0, #self.execPOPM,
            self.execX0, #self.execPUSHM,
            self.execX0, #self.execLIB,
            self.execX0, #self.execWAIT,
            self.execX0, #self.execSYS,
        ][self.digit00X(0)]()


##############################################################################
#
#  instruction set B tables
#

    def execB990(self):
        self.i += 1
        [
            self.execX0,
            self.execOR,
            self.execXOR,
            self.execAND,
            self.execCLR,
            self.execSHL,
            self.execSHR,
            self.execX0, #self.execSETcc,
            self.execX0, #self.execB9908,
            self.execB9909,
        ][self.digitX00(1)]()

    def execB9909(self):
        [
            self.execX0,
            self.execX0,
            self.execNOT,
            self.execX0,
            self.execX0,
            self.execX0, #self.execSHL1,
            self.execX0, #self.execSHR1,
            self.execX0,
            self.execX0,
            self.execX0, #self.execB99099,
        ][self.digit0X0(1)]()

    def execB890(self):
        self.i += 1
        [
            self.execX0,
            self.execTSTm,
            self.execX0, #self.execSCAN,
            self.execX0, #self.execLEN,
            self.execX0, #self.execCNT,
            self.execX0, #self.execROL,
            self.execX0, #self.execROR,
            self.execX0,
            self.execX0,
            self.execB8909,
        ][self.digitX00(1)]()

    def execB8909(self):
        [
            self.execX0,
            self.execTST,
            self.execX0,
            self.execCTB,
            self.execCTD,
            self.execX0, #self.execROXL,
            self.execX0, #self.execROXR,
            self.execX0, #self.execCLRXcc,
            self.execX0,
            self.execX0, #self.execB89099,
        ][self.digit0X0(1)]()


##############################################################################
#
#  arithmetic instructions
#

    def execADD(self):
        d = self.rd(self.digit0X0(0))
        s = self.rs(self.digit00X(0))
        d = (d + s) % 1000
        self.wd(self.digit0X0(0), d)

    def execSUB(self):
        d = self.rd(self.digit0X0(0))
        s = self.rs(self.digit00X(0))
        d = (d - s) % 1000
        self.wd(self.digit0X0(0), d)

    def execMUL(self):
        d = self.rd(self.digit0X0(0))
        s = self.rs(self.digit00X(0))
        d = (d * s) % 1000
        self.wd(self.digit0X0(0), d)

    def execDIV(self):
        d = self.rd(self.digit0X0(0))
        s = self.rs(self.digit00X(0))
        if s == 0:
            self.state = self.State.Error
            return
        d //= s
        self.wd(self.digit0X0(0), d)

    def execINC(self):
        d = self.rd(self.digit00X(0))
        d = (d + 1) % 1000
        self.wd(self.digit00X(0), d)

    def execDEC(self):
        d = self.rd(self.digit00X(0))
        d = (d - 1) % 1000
        self.wd(self.digit00X(0), d)

    def execNEG(self):
        d = self.rd(self.digit00X(0))
        d = (0 - d) % 1000
        self.wd(self.digit00X(0), d)


##############################################################################
#
#  misc instructions
#

    def execMOV(self):
        s = self.rs(self.digit00X(0))
        d = s
        self.wd(self.digit0X0(0), d)

    def execMOVZ(self):
        d = 0
        self.wd(self.digit00X(0), d)

    def execCMP(self):
        d = self.rd(self.digit0X0(0))
        s = self.rs(self.digit00X(0))
        if d < s:
            c = self.ComparisonResult.LessThan
        elif d > s:
            c = self.ComparisonResult.GreaterThan
        else:
            c = self.ComparisonResult.EqualTo
        self.reg[self.Reg.Flags] = c

    def execCMPZ(self):
        s = self.rs(self.digit00X(0))
        if s >= 500:
            c = self.ComparisonResult.LessThan
        elif s >= 1:
            c = self.ComparisonResult.GreaterThan
        else:
            c = self.ComparisonResult.EqualTo
        self.reg[self.Reg.Flags] = c

    def setIP(self):
        s = self.rs(self.digit00X(0))
        self.reg[self.Reg.IP] = s

    def execJMPcc(self):
        c = self.digit0X0(0)
        if self.reg[self.Reg.Flags] & c:
            self.setIP()


##############################################################################
#
# stack instructions
#

    def popValue(self):
        a = self.reg[self.Reg.SP]
        s = Mem[Map[a]]
        a = (a + 1) % 1000
        self.reg[self.Reg.SP] = a
        return s

    def pushValue(self, s):
        a = self.reg[self.Reg.SP]
        a = (a - 1) % 1000
        Mem[Map[a]] = s
        self.reg[self.Reg.SP] = a

    def execPOP(self):
        d = self.popValue()
        self.wd(self.digit00X(0), d)

    def execPUSH(self):
        s = self.rs(self.digit00X(0))
        self.pushValue(s)

    def execPUSHZ(self):
        s = 0
        self.pushValue(s)

    def execCALL(self):
        s = self.reg[self.Reg.IP]
        self.pushValue(s)
        self.setIP()

    def execRET(self):
        s = self.popValue()
        self.reg[self.Reg.IP] = s

    def execRETcc(self):
        c = self.digit00X(0)
        if self.reg[self.Reg.Flags] & c:
            self.execRET()


##############################################################################
#
#  bit logic instructions
#

    def execOR(self):
        d = self.rd(self.digit0X0(1))
        s = self.rs(self.digit00X(1))
        d = BitsToNum[NumToBits[d] | NumToBits[s]]
        self.wd(self.digit0X0(1), d)

    def execXOR(self):
        d = self.rd(self.digit0X0(1))
        s = self.rs(self.digit00X(1))
        d = BitsToNum[NumToBits[d] ^ NumToBits[s]]
        self.wd(self.digit0X0(1), d)

    def execAND(self):
        d = self.rd(self.digit0X0(1))
        s = self.rs(self.digit00X(1))
        d = BitsToNum[NumToBits[d] & NumToBits[s]]
        self.wd(self.digit0X0(1), d)

    def execCLR(self):
        d = self.rd(self.digit0X0(1))
        s = self.rs(self.digit00X(1))
        d = BitsToNum[NumToBits[d] & ~NumToBits[s]]
        self.wd(self.digit0X0(1), d)

    def execNOT(self):
        d = self.rd(self.digit00X(1))
        d = BitsToNum[NumToBits[d] ^ 0x1FF]
        self.wd(self.digit00X(1), d)


##############################################################################
#
#  bit misc instructions
#

    def execSHL(self):
        d = self.rd(self.digit0X0(1))
        s = self.rs(self.digit00X(1))
        s %= 10
        d = BitsToNum[(NumToBits[d] << s) & 0x1FF]
        self.wd(self.digit0X0(1), d)

    def execSHR(self):
        d = self.rd(self.digit0X0(1))
        s = self.rs(self.digit00X(1))
        s %= 10
        d = BitsToNum[NumToBits[d] >> s]
        self.wd(self.digit0X0(1), d)

    def execBitTest(self, d, s):
        if d == 0:
            c = self.ComparisonResult.LessThan
        elif d == s:
            c = self.ComparisonResult.GreaterThan
        else:
            c = self.ComparisonResult.EqualTo
        self.reg[self.Reg.Flags] = c

    def execTSTm(self):
        d = self.rd(self.digit0X0(1))
        s = self.rs(self.digit00X(1))
        d = BitsToNum[NumToBits[d] & NumToBits[s]]
        execBitTest(d, s)

    def execTST(self):
        d = self.rd(self.digit00X(1))
        execBitTest(d, 777)

    def execCTB(self):
        d = self.rd(self.digit00X(1))
        d = NumToBits[d]
        self.wd(self.digit00X(1), d)

    def execCTD(self):
        d = self.rd(self.digit00X(1))
        d = BitsToNum[d]
        self.wd(self.digit00X(1), d)


##############################################################################
#
#  special instructions
#

    def execNOP(self):
        pass

    def execHLT(self):
        self.state = self.State.Idle

    def execX0(self):
        self.state = self.State.Error


##############################################################################
#
#  ALEK's UI widgets
#

def setHeaderAttributes(header, size, font):
    header.setMinimumSectionSize(10)
    header.setDefaultSectionSize(size)
    header.setDefaultAlignment(Qt.AlignCenter)
    header.setSectionResizeMode(QHeaderView.Fixed)
    header.setFont(font)


def setTableAttributes(table, hlabels, vlabels, hsize, vsize, selectionMode):
    table.setSelectionMode(selectionMode)
    table.setHorizontalHeaderLabels(hlabels)
    table.setVerticalHeaderLabels(vlabels)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    table.setTextElideMode(Qt.ElideNone)
    font = table.font()
    font.setPixelSize(14)
    setHeaderAttributes(table.horizontalHeader(), hsize, font)
    header = table.verticalHeader()
    setHeaderAttributes(header, vsize, font)
    header.setFixedWidth(hsize)


class MemoryWidget(QTableWidget):
    def __init__(self, rows, columns, parent):
        QTableWidget.__init__(self, rows, columns, parent)
        hlabels = []
        for x in range(10):
            hlabels += ["0" + str(x)]
        vlabels = []
        for y in range(10):
            vlabels += [str(10 * y).zfill(3)]
        setTableAttributes(self, hlabels, vlabels, 60, 40, QTableWidget.ExtendedSelection)
        self.setPage(0)

    def setPage(self, page):
        self.page = page
        vlabels = []
        for y in range(10):
            vlabels += [str(100 * self.page + 10 * y).zfill(3)]
        self.setVerticalHeaderLabels(vlabels)
        self.updateCells()

    def updateCells(self):
        for y in range(10):
            for x in range(10):
                self.updateCell(y, x)

    def updateCell(self, y, x):
        v = Mem[Map[100 * self.page + 10 * y + x]]
        item = QTableWidgetItem(str(v).zfill(3))
        item.setTextAlignment(Qt.AlignCenter)
        if v == 0:
            item.setForeground(QColor(0, 0, 0, 60))
        self.setItem(y, x, item)

    def updateCellAddress(self, v):
        if v // 100 != self.page:
            return
        y = (v // 10) % 10
        x = (v % 10)
        self.updateCell(y, x)

    def highlightAddress(self, v):
        y = (v // 10) % 10
        x = (v % 10)
        self.setRangeSelected(QTableWidgetSelectionRange(0, 0, 9, 9), False)
        self.setRangeSelected(QTableWidgetSelectionRange(y, x, y, x), True)


class GenericInspectorWidget(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        w = QTableWidget(3, 10, self)
        hlabels = []
        for x in range(10):
            hlabels += [str(x)]
        vlabels = ["#xx", "x#x", "xx#"]
        setTableAttributes(w, hlabels, vlabels, 60, 40, QTableWidget.SingleSelection)
        self.table = w

    def setItems(l):
        text = l[y][x]
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        if text == "---":
            item.setForeground(QColor(0, 0, 0, 100))
        self.table.setItem(y, x, item)


class CodeInspectorWidget(QTableWidget):
    def __init__(self, rows, columns, parent):
        QTableWidget.__init__(self, rows, columns, parent)
        hlabels = []
        for x in range(10):
            hlabels += [str(x)]
        vlabels = ["Op", "☐⇄", "↢☐"]
        setTableAttributes(self, hlabels, vlabels, 60, 40, QTableWidget.SingleSelection)
        self.setEditTriggers(QTableWidget.NoEditTriggers)

        self.setData([999], 1)

    def setData(self, data, size = 1):
        self.setRangeSelected(QTableWidgetSelectionRange(0, 0, 2, 9), False)
        if size > 0:
            l = [ ["---", "ADD", "SUB", "---", "---", "MOV", "CMP", "JMP", "---", "HLT"] ]
            d = data[0] // 100
            if d in [0, 3, 4, 8, 9]:
                vlabels = ["Op", "---", "---"]
                l += [ ["---", "---", "---", "---", "---", "---", "---", "---", "---", "---"] ]
                l += [ ["---", "---", "---", "---", "---", "---", "---", "---", "---", "---"] ]
            elif d in [1, 2, 5, 6]:
                if d == 5:
                    vlabels = ["Op", "☐↢", "↢☐"]
                elif d == 6:
                    vlabels = ["Op", "☐↣", "↢☐"]
                else:
                    vlabels = ["Op", "☐⇄", "↢☐"]
                l += [ ["---",  "R1",  "R2",  "R3",  "R4","[R1]","[R2]","[R3]","[R4]","[##]"] ]
                l += [ ["###",  "R1",  "R2",  "R3",  "R4","[R1]","[R2]","[R3]","[R4]","[##]"] ]
            elif d in [7]:
                vlabels = ["Op", "if", "↢☐"]
                l += [ ["---",  "<",   ">",   "≠",   "=",   "≤",   "≥",  "any", "---", "---"] ]
                l += [ ["###",  "R1",  "R2",  "R3",  "R4","[R1]","[R2]","[R3]","[R4]","[##]"] ]
            self.setRangeSelected(QTableWidgetSelectionRange(0, d, 0, d), True)
            d = (data[0] % 100) // 10
            self.setRangeSelected(QTableWidgetSelectionRange(1, d, 1, d), True)
            d = data[0] % 10
            self.setRangeSelected(QTableWidgetSelectionRange(2, d, 2, d), True)
        else:
            vlabels = ["#xx", "9#x", "99#"]
            l = [ ["---", "ADD", "SUB", "MUL", "DIV", "MOV", "CMP", "JMP", "---", ">>>"] ]
            l += [ ["---", "INC", "DEC",  "IN", "OUT", "POP","PUSH","CALL", "---", ">>>"] ]
            l += [ ["B1>", "---", "---", "---","OUTZ", "---","PUSHZ","RET", "NOP", "HLT"] ]
        self.setVerticalHeaderLabels(vlabels)
        self.setItems(l)

    def setItems(self, l):
        for y in range(3):
            for x in range(10):
                text = l[y][x]
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                if text == "---":
                    item.setForeground(QColor(0, 0, 0, 100))
                self.setItem(y, x, item)


class TextInspectorWidget(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)

        font = QFont("Courier")
        font.setPixelSize(24)

        font2 = QFont("Courier")
        font2.setPixelSize(16)

        self.characterCodeTables = [None] * 2

        for c in range(2):
            w = QTableWidget(5, 10, self)
            hlabels = []
            for x in range(10):
                hlabels += [str(x)]
            vlabels = []
            for y in range(0 + c * 5, 5 + c * 5):
                vlabels += [str(y) + "0"]
            setTableAttributes(w, hlabels, vlabels, 28, 28, QTableWidget.SingleSelection)
            w.setGeometry(c * 340, 0, 324, 174)
            w.verticalHeader().setFixedWidth(40)
            w.horizontalHeader().setFixedHeight(30)
            w.setEditTriggers(QTableWidget.NoEditTriggers)
            self.characterCodeTables[c] = w
            for y in range(5):
                for x in range(10):
                    v = 50 * c + 10 * y + x
                    s = NumToChar[v]
                    item = QTableWidgetItem()
                    item.setFont(font)
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setTextAlignment(Qt.AlignTop | Qt.AlignHCenter)
                    item.setForeground(QColor(0, 0, 100))
                    if v < 5:
                        s = ["∅", "⇥", "↵", "↤", "⁙"][v]
                        item.setForeground(QColor(0, 0, 0, 100))
                        item.setFont(font2)
                        item.setTextAlignment(Qt.AlignBottom | Qt.AlignHCenter)
                    item.setText(s)
                    w.setItem(y, x, item)
        self.characterCodeTables[0].cellClicked.connect(self.table0Clicked)
        self.characterCodeTables[1].cellClicked.connect(self.table1Clicked)

    codeClicked = pyqtSignal(int)

    def table0Clicked(self, y, x):
        c = y * 10 + x
        self.codeClicked.emit(c)

    def table1Clicked(self, y, x):
        self.table0Clicked(y + 5, x)

    def setData(self, data, size = 1):
        if size != 1:
            return
        for i in range(2):
            w = self.characterCodeTables[i]
            w.setRangeSelected(QTableWidgetSelectionRange(0, 0, 4, 9), False)
        c = data[0]
        if c < 50:
            w = self.characterCodeTables[0]
        else:
            c -= 50
            w = self.characterCodeTables[1]
        y = c // 10
        x = c % 10
        w.setRangeSelected(QTableWidgetSelectionRange(y, x, y, x), True)


class AddrInspectorWidget(QWidget):
    pass


class ColorInspectorWidget(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)


class InspectorTabBar(QTabBar):
    def __init__(self, parent):
        QTabBar.__init__(self, parent)
        self.addTab("Code")
#        self.addTab("Data")
#        self.addTab("Addr")
#        self.addTab("Num")
        self.addTab("Char")
#        self.addTab("Emoji")
#        self.addTab("Color")
#        self.addTab("Pixels")
#        self.addTab("Bits")


class InspectorWidget(QStackedWidget):
    def __init__(self, parent):
        QStackedWidget.__init__(self, parent)
        self.addWidget(CodeInspectorWidget(3, 10, self))
#        self.addWidget(GenericInspectorWidget(self))
#        self.addWidget(GenericInspectorWidget(self))
#        self.addWidget(GenericInspectorWidget(self))
        self.addWidget(TextInspectorWidget(self))
#        self.addWidget(ColorInspectorWidget(self))
#        self.addWidget(GenericInspectorWidget(self))
#        self.addWidget(GenericInspectorWidget(self))
        self.setCurrentIndex(0)

#        self.widget(0).codeClicked.connect(self.codeClicked)
        self.widget(1).codeClicked.connect(self.codeClicked)

    codeClicked = pyqtSignal(int)

#    def codeClicked(self, c):
#        self.codeClicked.emit(c)

    def setData(self, data, size = 1):
        for i in range(2):
            self.widget(i).setData(data, size)


class MemoryTabBar(QTabBar):
    def __init__(self, parent):
        QTabBar.__init__(self, parent)
        self.addTab("Memory  0  ")
        self.addTab("1")
        self.addTab("2")
        self.addTab("3")
        self.addTab("4")
        self.addTab("5")
        self.addTab("6")
        self.addTab("Text  7  ")
        self.addTab("8")
        self.addTab("9")

    def minimumTabSizeHint(self, index):
        size = QTabBar.minimumTabSizeHint(self, index)
        if index in [1, 2, 3, 4, 5, 6, 8, 9]:
            size = QSize(10, size.height())
        return size


class CPUTabBar(QTabBar):
    def __init__(self, parent):
        QTabBar.__init__(self, parent)
        self.addTab("CPU")
        self.setToolTip("Central Processing Unit")


class CPUWidget(QFrame):
    def __init__(self, parent):
        QFrame.__init__(self, parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Sunken)
        self.setLineWidth(2)

        self.regs1 = self.addRegisterFile(["R1", "R2", "R3", "R4", "IP"], QRect(264, 10, 104, 144))
#        self.regs2 = self.addRegisterFile(["R5", "R6", "R7", "R8", "IP"], QRect(368, 10, 104, 144))
        self.regs2 = self.addRegisterFile(["", "", "", "", ""], QRect(368, 10, 104, 144))
        self.regs2.setEnabled(False)
        self.addLatch("Data", 60, 30, 50, QRect(30, 87, 114, 34), "")
        self.addLatch("Addr", 60, 30, 50, QRect(30, 122, 114, 34), "")
        self.addLatch("", 60, 30, 0, QRect(38, 8, 64, 34), "")
        self.addLatch("", 60, 30, 0, QRect(120, 8, 64, 34), "")
        self.cmpR = self.addLatch("CMP", 30, 28, 45, QRect(184, 122, 79, 32), "=")

        self.regs1.cellChanged.connect(self.registerChanged)

        self.old = [-1] * 10

    def addRegisterFile(self, labels, geometry):
        w = QTableWidget(5, 1, self)
        setTableAttributes(w, [], labels, 60, 28, QTableWidget.NoSelection)
        w.verticalHeader().setFixedWidth(40)
        w.horizontalHeader().hide()
        w.setGeometry(geometry)
        return w

    def addLatch(self, label, hsize, vsize, hwidth, geometry, text):
        w = QTableWidget(1, 1, self)
        setTableAttributes(w, [], [label], hsize, vsize, QTableWidget.NoSelection)
        if label == "":
            w.verticalHeader().hide()
        else:
            w.verticalHeader().setFixedWidth(hwidth)
        w.horizontalHeader().hide()
        w.setGeometry(geometry)
        item = QTableWidgetItem(text)
        item.setForeground(QColor(0, 0, 0, 100))
        item.setTextAlignment(Qt.AlignCenter)
        w.setItem(0, 0, item)
        return w

    def paintALU(self, p):
        x = 40
        y = 44
        p.setRenderHints(QPainter.Antialiasing, True)
        p.translate(0.5, 0.5)
        p.setPen(QPen(QColor(0, 0, 0), 0.75))
        p.setBrush(QColor(210, 210, 210))
        p.drawPolygon(QPolygon([
            QPoint(x, y),
            QPoint(x + 60, y),
            QPoint(x + 70, y + 10),
            QPoint(x + 80, y),
            QPoint(x + 140, y),
            QPoint(x + 100, y + 40),
            QPoint(x + 40, y + 40)
        ]))
        p.translate(-0.5, -0.5)
        p.drawText(QRect(x + 40, y + 7, 60, 30), Qt.AlignCenter, "ALU")

    def paintEvent(self, event):
        QFrame.paintEvent(self, event)
        p = QPainter(self)
        self.paintALU(p)

    def registerChanged(self, y, x):
        item = self.regs1.item(y, x)
        if item != None:
            v = 0
            text = item.text()
            if text.isnumeric():
                v = int(text) % 1000
            if y < 4:
                r = y + 1
            else:
                r = 9
            cpu.reg[r] = v
            self.updateState()

    def updateState(self):
        for r in range(10):
            v = cpu.reg[r]
            if self.old[r] != v:
                if r == 0:
                    w, i = self.regs1, 4
                elif r < 5:
                    w, i = self.regs1, r - 1
                elif r < 9:
                    continue
                    w, i = self.regs2, r - 5
                else:
#                    w, i = self.regs2, 4
                    w, i = self.regs1, 4
                item = QTableWidgetItem()
                item.setTextAlignment(Qt.AlignCenter)
                if v == 0:
                    item.setForeground(QColor(0, 0, 0, 100))
                v = str(v).zfill(3)
                if w.item(i, 0) == None or v != w.item(i, 0).text():
                    item.setText(v)
                    w.blockSignals(True)
                    w.setItem(i, 0, item)
                    w.blockSignals(False)
            self.old[r] = v
        self.updateCmpResult()

    def updateCmpResult(self):
        item = QTableWidgetItem()
        text = ["?", "<", ">", "?", "="][cpu.reg[cpu.Reg.Flags]]
        item.setText(text)
        item.setTextAlignment(Qt.AlignCenter)
        self.cmpR.setItem(0, 0, item)


class AnimationWidget(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.xp = 100
        self.yp = 100
        self.xs = 8
        self.ys = 0
        self.clock = 0

    def paintEvent(self, event):
        p = QPainter(self)
#        p.fillRect(QRect(self.xp, self.yp, 60, 30), QColor(255, 0, 0))
        p.setRenderHints(QPainter.Antialiasing, True)
        p.translate(0.5, 0.5)
        p.setPen(QPen(QColor(0, 0, 0), 1.25))
        p.drawLine(QLine(682, 155, 730, 155))
        p.drawLine(QLine(682, 190, 730, 190))
        p.drawLine(QLine(843, 155, 964, 155))
        p.drawPolyline(QPolygon([QPoint(720, 155), QPoint(720, 75), QPoint(738, 75)]))
        p.drawPolyline(QPolygon([QPoint(900, 155), QPoint(900, 75), QPoint(882, 75)]))
        p.drawEllipse(QRect(720 - 2, 155 - 2, 4, 4))
        p.drawEllipse(QRect(900 - 2, 155 - 2, 4, 4))
        p.drawLine(QLine(770, 93, 770, 95))
        p.drawLine(QLine(850, 93, 850, 95))
        p.drawLine(QLine(810, 137, 810, 139))
        p.drawLine(QLine(810, 172, 810, 174))
        p.drawPolyline(QPolygon([QPoint(860, 117), QPoint(870, 117), QPoint(870, 152)]))
        p.drawPolyline(QPolygon([QPoint(870, 158), QPoint(870, 189), QPoint(884, 189)]))
        if self.clock > 0:
            rect = QRect(400, 300, 400, 160)
            p.setPen(QPen(QColor(100, 0, 0), 2.0))
            p.setBrush(QColor(240, 220, 220))
            p.drawRect(rect)
            p.drawText(rect, Qt.AlignCenter, "ERROR! Processor Halted")

    def showError(self):
        self.clock = 90
        self.timer = self.startTimer(33)
        self.update()

    def timerEvent(self, event):
        self.clock -= 1
        if self.clock == 0:
            self.killTimer(self.timer)
            self.update()
        '''
        self.xp += self.xs
        self.yp += self.ys
        if self.xp > self.rect().width() - 65 or self.xp < 5:
            self.xs = -self.xs
        if self.yp > self.rect().height() - 35 or self.yp < 5:
            self.ys = -self.ys
        self.update(QRect(self.xp - 10, self.yp - 10, 80, 50))
        '''


class MenuButton(QToolButton):
    def __init__(self, parent):
        QToolButton.__init__(self, parent)
        self.setPopupMode(QToolButton.InstantPopup)
        self.setText(" ")


class ExecButton(QToolButton):
    def __init__(self, parent):
        QToolButton.__init__(self, parent)
        self.setText("Exec")
        self.setAutoRepeat(True)
        self.setAutoRepeatDelay(500)
        self.setAutoRepeatInterval(166)
#        self.setCheckable(True)
#        self.setChecked(True)


##############################################################################
#
#  ALEK's UI window
#

class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        font = self.font()
        font.setPixelSize(20)
        self.setFont(font)

        w = MemoryTabBar(self)
        self.memoryTabBar = w
        w.setGeometry(20, 16, 660 + 4, 36)

        w = MemoryWidget(10, 10, self)
        self.memoryWidget = w
        w.setGeometry(20, 52, 660 + 4, 432 + 4)
        w.updateCells()

        self.memoryTabBar.currentChanged.connect(self.memoryWidget.setPage)
#        self.memoryWidget.cellClicked.connect(self.memoryCellClicked)
        self.memoryWidget.cellChanged.connect(self.memoryCellChanged)
        self.memoryWidget.itemSelectionChanged.connect(self.memoryCellsSelected)

        w = InspectorTabBar(self)
        self.inspectorTabBar = w
        w.setGeometry(20, 496, 660 + 4, 36)

        w = InspectorWidget(self)
        self.inspectorWidget = w
        w.setGeometry(20, 532, 660 + 4, 170 + 4)

        self.inspectorTabBar.currentChanged.connect(self.inspectorWidget.setCurrentIndex)
        self.inspectorWidget.widget(0).cellClicked.connect(self.inspectorClicked)
        self.inspectorWidget.codeClicked.connect(self.codeClicked)

        w = CPUTabBar(self)
        self.cpuTabBar = w
        w.setGeometry(700, 16, 80, 36)

        w = CPUWidget(self)
        self.cpuWidget = w
        w.setGeometry(700, 52, 480, 164)

        w = MenuButton(self)
        self.menuButton = w
        w.setGeometry(1152, 16, 28, 30)
        menu = QMenu(w)
        w.setMenu(menu)
        menu.addAction("Reset").triggered.connect(self.resetClicked)
        menu.addSeparator()
        menu.addAction("Clear Video").triggered.connect(self.clearVideoClicked)
        menu.addAction("Clear Memory Cells").triggered.connect(self.clearMemoryClicked)
        menu.addSeparator()
        menu.addAction("Demo 1: Hi").triggered.connect(self.demo1Clicked)
        menu.addAction("Demo 2: Hello World").triggered.connect(self.demo2Clicked)
        menu.addAction("Demo 3: Count Down").triggered.connect(self.demo3Clicked)
        menu.addAction("Demo 4: Multiply").triggered.connect(self.demo4Clicked)
        menu.addAction("Demo 5: Multiply 2").triggered.connect(self.demo5Clicked)
        menu.addSeparator()
        menu.addAction("Font Size +").triggered.connect(self.fontSizePlus)
        menu.addAction("Font Size −").triggered.connect(self.fontSizeMinus)
#        menu.addSeparator()
#        menu.addAction("About")

        w = ExecButton(self)
        self.execButton = w
        w.setGeometry(1070, 16, 70, 36)

        self.execButton.clicked.connect(self.execClicked)

#        print(QApplication.desktop().screenGeometry().height())
        self.setFixedSize(self.sizeHint())

        w = AnimationWidget(self)
        self.animationWidget = w
        w.setGeometry(self.rect())

        self.clock = 0
        self.startTimer(33)
        self.execDelay = 3
        self.autoExec = False

#        self.demo1Clicked()
        self.resetClicked()

#        self.memoryWidget.updateCells()
#        self.cpuWidget.updateState()
#        self.memoryWidget.highlightAddress(cpu.reg[cpu.Reg.IP])


    def fontSizePlus(self):
        font = self.font()
        if font.pixelSize() < 24:
            font.setPixelSize(font.pixelSize() + 1)
            self.setFont(font)
            self.update()

    def fontSizeMinus(self):
        font = self.font()
        if font.pixelSize() > 10:
            font.setPixelSize(font.pixelSize() - 1)
            self.setFont(font)
            self.update()

    def codeClicked(self, c):
        page = self.memoryTabBar.currentIndex()
        ranges = self.memoryWidget.selectedRanges()
        a = -1
        if len(ranges) == 1:
            sr = ranges[0]
            if sr.rowCount() == 1 and sr.columnCount() == 1:
                my = sr.topRow()
                mx = sr.leftColumn()
                a = 100 * page + 10 * my + mx
        if a < 0:
            return
        Mem[Map[a]] = c
        self.memoryWidget.updateCellAddress(a)
        self.inspectorWidget.setData([c], 1)

    def inspectorClicked(self, y, x):
        page = self.memoryTabBar.currentIndex()
        ranges = self.memoryWidget.selectedRanges()
        a = -1
        if len(ranges) == 1:
            sr = ranges[0]
            if sr.rowCount() == 1 and sr.columnCount() == 1:
                my = sr.topRow()
                mx = sr.leftColumn()
                a = 100 * page + 10 * my + mx
        if a >= 0:
            c = Mem[Map[a]]
        if y == 0:
            if x == 0:
                c = 0
            elif x == 9:
                c = 999
            else:
                c = c % 100 + 100 * x
        elif y == 1:
            c = 100 * (c // 100) + 10 * x + c % 10
        elif y == 2:
            c = 10 * (c // 10) + x
        else:
            print("?")
        Mem[Map[a]] = c
        self.memoryWidget.updateCellAddress(a)
        self.inspectorWidget.setData([c], 1)

    def memoryCellsSelected(self):
        page = self.memoryTabBar.currentIndex()
        ranges = self.memoryWidget.selectedRanges()
        if len(ranges) == 1:
            sr = ranges[0]
            if sr.rowCount() == 1 and sr.columnCount() == 1:
                y = sr.topRow()
                x = sr.leftColumn()
                self.memoryCellClicked(y, x)

    def memoryCellChanged(self, y, x):
        item = self.memoryWidget.takeItem(y, x)
        if item != None:
            v = 0
            text = item.text()
            if text.isnumeric():
                v = int(text) % 1000
            elif len(text) == 1 and ord(text[0]) < 128 and CharToNum[ord(text[0])] > 4:
                v = CharToNum[ord(text[0])]
            page = self.memoryTabBar.currentIndex()
            a = 100 * page + 10 * y + x
            Mem[Map[a]] = v
            self.memoryWidget.blockSignals(True)
            self.memoryWidget.updateCellAddress(a)
            self.memoryWidget.blockSignals(False)
            self.memoryCellsSelected()
            if page == 7 or page == 8:
                self.update()

    def memoryCellClicked(self, y, x):
        page = self.memoryTabBar.currentIndex()
        a = 100 * page + 10 * y + x
#        if page < 5:
#            cpu.reg[cpu.Reg.IP] = a
#            self.cpuWidget.updateState()
        self.inspectorWidget.setData([Mem[Map[a]]], 1)

    def clearMemoryClicked(self):
        page = self.memoryTabBar.currentIndex()
        ranges = self.memoryWidget.selectedRanges()
        for sr in ranges:
            for y in range(sr.topRow(), sr.bottomRow() + 1):
                for x in range(sr.leftColumn(), sr.rightColumn() + 1):
                    a = 100 * page + 10 * y + x
                    Mem[Map[a]] = 0
        self.memoryWidget.updateCells()
        self.memoryCellsSelected()
        self.update()

    def clearVideoClicked(self):
        gpu.clearVideo()
        page = self.memoryTabBar.currentIndex()
        if page == 7 or page == 8:
            self.memoryWidget.updateCells()
        self.update()

    def demo1Clicked(self):
        self.demoClicked([510, 48, 591, 700, 510, 79, 591, 701, 999])

    def demo2Clicked(self):
        self.demoClicked([520, 20, 540, 700, 516, 610, 1, 710, 16, 581,
                          120, 1, 140, 1, 770, 4, 999, 0, 0, 0,
                          48, 75, 82, 82, 85, 7, 5, 63, 85, 88, 82, 74, 8, 0])

    def demo3Clicked(self):
        self.demoClicked([510, 9, 521, 120, 30, 592, 700, 210, 1, 610, 999, 730, 2, 999])

    def demo4Clicked(self):
        self.demoClicked([510, 0, 529, 20, 539, 21, 620, 0, 740, 15,
                          113, 220, 1, 770, 6, 591, 22, 999, 0, 0,
                          3, 17, 0])

    def demo5Clicked(self):
        self.demoClicked([510, 0, 529, 95, 539, 96, 620, 0, 740, 15,
                          113, 220, 1, 770, 6,
                          591, 97, 540, 99, 530, 700,
                          519, 95, 580, 27, 770, 50, 510, 12, 571, 130, 1,
                          519, 96, 580, 38, 770, 50, 510, 28, 571, 530, 710,
                          519, 97, 580, 49, 770, 50, 999,
                          240, 1, 520, 30, 572, 130, 1, 572, 130, 1, 572, 230, 2,
                          520, 100, 580, 69, 770, 84,
                          520, 10, 580, 75, 770, 84,
                          520, 1, 580, 81, 770, 84,
                          140, 1, 778,
                          612, 710, 92, 170, 1, 212, 770, 84, 130, 1, 778,
                          3, 17,
                          ])

    def demoClicked(self, code):
        for a in range(100):
            Mem[Map[a]] = 0
        for i in range(len(code)):
            Mem[Map[i]] = code[i]
        self.resetClicked()

    def updateAll(self):
        self.memoryWidget.updateCells()
        self.cpuWidget.updateState()
        self.memoryTabBar.setCurrentIndex(cpu.reg[cpu.Reg.IP] // 100)
        self.memoryWidget.highlightAddress(cpu.reg[cpu.Reg.IP])
        self.memoryCellsSelected()
        self.update()

    def RunClicked(self):
        cpu.state = cpu.State.Running
        while cpu.state == cpu.State.Running:
            cpu.fetch()
            cpu.execute()
        self.updateAll()
        self.execButton.setEnabled(False)

    def resetClicked(self):
        cpu.reset()
        gpu.reset()
        cpu.state = cpu.State.Running
        self.updateAll()
        self.execButton.setEnabled(True)

    def execClicked(self):
        if cpu.state == cpu.State.Running:
            cpu.fetch()
            cpu.execute()
            self.updateAll()
        if cpu.state == cpu.State.Error:
            self.animationWidget.showError()
        if cpu.state != cpu.State.Running:
            self.execButton.setEnabled(False)

    def showEvent(self, event):
        pass

    def timerEvent(self, event):
        self.clock += 1
        if self.autoExec:
            if (self.clock % self.execDelay) == 0:
                if self.execButton.isEnabled():
                    self.execClicked()
        if self.clock == 180:
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = QRect(700, 224, 480, 480)
        gpu.paintVideo(painter, rect)
        if self.clock < 150:
            painter.setPen(QColor(240, 240, 240))
            copyright = "ALEK 0.1 Copyright 2023 Christoph Feck"
            painter.drawText(rect.adjusted(20, 10, -20, -10), Qt.AlignBottom | Qt.AlignHCenter, copyright)

    def sizeHint(self):
#        return QSize(2000, 1200)
#        return QSize(1880, 1020)
        return QSize(1200, 720)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


##############################################################################
#
#  main
#

app = QApplication(["alek.py"])

initTables()

gpu = VirtualGPU()
cpu = VirtualCPU()

window = MainWindow()
if QApplication.desktop().screenGeometry().height() < 768:
    window.showFullScreen()
else:
    window.show()

app.exec()

