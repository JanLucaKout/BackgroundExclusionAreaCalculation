"""
# This scripts extracts the desired total area by using the background exclusion method.
Created in April 2026
@author: Jan Luca Kout
"""

#################################################################################
# Libraries

import cv2
import numpy as np
import os
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox
import csv

#################################################################################
# Global Variables
INPUT_FOLDER_PATH = None
OUTPUT_FOLDER_PATH = None
DEFAULT_DPI = 300
VALID_EXTENSIONS = ('.jpg', '.jpeg', '.tif')
RESULT_IMAGE_NAME_EXTENSION = '_InverseArea.jpg'
CSV_FILE_NAME = "total_areas.csv"

# Background HSV [Hue, Saturation, Value]
# Full Hue Scale (0-179, Min. 0, Max. 179)
# Low Saturation (0-40, Min. 0, Max. 255)
# Value must be above a certain point to exclude dark shadows (70-255, Min. 0, Max. 255)

# Standard Values Lower Range
BGR_LOWER_HUE = 0
BGR_LOWER_SAT = 0
BGR_LOWER_VAL = 70

# Standard Values Upper Range
BGR_UPPER_HUE = 179
BGR_UPPER_SAT = 30
BGR_UPPER_VAL = 255

# Standard Values Color Overlay (Magenta)
COLOR_RED = 255
COLOR_GREEN = 0
COLOR_BLUE = 255

#################################################################################
# Area Extraction Methods

def update_and_validate_background_settings(settings_dictionary):
	global BGR_LOWER_HUE, BGR_LOWER_SAT, BGR_LOWER_VAL, BGR_UPPER_HUE, BGR_UPPER_SAT, BGR_UPPER_VAL, COLOR_RED, \
		COLOR_GREEN, COLOR_BLUE

	try:
		# Convert all strings to integers
		vals = {k: int(v) for k, v in settings_dictionary.items()}

		# Check Absolute HSV/RGB Ranges
		# Hue is 0-179, others are 0-255
		if not (0 <= vals['lower_hue'] <= 179 and 0 <= vals['upper_hue'] <= 179):
			raise ValueError("Hue must be between 0 and 179.")

		for k in ['lower_sat', 'upper_sat', 'lower_val', 'upper_val', 'red', 'green', 'blue']:
			if not (0 <= vals[k] <= 255):
				raise ValueError(f"{k.replace('_', ' ').title()} must be between 0 and 255.")

		# Check Logical Ranges (Lower must be <= Upper)
		if vals['lower_hue'] > vals['upper_hue']:
			raise ValueError("Lower Hue cannot be greater than Upper Hue.")
		if vals['lower_sat'] > vals['upper_sat']:
			raise ValueError("Lower Saturation cannot be greater than Upper Saturation.")
		if vals['lower_val'] > vals['upper_val']:
			raise ValueError("Lower Value cannot be greater than Upper Value.")

		# Successful Validation -> Assign to Globals
		BGR_LOWER_HUE, BGR_UPPER_HUE = vals['lower_hue'], vals['upper_hue']
		BGR_LOWER_SAT, BGR_UPPER_SAT = vals['lower_sat'], vals['upper_sat']
		BGR_LOWER_VAL, BGR_UPPER_VAL = vals['lower_val'], vals['upper_val']
		COLOR_RED = vals['red']
		COLOR_GREEN = vals['green']
		COLOR_BLUE = vals['blue']

		print("Settings successfully updated and validated.")
		return True

	except ValueError as e:
		# Catch conversion errors or custom range errors
		messagebox.showerror("Validation Error", str(e))
		return False

	return


def get_dpi(image_file):
	img = Image.open(image_file)

	try:
		dpi = int(img.info["dpi"][1])
	except:
		dpi = DEFAULT_DPI

	return dpi


