import logging
import threading
from tkinter import *
from tkinter import filedialog
from tkinter.ttk import Progressbar

from deezload.base import LoadStatus, Loader
from deezload.settings import HOME_DIR
from deezload.utils import setup_logging


logger = logging.getLogger(__name__)


class Application(Frame):
    def __init__(self, master=None, *args, **kwargs):
        """
        urls - text
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

        self.url = StringVar()
        self.output_dir = StringVar(value=HOME_DIR)
        self.format = StringVar()
        self.index = StringVar(value='0')
        self.limit = StringVar(value='50')
        self.use_tree = StringVar(value='1')
        self.logs_var = StringVar(value='foo')
        self.should_stop = False

        self.download_btn: Button = None
        self.stop_btn: Button = None
        self.info_label: Label = None
        self.error_label: Label = None
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
        label = Label(frame, text='Deezer URL of playlist, artist, album or user profile',
                      font='Helvetica 14 bold')
        label.grid(row=0, column=0, sticky='w')

        list_id_entry = Entry(frame, textvariable=self.url, width=50)
        list_id_entry.focus_set()
        list_id_entry.grid(row=1, column=0, sticky='ew', columnspan=5)

    def set_output_dir_frame(self, frame: Frame):
        label = Label(frame, text='Output dir', font='Helvetica 14 bold')
        label.grid(row=0, column=0, sticky='w')

        output_dir = Entry(frame, textvariable=self.output_dir, width=50)
        output_dir.grid(row=1, column=0, sticky='ew', columnspan=5)

        output_dir_btn = Button(frame, text="pick directory", command=self.browse_button)
        output_dir_btn.grid(row=2, column=0, sticky='ew', columnspan=5)

    def set_misc_frame(self, frame: Frame):
        def validate_int(value: str, acttyp: str):
            if acttyp == '1':  # insert
                try:
                    int(value)
                    return True
                except ValueError:
                    return False
            return True

        index_label = Label(frame, text='Start index')
        index_label.grid(row=0, column=0, sticky='w')

        index_entry = Entry(frame, textvariable=self.index, validate="key")
        index_entry['validatecommand'] = (index_entry.register(validate_int), '%P', '%d')
        index_entry.grid(row=0, column=1, sticky='w')

        limit_label = Label(frame, text='Load limit')
        limit_label.grid(row=1, column=0, sticky='w')

        limit_entry = Entry(frame, textvariable=self.limit, validate="key")
        limit_entry['validatecommand'] = (limit_entry.register(validate_int), '%P', '%d')
        limit_entry.grid(row=1, column=1, sticky='w')

        format_label = Label(frame, text='Audio format')
        format_label.grid(row=2, column=0, sticky='w')

        format_options = ('mp3', 'flac')
        self.format.set(format_options[0])
        format_menu = OptionMenu(frame, self.format, *format_options)
        format_menu.grid(row=2, column=1, sticky='w')

        tree_checkbox = Checkbutton(frame, text="save as tree (artist / album / song)",
                                    onvalue='1', offvalue='0',
                                    variable=self.use_tree)
        tree_checkbox.grid(row=3, column=0, sticky='w', columnspan=2)

    def set_download_frame(self, frame: Frame):
        self.download_btn = Button(frame, text='Download', width=24,
                                   command=self.download_click)
        self.download_btn.grid(row=0, sticky='ew')
        self.stop_btn = Button(frame, text='Stop', width=24,
                               command=self.stop_work, state=DISABLED)
        self.stop_btn.grid(row=0, column=1, sticky='ew')

        self.progress = Progressbar(frame, orient="horizontal", value=0,
                                    style="red.Horizontal.TProgressbar")
        self.progress.grid(row=1, sticky='ew', columnspan=2)

        self.info_label = Label(frame, font='Helvetica 14 bold')
        self.info_label.grid(row=2, sticky='ew', columnspan=2, pady=5)
        self.error_label = Label(frame, font='Helvetica 14 bold', fg='red')
        self.error_label.grid(row=3, sticky='ew', columnspan=2, pady=5)

    def browse_button(self):
        filename = filedialog.askdirectory()
        if filename:
            self.output_dir.set(filename)

    def download_click(self):
        self.download_btn.configure(state=DISABLED)
        self.stop_btn.configure(state=NORMAL)
        threading.Thread(target=self.download).start()

    def stop_work(self):
        self.should_stop = True
        self.show_error('waiting for one last song to load before stop...')
        self.stop_btn.configure(state=DISABLED)

    def show_msg(self, msg: str):
        self.info_label.config(text=msg)
        self.info_label.update()

    def show_error(self, msg: str):
        self.error_label.config(text=msg)
        self.error_label.update()

    def set_progress(self, val: int):
        self.progress['value'] = val
        self.progress.update()

    def download(self):
        try:
            self.show_msg('loading tracks...')
            loader = Loader(
                urls=self.url.get(),
                output_dir=self.output_dir.get(),
                index=int(self.index.get()),
                limit=int(self.limit.get()),
                format=self.format.get(),
                tree=self.use_tree.get() == '1',
            )
            self.set_progress(0)
            self.output_dir.set(loader.output_dir)
            self.update()
            loaded = 0
            skipped = 0
            existed = 0
            for status, track, i, prog in loader.load_gen():
                num = f'{i + 1}/{len(loader)}'
                if status == LoadStatus.STARTING:
                    self.show_msg(f"{num} - init")
                elif status == LoadStatus.SEARCHING:
                    self.show_msg(f"{num} - searching for video")
                elif status == LoadStatus.LOADING:
                    self.show_msg(f"{num} - loading video")
                elif status == LoadStatus.MOVING:
                    self.show_msg(f"{num} - moving file")
                elif status == LoadStatus.RESTORING_META:
                    self.show_msg(f"{num} - restoring audio meta data")

                elif status == LoadStatus.EXISTED:
                    existed += 1
                elif status == LoadStatus.SKIPPED:
                    skipped += 1
                elif status == LoadStatus.FINISHED:
                    loaded += 1
                    logger.debug('loaded track %s', track)

                self.set_progress(int((i + prog) / len(loader) * 100))

                if self.should_stop and status in LoadStatus.finite_states():
                    break

            self.set_progress(100)
            self.show_msg(f"DONE. loaded: {loaded}, skipped: {skipped}, existed: {existed}")
        except Exception as e:
            logger.exception(e)
            self.info_label.config(text=str(e), fg='red')
            self.info_label.update()
        finally:
            self.download_btn.configure(state=NORMAL)
            self.stop_btn.configure(state=DISABLED)
            self.should_stop = False
            self.show_error('')


def center(win, width=None, height=None):
    win.withdraw()
    win.update_idletasks()
    width = width or win.winfo_width()
    height = height or win.winfo_height()
    x = (win.winfo_screenwidth() // 3) - (width // 2)
    y = (win.winfo_screenheight() // 3) - (height // 2)
    win.geometry(f'+{x}+{y}')
    win.deiconify()


def raise_to_the_top(win):
    win.lift()
    win.attributes("-topmost", True)
    win.focus_force()
    win.after_idle(win.call, 'wm', 'attributes', '.', '-topmost', False)


def start_app():
    root = Tk()
    app = Application(master=root)

    root.title("deezer songs downloader")
    center(root)
    root.resizable(width=False, height=False)

    raise_to_the_top(root)
    root.after(1, lambda: root.focus_force())
    app.mainloop()


if __name__ == '__main__':
    setup_logging(debug=True)
    start_app()
