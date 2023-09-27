import tkinter as tk
from tkinter import ttk
from tkinter import Canvas, Frame, Label, Scrollbar, Button
import zipfile, cv2, os, time, re
from PIL import Image, ImageTk
from threading import Thread
from collections import deque
from difflib import ndiff

zippath="/home/sujit/Desktop/omniverse gymn frozen envs"

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Zip Content Viewer")

        # Create a parent frame to hold both the canvas and the non-scrolling section
        parent_frame = tk.Frame(self.root)
        parent_frame.pack(fill="both", expand=True)

        # Initialize Canvas
        self.canvas = tk.Canvas(parent_frame)
        self.canvas.grid(row=0, column=0, sticky='nswe')

        # Initialize Scrollbar and position it beside the canvas
        self.scrollbar = tk.Scrollbar(parent_frame, orient="vertical", command=self.canvas.yview)
        self.scrollbar.grid(row=0, column=1, sticky='ns')
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Non-scrolling section to the right
        non_scrolling_frame = tk.Frame(parent_frame, bg='gray')  # using gray bg to distinguish it
        non_scrolling_frame.grid(row=0, column=2, sticky='nw')

        combobox_frame = tk.Frame(non_scrolling_frame)
        combobox_frame.pack(pady=10)

        # Add the original combobox to the combobox_frame
        self.combobox = ttk.Combobox(combobox_frame, state="readonly")
        self.combobox.grid(row=0, column=0)  # Changed from pack to grid
        self.combobox.bind("<<ComboboxSelected>>", self.show_file_content)

        # Add some spacing between the two comboboxes
        self.textinfo = tk.Label(combobox_frame, text="from...Compared to ")
        self.textinfo.grid(row=0, column=1)
        # Add the combobox for baseline files next to the original combobox
        self.baseline_combobox = ttk.Combobox(combobox_frame, state="readonly")
        self.baseline_combobox.grid(row=0, column=2)  # New combobox in the next column

        # After initializing the combobox
        self.text_container = tk.Text(non_scrolling_frame, width=120)  # Assuming a character height of roughly 20 pixels; adjust if necessary
        self.text_container.pack(pady=10, padx=10, expand=True, fill="both")

        # Add vertical scrollbar to the text widget
        self.v_scroll = tk.Scrollbar(self.text_container, orient=tk.VERTICAL)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Add horizontal scrollbar to the text widget
        self.h_scroll = tk.Scrollbar(self.text_container, orient=tk.HORIZONTAL)
        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        # Create the Text widget with the scrollbars and no wrapping
        self.content_text = tk.Text(self.text_container, width=95, height=100,
                                    yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set, wrap=tk.NONE)
        self.content_text.pack(expand=True, fill="both")

        # Configure the scrollbars to control the Text widget
        self.v_scroll.config(command=self.content_text.yview)
        self.h_scroll.config(command=self.content_text.xview)

        # Allow the canvas to expand with the window
        parent_frame.grid_columnconfigure(0, weight=1)
        parent_frame.grid_rowconfigure(0, weight=1)

        # Frame inside Canvas
        self.zip_frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.zip_frame, anchor="nw")
        self.zip_frame.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Load zips and display
        self.load_zips(zippath)

        self.thumbnails = []
        self.currently_selected_btn = None
        self.bind_scroll_recursively(self.zip_frame, self.on_mousewheel)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-4>", self.on_mousewheel)
        self.canvas.bind("<Button-5>", self.on_mousewheel)

        self.content_text.tag_configure("addition", foreground="green")
        self.content_text.tag_configure("deletion", foreground="red", overstrike=True)
        self.content_text.tag_configure("common", foreground="black")

    def show_file_content(self, event, matched=0):
        selected_file = self.combobox.get()

        if matched==1:
            current_yview = self.content_text.yview()
        else:
            current_yview = None

        if any(selected_file.endswith(ext) for ext in ['.py', '.yaml', '.txt']):
            # Extract the selected file's content
            with zipfile.ZipFile(self.currently_selected_btn.zip_filepath, 'r') as zip_ref:
                with zip_ref.open(selected_file) as file:
                    content = file.read().decode('utf-8')
                    self.content_text.delete("1.0", tk.END)  # Clear the existing content
                    self.content_text.insert(tk.END, content)
        else:
            self.content_text.delete("1.0", tk.END)  # Clear the textbox if a non-supported file is selected

        baseline_zip_file = self.baseline_combobox.get()
        baseline_content = ""  # Initialize baseline_content variable
        if baseline_zip_file != "None":
            baseline_zip_filepath = os.path.join(zippath, baseline_zip_file + ".zip")
            with zipfile.ZipFile(baseline_zip_filepath, 'r') as zip_ref:
                with zip_ref.open(selected_file) as file:
                    baseline_content = file.read().decode('utf-8')

        if baseline_content:
            self.display_differences(baseline_content, content)

        if current_yview:
            self.content_text.yview_moveto(current_yview[0])

    def display_differences(self, baseline_content, content):
        # Tokenize the entire content
        def tokenize(text):
            return re.findall(r'[\w._]+|\s+|[^\w\s]|\n', text)  # Including underscores as part of words

        baseline_tokens = tokenize(baseline_content)
        content_tokens = tokenize(content)

        diff = list(ndiff(baseline_tokens, content_tokens))
        styled_tokens = deque()

        i = 0
        while i < len(diff):
            line = diff[i]
            if line.startswith(" "):
                styled_tokens.append((line[2:], "common"))
            elif line.startswith("+"):
                # Check for deletion immediately after the current addition
                if i + 1 < len(diff) and diff[i + 1].startswith("-"):
                    del_token = diff[i + 1][2:]
                    # Check if the deletion token ends with a newline and remove it
                    if del_token.endswith("\n"):
                        del_token = del_token[:-1]
                    styled_tokens.append((del_token, "deletion"))
                    styled_tokens.append((line[2:], "addition"))
                    i += 1  # Increase by 1, as the next iteration will handle the "-"
                else:
                    styled_tokens.append((line[2:], "addition"))
            elif line.startswith("-"):
                del_token = line[2:]
                # Check if the deletion token ends with a newline and remove it
                if del_token.endswith("\n"):
                    del_token = del_token[:-1]
                styled_tokens.append((del_token, "deletion"))
            i += 1

        self.content_text.delete("1.0", tk.END)  # Clear existing content

        index = "1.0"
        for token, style in styled_tokens:
            # Check if the token is a newline character or a space
            if token in ["\n", " "] or token.startswith(" "):
                self.content_text.insert(index, token, (style,))
            else:
                if style == "common":
                    self.content_text.insert(index, token, ("common",))
                elif style == "addition":
                    self.content_text.insert(index, token, ("addition",))
                elif style == "deletion":
                    self.content_text.insert(index, token, ("deletion",))
            index = self.content_text.index("end - 1 chars")  # Update index

    def bind_scroll_recursively(self, widget, callback):
        """Recursively bind the mouse scroll event to a widget and its descendants."""
        widget.bind("<MouseWheel>", callback)
        widget.bind("<Button-4>", callback)
        widget.bind("<Button-5>", callback)
        for child in widget.winfo_children():
            self.bind_scroll_recursively(child, callback)

    def on_root_resize(self, event=None):
        # Width of first column
        video_column_width = 500  # As defined in your code for the placeholder

        # Calculate width of the Text widget based on average character width and number of characters
        font = tk.font.Font()  # Default font for the Text widget
        average_char_width = font.measure('0')  # Measure width of character '0' which is fairly average in width
        textbox_width = 100 * average_char_width  # 80 characters wide

        combobox_x_position = video_column_width + textbox_width

        self.combobox.place(x=combobox_x_position, y=0, anchor="ne")

    def button_selected(self, button, zip_filepath):
        # Capture the previously selected filename
        previous_selected_filename = self.combobox.get()

        # Deselect the current button if it's selected
        if self.currently_selected_btn:
            self.currently_selected_btn.config(relief=tk.RAISED, state=tk.NORMAL,
                                               bg=self.currently_selected_btn.default_bg, activebackground="#ffd494")
        # Select the new button
        button.config(relief=tk.RAISED, state=tk.NORMAL, background="#ffd494", activebackground="#ffd494")
        self.currently_selected_btn = button

        # Populate the combobox with the filenames from the zip
        with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
            file_names = zip_ref.namelist()
        self.combobox['values'] = file_names

        # After setting the 'values' of combobox, check if the previous_selected_filename exists in the new zip and set it.
        if previous_selected_filename in file_names:
            current_yview = self.content_text.yview()
            self.combobox.set(previous_selected_filename)
            self.show_file_content(None, matched=1)  # Display the content of the selected file.
        else:
            self.combobox.set("Select a file")

        self.textinfo.config(text="from "+os.path.basename(zip_filepath)[:-4] +" compared to ")

    def on_mousewheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def load_zips(self, directory_path):
        # Extract dates and corresponding zip filepaths
        zip_dates_and_files = []

        for zip_file in os.listdir(directory_path):
            if zip_file.endswith(".zip"):
                zip_filepath = os.path.join(directory_path, zip_file)
                with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
                    biped_name = next((name for name in zip_ref.namelist() if 'biped.py' in name), None)
                    if biped_name:
                        biped_info = zip_ref.getinfo(biped_name)
                        date_time = "{:04}-{:02}-{:02} {:02}:{:02}".format(*biped_info.date_time)
                        zip_dates_and_files.append((date_time, zip_filepath))

        # Sort by date
        zip_dates_and_files.sort(key=lambda x: x[0], reverse=True)
        self.baseline_combobox['values'] = [""] +[os.path.basename(file_path)[:-4] for _, file_path in zip_dates_and_files]
        # Add to canvas
        for _, zip_filepath in zip_dates_and_files:
            self.add_zip_to_canvas(zip_filepath)

    def add_zip_to_canvas(self, zip_filepath):
        with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
            biped_name = next((name for name in zip_ref.namelist() if 'biped.py' in name), None)
            if biped_name:
                biped_info = zip_ref.getinfo(biped_name)
                formatted_time = "{:04}-{:02}-{:02} {:02}:{:02}".format(*biped_info.date_time)
            else:
                formatted_time = "N/A"

            video_name = next(
                (name for name in zip_ref.namelist() if '_nofreeze' in name and (('.mkv' in name) or ('.mp4' in name))),
                None)
            if not video_name:
                video_name = next((name for name in zip_ref.namelist() if '.mkv' in name or '.mp4' in name), None)
            description_name = next((name for name in zip_ref.namelist() if 'description.txt' in name), None)

            frame = Frame(self.zip_frame)
            frame.pack(fill=tk.X)

            if video_name:
                zip_ref.extract(video_name, '/tmp')
                video_label = Label(frame)
                video_label.pack(side=tk.LEFT, padx=5)
                Thread(target=self.play_decimated_video, args=(video_label, '/tmp/' + video_name)).start()
            else:
                placeholder = tk.Canvas(frame, width=500, height=300, bg='black')
                placeholder.pack(side=tk.LEFT, padx=5)
                placeholder.create_rectangle(0, 0, 500, 300, fill='black')

            desc_frame = Frame(frame)
            desc_frame.pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)

            filename_without_zip = os.path.basename(zip_filepath)[:-4]


            # Create a Button widget for the date and name
            date_and_name_button = tk.Button(desc_frame, text=f"{formatted_time} | {filename_without_zip}", anchor='w',
                                             relief=tk.RAISED, activebackground="#ffd494")
            date_and_name_button.pack(fill=tk.X, padx=5, pady=5)
            date_and_name_button.default_bg = date_and_name_button.cget("background")
            date_and_name_button.zip_filepath = zip_filepath

            # Updated binding for the button
            date_and_name_button.config(command=lambda btn=date_and_name_button, zf=zip_filepath: self.button_selected(btn, zf))

            description_text = tk.Text(desc_frame, width=60, wrap=tk.WORD, height=5)
            description_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            # Save button, using place() for positioning
            def save_and_update_content():
                self.save_description(zip_filepath, description_text.get("1.0", 'end-1c'))
                description_text._initial_content = description_text.get("1.0", 'end-1c')
                save_button.place_forget()

            save_button = tk.Button(desc_frame, text="Save", command=save_and_update_content)
            save_button.place(relx=1.0, rely=1.0, x=-10, y=-10,
                              anchor="se")  # Positioning at bottom-right of the parent frame
            save_button.place_forget()  # Initially hidden

            # Set the initial content and save it in an instance variable
            initial_content = ""
            if description_name:
                zip_ref.extract(description_name, '/tmp')
                with open('/tmp/' + description_name, 'r') as desc_file:
                    initial_content = desc_file.read()
            description_text.insert(tk.END, initial_content)

            # Set instance variable for initial content
            description_text._initial_content = initial_content

            # Handle visibility of save button based on text changes
            def on_text_change(event=None):
                if description_text.get("1.0", 'end-1c') != description_text._initial_content:
                    save_button.place(relx=1.0, rely=1.0, x=-10, y=-10, anchor="se")  # Show button
                else:
                    save_button.place_forget()  # Hide button

            description_text.bind('<KeyRelease>', on_text_change)

    def save_description(self, zip_filepath, new_description):
        # Rename the original zip file
        renamed_zip = zip_filepath + ".old"
        os.rename(zip_filepath, renamed_zip)

        with zipfile.ZipFile(renamed_zip, 'r') as old_zip, zipfile.ZipFile(zip_filepath, 'w') as new_zip:
            # Copy items from old zip to the new one, excluding description.txt
            for item in old_zip.infolist():
                if item.filename != 'description.txt':
                    new_zip.writestr(item, old_zip.read(item.filename))

            # Add the updated description.txt
            new_zip.writestr('description.txt', new_description)

        # Delete the renamed (old) zip file
        os.remove(renamed_zip)

    def play_decimated_video(self, label, video_path):
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        sleep_time = 3 / fps

        # Store the resized and decimated frames
        frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if int(cap.get(cv2.CAP_PROP_POS_FRAMES)) % 3 == 0:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                img = img.resize((500, 300))
                thumbnail = ImageTk.PhotoImage(image=img)
                frames.append(thumbnail)
        cap.release()
        # Set the first frame as the thumbnail if there are frames
        if frames:
            label.config(image=frames[0])
        # Set the paused attribute for the label
        label.paused = True

        def toggle_play_pause(event):
            label.paused = not label.paused

        label.bind("<Button-1>", toggle_play_pause)  # Bind left-click to the toggle function

        # Now, play the frames from the list
        frame_index = 0
        while True:
            if label.paused:
                time.sleep(0.1)  # Sleep for a short duration and then check again
                continue
            if frame_index >= len(frames):
                frame_index = 0  # Reset index to loop the frames
            label.config(image=frames[frame_index])
            time.sleep(sleep_time)
            frame_index += 1

if __name__ == "__main__":
    root = tk.Tk()
    root.attributes('-zoomed', True)
    app = App(root)
    root.mainloop()