def generate_overlay_image(cv2_image_file, mask, base_name, output_path, area_cm2, dpi, settings_list):

	# Create a copy of the image
	overlay = cv2_image_file.copy()

	# Create a colored overlay
	overlay[mask == 255] = [COLOR_RED, COLOR_GREEN, COLOR_BLUE]
	visual_check = cv2.addWeighted(cv2_image_file, 0.7, overlay, 0.3, 0)

	# Prepare the Metadata Text
	lines = [
		'Background Exclusion Area Calculation',
		f"File: {base_name}",
		f"Area: {area_cm2:.4f} cm2",
		f"DPI: {dpi:.4f}",
		"",
	]
	for setting in settings_list:
		lines.append(setting)

	# Draw Text onto the Image
	font = cv2.FONT_HERSHEY_SIMPLEX
	font_scale = 1.2
	thickness = 2
	# Starting coordinates
	x, y = 50, 80

	for i, line in enumerate(lines):
		# Calculate vertical position for each line
		line_y = y + (i * 50)

		# Draw Black Outline (Shadow) for readability
		cv2.putText(visual_check, line, (x+2, line_y+2), font, font_scale, (0, 0, 0), thickness + 2)
		# Draw White Text
		cv2.putText(visual_check, line, (x, line_y), font, font_scale, (255, 255, 255), thickness)

	# Save
	output_filename = f"{base_name}{RESULT_IMAGE_NAME_EXTENSION}"
	cv2.imwrite(os.path.join(output_path, output_filename), visual_check)


def get_area_by_background_exclusion(cv2_image_file, dpi):

	# Convert to HSV
	hsv = cv2.cvtColor(cv2_image_file, cv2.COLOR_BGR2HSV)

	# Define the Background Range
	background_lower_range = np.array([BGR_LOWER_HUE, BGR_LOWER_SAT, BGR_LOWER_VAL])
	background_upper_range = np.array([BGR_UPPER_HUE, BGR_UPPER_SAT, BGR_UPPER_VAL])

	# Create the Background Mask
	paper_mask = cv2.inRange(hsv, background_lower_range, background_upper_range)

	# Invert the mask
	mask = cv2.bitwise_not(paper_mask)

	# Calculate Area
	total_pixels = np.sum(mask == 255)
	pixel_to_cm2 = (2.54 / dpi) ** 2
	total_area_cm2 = total_pixels * pixel_to_cm2

	return total_area_cm2, mask


def export_results_to_csv(data_dict, output_folder):
	# Construct the full file path
	file_path = os.path.join(output_folder, CSV_FILE_NAME)

	# Define the headers
	headers = ["sample_name", "total_area_cm2"]

	try:
		with open(file_path, mode='w', newline='') as csvfile:
			writer = csv.writer(csvfile, delimiter=';')

			writer.writerow(headers)

			for sample_name, area in data_dict.items():
				writer.writerow([sample_name, f"{area:.6f}"])

		print(f"Successfully created: {file_path}")
		return file_path

	except Exception as e:
		print(f"An error occurred while saving the CSV: {e}")
		return None


def get_settings_list():
	settings = []
	settings.append('Background Range Settings:')
	settings.append(f"Hue: {BGR_LOWER_HUE}-{BGR_UPPER_HUE}")
	settings.append(f"Saturation: {BGR_LOWER_SAT}-{BGR_UPPER_SAT}")
	settings.append(f"Value: {BGR_LOWER_VAL}-{BGR_UPPER_VAL}")
	return settings


def calculate_area(input_folder_path, output_folder_path):

	# Get a list of all valid image files
	image_file_paths = [
		os.path.join(input_folder_path, f) for f in os.listdir(input_folder_path)
		if f.lower().endswith(VALID_EXTENSIONS) and os.path.isfile(os.path.join(input_folder_path, f))
	]

	result_dictionary = {}
	settings_list = get_settings_list()

	for image_file_path in image_file_paths:
		base_name = os.path.splitext(os.path.basename(image_file_path))[0]
		dpi = get_dpi(image_file_path)
		cv2_image = cv2.imread(image_file_path)
		total_area, mask = get_area_by_background_exclusion(cv2_image, dpi)
		result_dictionary[base_name] = total_area
		print(f"{base_name} | Total Area: {total_area:.4f} cm2")
		generate_overlay_image(cv2_image, mask, base_name, output_folder_path, total_area, dpi, settings_list)

	export_results_to_csv(result_dictionary, output_folder_path)


#################################################################################
# GUI Button Functions

