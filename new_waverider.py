#!/usr/bin/env python3
import curses
import math
import random
import sys
import time
import traceback
import pygame

import song1


# Game constants
SYNC_FRAMES = -8 # ADJUST GAME SYNC
BEAT_EPS = 3
JUDGE_EXIST_DUR = 20

JUDGE_NORMAL = 1
JUDGE_PERFECT = 2
JUDGE_PERFECT_TEXT = "PERFECT"
JUDGE_MISS = 3
JUDGE_MISS_TEXT = "  MISS  "
JUDGE_GOOD = 4
JUDGE_GOOD_TEXT = "  GOOD  "
JUDGE_EMPTY_TEXT = "        "
JUDGE_DIR_OFFSET_DEFAULT = 6

NOTE_TYPE_DEFAULT = 0
NOTE_TYPE_HOLD = 1

MILLIS_PER_DOT = 40
MAIN_WINDOW_MARGIN = 8
dir_dict = {
    curses.KEY_UP: 1,
    curses.KEY_DOWN: 2,
    48: 5
}

# For color printnig


# Factoring out these functions so we can add graphical flair later
def beat_success(offset):
    global score, streak, misses, judge, judge_dur, judge_text, health
    streak += 1
    misses = 0

    accuracy = abs(offset) / BEAT_EPS
    if accuracy < 0.4: # Perfect judgement
        judge = JUDGE_PERFECT
        judge_text = JUDGE_PERFECT_TEXT
        health += 3
    else:
        judge = JUDGE_GOOD
        judge_text = JUDGE_GOOD_TEXT
        health += 1
    if health > 100:
        health = 100
    judge_dur = JUDGE_EXIST_DUR

    score += int(100 + math.log10(streak))

def hold_success():
    global score, streak, misses, judge_dur, health
    streak += 1
    misses = 0

    health += 0.1
    if health > 100:
        health = 100
    judge_dur = JUDGE_EXIST_DUR

    score += int(100 + math.log10(streak))

def beat_failed():
    global streak, misses, health, judge, judge_dur, judge_text
    streak = 0
    misses += 1
    # loss = int(1 + math.log2(misses))
    loss = 10
    judge = JUDGE_MISS
    judge_dur = JUDGE_EXIST_DUR
    judge_text = JUDGE_MISS_TEXT
    health = 0 if health - loss < 0 else health - loss

