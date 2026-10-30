from stick.placement import GAP, Rect, next_position

AREA = Rect(0, 0, 1000, 700)
SIZE = (220, 140)


def test_first_sticky_goes_top_left():
    assert next_position(AREA, SIZE, []) == (GAP, 700 - GAP - 140)


def test_next_sticky_goes_to_the_right_without_overlap():
    first = next_position(AREA, SIZE, [])
    taken = [Rect(*first, *SIZE)]
    x, y = next_position(AREA, SIZE, taken)
    assert y == first[1]
    assert x >= first[0] + SIZE[0]
    assert not Rect(x, y, *SIZE).intersects(taken[0])


def test_row_wraps_down_when_full():
    taken = []
    for _ in range(4):  # 4 stickies fill the first row of a 1000 wide area
        taken.append(Rect(*next_position(AREA, SIZE, taken), *SIZE))
    x, y = next_position(AREA, SIZE, taken)
    assert y < taken[0].y
    assert x == GAP


def test_many_stickies_never_overlap_while_there_is_room():
    taken = []
    for _ in range(12):
        taken.append(Rect(*next_position(AREA, SIZE, taken), *SIZE))
    for i, a in enumerate(taken):
        for b in taken[i + 1 :]:
            assert not a.intersects(b)


def test_freed_gap_is_reused():
    taken = []
    for _ in range(3):
        taken.append(Rect(*next_position(AREA, SIZE, taken), *SIZE))
    hole = taken.pop(1)
    assert next_position(AREA, SIZE, taken) == (hole.x, hole.y)


def test_full_screen_cascades_instead_of_failing():
    taken = [Rect(0, 0, 1000, 700)]
    x, y = next_position(AREA, SIZE, taken)
    assert (x, y) == (GAP + 30, 700 - GAP - 140 - 30)
