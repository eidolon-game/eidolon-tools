"""Revise the Hagfish, Mortar Leech, Millipede and Rootclaw with Blender."""

import argparse
from math import cos, pi, sin
from pathlib import Path
import random
import sys

from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from refine_catacomb_armor import add_ligament, bounds, build, replace_plate, shell_weathering, tendon_groups
from refine_riftroot_tangle import fracture


def mouth_folds(objects):
    funnel = objects['Concave feeding funnel']
    shell_weathering(funnel, .009, 11, 1)
    lip = funnel.data.materials[0]
    tissue = funnel.data.materials[2]
    # Pleats follow the original mouth's concave section and recede inside it.
    for index in range(21):
        angle = index * 2 * pi / 21
        points = []
        for step in range(9):
            t = step / 8
            u = angle + .12 * sin(pi * t + index * .8)
            radius = .21 - .15 * t
            points.append(Vector((-.057 + radius * cos(u), -1.045 + .273 * t,
                                  .522 - .051 * t + radius * .75 * sin(u))))
        add_ligament(f'Mouth radial fold {index + 1}', points, .008 + .002 * sin(index * 2.6),
                      lip if index % 4 == 0 else tissue)


def hagfish_form(objects):
    shell_weathering(objects['Flattened ribbon body'], .008, 38, 1)
    shell_weathering(objects['Raised dorsal seam'], .009, 96, 2)
    mouth_folds(objects)
    flesh = objects['Gill slit 1 0'].data.materials[0]
    for sign in (-1, 1):
        shell_weathering(objects[f'Lateral ribbon fin {sign}'], .007, 28 + sign, 1)
        for index in range(6):
            lo, hi = bounds((objects[f'Gill slit {sign} {index}'],))
            center = (lo + hi) / 2
            for lip in (-1, 1):
                points = [center + Vector((sign * .017 * sin(pi * step / 8),
                          (step / 8 - .5) * .079, lip * .017 * sin(pi * step / 8))) for step in range(9)]
                add_ligament(f'Gill lip {sign} {index} {lip}', points, .0044, flesh)


def leech_form(objects):
    column = objects['Anchored soft column']
    shell_weathering(column, .023, 23, 2)
    shell_weathering(objects['Ground adhesion pad'], .011, 58, 1)
    mantle = objects['Raised annular mantle']
    shell_weathering(mantle, .009, 109, 1)
    center = sum(bounds((mantle,)), Vector()) / 2
    membrane = objects['Collar base'].data.materials[0]
    # Narrow radial folds define the transition into the feeding collar.
    for index in range(19):
        angle = index * 2 * pi / 19
        points = []
        for step in range(8):
            t = step / 7
            radius = .273 - .138 * t
            u = angle + .04 * sin(t * pi + index)
            points.append(center + Vector((radius * cos(u), radius * sin(u),
                          -.12 + .194 * sin(t * pi / 2))))
        add_ligament(f'Feeding collar fold {index + 1}', points, .006 + .002 * (index % 4 == 0), membrane)
    for index in range(1, 4):
        shell_weathering(objects[f'Upper hook crook {index}'], .009, 31 * index, 2)
    for index in range(8):
        shell_weathering(objects[f'Mineral holdfast {index}'], .009, 77 * index, 1)


def millipede_form(objects):
    for index in range(1, 19):
        plate = objects[f'Dorsal segment {index:02}']
        replace_plate(plate, Vector((0, 0, 1)), index * .817, .18)
        if 3 <= index <= 15:
            shell_weathering(objects[f'Raised rattle plate {index:02}'], .007, 34 + index, 2)
            shell_weathering(objects[f'Folded rattle plate {index:02}'], .004, 36 + index, 1)
    cap = objects['Blunt sensory head']
    shell_weathering(cap, .011, 11, 2)
    lo, hi = bounds((cap,))
    center = (lo + hi) / 2 + Vector((0, -.069, .103))
    tendon_groups(center, Vector((1, 0, 0)), .123, .186, 8, cap.data.materials[0], 'Sensory ridges')


def rootclaw_form(objects):
    rng = random.Random(13050)
    cap = objects['Stone mantle near buttress'].data.materials[0]
    recess = objects['Lifted barrel torso'].data.materials[0]
    # Physical joints separate the heavy limestone armor on the back and claw.
    for name in ('Stone mantle crown', 'Stone mantle haunch', 'Stone mantle near buttress',
                 'Low frontal faceplate', 'Heavy arm buttress', 'Heavy chela broken keystone',
                 'Heavy chela pale strike face'):
        obj = objects[name]
        exterior = obj.data.materials[0]
        fracture(obj, exterior, cap, recess, rng)
    shoulder = objects['Heavy side exposed hinge']
    lo, hi = bounds((shoulder,))
    tendon_groups((lo + hi) / 2 + Vector((.033, -.06, .186)),
                  Vector((1, 0, 0)), .292, .268, 8, shoulder.data.materials[0], 'Claw tension')
    for name, obj in objects.items():
        if name.startswith('Chela binding') and 'knot' not in name:
            shell_weathering(obj, .008, len(name), 1)


RECIPES = {'CenserHagfish': hagfish_form, 'MortarLeech': leech_form,
           'RattleMillipede': millipede_form, 'Rootclaw': rootclaw_form}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_catalog', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--asset', choices=tuple(RECIPES), action='append')
    parser.add_argument('--samples', type=int, default=24)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    for name in args.asset or RECIPES:
        build(name, args.input_catalog.resolve(), args.output.resolve(), args.samples, RECIPES[name])


if __name__ == '__main__':
    main()
