#! /usr/bin/env python3

# GPLv3

import sys
from PIL import Image, ImageChops
from collections import defaultdict
from itertools import *
from math import ceil

"""
Ascii art version of PanTheSatyr's beautiful work:
http://www.reddit.com/r/dwarffortress/comments/1wcdi6/the_dwarven_compendium/

made so that people could easily fix and extend the data
or generate custom versions for their tileset and theme

todo:
    animal chart
    don't embed alignments
    robust parsing
    lump the globals into an object
    bitmap memoization for speed
"""

tile_unicode = """ ☺☻♥♦♣♠•◘○◙♂♀♪♫☼►◄↕‼¶§▬↨↑↓→←∟↔▲▼ !"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~⌂ÇüéâäàåçêëèïîìÄÅÉæÆôöòûùÿÖÜ¢£¥₧ƒáíóúñÑªº¿⌐¬½¼¡«»░▒▓│┤╡╢╖╕╣║╗╝╜╛┐└┴┬├─┼╞╟╚╔╩╦╠═╬╧╨╤╥╙╘╒╓╫╪┘┌█▄▌▐▀αßΓπΣσµτΦΘΩδ∞φε∩≡±≥≤⌠⌡÷≈°∙·√ⁿ²■ """


def dictify(data_list, setify=False, listify=False):
    data2 = {}
    for d in data_list:
        name,_,tags = d.partition(',')
        name = name.strip()
        tags = tags.strip()
        if setify or listify:
            tags = [t.strip() for t in tags.split(' ')]
        if setify:
            tags = set(t for t in tags if t)
        data2[name] = tags
    return data2

def load_data(data_path):
    data = defaultdict(list)
    for line in open(data_path):
        line = line.strip()
        if not line:
            continue
        if line.startswith('#'):
            continue
        field,_,value = line.partition(':')
        data[field].append(value.strip())
    # clean up
    data['title'] = data['title'][0]
    data['cols'] = [c.strip() for c in data['cols'][0].split(',')]
    data['subcol'] = dictify(data['subcol'], listify=True)
    for d in data['row']:
        data['order'].append(d.partition(',')[0].strip())
    data['row'] = dictify(data['row'], setify=True)
    data['icon'] = dictify(data['icon'], listify=True)
    data['note'] = dictify(data['note'])
    return data

def colorize(img, foreground, background):
    img = img.copy()
    pix = img.load()
    for x,y in product(*map(range, img.size)):
        p = pix[x,y]
        if len(p) == 3 and p == (255, 0, 255):
            pix[x,y] = background
        if len(p) == 3 and p == (255, 255, 255):
            pix[x,y] = foreground
        if len(p) == 4:
            a = p[3] / 255
            r = int(a*(foreground[0] - background[0]) + background[0])
            g = int(a*(foreground[1] - background[1]) + background[1])
            b = int(a*(foreground[2] - background[2]) + background[2])
            pix[x,y] = (r, g, b, 255)
    return img

