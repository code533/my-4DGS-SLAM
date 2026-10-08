# M5-C implementation fix: add_dygs propagation

Date: 2026-10-08

Branch:

    feature/m5c-flow-reliability-opacity

Fix commit:

    4691df5bc0160c7ce7cc1511a1a3e5e0027f859f

## Symptom

The first cross-system M5-C run crashed in:

    create_pcd_from_image_and_depth(...)

with:

    NameError: name 'add_dygs' is not defined

## Root cause

The M5-C opacity rule intentionally preserves baseline opacity for
dynamic-object initialization, which requires knowing add_dygs inside
create_pcd_from_image_and_depth().

The outer helper already had add_dygs, but the inner helper was still called as:

    create_pcd_from_image_and_depth(cam, rgb, depth, init)

and its signature was:

    def create_pcd_from_image_and_depth(..., init=False)

Therefore add_dygs was out of scope.

## Fix

Propagate the flag explicitly:

    create_pcd_from_image_and_depth(
        cam, rgb, depth, init, add_dygs=add_dygs
    )

and extend the helper signature with:

    add_dygs=False

The frozen M5-C method itself is unchanged.

## Experimental consequence

Discard the crashed run and restart it from the beginning after pulling this
commit.
