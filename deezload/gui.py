import logging
import os
import threading
from pathlib import Path
from tkinter import *
from tkinter import filedialog
from tkinter.ttk import Progressbar

from deezload.base import LoadStatus, Loader, setup_logging


logger = logging.getLogger(__name__)


class Application(Frame):
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
        self.grid(padx=20, pady=20)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.list_id = StringVar()
        self.list_type = StringVar()
        self.output_dir = StringVar(value=os.path.join(str(Path.home()), 'deezload'))
        self.format = StringVar()
        self.index = StringVar(value='0')
        self.limit = StringVar(value='50')
        self.use_tree = StringVar(value='0')
        self.logs_var = StringVar(value='foo')

        self.download_btn: Button = None
        self.info_label: Label = None
        self.progress: Progressbar = None

        list_params_frame = Frame(self, width=400)
        output_dir_frame = Frame(self, width=400)
        misc_frame = Frame(self, width=400)
        download_frame = Frame(self, width=400)

        self.set_list_params_frame(list_params_frame)
        self.set_output_dir_frame(output_dir_frame)
        self.set_misc_frame(misc_frame)
        self.set_download_frame(download_frame)

        list_params_frame.grid(row=0, pady=(0, 20), sticky='ew')
        output_dir_frame.grid(row=1, pady=(0, 20), sticky='ew')
        misc_frame.grid(row=2, pady=(0, 20), sticky='ew')
        download_frame.grid(row=3, sticky='ew')

    def set_list_params_frame(self, frame: Frame):
        label = LabelFrame(frame, text='List id or URL', borderwidth=0)
        label.grid(row=0, column=0, sticky='w', columnspan=10)

        list_id_entry = Entry(label, textvariable=self.list_id, width=50)
        list_id_entry.focus_set()
        list_id_entry.pack()

        label = Label(frame, text='List type')
        label.grid(row=1, column=0, sticky='w')

        list_type_options = ('from url', 'playlist', 'album', 'profile')
        self.list_type.set(list_type_options[0])
        list_type_menu = OptionMenu(frame, self.list_type, *list_type_options)
        list_type_menu.grid(row=1, column=1, sticky='w')

    def set_output_dir_frame(self, frame: Frame):
        label = LabelFrame(frame, text='Output dir', borderwidth=0)
        label.grid(row=0, column=0, sticky='w')

        output_dir = Entry(label, textvariable=self.output_dir, width=44)
        output_dir.pack(side=LEFT, fill=X)

        output_dir_btn = Button(label, text="pick", command=self.browse_button)
        output_dir_btn.pack(side=LEFT)

    def set_misc_frame(self, frame: Frame):
        def validate_int(value: str, acttyp: str):
            if acttyp == '1':  # insert
                try:
                    int(value)
                    return True
                except ValueError:
                    return False
            return True

        limit_label = Label(frame, text='Load limit')
        limit_label.grid(row=0, column=0, sticky='w')

        limit_entry = Entry(frame, textvariable=self.limit, validate="key")
        limit_entry['validatecommand'] = (limit_entry.register(validate_int), '%P', '%d')
        limit_entry.grid(row=0, column=1, sticky='w')

        index_label = Label(frame, text='Start index')
        index_label.grid(row=1, column=0, sticky='w')

        index_entry = Entry(frame, textvariable=self.index, validate="key")
        index_entry['validatecommand'] = (limit_entry.register(validate_int), '%P', '%d')
        index_entry.grid(row=1, column=1, sticky='w')

        format_label = Label(frame, text='Audio format')
        format_label.grid(row=2, column=0, sticky='w')

        format_options = ('mp3', 'flac', 'best')
        self.format.set(format_options[0])
        format_menu = OptionMenu(frame, self.format, *format_options)
        format_menu.grid(row=2, column=1, sticky='w')

        tree_checkbox = Checkbutton(frame, text="save as tree (artist / album / song)",
                                    onvalue='1', offvalue='0',
                                    variable=self.use_tree)
        tree_checkbox.grid(row=3, column=0, sticky='w', columnspan=2)

    def set_download_frame(self, frame: Frame):
        self.download_btn = Button(frame, text='Download', width=48,
                                   command=self.download_click)
        self.download_btn.grid(row=0, sticky='ew')

        self.info_label = Label(frame, font='Helvetica 14 bold')
        self.info_label.grid(row=1, sticky='ew', pady=5)

        self.progress = Progressbar(frame, orient="horizontal", value=0,
                                    style="red.Horizontal.TProgressbar")
        self.progress.grid(row=2, sticky='ew')

    def browse_button(self):
        filename = filedialog.askdirectory()
        if filename:
            self.output_dir.set(filename)

    def download_click(self):
        threading.Thread(target=self.download).start()

    def show_msg(self, msg: str):
        self.info_label.config(text=msg, fg='black')
        self.info_label.update()

    def show_error(self, msg: str):
        self.info_label.config(text=msg, fg='red')
        self.info_label.update()

    def set_progress(self, val: int):
        self.progress['value'] = val
        self.progress.update()

    def download(self):
        self.download_btn.configure(state=DISABLED)
        try:
            self.show_msg('starting...')
            loader = Loader(
                list_id=self.list_id.get(),
                list_type=self.list_type.get(),
                output_dir=self.output_dir.get(),
                index=int(self.index.get()),
                limit=int(self.limit.get()),
                format=self.format.get(),
                tree=self.use_tree.get() == '1',
            )
            self.set_progress(0)
            self.output_dir.set(loader.output_dir)
            self.update()
            skipped = 0
            existed = 0
            for status, track, i, prog in loader.load_gen():
                # percent = int((i + 1) / len(loader) * 100)
                num = f'{i + 1}/{len(loader)}'
                if status == LoadStatus.STARTING:
                    self.show_msg(f"{num} - starting...")
                elif status == LoadStatus.SEARCHING:
                    self.show_msg(f"{num} - searching...")
                elif status == LoadStatus.LOADING:
                    self.show_msg(f"{num} - loading...")
                elif status == LoadStatus.MOVING:
                    self.show_msg(f"{num} - moving...")
                elif status == LoadStatus.RESTORING_META:
                    self.show_msg(f"{num} - restoring meta data...")

                elif status == LoadStatus.EXISTED:
                    existed += 1
                elif status == LoadStatus.SKIPPED:
                    skipped += 1
                elif status == LoadStatus.FINISHED:
                    logger.debug('loaded track %s', track)

                self.set_progress(int((i + prog) / len(loader) * 100))

            self.set_progress(100)
            loaded = len(loader) - skipped - existed
            self.show_msg(f"DONE. loaded: {loaded}, skipped: {skipped}, existed: {existed}")
        except Exception as e:
            logger.exception(e)
            self.info_label.config(text=str(e), fg='red')
            self.info_label.update()
        finally:
            self.download_btn.configure(state=NORMAL)


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


def start_app():
    root = Tk()
    app = Application(master=root)

    root.title("deezer songs downloader")
    center(root)
    root.resizable(width=False, height=False)

    raise_to_the_top(root)
    app.mainloop()


if __name__ == '__main__':
    setup_logging(debug=True)
    start_app()
