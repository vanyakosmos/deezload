import tkinter as tk
from tkinter import filedialog


class Application(tk.Frame):
    def __init__(self, master=None, *args, **kwargs):
        """
        list_id - text
        list_type - select
        output_dir - dir picker
        limit - num field
        format - select
        tree - checkbox
        debug - checkbox
        """
        super().__init__(master, *args, **kwargs)
        self.root = master
        self.pack()

        list_id = tk.Entry(master)
        list_id.pack()

        output_dir_btn = tk.Button(master, text="Output directory", command=self.browse_button)
        output_dir_btn.pack()
        output_dir_lbl = tk.Label(master)
        output_dir_lbl.pack()

        list_type_options = ('auto from url', 'playlist', 'album', 'track')
        list_type = tk.StringVar()
        list_type.set(list_type_options[0])
        list_type_menu = tk.OptionMenu(master, list_type, *list_type_options)
        list_type_menu.pack()

        limit = tk.Entry(master)
        limit.pack()

        format_options = ('mp3', 'flac', 'best')
        format = tk.StringVar()
        format.set(format_options[0])
        format_menu = tk.OptionMenu(master, format, *format_options)
        format_menu.pack()

        use_tree = tk.BooleanVar()
        tree_checkbox = tk.Checkbutton(master, text="tree", variable=use_tree)
        tree_checkbox.pack()

        debug = tk.BooleanVar()
        debug_checkbox = tk.Checkbutton(master, text="debug", variable=debug)
        debug_checkbox.pack()

        logs_entry = tk.Entry(master)
        logs_entry.configure(state="readonly")
        logs_entry.pack()

    def browse_button(self):
        filename = filedialog.askdirectory()
        print(filename)


def center(win, width=None, height=None):
    if not width or not height:
        win.update_idletasks()
    width = width or win.winfo_width()
    height = height or win.winfo_height()
    x = (win.winfo_screenwidth() // 2) - (width // 2)
    y = (win.winfo_screenheight() // 2) - (height // 2)
    win.geometry(f'{width}x{height}+{x}+{y}')


def raise_to_the_top(win):
    win.lift()
    win.call('wm', 'attributes', '.', '-topmost', True)
    win.after_idle(win.call, 'wm', 'attributes', '.', '-topmost', False)


def get_size():
    # todo
    return 600, 400


def main():
    root = tk.Tk()
    app = Application(master=root)

    root.title("deezer playlist downloader")
    width, height = get_size()
    # root.maxsize(width, height)
    root.minsize(width, height)
    center(root, width, height)

    raise_to_the_top(root)
    app.mainloop()


if __name__ == '__main__':
    main()