# Core game logic
def start_game():
    # Initialise screen, disable echo of inputs and input buffering
    sc = curses.initscr()
    curses.start_color()
    curses.use_default_colors()

    curses.init_pair(JUDGE_NORMAL, -1, -1)
    curses.init_pair(JUDGE_PERFECT, curses.COLOR_BLUE, -1)
    curses.init_pair(JUDGE_MISS, curses.COLOR_RED, -1)
    curses.init_pair(JUDGE_GOOD, curses.COLOR_GREEN, -1)

    h, w = sc.getmaxyx()
    
    # Initialize Song
    pygame.init()
    pygame.mixer.init()
    pygame.mixer.music.load(song1.file_name)


    # Initialise banner, header and game windows
    ban = curses.newwin(6, w, 0, 0)
    hdr = curses.newwin(5, w, 6, 0)
    win = curses.newwin(h - 11, w, 11, 0)
    ban.border(0)
    hdr.border(0)
    win.border(0)

    # Display game and song title in banner window
    # title_padding = (w - 18) // 2
    # title_text = title_padding * ">" + " WAVERIDER " + title_padding * "<"
    title_text = "WAVE RIDER"
    song_padding = (w - len(song1.song_name) - 22) // 2
    song_text = song_padding * ">" + f" NOW PLAYING: {song1.song_name} " \
            + song_padding * "<"
    ban.addstr(2, w // 2 - 5, title_text)
    ban.addstr(3, 4, song_text)
    ban.refresh()

    # Enable keypad, set cursor to invisible
    win.keypad(1)
    curses.curs_set(0)

    # Initialise game variables
    global score, streak, misses, health, judge, judge_dur, judge_text, judge_dir_offset, health
    score = 0
    streak = 0
    misses = 0
    health = 100
    health_color = JUDGE_GOOD
    judge = 0
    judge_dur = JUDGE_EXIST_DUR
    judge_text = JUDGE_EMPTY_TEXT
    judge_dir_offset = JUDGE_DIR_OFFSET_DEFAULT
    beatmap_dir = 1

    hold_status = 0

    beat_abs_pos = 0

    # Load beatmap
    beatmap = song1.beatmap.copy()
    for beat in beatmap:
        beat[0] = beat[0] + song1.start_delay
    
    cur_pos, prev_pos = 0, 0

    # 0 = normal, 1 = up, 2 = down
    cur_dir = 0
    debug = ""

    start_time = time.time() * 1000
    pygame.mixer.music.play()

    # Game loop
    while True:
        win.timeout(20)

        # Calculate current position (in dots)
        elapsed_time = time.time() * 1000 - start_time
        cur_pos = int(elapsed_time // MILLIS_PER_DOT)

        
        if judge != 0:
            judge_dur = judge_dur - 1
            if judge_dur <= 0:
                judge = JUDGE_NORMAL
                judge_text = JUDGE_EMPTY_TEXT

        # Delete all the beats that have already passed
        while len(beatmap) > 0 and elapsed_time > beatmap[0][0] + (BEAT_EPS + SYNC_FRAMES) * MILLIS_PER_DOT:
            if beatmap[0][1] == 1:
                judge_dir_offset = 0 - JUDGE_DIR_OFFSET_DEFAULT
            elif beatmap[0][1] == 2:
                judge_dir_offset = 0 + JUDGE_DIR_OFFSET_DEFAULT
            beat_failed()
            if (beatmap[0][1] == 5):
                judge_dir_offset = 0 - JUDGE_DIR_OFFSET_DEFAULT
                beatmap.pop(0)
            beatmap.pop(0)
            
        # Exit at end of song or if dead:
        if song1.song_dur < elapsed_time or health <= 0:
            break

        # Read keypress
        key = win.getch()

        elif key != -1:
            # Exit game loop if unrecognised keys are entered
            if key not in dir_dict:
                break

            # Set the direction of the player
            cur_dir = dir_dict[key]
            
            if (len(beatmap) > 0):
                beat_abs_pos = int(beatmap[0][0] // MILLIS_PER_DOT)
                offset = beat_abs_pos - cur_pos + SYNC_FRAMES
                beatmap_dir = beatmap[0][1]
            else:
                beatmap_dir = 0
            
            if abs(offset) < BEAT_EPS and dir_dict[key] == beatmap_dir:
                beat_success(offset)
                # debug = f"offset {offset}"
                if beatmap_dir == 5 and hold_status == 0:
                    hold_status = 1
                elif beatmap_dir == 5 and hold_status == 1:
                    
                else:
                    beatmap.pop(0) # delete the beat so you can't double score?      
                
            else:
                beat_failed()
                # debug = f"failed offset {offset}"
                # debug = f"positions {beat_abs_pos}, {cur_pos}"

        # RENDERING LOGIC

        # Skip rendering this frame if it is identical to the previous frame
        if cur_pos == prev_pos:
            continue
        
        prev_pos = cur_pos

        # Clear screen and re-draw borders
        for i in range(-6, 7):
            win.addstr(12 + i, MAIN_WINDOW_MARGIN - 1, ' ' * w)
        win.border(0)

        # Print variables and debugging information in the header
        score_text = f"Score: {score}"
        streak_text = f"Streak: {streak}"
        health_text = f"Health: {health//2 * '■'}{(50 - health//2) * ' '} |"
        debug_text = f"Debug: {debug}"

        
        if health > 30:
            health_color = JUDGE_GOOD
        else:
            health_color = JUDGE_MISS

        hdr.addstr(2, 1, (w - 2) * ' ')
        hdr.addstr(2, 3, health_text, curses.color_pair(health_color))
        hdr.addstr(2, 78, streak_text)
        hdr.addstr(2, 104, score_text)
        win.addstr(2, w // 2 - len(debug_text) // 2, debug_text)
        

        # Draw '@'
        if cur_dir == 1:
            win.addch(12 - 4, MAIN_WINDOW_MARGIN, '◎', curses.color_pair(judge))
            judge_dir_offset = 0 - JUDGE_DIR_OFFSET_DEFAULT
        elif cur_dir == 2:
            win.addch(12 + 4, MAIN_WINDOW_MARGIN, '◎', curses.color_pair(judge))
            judge_dir_offset = 0 + JUDGE_DIR_OFFSET_DEFAULT
        else:
            win.addch(12, MAIN_WINDOW_MARGIN, '○', curses.color_pair(judge))
        
        win.addstr(12 + judge_dir_offset, 5, judge_text, curses.color_pair(judge))
        
        cur_dir = 0

        # Draw dots (main line)
        for i in range(MAIN_WINDOW_MARGIN + 1, w - MAIN_WINDOW_MARGIN):
            win.addch(12, i, '·')

        # Draw bumps
        for i in range(0, len(beatmap)):
            beat = beatmap[i]
            beat_pos = int((beat[0]) // MILLIS_PER_DOT) - cur_pos

            if beat[1] == 6:
                continue
            
            # Render only up till the end of the screen
            if beat_pos > w - MAIN_WINDOW_MARGIN - 1:
                break

            if beat_pos < MAIN_WINDOW_MARGIN:
                continue
            
            if beat[1] == 1 or beat[1] == 2:
                win.addch(12, beat_pos, ' ')
                if beat[1] == 1:
                    win.addch(12 - 4, beat_pos, '·')
                    for i in range(1, 4):
                        win.addch(12 - i, beat_pos - 1, '·')
                        win.addch(12 - i, beat_pos + 1, '·')
                elif beat[1] == 2:
                    win.addch(12 + 4, beat_pos, '·')
                    for i in range(1, 4):
                        win.addch(12 + i, beat_pos - 1, '·')
                        win.addch(12 + i, beat_pos + 1, '·')
            
            if beat[1] == 5:
                nextbeat = beatmap[i + 1]
                nextbeat_pos = int((nextbeat[0]) // MILLIS_PER_DOT) - cur_pos
                for i in range(beat_pos, nextbeat_pos, 2):
                    win.addch(12, i, '^')
                    win.addch(12, i + 1, 'v')

        win.refresh()
        hdr.refresh()
    pygame.mixer.music.stop()

try:
    start_game()
except KeyboardInterrupt:
    # Graceful termination
    pass
except Exception as e:
    curses.endwin()
    traceback.print_exc()
    pygame.quit()
    sys.exit()

curses.endwin()

