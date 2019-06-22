#!/usr/bin/env python3
from PIL import Image
import numpy as np

import smush
from fobj import unobj, mkobj
from ahdr import parse_header
from codex import get_decoder, get_encoder
from image import save_single_frame_image
from smush_writer import mktag

import struct
from functools import partial

def clip(lower, upper, value):
    return lower if value < lower else upper if value > upper else value

clip_byte = partial(clip, 0, 255)

def convert_fobj(datam):
    meta, data = unobj(datam)
    width = meta['x2'] - meta['x1']
    height = meta['y2'] - meta['y1']
    decode = get_decoder(meta['codec'])
    if decode == NotImplemented:
        print(f"Codec not implemented: {meta['codec']}")
        return None

    if meta['x1'] != 0 or meta['y1'] != 0:
        print('TELL ME')

    print(meta)

    locs = {'x1': meta['x1'], 'y1': meta['y1'], 'x2': meta['x2'], 'y2': meta['y2']}
    return locs, decode(width, height, data)

def non_parser(chunk):
    return chunk

def parse_frame(frame, parsers):
    chunks = list(smush.read_chunks(frame))
    return [(tag, parsers.get(tag, non_parser)(chunk)) for tag, chunk in chunks]

def verify_nframes(frames, nframes):
    for idx, frame in enumerate(frames):
        if nframes and idx > nframes:
            raise ValueError('too many frames')
        yield frame

def filter_chunk_once(chunks, target):
    return next((frame for tag, frame in chunks if tag == target), None)

def delta_color(org_color, delta_color):
    return clip_byte((org_color * 129 + delta_color) // 128)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='read smush file')
    parser.add_argument('filename', help='filename to read from')
    args = parser.parse_args()

    with smush.open(args.filename) as smush_file:
        header = parse_header(smush_file.header)
        # print(header['palette'][39])

        # palette = header['palette']

        frames = verify_nframes(smush_file, header['nframes'])
        frames = (list(smush.read_chunks(frame)) for frame in frames)

        # parsers = {
        #     'FOBJ': convert_fobj
        # }

        # frames = (frame for idx, frame in enumerate(frames) if 1050 > idx)
        # parsed_frames = list(parse_frame(frame, parsers) for frame in frames)

        # for idx, frame in enumerate(parsed_frames):
        #     print((idx, [tag for tag, chunk in frame]))

        # image_frames = ((filter_chunk_once(parsed, 'FOBJ'), filter_chunk_once(parsed, 'NPAL')) for parsed in parsed_frames)
        # image_frames, pal_frames = zip(*image_frames)
        # frames_pil = save_frame_image(image_frames)

        # palette = [x for l in palette for x in l]
        # screen = []

        # delta_pal = []

        chars = []

        def get_frame_image(idx):
            im = Image.open(f'out/FRME_{idx:05d}.png')
            return list(np.asarray(im))

        def encode_fake(image):
            encode = get_encoder(37)
            loc = {'x1': 0, 'y1': 0, 'x2': len(image[0]), 'y2': len(image)}
            meta = {'codec': 37, **loc, 'unk1': 0, 'unk2': 0}
            return mkobj(meta, encode(image))

        for idx, frame in enumerate(frames):
            print(f'{idx} - {[tag for tag, _ in frame]}')
            fdata = b''
            for tag, chunk in frame:
                if tag == 'FOBJ':
                    image = get_frame_image(idx)
                    fdata += mktag('FOBJ', encode_fake(image))
                    continue
                else:
                    fdata += mktag(tag, chunk)
                    continue

            chars.append(mktag('FRME', fdata))
            # im = save_single_frame_image(screen)
            # # im = im.crop(box=(0,0,320,200))
            # im.putpalette(palette)
            # im.save(f'out/FRME_{idx:05d}.png')
        with open('NEW-VIDEO.SAN', 'wb') as output_file:
            header = mktag('AHDR', smush_file.header)
            output_file.write(mktag('ANIM', header + b''.join(chars)))