def load_tileset(img):
    "returns a unicode:img dict"
    # largely lifted from chop16() in df2ttf.py
    if 'P' in img.getbands():
        img = img.convert('RGB')
    size = img.size
    w = size[0] // 16
    h = size[1] // 16
    assert size == (w*16, h*16)
    tiles = {}
    for y,x in product(range(0, size[1], h), range(0, size[0], w)):
        c = tile_unicode[y//h*16 + x//w]
        tiles[c] = img.crop((x, y, x+w, y+h))
    return tiles

def load_colors(color_path):
    "returns a color:(r,g,b) dict"
    colors = {}
    for line in open(color_path):
        line = line.strip()
        if not line.startswith('['):
            continue
        c,v = line[1:-1].split(':')
        colors[c] = int(v)
    names = set(c.split('_')[0] for c in colors)
    colors2 = {}
    for c in names:
        colors2[c] = (colors[c+'_R'], colors[c+'_G'], colors[c+'_B'])
    return colors2

def double_size(img):
    "because resize nearest sucks"
    xs,ys = img.size
    img2 = Image.new('RGB', (xs*2, ys*2), colors['BLACK'])
    pix = img.load()
    pix2 = img2.load()
    for x,y in product(range(xs), range(ys)):
        rgb = pix[x,y]
        pix2[x*2+0,y*2+0] = rgb
        pix2[x*2+1,y*2+0] = rgb
        pix2[x*2+0,y*2+1] = rgb
        pix2[x*2+1,y*2+1] = rgb
    return img2

def triple_size(img):
    "because resize nearest sucks"
    xs,ys = img.size
    img2 = Image.new('RGB', (xs*3, ys*3), colors['BLACK'])
    pix = img.load()
    pix2 = img2.load()
    for x,y in product(range(xs), range(ys)):
        rgb = pix[x,y]
        pix2[x*3+0,y*3+0] = rgb
        pix2[x*3+1,y*3+0] = rgb
        pix2[x*3+2,y*3+0] = rgb
        pix2[x*3+0,y*3+1] = rgb
        pix2[x*3+1,y*3+1] = rgb
        pix2[x*3+2,y*3+1] = rgb
        pix2[x*3+0,y*3+2] = rgb
        pix2[x*3+1,y*3+2] = rgb
        pix2[x*3+2,y*3+2] = rgb
    return img2

def single_icon(char, fore, back, bright=True, scale=1):
    "all inputs are strings"
    # memoize this?
    if not bright:
        if fore != 'BLACK':
            fore = 'DGRAY'
        if back != 'BLACK':
            back = 'DGRAY'
        return single_icon(char, fore, back, bright=True, scale=scale)
    if char not in tiles:
        char = ' '
    img = colorize(tiles[char], colors[fore], colors[back])
    if scale == 2:
        return double_size(img)
    if scale == 3:
        return triple_size(img)
    return img

def large_icon(desc, bright=True):
    "takes list of strings"
    xys = [(0,0), (1,0), (2,0), (0,1), (1,1), (2,1), (0,2), (1,2), (2,2)]
    icons = []
    for i in range(0, len(desc), 3):
        f = desc[i + 0]
        b = desc[i + 1]
        c = desc[i + 2]
        icons.append(single_icon(c, f, b, bright=bright))
    xi = icons[0].size[0]
    yi = icons[0].size[1]
    img = Image.new('RGB', (xi*3, yi*3), colors['BLACK'])
    for i,xy in zip(icons, xys):
        img.paste(i, (xy[0]*xi, xy[1]*yi))
    return img

def word_icon(letters, fore, back, scale=1):
    icons = []
    for c in letters:
        icons.append(single_icon(c, fore, back, scale=scale))
    xi = icons[0].size[0]
    yi = icons[0].size[1]
    img = Image.new('RGB', (xi*len(letters), yi), colors['BLACK'])
    for i,x in zip(icons, count(0, xi)):
        img.paste(i, (x, 0))
    return img

def parse_single_icon(desc):
    f = desc[0]
    b = desc[1]
    c = desc[2]
    s = 1
    if 'DOUBLE' in desc:
        s = 2
    if 'TRIPLE' in desc:
        s = 3
    return f,b,c,s

def row_icon(name):
    tags = data['row'][name]
    icons = []
    for col in data['cols']:
        if col == 'Name':
            icons.append(in_a_row([word_icon(name, 'WHITE', 'BLACK')]))
            continue
        if col == 'Icon':
            f,b,c,s = parse_single_icon(data['icon'][name])
            icons.append(single_icon(c, f, b, scale=s))
            continue
        if col == 'Note':
            text = ' '
            if name in data['note']:
                text = data['note'][name]
            icons.append(in_a_row([word_icon(text, 'LGRAY', 'BLACK')]))
            continue
        if col not in data['subcol']:
            continue
        sub_icons = []
        for scol in data['subcol'][col]:
            bright = scol in tags
            if len(data['icon'][scol]) == 27:
                sub_icons.append(large_icon(data['icon'][scol], bright=bright))
                continue
            f,b,c,s = parse_single_icon(data['icon'][scol])
            sub_icons.append(single_icon(c, f, b, bright=bright, scale=s))
        # minor bit of cheating here
        icons.append(in_a_row(sub_icons))
    return icons

def in_a_row(imgs):
    x_dim = [i.size[0] for i in imgs]
    y_dim = [i.size[1] for i in imgs]
    x_char = tiles[' '].size[0]
    y_char = tiles[' '].size[1]
    x_total = sum(x_dim) + x_char*(len(x_dim))
    y_total = max(y_dim)
    img = Image.new('RGB', (x_total, y_total), colors['BLACK'])
    x = x_char // 2
    for i in imgs:
        y_sub = y_total // 2 - i.size[1] // 2
        img.paste(i, (x, y_sub))
        x += i.size[0] + x_char
    return img

def add_title(img, text):
    text = word_icon(text, 'WHITE', 'BLACK', scale=2)
    x,y = img.size
    y += text.size[1]
    img2 = Image.new('RGB', (x,y), colors['BLACK'])
    img2.paste(img, (0, text.size[1]))
    img2.paste(text, (x//2 - text.size[0]//2, 0))
    return img2

def find_widths(subgrid):
    widths = defaultdict(list)
    for row in subgrid:
        if len(row) == 1:
            continue
        for i,img in enumerate(row):
            x,y = img.size
            widths[i].append(x)
    x_char = tiles[' '].size[0]
    for i in range(max(widths)+1):
        widths[i] = ceil(max(widths[i]) / x_char) * x_char
    return widths

def find_heights(subgrid):
    heights = defaultdict(list)
    for i,row in enumerate(subgrid):
        for img in row:
            x,y = img.size
            heights[i].append(y)
    y_char = tiles[' '].size[1]
    for i in range(max(heights)+1):
        heights[i] = ceil(max(heights[i]) / y_char) * y_char
    return heights

def render(subgrid, line):
    "glue stuff together, add borders and negative space"
    # oh gosh how did this function end up being +70 lines long
    widths = find_widths(subgrid)
    heights = find_heights(subgrid)
    x_char = tiles[' '].size[0]
    y_char = tiles[' '].size[1]
    x_total = sum(widths.values())
    x_total += x_char * (len(widths) + 1)
    y_total = sum(heights.values())
    y_total += y_char * (len(heights) + 1)
    img = Image.new('RGB', (x_total, y_total), colors['BLACK'])
    img.paste(single_icon('┌', line, 'BLACK'), (0, 0))
    img.paste(single_icon('└', line, 'BLACK'), (0, y_total - y_char))
    img.paste(single_icon('┐', line, 'BLACK'), (x_total-x_char, 0))
    img.paste(single_icon('┘', line, 'BLACK'), (x_total-x_char, y_total - y_char))
    special_x = [0]
    for i in range(len(widths)):
        special_x.append(widths[i] + special_x[-1] + x_char)
    special_y = [0]
    for i in range(len(heights)):
        special_y.append(heights[i] + special_y[-1] + y_char)
    for y in range(y_char, y_total-y_char, y_char):
        chr_left = '│'
        chr_right = '│'
        if y in special_y:
            chr_left = '├'
            chr_right = '┤'
        img.paste(single_icon(chr_left, line, 'BLACK'), (0, y))
        img.paste(single_icon(chr_right, line, 'BLACK'), (x_total-x_char, y))
    y = y_char
    for j,imgs in enumerate(subgrid):
        x_dim = [i.size[0] for i in imgs]
        y_dim = [i.size[1] for i in imgs]
        x = 0
        x += x_char
        row_height = max(y_dim)
        for i,sub_i in enumerate(imgs):
            x_sub = widths[i]
            y_sub = row_height // 2 - sub_i.size[1] // 2
            x_offset = x_sub//2 - sub_i.size[0]//2
            if i == min(widths) or i == max(widths):
                x_offset = 0
            img.paste(sub_i, (x+x_offset, y+y_sub))
            for x2 in range(x, x_total-x_char, x_char):
                chr_rule = '─'
                if x2 in special_x:
                    chr_rule = '┼'
                if x2 in special_x and y == y_char:
                    chr_rule = '┬'
                if len(imgs) == 1 and  chr_rule == '┼':
                    chr_rule = '┴'
                if len(imgs) == 1 and  chr_rule == '┬':
                    chr_rule = '─'
                if j > 0 and len(subgrid[j-1])==1 and chr_rule == '┼':
                    chr_rule = '┬'
                img.paste(single_icon(chr_rule, line, 'BLACK'), (x2, y-y_char))
            x += x_sub
            if x >= x_total-x_char:
                continue
            if len(imgs) == 1:
                break
            for y2 in range(y, y+row_height, y_char):
                img.paste(single_icon('│', line, 'BLACK'), (x, y2))
            x += x_char
        y += row_height
        # line stuff
        y += y_char
    for x2 in range(x_char, x_total-x_char, x_char):
        chr_rule = '─'
        if x2 in special_x:
            chr_rule = '┴'
        img.paste(single_icon(chr_rule, line, 'BLACK'), (x2, y_total-y_char))
    return img
    


if __name__ == '__main__':
    if len(sys.argv) != 5:
        print('use: python compendium.py chart.txt tileset.png colors.txt output.png')
        sys.exit()
    data_path  = sys.argv[1]
    tile_path  = sys.argv[2]
    color_path = sys.argv[3]
    save_path  = sys.argv[4]
    print('loading')
    data = load_data(data_path)
    tiles = load_tileset(Image.open(tile_path))
    colors = load_colors(color_path)
    print('pushing pixels')
    subgrid = []
    labels = []
    for col in data['cols']:
        if col in ['Icon', 'Note']:
            col = ' '
        word = word_icon(col, 'LGRAY', 'BLACK', scale=1)
        labels.append(in_a_row([word]))
    subgrid.append(labels)
    for name in data['order']:
        if 'heading' in data['row'][name]:
            #name = ' '.join(list(name))
            word = word_icon(name, 'DGRAY', 'BLACK', scale=2)
            subgrid.append([in_a_row([word])])
            continue
        subgrid.append(row_icon(name))
    img = render(subgrid, 'DGRAY')
    img = add_title(img, data['title'])
    print('saving')
    img.save(save_path)

