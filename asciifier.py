#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Convert an image to ASCII art.
#
# Copyright (c) 2015 Oliver Lau <ola@ct.de>, Heise Medien GmbH & Co. KG
# All rights reserved.

from PIL import Image, ImageFont, ImageDraw, ImageColor
from datetime import datetime
from math import ceil
from ttfquery import describe, glyphquery, glyph
from fpdf import fonts, ttfonts
import string
import argparse


def cumsum(arr):
    s = 0
    result = []
    for x in arr:
        s += x
        result.append(s)
    return result


def mm2pt(mm):
    return 2.834645669 * mm


class Size:
    """ Class to store the size of a rectangle."""

    def __init__(self, width, height):
        self.width = width
        self.height = height

    def to_tuple(self):
        return self.width, self.height


class Point:
    """ Class to store a point on a 2D plane."""

    def __init__(self, x, y):
        self.x = x
        self.y = y


class Margin:
    """ Class to store the margins of a rectangular boundary."""

    def __init__(self, top, right, bottom, left):
        self.top = top
        self.right = right
        self.bottom = bottom
        self.left = left


class Asciifier:
    """ Class to convert a pixel image to ASCII art."""

    PAPER_SIZES = {
        'a6': Size(105, 148),
        'a5': Size(148, 210),
        'a4': Size(210, 297),
        'a3': Size(297, 420),
        'a2': Size(420, 594),
        'a1': Size(594, 841),
        'a0': Size(841, 1189),
        'letter': Size(215.9, 279.4)
    }
    TYPE_CHOICES = ['text', 'postscript', 'pdf']
    PAPER_CHOICES = PAPER_SIZES.keys()

    def __init__(self, **kwargs):
        self.margins = kwargs.get('margin', Margin(10, 10, 10, 10))
        self.result = None
        self.im = None
        self.luminosity = ['H', 'R', 'B', 'E', 'p', 'M', 'q', 'Q', 'N', 'W', 'g', '#', 'm', 'b',
                           'A', 'K', 'd', 'D', '8', '@', 'P', 'G', 'F', 'U', 'h', 'X', 'e', 'T',
                           'Z', 'S', 'k', 'O', '$', 'y', 'a', 'L', 'f', '6', '0', 'w', '9', '&',
                           '5', 'Y', 'x', '4', 'n', 's', 'C', '%', 'V', 'o', '2', 'u', 'J', 'I',
                           'z', '3', 'j', 'c', 't', 'r', 'l', 'v', 'i', '}', '?', '{', '1', '=',
                           ']', '[', '+', '7', '<', '>', '|', '!', '*', '/', ';', ':', '~', '-',
                           '.', ' ']

    def generate_luminosity_mapping(self, font_file):
        n = 64
        try:
            font = ImageFont.truetype(font_file, int(round(0.8 * n)))
        except IOError:
            return
        image_size = Size(n, n)
        self.luminosity = []
        intensity = []
        for c in range(32, 127):
            image = Image.new('RGB', image_size.to_tuple(), ImageColor.getrgb('#ffffff'))
            draw = ImageDraw.Draw(image)
            draw.text((0, 0), chr(c), font=font, fill=(0, 0, 0))
            l = 0
            for pixel in image.getdata():
                r, g, b = pixel
                l += 0.2126 * r + 0.7152 * g + 0.0722 * b
            intensity.append({'l': l, 'c': chr(c)})
        self.luminosity = map(lambda i: i['c'], sorted(intensity, key=lambda lum: lum['l']))

    def to_pdf(self, **kwargs):
        import zlib
        paper_type = kwargs.get('paper', 'a4')
        compress = kwargs.get('compress', True)
        font_name = 'Courier'
        if kwargs.get('font_name') is not None:
            font_name = kwargs.get('font_name')
            self.generate_luminosity_mapping(font_name)
        paper = self.PAPER_SIZES[string.lower(paper_type)]
        inner = Size(ceil(paper.width - self.margins.left - self.margins.right),
                     ceil(paper.height - self.margins.top - self.margins.bottom))
        size = Size(self.im.width, self.im.height)
        scale = inner.width / size.width
        offset = Point(self.margins.left + (inner.width - size.width * scale) / 2,
                       self.margins.bottom + (inner.height - size.height * scale) / 2)
        stream_lines = []
        for y in range(0, self.im.height):
            yy = offset.y + scale * (self.im.height - y)
            for x in range(0, self.im.width):
                c = self.result[x][y]
                if c != ' ':
                    tj = 'BT /F1 {} Tf {} {} Td ({}) Tj ET'\
                        .format(scale,
                                offset.x + x * scale,
                                yy,
                                c)
                    stream_lines.append(tj)
        stream = '\n'.join(stream_lines)
        if compress:
            stream = zlib.compress(stream, 9)
        glyph_widths = []
        for ch in self.luminosity:
            glyph_widths.append('200')
        blocks = [
            [
                '%PDF-1.7',
                '%{0:c}{1:c}{2:c}'.format(254, 245, 244),
            ],
            [
                '1 0 obj<< /Type/Catalog/Pages 2 0 R >>endobj',
            ],
            [
                '2 0 obj<< /Type/Pages/Count 1 /Kids [3 0 R] >>endobj',
            ],
            [
                '3 0 obj<< /Type/Page',
                '     /UserUnit 2.834645669',
                '     /MediaBox [0 0 {} {}]'.format(paper.width, paper.height),
                '     /Parent 2 0 R',
                '     /Resources << /Font << /F1 4 0 R >> >>',
                '     /Contents 5 0 R',
                '  >>',
                'endobj'
            ],
            [
                '4 0 obj',
                '  << /Type/Font /Subtype/TrueType /Name/F1',
                '     /BaseFont/{}'.format(font_name),
                '     /FirstChar {} /LastChar {}'.format(ord(min(self.luminosity)), ord(max(self.luminosity))),
                '     /Widths 7 0 R',
                '     /FontDescriptor 8 0 R',
                '     /Encoding/MacRomanEncoding'
                '  >>',
                'endobj',
            ],
            [
                '5 0 obj<< /Length {} {}>>stream'.format(len(stream), '/Filter[/FlateDecode]' if compress else ''),
                stream,
                'endstream',
                'endobj'
            ],
            [
                '6 0 obj<<',
                '  /Producer(ASCIIfier)',
                '  /Creator(ASCIIfier)',
                '  /Subject(retro computing)',
                '  /Keywords(ASCII art fun)',
                '  /CreationDate(D:{})'.format(datetime.today().strftime('%Y%m%d%H%M%S')),
                '>>endobj'
            ],
            [
                '7 0 obj [',
                ' '.join(glyph_widths),
                ']'
            ],
            [
                '8 0 obj<<',
                '>>'
            ]
        ]
        blockoffsets = cumsum(map(lambda b: len(b), map(lambda block: '\n'.join(block), blocks)))
        blockcount = len(blockoffsets)
        xref = [
            'xref',
            '0 {}'.format(blockcount),
            '{0:010d} 65535 f'.format(0)
        ]
        for i in range(0, blockcount):
            xref += ['{0:010d} 00000 n'.format(blockoffsets[i])]
        xref += [
            'trailer<<',
            '  /Root 1 0 R',
            '  /Info 6 0 R',
            '  /Size {}'.format(len(blocks)+1),
            '>>',
            'startxref',
            '{}'.format(blockoffsets[blockcount-1]),
            '%%EOF'
        ]
        blocks.append(xref)
        return '\n'.join(map(lambda l: '\n'.join(l), blocks))

    def to_postscript(self, **kwargs):
        paper = kwargs.get('paper', 'a4')
        font_name = kwargs.get('font_name', 'Courier')
        paper_size = self.PAPER_SIZES[string.lower(paper)]
        paper_pt = Size(mm2pt(paper_size.width), mm2pt(paper_size.height))
        size_pt = Size(ceil(paper_pt.width - mm2pt(self.margins.left + self.margins.right)),
                       ceil(paper_pt.height - mm2pt(self.margins.top + self.margins.bottom)))
        grid_pt = 12
        font_pt = 12
        size = Size(self.im.width * grid_pt, self.im.height * grid_pt)
        scale = size_pt.width / size.width
        now = datetime.today()
        offset = Point(self.margins.left + (size_pt.width - size.width * scale) / 2,
                       self.margins.top + (size_pt.height - size.height * scale) / 2)
        lines = [
            '%!PS-Adobe-3.0',
            '%%BoundingBox: 0 0 {} {}'.format(size.width, size.height),
            '%%Creator: asciifier',
            '%%CreationDate: {}'.format(now.isoformat()),
            '%%DocumentMedia: {} {} {} 80 white ()'.format(paper, paper_pt.width, paper_pt.height),
            '%%Pages: 1',
            '%%EndComments',
            '%%BeginSetup',
            '  % A4, unrotated',
            '  << /PageSize [{} {}] /Orientation 0 >> setpagedevice'.format(paper_pt.width, paper_pt.height),
            '%%EndSetup',
            '%Copyright: Copyright (c) 2015 Oliver Lau <ola@ct.de>, Heise Medien GmbH & Co. KG',
            '%Copyright: All rights reserved.',
            '% Image converted to ASCII by asciifier.py (https://github.com/ola-ct/asciifier)',
            '',
            '/{} findfont'.format(font_name),
            '{} scalefont'.format(font_pt),
            'setfont',
            '',
            '/c { moveto show } def',
            '',
            '{} {} translate'.format(offset.x, offset.y),
            '{} {} scale'.format(scale, scale)
        ]
        for y in range(0, self.im.height):
            yoff = (self.im.height - y) * grid_pt
            for x in range(0, self.im.width):
                c = self.result[x][y]
                if c != ' ':
                    lines.append('({}) {} {} c'.format(c, x * grid_pt, yoff))

        lines += [
            '',
            'showpage'
        ]
        return '\n'.join(lines)

    def to_plain_text(self):
        txt = zip(*self.result)
        return '\n'.join([''.join(line).rstrip() for line in txt])

    def process(self, image_filename, **kwargs):
        self.im = Image.open(image_filename)
        if 'aspect_ratio' in kwargs:
            self.im = self.im.resize((int(self.im.width * kwargs['aspect_ratio']), self.im.height), Image.BILINEAR)
        resolution = kwargs.get('resolution', 80)
        self.im.thumbnail((resolution, self.im.height), Image.ANTIALIAS)
        w, h = self.im.size
        nchars = len(self.luminosity)
        self.result = [a[:] for a in [[' '] * h] * w]
        for x in range(0, w):
            for y in range(0, h):
                r, g, b = self.im.getpixel((x, y))
                l = 0.2126 * r + 0.7152 * g + 0.0722 * b
                self.result[x][y] = self.luminosity[int(l * nchars / 255)]


