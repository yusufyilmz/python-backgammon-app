__author__ = 'yusufyilmz'

__all__ = ['Board', 'Roll', 'Turn', 'WHITE', 'BLACK']

import random, operator
from util import KeyedMixin

WHITE = 'W'
BLACK = 'B'


class Board(object):

    @property
    def points(I):

        return I._points

    def __init__(I):

        I._points = tuple(Point(i) for i in range(26))
        num = 0
        for pt, count in ((1,2), (12,5), (17,3), (19,5)):
            for i in range(count):
                I.points[pt].push(Piece(WHITE, num))
                num += 1
        num = 0
        for pt, count in ((24,2), (13,5), (8,3), (6,5)):
            for i in range(count):
                I.points[pt].push(Piece(BLACK, num))
                num += 1

    @staticmethod
    def from_str(s):

        is_digit = ('0','1','2','3','4','5','6','7','8','9').__contains__
        brd = Board()
        for pt in brd.points:
            while pt.pieces:
                pt.pop()
        counts = {WHITE: 0, BLACK: 0}
        for line in s.split('\n'):
            for i in line.split():
                if is_digit(i[0]):
                    l = i.split(':')
                    if len(l) > 1:
                        pt = int(l[0])
                        for pieces in l[1:]:
                            color = pieces[0]
                            count = int(pieces[1:])
                            for j in range(count):
                                brd.points[pt].push(Piece(color, counts[color]))
                                counts[color] += 1
        return brd


    def __str__(I):
        l = []
        out = l.append
        out('[ ')
        for i in range(12, 0, -1):
            if i == 6:
                out(' ] [ ')
            out(str(I.points[i]))
            if i not in (7, 1):
                out(' | ')
        homed = len(I.homed(BLACK))
        jailed = len(I.jailed(WHITE))
        out(" ] [  0:W{}:B{} ]\n[ ".format(jailed, homed))
        for i in range(13, 25):
            if i == 19:
                out(' ] [ ')
            out(str(I.points[i]))
            if i not in (18,24):
                out(' | ')
        homed = len(I.homed(WHITE))
        jailed = len(I.jailed(BLACK))
        out(" ] [ 25:B{}:W{} ]".format(jailed, homed))
        return ''.join(l)

    def copy(I):

        new = Board()
        new._points = tuple(pt.copy() for pt in I.points)
        return new

    def move(I, src, dst):

        new = I.copy()
        if not isinstance(dst, int):
            dst = dst.num
        assert dst >= 0 and dst <= 25, 'valid points are [0..25]'
        dst = new.points[dst]
        if not isinstance(src, int):
            src = src.num
        assert src >= 0 and src <= 25, 'valid points are [0..25]'
        src = new.points[src]
        sharing_allowed = dst in (new.home(WHITE), new.home(BLACK))
        if not sharing_allowed:
            assert not dst.blocked(src.color), 'cannot move to a blocked point'
        if dst.pieces and src.color != dst.color and not sharing_allowed:
            # Move exposed piece to jail.
            new.jail(dst.color).push(dst.pop())
        dst.push(src.pop())
        return new

    def possible_moves(I, roll, point):
        if isinstance(point, int):
            assert point >= 0 and point <= 25, 'valid points are [0..25]'
            point = I.points[point]
        assert point.pieces, 'there are no pieces on this point'
        piece = point.pieces[0]
        direction = 1 if piece.color == WHITE else -1
        dies = roll.dies
        if not dies:
            return []
        if len(dies) == 1:
            paths = [[dies[0]]]
        elif dies[0] == dies[1]:
            paths = [len(dies) * [dies[0]]]
        else:
            paths = [(dies[0], dies[1]), (dies[1], dies[0])]
        multiple_jailed = len(I.jailed(piece.color)) > 1
        moves = []
        min_point = 1
        max_point = 24
        if I.can_go_home(piece.color):
            if piece.color == BLACK:
                min_point -= 1
            else:
                max_point += 1
        for hops in paths:
            if multiple_jailed:
                hops = hops[:1]
            num = point.num
            for hop in hops:
                num += direction * hop
                if num < min_point or num > max_point or I.points[num].blocked(piece.color):
                    break
                if num not in moves:
                    moves.append(num)
        return sorted(moves)

    def can_go_home(I, color):
        points = range(7, 26) if color == BLACK else range(19)
        for point in points:
            if color == I.points[point].color:
                return False
        return True

    def finished(I):
        return 15 == len([i for i in I.home(WHITE).pieces if i.color == WHITE]) or \
            15 == len([i for i in I.home(BLACK).pieces if i.color == BLACK])

    def jail(I, color):
        return I.points[0 if color == WHITE else 25]

    def jailed(I, color):
        return tuple(i for i in I.jail(color).pieces if i.color == color)

    def home(I, color):
        return I.points[0 if color == BLACK else 25]

    def homed(I, color):
        return tuple(i for i in I.home(color).pieces if i.color == color)

    def strongholds(I, color):
        return [pt for pt in I.points if pt.color == color and len(pt.pieces) > 1]

    def safe(I, color):
        if color == WHITE:
            enemy = BLACK
            behind = operator.gt
            enemy_line = I.points[max(i for i in range(25, 1, -1) if I.points[i].color == enemy)]
        else:
            enemy = WHITE
            behind = operator.lt
            enemy_line = I.points[min(i for i in range(0, 24, 1) if I.points[i].color == enemy)]
        return [pt for pt in I.points if behind(pt, enemy_line) and pt.pieces]

    def exposed(I, color):
        """
        List of points for given color that contain 1 piece that are not safe.
        """
        safe = I.safe(color)
        jail = I.jail(color)
        return [pt for pt in I.points if pt.color == color and len(pt.pieces) == 1 and pt not in safe and pt != jail]


