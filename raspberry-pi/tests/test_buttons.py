
from gpiozero import Button
from signal import pause

pins = {
    "UP": 6,
    "DOWN": 19,
    "LEFT": 5,
    "RIGHT": 26,
    "PRESS": 13,
    "KEY1": 21,
    "KEY2": 20,
    "KEY3": 16
}

buttons = {}

for name, pin in pins.items():
    button = Button(pin, pull_up=True, bounce_time=0.05)
    button.when_pressed = (
        lambda n=name: print(f"Pressed: {n}", flush=True)
    )
    buttons[name] = button

print("Joystick and button test ready.")
print("Press each control. Ctrl+C to exit.")

pause()