def main():
    f = describe.openFont('fonts/Hack-Bold.ttf')
    n = glyphquery.glyphName(f, 'g')
    g = glyph.Glyph(n)
    c = g.calculateContours(f)
    o = glyph.decomposeOutline(c[1])
    print o

    parser = argparse.ArgumentParser(description='Convert images to ASCII art.')
    parser.add_argument('image', type=str, help='file name of image to be converted')
    parser.add_argument('--out', type=str, help='file name of postscript file to write.')
    parser.add_argument('--type', type=str, choices=Asciifier.TYPE_CHOICES, help='output type.')
    parser.add_argument('--aspect', type=float, help='aspect ratio of terminal font.')
    parser.add_argument('--font', type=str, help='file name of font to be used.')
    parser.add_argument('--paper', type=str, choices=Asciifier.PAPER_CHOICES, help='paper size.')
    parser.add_argument('--resolution', type=int, help='number of characters per line.')
    args = parser.parse_args()

    asciifier = Asciifier()

    output_type = 'text'
    if args.out is not None:
        if args.out.endswith('.ps'):
            output_type = 'postscript'
        elif args.out.endswith('.pdf'):
            output_type = 'pdf'
    if args.type in ['postscript', 'pdf']:
        output_type = args.type

    aspect_ratio = 2.0
    if args.aspect is not None:
        aspect_ratio = args.aspect

    resolution = 80
    if args.resolution is not None:
        resolution = args.resolution

    paper = 'a3'
    if args.paper is not None:
        paper = args.paper

    font_name = 'Courier'
    if args.paper is not None:
        font_name = args.font

    if output_type == 'text':
        asciifier.process(args.image, resolution=resolution, aspect_ratio=aspect_ratio)
        result = asciifier.to_plain_text()
    elif output_type == 'postscript':
        asciifier.process(args.image, resolution=resolution)
        result = asciifier.to_postscript(paper=paper, font_name=font_name)
    elif output_type == 'pdf':
        asciifier.process(args.image, resolution=resolution)
        result = asciifier.to_pdf(paper=paper, font_name=font_name)
    else:
        result = '<invalid type>'

    if args.out is None:
        print(result)
    else:
        with open(args.out, 'wb+') as f:
            f.write(result)


if __name__ == '__main__':
    main()
