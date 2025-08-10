import random
import time
from machine import Pin
from pico_lcd import LCD_1inch14  # Your driver file

# Convert RGB888 to RGB565 (BGR order for your LCD)
def color565(r, g, b):
    return ((b & 0xF8) << 8) | ((g & 0xFC) << 3) | (r >> 3)

# Initialize LCD
lcd = LCD_1inch14()

# Initialize button pins
button_a = Pin(15, Pin.IN, Pin.PULL_UP)      # Spin/start button A
button_b = Pin(17, Pin.IN, Pin.PULL_UP)      # Pause/unpause button B
joystick_up = Pin(2, Pin.IN, Pin.PULL_UP)    # Joystick up (GP2), acts like button A

# Color mapping for numbers in the middle row
num_colors = {
    1: color565(255, 0, 0),       # Green
    2: color565(255, 165, 0),     # Green
    3: color565(255, 255, 0),     # Yellow
    4: color565(0, 0, 255),       # Blue
    5: color565(0, 255, 255),     # Purple
    6: color565(0, 255, 0),       # Red
    7: color565(255, 105, 180),   # Green
    8: color565(255, 255, 0),     # Yellow
    9: color565(0, 255, 255),     # Purple
}

GAME_DURATION = 120  # seconds

score = 0
high_score = 0
game_start_time = None
game_over = False
waiting_for_restart = False
in_main_screen = True
paused = False
pause_start_time = 0
accumulated_pause_time = 0  # total paused time

# Current frame toggle for handle animation (0 or 1)
frame = 0

# Store current slot numbers for redraw
top = [random.randint(1, 9) for _ in range(3)]
mid = [random.randint(1, 9) for _ in range(3)]
bot = [random.randint(1, 9) for _ in range(3)]

def load_high_score():
    try:
        with open("highscore.txt", "r") as f:
            return int(f.read())
    except:
        return 0

def save_high_score(new_high):
    try:
        with open("highscore.txt", "w") as f:
            f.write(str(new_high))
    except:
        pass

def wait_for_press(pin):
    while pin.value() == 1:
        time.sleep_ms(10)
    time.sleep_ms(50)
    while pin.value() == 0:
        time.sleep_ms(10)

def draw_main_screen():
    lcd.fill(color565(0, 0, 0))
    white = color565(255, 255, 255)
    lcd.text("Gambling", 40, 30, white)
    lcd.text("Press A to start", 0, 60, white)
    lcd.text(f"High Score: {high_score}", 20, 90, white)
    lcd.show()

def draw_slot(top, mid, bot, score, remaining_time):
    global frame
    lcd.fill(color565(0, 0, 0))  # Clear background black
    white = color565(255, 255, 255)

    y = 10
    score_str = f"Score: {score}"
    mins = remaining_time // 60 if remaining_time is not None else 0
    secs = remaining_time % 60 if remaining_time is not None else 0
    time_str = f"Time: {mins}:{secs:02d}"

    if frame == 0:
        # HANDLE UP FRAME
        lcd.text("=========", 10, y, white); y += 20

        # Top row + spinner O + fixed score position
        lcd.text("||", 10, y, white)
        x_pos = 26
        for num in top:
            lcd.text(str(num), x_pos, y, white)
            x_pos += 12
        lcd.text("||  O", x_pos, y, white)  # O handle here
        lcd.text(score_str, 110, y, white) # fixed score position
        y += 20

        # Middle row colored + spinner / + fixed time position
        lcd.text("|-", 10, y, white)
        x_pos = 26
        for num in mid:
            lcd.text(str(num), x_pos, y, num_colors[num])
            x_pos += 12
        lcd.text("-| /", x_pos, y, white)    # handle slash
        lcd.text(time_str, 110, y, white)   # fixed time position
        y += 20

        # Bottom row + spinner /
        lcd.text("||", 10, y, white)
        x_pos = 26
        for num in bot:
            lcd.text(str(num), x_pos, y, white)
            x_pos += 12
        lcd.text("||/", x_pos, y, white)
        y += 20

        lcd.text("=========", 10, y, white); y += 20

    else:
        # HANDLE DOWN FRAME
        lcd.text("=========", 10, y, white); y += 20

        # Top row, no O here, fixed score
        lcd.text("||", 10, y, white)
        x_pos = 26
        for num in top:
            lcd.text(str(num), x_pos, y, white)
            x_pos += 12
        lcd.text("||", x_pos, y, white)       # no O here
        lcd.text(score_str, 110, y, white)    # fixed score position
        y += 20

        # Middle row colored + NO backslash here + fixed time
        lcd.text("|-", 10, y, white)
        x_pos = 26
        for num in mid:
            lcd.text(str(num), x_pos, y, num_colors[num])
            x_pos += 12
        lcd.text("-|", x_pos, y, white)       # NO backslash here
        lcd.text(time_str, 110, y, white)    # fixed time position
        y += 20

        # Bottom row + spinner backslash, no trailing spaces
        lcd.text("||", 10, y, white)
        x_pos = 26
        for num in bot:
            lcd.text(str(num), x_pos, y, white)
            x_pos += 12
        lcd.text("||\\", x_pos, y, white)     # backslash at end
        y += 20

        # Last line with trailing backslash and separate O on next line
        lcd.text("========= \\", 10, y, white); y += 20
        lcd.text("           O", 10, y, white)  # indent O under backslash

    # Move down one line before winner text
    y += 15
    if mid[0] == mid[1] == mid[2]:
        lcd.text("ding ding ding winner", 10, y, white)

    lcd.show()

