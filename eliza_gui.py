import glob
import math
import six
import sys
import cv2
import numpy as np
import pyautogui
import time
import mss
from PIL import Image
import eliza_logic

def anchor_and_clip(image):
	""" Locates the Eliza game inside the full screenshot and clips it out. """

	# Offsets for approximate in-game solitaire window size at 1600x900 game window size
	max_x = 1074
	max_y = 675

	corner = cv2.imread("card_back/anchor/anchor.png")
	result = cv2.matchTemplate(image, corner, cv2.TM_SQDIFF)
	x, y = cv2.minMaxLoc(result)[2]
	x += 3
	y += 2

	crop_image = image[y:y + max_y, x:x + max_x]
	return x, y, crop_image

def read_freecells(image):
	""" Determines how many unlocked free cells there are. """

	unlocked = cv2.imread("card_back/freecells/cell_unlocked.png")
	locked = cv2.imread("card_back/freecells/cell_locked.png")

	lock_results = []
	for i in range(4):
		# Offsets for approximately here the free cells are given 1600x900 game window size
		x_offset = 314 + (128 * i)
		y_offset = 24
		
		crop_image = image[y_offset:y_offset + 4, x_offset:x_offset + 4]
		# cv2.rectangle(image, (x_offset, y_offset), (x_offset + 4, y_offset + 2), (255, 0, 0), 1)
		unlocked_result = cv2.matchTemplate(crop_image, unlocked, cv2.TM_SQDIFF)
		locked_result = cv2.matchTemplate(crop_image, locked, cv2.TM_SQDIFF)

		lock_results.append(0 if unlocked_result * 10 < locked_result else 1)

	return lock_results

def read_stacks(image):
	""" Determines which cards are in which stack """

	# Offsets for where the stacks are given 1600x900 game window size
	width = 128
	height = 30
	base_x = 46
	base_y = 238

	digits = {}
	for file in glob.glob("card_back/cards/*.png"):
		digit = file.rsplit("/", 1)[1].split(".")[0]
		digits[str(digit)] = cv2.imread(file)

	stacks = []
	for x_stack in range(8):
		stack = []
		for y_stack in range(5):
			sub_amount = int(math.floor(x_stack / 2))
			coord_x = base_x + (width * x_stack) - sub_amount
			coord_y = base_y + (height * y_stack)
			crop_image = image[coord_y:coord_y + 16, coord_x:coord_x + 16]

			result_scores = [cv2.matchTemplate(crop_image, digits[str(i)], cv2.TM_SQDIFF) for i in range(10)]
			card_type = result_scores.index(min(result_scores))

			stack.append(card_type)

		stacks.append(stack)

	return stacks

def computer_hash(my_image):
	""" Uses image to build the game, returns information for solving the game """

	print("Beginning screen detection")
	offset_screen_x, offset_screen_y, my_image = anchor_and_clip(my_image)
	freecells = read_freecells(my_image)
	freecell_hash = "".join(["FU/" if x == 0 else "FL/" for x in freecells])
	stacks = read_stacks(my_image)
	stack_hash = "".join(["SU%s/" % "".join([str(s) for s in stack]) for stack in stacks])
	print("Done. Game detected.")
	return [offset_screen_x, offset_screen_y, stack_hash + freecell_hash]

def read_file(filename):
	""" Reads a screenshot from a file and solves it. """
	print("Beginning file read...")
	my_image = cv2.imread(filename)
	return computer_hash(my_image)

def screenshot():
	""" Takes a screenshot from the screen and solves it. """
	print("Taking screenshot...")
	with mss.mss() as screenshot:
		monitor = screenshot.monitors[0]
		shot = screenshot.grab(monitor)
		frame = np.array(Image.frombytes("RGB", (shot.width, shot.height), shot.rgb))
		frame_2 = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
	return computer_hash(frame_2)

def execute_solution(offset_x, offset_y, moves):
	""" Executes solution by moving mouse and clicking. """

	# Offsets for approximately where everything is given 1600x900 game window size
	base_x = 46
	base_y = 238
	freecell_x = 314
	freecell_y = 24
	width = 128
	height = 30
	modifier_x = 40
	modifier_y = 19

	# Correct for retina display (change to 1 on conventional monitor)
	res_scale = 0.5

	# First, click the window
	pyautogui.mouseDown((offset_x + 100) * res_scale, (offset_y + 100) * res_scale, button="left")
	time.sleep(0.5)
	pyautogui.mouseUp()
	time.sleep(1)

	# Now, replay the moves one by one
	for move in moves:
		# which stack, how many cards down -> which stack, how many cards down
		x_pre, y_pre, x_post, y_post = move

		# If it's a regular stack, move to the offset
		if x_pre < 8:
			x_pre_final = offset_x + base_x + (width * x_pre) + modifier_x
			y_pre_final = offset_y + base_y + (height * y_pre) + modifier_y
		# Separate offsets for freecell
		else:
			x_pre_final = offset_x + freecell_x + (width * (x_pre - 8)) + modifier_x
			y_pre_final = offset_y + freecell_y + modifier_y

		if x_post < 8:
			x_post_final = offset_x + base_x + (width * x_post) + modifier_x
			y_post_final = offset_y + base_y + (height * y_post) + modifier_y
		else:
			x_post_final = offset_x + freecell_x + (width * (x_post - 8)) + modifier_x
			y_post_final = offset_y + freecell_y + modifier_y

		print("Mouse to %d, %d -> drag to %d, %d" % (x_pre_final, y_pre_final, x_post_final, y_post_final))

		# Move the mouse to the beginning place
		pyautogui.moveTo(x_pre_final * res_scale, y_pre_final * res_scale, duration = 0.25)

		# Click and drag to the end
		pyautogui.dragTo(x_post_final * res_scale, y_post_final * res_scale, duration = 0.25, button = "left")

		# Wait for a while
		time.sleep(0.25)

def main():
	""" Dispatches by reading file argument on command line or taking snapshot of screen. """

	if len(sys.argv) > 1 and sys.argv[1]:
		_, _, hash = read_file(sys.argv[1])
		offset_x = 0
		offset_y = 0
	else:
		offset_x, offset_y, hash = screenshot()

	print(hash)
	game = eliza_logic.Game(0)
	game.exact_setup(hash)
	print(game)
	result = game.global_solve(-1)
	print(result)

	# If it was a screen grab, we can actually do this -- just type n/q/c to quit or anything else to continue
	if result is not None and offset_x and offset_y:
		x = six.moves.input("Ready for automated solution? ")
		if x.lower() in ["n", "q", "c"]:
			return

		execute_solution(offset_x, offset_y, result)

if __name__ == "__main__":
	main()