class Point(object):
    @property
    def pieces(I):
        return I._pieces

    def __init__(I, num):
        I._pieces = ()
        I.num = num
        I.key = num 

    def __str__(I):
        s = "{:2d}".format(I.num)
        if I.pieces:
            s += ":{}{}".format(I.color, len(I.pieces))
        else:
            s += '   '
        return s

    def __repr__(I):
        color = 'NA'
        if I.pieces:
            color = "{}{}".format(I.color, len(I.pieces))
        return "{}:{}".format(I.num, color)

    def copy(I):
        new = Point(I.num)
        new._pieces = tuple(p.copy() for p in I.pieces)
        return new

    def push(I, piece):
        if piece not in I.pieces:
            I._pieces += (piece,)
            if I.num not in (0,25): # Making exception for jail/home.
                assert set(i.color for i in I.pieces) == set([piece.color]), \
                    'only pieces of same color allowed in a point'

    def pop(I):
        assert I.pieces, 'no pieces at this point'
        piece = I.pieces[-1]
        I._pieces = I.pieces[:-1]
        return piece

    def blocked(I, color):
        return I.num not in (0,25) and color != I.color and len(I.pieces) > 1

    @property
    def color(I):
        val = None
        if I.pieces:
            colors = set(i.color for i in I.pieces)
            if I.num == 0:
                if WHITE in colors:
                    val = WHITE
            elif I.num == 25:
                if BLACK in colors:
                    val = BLACK
            elif len(colors) == 1:
                val = I.pieces[0].color
            else:
                raise ValueError("multiple colors occupy same point: {}".format(I))
        return val


class Piece(object):
    @property
    def color(I):
        return I._color

    @property
    def num(I):
        return I._num

    def __init__(I, color, num):
        assert num >= 0 and num <= 15, \
            "number out of range [0,15]: {}".format(num)
        assert color in (WHITE, BLACK), \
            "color must be '{}' or '{}': {}".format(WHITE, BLACK, color)
        I._color = color
        I._num = num

    def __repr__(I):
        return "{}:{}".format(I.color, I.num)

    def __hash__(I):
        return (100 if I.color == WHITE else 200) + I.num

    def copy(I):
        return Piece(I.color, I.num)