def draw_game_over(final_score):
    lcd.fill(color565(0, 0, 0))
    white = color565(255, 255, 255)
    lcd.text("TIME UP", 40, 40, white)
    lcd.text("Final Score: {}".format(final_score), 40, 60, white)
    lcd.text("Press A to play again", 0, 90, white)
    lcd.show()

def draw_paused():
    lcd.fill(color565(0, 0, 0))
    white = color565(255, 255, 255)
    lcd.text("PAUSED", 50, 60, white)
    lcd.show()

# Load high score at start
high_score = load_high_score()

last_timer_update = 0

while True:
    current_time = time.time()

    # Handle pause toggle (on B button press)
    if not button_b.value():
        wait_for_press(button_b)
        if not paused:
            paused = True
            pause_start_time = time.time()
            draw_paused()
        else:
            paused = False
            accumulated_pause_time += time.time() - pause_start_time
            if game_start_time is not None and not game_over:
                elapsed = int(current_time - game_start_time - accumulated_pause_time)
                remaining_time = max(0, GAME_DURATION - elapsed)
                draw_slot(top, mid, bot, score, remaining_time)
            else:
                draw_main_screen()
        time.sleep(0.2)
        continue

    if in_main_screen:
        draw_main_screen()
        if not button_a.value() or not joystick_up.value():
            if not button_a.value():
                wait_for_press(button_a)
            else:
                wait_for_press(joystick_up)
            score = 0
            game_start_time = time.time()
            accumulated_pause_time = 0
            game_over = False
            waiting_for_restart = False
            paused = False
            in_main_screen = False
            frame = 0
            top = [random.randint(1, 9) for _ in range(3)]
            mid = [random.randint(1, 9) for _ in range(3)]
            bot = [random.randint(1, 9) for _ in range(3)]
            draw_slot(top, mid, bot, score, GAME_DURATION)
            last_timer_update = current_time
        time.sleep(0.1)
        continue

    if waiting_for_restart:
        if not button_a.value() or not joystick_up.value():
            if not button_a.value():
                wait_for_press(button_a)
            else:
                wait_for_press(joystick_up)
            in_main_screen = True
            waiting_for_restart = False
        time.sleep(0.1)
        continue

    if paused:
        time.sleep(0.1)
        continue

    if game_start_time is not None and not game_over:
        elapsed = int(current_time - game_start_time - accumulated_pause_time)
        remaining_time = max(0, GAME_DURATION - elapsed)
        if current_time - last_timer_update >= 1:
            draw_slot(top, mid, bot, score, remaining_time)
            last_timer_update = current_time
        if remaining_time == 0:
            game_over = True
            if score > high_score:
                high_score = score
                save_high_score(high_score)
            draw_game_over(score)
            waiting_for_restart = True
            continue
    else:
        remaining_time = None

    if (not button_a.value() or not joystick_up.value()) and not game_over and not in_main_screen:
        if not button_a.value():
            wait_for_press(button_a)
        else:
            wait_for_press(joystick_up)
        frame = 1 - frame
        top = [random.randint(1, 9) for _ in range(3)]
        mid = [random.randint(1, 9) for _ in range(3)]
        bot = [random.randint(1, 9) for _ in range(3)]
        if mid[0] == mid[1] == mid[2]:
            score += mid[0]
        elapsed = int(current_time - game_start_time - accumulated_pause_time)
        remaining_time = max(0, GAME_DURATION - elapsed)
        draw_slot(top, mid, bot, score, remaining_time)