def on_button_press_select_input_folder():
	global INPUT_FOLDER_PATH
	INPUT_FOLDER_PATH = filedialog.askdirectory(title="Select the Input Folder")

	update_input_folder_label()

def update_input_folder_label():
	if INPUT_FOLDER_PATH:
		input_folder_path_label.config(text=f"Input Folder: {INPUT_FOLDER_PATH}")
	else:
		input_folder_path_label.config(text="No folder selected")

def on_button_press_select_output_folder():
	global OUTPUT_FOLDER_PATH
	OUTPUT_FOLDER_PATH = filedialog.askdirectory(title="Select the Output Folder")

	update_output_folder_label()

def update_output_folder_label():
	if OUTPUT_FOLDER_PATH:
		output_folder_path_label.config(text=f"Output Folder: {OUTPUT_FOLDER_PATH}")
	else:
		output_folder_path_label.config(text="No folder selected")

def get_entry_field_settings():
	settings = {
		'lower_hue':bgr_lower_hue_entry.get(),
		'lower_sat':bgr_lower_sat_entry.get(),
		'lower_val':bgr_lower_val_entry.get(),
		'upper_hue':bgr_upper_hue_entry.get(),
		'upper_sat':bgr_upper_sat_entry.get(),
		'upper_val':bgr_upper_val_entry.get(),
		'red':color_red_entry.get(),
		'green':color_green_entry.get(),
		'blue':color_blue_entry.get()
	}
	return settings


def on_button_press_calculate_area():
	if not INPUT_FOLDER_PATH or not OUTPUT_FOLDER_PATH:
		messagebox.showwarning("Missing Paths", "Please select both Input and Output folders.")

	input_exists = os.path.isdir(INPUT_FOLDER_PATH)
	output_exists = os.path.isdir(OUTPUT_FOLDER_PATH)

	if input_exists and output_exists:
		try:
			settings = get_entry_field_settings()
			update_and_validate_background_settings(settings)

			calculate_area(INPUT_FOLDER_PATH, OUTPUT_FOLDER_PATH)
			messagebox.showinfo("Success", "Area calculation completed successfully!")
		except Exception as e:
			messagebox.showerror("Error", f"An error occurred during processing:\n{e}")


#################################################################################
# Gui Window Root

# Initialize the main window
root = tk.Tk()
root.title("Background Exclusion Area Calculation")
root.geometry("700x700")

#################################################################################
# TKINTER GUI FILEDIALOG BUTTONS

top_frame = tk.Frame(root)

label_top_frame = tk.Label(top_frame, text="Select Input/Output Folders", justify="center", font=("Arial", 14, "bold"))
label_top_frame.grid(row=0, column=0, padx=10, pady=10, columnspan=2)

button_input_folder = tk.Button(top_frame, text="Select Input Folder", command=on_button_press_select_input_folder, width=22, height=2)
button_input_folder.grid(row=1, column=0, padx=10, pady=10)

input_folder_path_label = tk.Label(top_frame, text="", wraplength=500, justify="center")
input_folder_path_label.grid(row=1, column=1, padx=10, pady=10)

button_output_folder = tk.Button(top_frame, text="Select Output Folder", command=on_button_press_select_output_folder, width=22, height=2)
button_output_folder.grid(row=2, column=0, padx=10, pady=10)

output_folder_path_label = tk.Label(top_frame, text="", wraplength=500, justify="center")
output_folder_path_label.grid(row=2, column=1, padx=10, pady=10)

top_frame.grid(row=0, column=0)

#################################################################################
# TKINTER GUI ENTRY FIELDS

middle_frame = tk.Frame(root)

label_background_range = tk.Label(middle_frame, text="Background Range Settings", justify="center", font=("Arial", 14, "bold"))
label_background_range.grid(row=0, column=0, padx=10, pady=10, columnspan=3)


label_lower_hue = tk.Label(middle_frame, text="Lower Hue", justify="center")
label_lower_hue.grid(row=1, column=0, padx=10, pady=10)

label_lower_sat = tk.Label(middle_frame, text="Lower Saturation", justify="center")
label_lower_sat.grid(row=1, column=1, padx=10, pady=10)

