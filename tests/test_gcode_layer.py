"""The slicer-preview check (PLAN rev 2.1 §4.3): in the sliced G-code, count the extrusion lines that cross a short line
across a thin wall at one layer, and draw that layer as an SVG for out/. Proven on a hand-written G-code first."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'slicer'))
from gcode_layer import layer_segments, lines_across, layer_svg  # noqa: E402

G = """;LAYER_CHANGE
;Z:0.2
G1 Z0.2
G1 X0 Y0 F1000
G1 X10 Y0 E1
;LAYER_CHANGE
;Z:0.4
G1 Z0.4
G1 X5 Y-1
G1 X5 Y1 E1.5
G1 X6 Y-1
G1 X6 Y1 E2.0
G1 X7 Y-1
G92 E0
G1 X9 Y1 E0.2
"""


def test_segments_of_one_layer_only_extruding_moves():
    segs = layer_segments(G, 0.4)
    assert ((5.0, -1.0), (5.0, 1.0)) in segs and ((6.0, -1.0), (6.0, 1.0)) in segs
    assert ((5.0, 1.0), (6.0, -1.0)) not in segs          # a travel (no E increase) is not a line
    assert ((7.0, -1.0), (9.0, 1.0)) in segs              # after G92 E0 the next E counts again
    assert layer_segments(G, 0.2) == [((0.0, 0.0), (10.0, 0.0))]


def test_lines_across_a_band():
    segs = layer_segments(G, 0.4)
    xs = lines_across(segs, y=0.0, x_min=4.5, x_max=6.5)
    assert xs == [5.0, 6.0]


def test_svg_is_written():
    svg = layer_svg(layer_segments(G, 0.4), (4, -2, 10, 2), width_mm=0.45, marks=[5.0, 6.0], y=0.0)
    assert svg.startswith('<svg') and svg.count('<line') >= 3
