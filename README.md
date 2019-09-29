# eliza_solitaire_bot

This code solves Kabufuda solitaire as implemented in Eliza (not intended for public use at this time).

`eliza_logic.py` contains all of the code to solve solitaire. `eliza_gui.py` contains code to read the screen, detect the game being played, and implement the solution via mouse -- simply run `python eliza_gui.py` to read directly from the screen or `python eliza_gui.py screenshot.png` to load from a previously saved screenshot. Running `eliza_logic.py` directly generates a random game and solves it.

Currently, the code expects the game to be running in a 1600x900 window, unobscured, anywhere on the screen, and expects a 2x DPI screen (e.g. Mac Retina).