label_lower_val = tk.Label(middle_frame, text="Lower Value",  justify="center")
label_lower_val.grid(row=1, column=2, padx=10, pady=10)


bgr_lower_hue_entry = tk.Entry(middle_frame, width=15, font=("Arial", 12))
bgr_lower_hue_entry.insert(0, str(BGR_LOWER_HUE))
bgr_lower_hue_entry.grid(row=2, column=0, padx=10, pady=10)

bgr_lower_sat_entry = tk.Entry(middle_frame, width=15, font=("Arial", 12))
bgr_lower_sat_entry.insert(0, str(BGR_LOWER_SAT))
bgr_lower_sat_entry.grid(row=2, column=1, padx=10, pady=10)

bgr_lower_val_entry = tk.Entry(middle_frame, width=15, font=("Arial", 12))
bgr_lower_val_entry.insert(0, str(BGR_LOWER_VAL))
bgr_lower_val_entry.grid(row=2, column=2, padx=10, pady=10)


empty_label = tk.Label(middle_frame, text="", justify="center")
empty_label.grid(row=3, column=0, padx=10, pady=10)


label_upper_hue = tk.Label(middle_frame, text="Upper Hue", justify="center")
label_upper_hue.grid(row=4, column=0, padx=10, pady=10)

label_upper_sat = tk.Label(middle_frame, text="Upper Saturation", justify="center")
label_upper_sat.grid(row=4, column=1, padx=10, pady=10)

label_upper_val = tk.Label(middle_frame, text="Upper Value",  justify="center")
label_upper_val.grid(row=4, column=2, padx=10, pady=10)


bgr_upper_hue_entry = tk.Entry(middle_frame, width=15, font=("Arial", 12))
bgr_upper_hue_entry.insert(0, str(BGR_UPPER_HUE))
bgr_upper_hue_entry.grid(row=5, column=0, padx=10, pady=10)

bgr_upper_sat_entry = tk.Entry(middle_frame, width=15, font=("Arial", 12))
bgr_upper_sat_entry.insert(0, str(BGR_UPPER_SAT))
bgr_upper_sat_entry.grid(row=5, column=1, padx=10, pady=10)

bgr_upper_val_entry = tk.Entry(middle_frame, width=15, font=("Arial", 12))
bgr_upper_val_entry.insert(0, str(BGR_UPPER_VAL))
bgr_upper_val_entry.grid(row=5, column=2, padx=10, pady=10)


label_color = tk.Label(middle_frame, text="Result Image Overlay Color", justify="center", font=("Arial", 14, "bold"))
label_color.grid(row=6, column=0, padx=10, pady=10, columnspan=3)


label_color_red = tk.Label(middle_frame, text="Red", justify="center")
label_color_red.grid(row=7, column=0, padx=10, pady=10)

label_color_green = tk.Label(middle_frame, text="Green", justify="center")
label_color_green.grid(row=7, column=1, padx=10, pady=10)

label_color_blue = tk.Label(middle_frame, text="Blue",  justify="center")
label_color_blue.grid(row=7, column=2, padx=10, pady=10)


color_red_entry = tk.Entry(middle_frame, width=15, font=("Arial", 12))
color_red_entry.insert(0, str(COLOR_RED))
color_red_entry.grid(row=8, column=0, padx=10, pady=10)

color_green_entry = tk.Entry(middle_frame, width=15, font=("Arial", 12))
color_green_entry.insert(0, str(COLOR_GREEN))
color_green_entry.grid(row=8, column=1, padx=10, pady=10)

color_blue_entry = tk.Entry(middle_frame, width=15, font=("Arial", 12))
color_blue_entry.insert(0, str(COLOR_BLUE))
color_blue_entry.grid(row=8, column=2, padx=10, pady=10)


empty_label.grid(row=9, column=0, padx=10, pady=10)


middle_frame.grid(row=1, column=0)
#################################################################################
# TKINTER GUI CALCULATE BUTTON

button_input_folder = tk.Button(root, text="Calculate Area", command=on_button_press_calculate_area, width=22, height=2)
button_input_folder.grid(row=2, column=0, padx=10, pady=10)

# GUI MAINLOOP
update_input_folder_label()
update_output_folder_label()
root.mainloop()
