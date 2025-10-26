"""Test the macro parser with examples from the NXBT spec."""

from ns_controller.controller import Buttons
from ns_controller.macro_parser import parse_macro


def test_simple_button_press():
    """Test: B 0.1s"""
    macro = "B 0.1s"
    steps = parse_macro(macro)
    
    assert len(steps) == 2
    # First step: B pressed for 0.1s
    assert steps[0].state.is_pressed(Buttons.B)
    assert steps[0].duration == 0.1
    # Second step: B released (0s)
    assert not steps[1].state.is_pressed(Buttons.B)
    assert steps[1].duration == 0.0
    
    print("✓ Simple button press test passed")


def test_button_press_with_wait():
    """Test: B 0.1s\n1s"""
    macro = """B 0.1s
1s"""
    steps = parse_macro(macro)
    
    assert len(steps) == 3
    # First step: B pressed for 0.1s
    assert steps[0].state.is_pressed(Buttons.B)
    assert steps[0].duration == 0.1
    # Second step: B released (0s)
    assert not steps[1].state.is_pressed(Buttons.B)
    assert steps[1].duration == 0.0
    # Third step: wait 1s
    assert not steps[2].state.is_pressed(Buttons.B)
    assert steps[2].duration == 1.0
    
    print("✓ Button press with wait test passed")


def test_multiple_buttons():
    """Test: A B 0.5s\nB 0.1s\n0.1s"""
    macro = """A B 0.5s
B 0.1s
0.1s"""
    steps = parse_macro(macro)
    
    assert len(steps) == 5
    # First step: A and B pressed for 0.5s
    assert steps[0].state.is_pressed(Buttons.A)
    assert steps[0].state.is_pressed(Buttons.B)
    assert steps[0].duration == 0.5
    # Second step: A and B released
    assert not steps[1].state.is_pressed(Buttons.A)
    assert not steps[1].state.is_pressed(Buttons.B)
    assert steps[1].duration == 0.0
    # Third step: B pressed for 0.1s
    assert steps[2].state.is_pressed(Buttons.B)
    assert not steps[2].state.is_pressed(Buttons.A)
    assert steps[2].duration == 0.1
    # Fourth step: B released
    assert not steps[3].state.is_pressed(Buttons.B)
    assert steps[3].duration == 0.0
    # Fifth step: wait 0.1s
    assert steps[4].duration == 0.1
    
    print("✓ Multiple buttons test passed")


def test_stick_input():
    """Test: L_STICK@-100+000 0.75s\n1.0s"""
    macro = """L_STICK@-100+000 0.75s
1.0s"""
    steps = parse_macro(macro)
    
    assert len(steps) == 3
    # First step: Left stick tilted left for 0.75s
    assert steps[0].state.ls.x == -1.0
    assert steps[0].state.ls.y == 0.0
    assert steps[0].duration == 0.75
    # Second step: Left stick returns to neutral
    assert steps[1].state.ls.x == 0.0
    assert steps[1].state.ls.y == 0.0
    assert steps[1].duration == 0.0
    # Third step: wait 1.0s
    assert steps[2].duration == 1.0
    
    print("✓ Stick input test passed")


def test_stick_neutral():
    """Test: L_STICK@+000+000 0.75s"""
    macro = "L_STICK@+000+000 0.75s"
    steps = parse_macro(macro)
    
    assert len(steps) == 2
    assert steps[0].state.ls.x == 0.0
    assert steps[0].state.ls.y == 0.0
    assert steps[0].duration == 0.75
    
    print("✓ Stick neutral test passed")


def test_stick_diagonal():
    """Test: L_STICK@+100+100 (45° angle)"""
    macro = "L_STICK@+100+100 0.5s"
    steps = parse_macro(macro)
    
    assert len(steps) == 2
    assert steps[0].state.ls.x == 1.0
    assert steps[0].state.ls.y == 1.0
    assert steps[0].duration == 0.5
    
    print("✓ Stick diagonal test passed")


def test_simple_loop():
    """Test: LOOP 3\n    B 0.1s\n    0.1s"""
    macro = """LOOP 3
    B 0.1s
    0.1s"""
    steps = parse_macro(macro)
    
    # Should have 3 iterations × 3 steps per iteration = 9 steps
    # Each iteration: B pressed, B released, wait
    assert len(steps) == 9
    
    # Check first iteration
    assert steps[0].state.is_pressed(Buttons.B)
    assert steps[0].duration == 0.1
    assert not steps[1].state.is_pressed(Buttons.B)
    assert steps[2].duration == 0.1
    
    # Check third iteration
    assert steps[6].state.is_pressed(Buttons.B)
    assert steps[6].duration == 0.1
    
    print("✓ Simple loop test passed")


def test_nested_loop():
    """Test nested loops"""
    macro = """LOOP 2
    A 0.1s
    LOOP 2
        B 0.1s"""
    steps = parse_macro(macro)
    
    # Outer loop: 2 iterations
    # Each outer iteration: A press (2 steps) + inner loop
    # Inner loop: 2 iterations of B press (2 steps each)
    # Total: 2 × (2 + 2 × 2) = 2 × 6 = 12 steps
    assert len(steps) == 12
    
    print("✓ Nested loop test passed")


def test_comments():
    """Test that comments are ignored"""
    macro = """# This is a comment
B 0.1s
# Another comment
0.1s"""
    steps = parse_macro(macro)
    
    assert len(steps) == 3
    assert steps[0].state.is_pressed(Buttons.B)
    
    print("✓ Comments test passed")


def test_right_stick():
    """Test right stick input"""
    macro = "R_STICK@+050+025 0.5s"
    steps = parse_macro(macro)
    
    assert len(steps) == 2
    assert steps[0].state.rs.x == 0.5
    assert steps[0].state.rs.y == 0.25
    assert steps[0].duration == 0.5
    
    print("✓ Right stick test passed")


def test_all_button_mappings():
    """Test that all NXBT button names are recognized"""
    buttons_to_test = [
        ("Y", Buttons.Y),
        ("X", Buttons.X),
        ("B", Buttons.B),
        ("A", Buttons.A),
        ("R", Buttons.R),
        ("ZR", Buttons.ZR),
        ("MINUS", Buttons.MINUS),
        ("PLUS", Buttons.PLUS),
        ("R_STICK_PRESS", Buttons.RS),
        ("L_STICK_PRESS", Buttons.LS),
        ("HOME", Buttons.HOME),
        ("CAPTURE", Buttons.CAPTURE),
        ("DPAD_DOWN", Buttons.DPAD_DOWN),
        ("DPAD_UP", Buttons.DPAD_UP),
        ("DPAD_RIGHT", Buttons.DPAD_RIGHT),
        ("DPAD_LEFT", Buttons.DPAD_LEFT),
        ("L", Buttons.L),
        ("ZL", Buttons.ZL),
    ]
    
    for btn_name, btn_enum in buttons_to_test:
        macro = f"{btn_name} 0.1s"
        steps = parse_macro(macro)
        assert steps[0].state.is_pressed(btn_enum), f"Button {btn_name} not working"
    
    print("✓ All button mappings test passed")


if __name__ == "__main__":
    test_simple_button_press()
    test_button_press_with_wait()
    test_multiple_buttons()
    test_stick_input()
    test_stick_neutral()
    test_stick_diagonal()
    test_simple_loop()
    test_nested_loop()
    test_comments()
    test_right_stick()
    test_all_button_mappings()
    
    print("\n✅ All tests passed!")

