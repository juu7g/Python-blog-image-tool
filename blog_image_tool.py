"""
はてなブログ向け画像ツール
"""

from ntpath import join
import os, sys
import tkinter as tk
from tkinter import messagebox
from tkinter.tix import Tree
import tkinter.ttk as ttk
import tkinter.font as tkFont
from tkinter import filedialog
from turtle import width
from tkinterdnd2 import *
from typing import Tuple                # 関数アノテーション用 
from PIL import Image, ImageTk          # Pillow
from PIL.ExifTags import TAGS, GPSTAGS  # Exifタグ情報
from tkinter_libs import TkinterLib
from tkinter_libs import ScrolledFrame
import image_resize_sig
import fotolifeUpload
from toml_file_util import TomlFileUtil
import pyperclip
import re
import threading

class ListView(ttk.Frame):
    """
    画像をリストビューで表示する
    """
    def __init__(self, master):
        """
        画面の作成
        上のFrame：入力用
        下のFrame：出力用
        右のフレーム：設定用
        """
        super().__init__(master)
        self.frame_children = {}
        self.images4display = set()
        self.tab1_name = "読み込み画像"
        self.thumbnail_xy = 250
        self.image_op = ImageOp()
        self.u_frame = tk.Frame(master, bg="white")     # 背景色を付けて配置を見る
        self.b_frame = tk.Frame(master, bg="green")     # 背景色を付けて配置を見る
        self.r_frame = ScrolledFrame(master, width=50, bg="lightblue")  # 背景色を付けるとセクションの境に色が出る
        self.r_frame.parent_frame.pack(side="right", fill="y")
        self.u_frame.pack(fill=tk.X)
        self.b_frame.pack(fill=tk.BOTH, expand=True)
        # 設定用フレーム内の作成 設定値をself.var_dictに設定
        self.create_config_frame(self.r_frame)
        # geometry
        geometry_ = self.var_dict.get("geometry").get()
        is_match = re.match("\d+x\d+\+\d+\+\d+", geometry_)
        if is_match:
            master.geometry(self.var_dict.get("geometry").get())
        # 入力用フレーム内の作成
        self.create_input_frame(self.u_frame)
        # タブの作成
        self.note = ttk.Notebook(self.b_frame)
        self.note.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # 新しいタブの追加
        self.frame4images = self.create_frame4images(self.note, tab_name=self.tab1_name)
        # 画像編集モジュールのインスタンス作成(リサイズ用)
        self.image_ui = image_resize_sig.ImageUI()
        # アップロードモジュールのインスタンス作成
        self.upload_ui = fotolifeUpload.HatenaFotolifeUI()

    def create_frame4images(self, parent:ttk.Notebook, tab_name:str) -> ScrolledFrame:
        """
        画像用ScrolledFrameを作成し、parentにタブを追加
        Args:
            Any:    親ウィジェット(Notebook)
            str:    タブ名
        """
        scrolled_frame = ScrolledFrame(parent)
        
        # チェックされた画像用セットを初期化
        scrolled_frame.parent_frame.checked_image_paths = set()

        # bind
        scrolled_frame.bind_class("Checkbutton", "<Double 3>", self.preview_image)  # マウスを右ダブルクリックしたときの動作
        # wrapped_gridのbind
        self.frame_children[tab_name] = []
        scrolled_frame.parent_canvas.bind("<Configure>", lambda event: TkinterLib.wrapped_grid(
            scrolled_frame.parent_canvas, *self.frame_children.get(tab_name), event=event, flex=False), add=True)
        self.note.add(scrolled_frame.parent_frame, text=tab_name)   # タブを追加
        return scrolled_frame
    
    def create_config_frame(self, parent):
        """
        設定項目用画面の作成
        self.var_dict(設定項目の辞書)の作成

        Args:
            ScrolledFrame:  親ウィジェット
        """
        # pyinstallerで作成したexeか判断してexeの場所を特定する
        if getattr(sys, 'frozen', False):
            exe_path = os.path.dirname(sys.executable)
        else:
            exe_path = sys.prefix
        my_path = os.path.join(exe_path, r"blog_image_tool.toml")
        toml = TomlFileUtil()
        result = toml.read_toml(my_path)
        if not result:
            self.master.withdraw()  # トップレベルウィンドウを出さない
            messagebox.showerror("使用上のエラー", f"{my_path}\nファイルが見つかりません")
            sys.exit()
        self.var_dict = toml.create_frame_from_toml_dict(parent, True)
        toml.btn_save.config(command=lambda path=my_path: toml.save_toml(path, "USER"))
        parent.update()
        if parent.parent_canvas.winfo_width() > parent.winfo_width():
            parent.parent_canvas.config(width=parent.winfo_width())
        toml.set_toml2var_dict("USER")

    def create_input_frame(self, parent):
        """
        入力項目の画面の作成
        上段：ファイル選択ボタン、すべて選択、選択解除、プレビューボタン
        下段：メッセージ
        """
        self.btn_resize = tk.Button(parent, text="画像変換", command=self.convert_images)
        self.btn_upload = tk.Button(parent, text="アップロード", command=self.upload_images)
        self.btn_break = ttk.Button(parent, text="中断", command=self.break_upload, width=4, state=tk.DISABLED)
        self.btn_copy = tk.Button(parent, text="URLコピー", command=self.copy_image_url)
        self.btn_f_sel = tk.Button(parent, text="ファイル選択", command=self.select_files)
        self.btn_select_all = tk.Button(parent, text="すべて選択", command=self.select_all)
        self.btn_deselection = tk.Button(parent, text="選択解除", command=self.deselection)
        self.btn_preview = tk.Button(parent, text="プレビュー", command=self.preview_images)
        self.msg = tk.StringVar(value="msg")
        self.lbl_msg = tk.Label(parent
                                , textvariable=self.msg
                                , justify=tk.LEFT
                                # , font=("Fixedsys", 11)   # 日本語フォントが意図しないフォントになる
                                , font=("ゴシック", 11)
                                , relief=tk.RIDGE
                                , anchor=tk.W)
        # pack
        self.lbl_msg.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)    # 先にpackしないと下に配置されない
        self.btn_preview.pack(side=tk.RIGHT, padx=5)
        self.btn_deselection.pack(side=tk.RIGHT, padx=5)
        self.btn_select_all.pack(side=tk.RIGHT, padx=5)
        self.btn_f_sel.pack(side=tk.LEFT, padx=5)
        self.btn_resize.pack(side=tk.LEFT, padx=5)
        self.btn_upload.pack(side=tk.LEFT, padx=5)
        self.btn_break.pack(side=tk.LEFT, padx=5)
        self.btn_copy.pack(side=tk.LEFT, padx=5)

    def on_Check(self, event=None, var_check=None, obj_check=None):
        """
        チェックボックスがクリックされたらチェックされているリストの内容を更新する
        Args:
            bool:      チェック状態
            Any:       チェック対象の画像のパス
        """
        w = self.note.nametowidget(self.note.select())  # get current tab widget
        if var_check.get():
            w.checked_image_paths.add(obj_check)
        else:
            w.checked_image_paths.discard(obj_check)

    def set_images2frame(self, parent:ScrolledFrame, rows:list, images:list, tab_name:str):
        """
        parent(Frame)にimagesの要素分Frameを作成しgrid
        Frameはself.frame_childrenにappendして画像が残るようにする
        Frameには画像用Checkbuttonと情報用Labelを追加
        Args:
            Frame:      親ScrolledFrame
            list:       行データ(行リストの列リスト)
                        列：ファイル名、幅、高さ、ファイルサイズ、exif情報、gps情報
            list:       画像データ
            str:        タブ名
        """
        if not rows:    # 要素が無ければ戻る
            return

        # チェックされた画像用セットを初期化
        parent.parent_frame.checked_image_paths = set()

        # 要素の削除
        for w in parent.winfo_children():
            w.destroy()

        # 要素の追加
        self.frame_children[tab_name] = []
        for row, image in zip(rows, images):
            # 要素の追加(Frameに画像用Checkbuttonと情報用Label)
            frame1 = tk.Frame(parent, relief=tk.GROOVE, borderwidth=2)
            if row[4]:
                exif = " | Exifあり"
            else:
                exif = ""
            # ファイル名、Exif情報のあり/なしを表示するラベルの作成。文字はサムネイルの幅+10pxで折り返し
            # row[0]ファイル名、row[1]幅、row[2]高さ
            disp_text = f"{os.path.basename(row[0])}\n{row[1]} x {row[2]}{exif}" 
            label_f_name = tk.Label(frame1, text=disp_text, wraplength=self.thumbnail_xy + 10)
            boolen_var = tk.BooleanVar(False)
            # チェックボックスの作成(imageに画像、textに画像パス(ダブルクリックプレビューで使用))
            check_box = tk.Checkbutton(frame1, image=image, width=self.thumbnail_xy + 10, text=row[0], compound=tk.NONE, variable=boolen_var, indicatoron=False)
            check_box.config(command = lambda x=boolen_var, path=row[0]: self.on_Check(var_check=x, obj_check=path))
            # pack
            label_f_name.pack(side=tk.BOTTOM)
            check_box.pack()
            self.frame_children[tab_name].append(frame1)
            frame1.grid(row=0, column=0)    # 一度仮にgridして個々のサイズが確定できるようにする


        # 親Frameの幅に合わせてgridする
        if self.frame_children[tab_name]:
            TkinterLib.wrapped_grid(parent.parent_canvas
                                , *self.frame_children.get(tab_name), flex=False, force=True)
        
        # 画像の数が少なくなるとcanvasが大きいままなのでスクロール位置を戻す
        parent.parent_canvas.yview_moveto(0.0)

    def open_files_get_images_set2frame(self, event=None, parent=None, file_paths_:tuple=None, tab_name:str=None):
        """
        file_paths_のパスからファイル情報、画像サムネイルを作成
        parent(ScrolledFrame)に画像を含んだFrameを追加
        Args:
            Frame:      画像Frameの追加先Frame
            tuple:       画像のパスのタプル(eventがある場合はeventから)
            str:        タブ名
        """
        self.image_op.msg = ""
        if not tab_name: tab_name = self.tab1_name
        # DnD対応
        if event:
            # DnDのファイル情報はevent.dataで取得
            # "{空白を含むパス名1} 空白を含まないパス名1"が返る
            # widget.tk.splitlistでパス名のタプルに変換
            file_paths_ = self.u_frame.tk.splitlist(event.data)
            
        # 取得したパスから拡張子がself.extentiosのkeyに含まれるものだけにする
        file_paths2 = tuple(path for path in file_paths_ if os.path.splitext(path)[1].lower() in self.image_op.extensions)
        if len(file_paths2) == 0:
            self.image_op.msg = "対象のファイルがありません"
            self.msg.set(self.image_op.msg)
            return
        if file_paths2 != file_paths_:
            self.image_op.msg = "対象外のファイルは除きました"
            file_paths_ = file_paths2

        # サムネイル画像の幅を設定画面から取得
        thumbnail_xy_ = self.var_dict.get("width4thumbnail")
        if thumbnail_xy_:
            self.thumbnail_xy = thumbnail_xy_.get()

        # 取得したパスから表示データと画像を作成
        columns1, rows1, images1, msg1 = self.image_op.get_images(file_paths_, self.thumbnail_xy)
        self.images4display = self.images4display | set(images1)
        self.images4dialog = {}  # ダイアログ表示用画像初期化

        self.msg.set(self.image_op.msg)     # エラーメッセージの表示

        # 画像を含むFrameをframe4imagesに新規追加
        self.set_images2frame(parent, rows1, images1, tab_name)

    def select_files(self, event=None):
        """
        ファイル選択ダイアログを表示。選択したファイルパスを取得
        ファイル情報や画像を取得して表示
        """
        # 拡張子の辞書からfiletypes用のデータを作成
        # 辞書{".csv":"CSV", ".tsv":"TSV"}、filetypes=[("CSV",".csv"), ("TSV",".tsv")]
        file_paths_ = filedialog.askopenfilenames(
            filetypes=[(value, key) for key, value in self.image_op.extensions.items()])
        self.open_files_get_images_set2frame(parent=self.frame4images, file_paths_=file_paths_)		# ファイル情報や画像を取得して表示

    def preview_image(self, event=None, path=""):
        """
        画像のプレビュー
        ダイアログ表示
		Args:
            string:     ファイルパス(ない場合もある)
        """

        if event:
            if not event.widget.config("image"): return # imageオプションに指定がないなら抜ける
            path1 = event.widget.cget("text")   # ファイル名取得
        else:
            path1 = path

        # ダイアログ表示
        dialog_ = tk.Toplevel(self)      # モードレスダイアログの作成
        dialog_.title("Preview")         # タイトル
        self.images4dialog[path1] = ImageTk.PhotoImage(file=path1)    # 複数表示する時のために画像を残す
        label1 = tk.Label(dialog_, image=self.images4dialog[path1])      # 最後のものを表示
        label1.pack()
        dialog_.focus()
        # 閉じた時の動作を指定 最前面のウィジェットに設定しないと複数回発生する
        label1.bind("<Destroy>", lambda e: self.on_destroy(event=e, path=path1))
        # make Esc exit the preview
        dialog_.bind('<Escape>', lambda e: dialog_.destroy())

    def on_destroy(self, event=None, path=None):
        if event:
            # print(f"do pop key:{path} widget:{event.widget}")   # for debug
            self.images4dialog.pop(path)    # 表示用に残した画像を削除

    def preview_images(self, event=None):
        """
        選択された画像のプレビュー
        """
        self.msg.set("")
        w = self.note.nametowidget(self.note.select())  # get current tab widget
        paths = w.checked_image_paths
        for path1 in paths:
            self.preview_image(path=path1)
        if not paths:
            self.msg.set("選択された画像がありません")

    def convert_images(self, event=None):
        """
        選択された画像の変更(リサイズ、回転、反転、Exif除去、透かし)
        画像変更し、保存し、新しいタブに表示する
        """
        self.msg.set("")
        w = self.note.nametowidget(self.note.select())  # get current tab widget
        paths = list(w.checked_image_paths)
        if not paths:
            self.msg.set("選択された画像がありません")
            return
        settings_dict = {key: value.get() for key, value in self.var_dict.items()}  # variableの辞書を値の辞書に変換
        self.resized_paths, err_msg = self.image_ui.convert_image_from_dialog_or_args(settings_dict, paths=paths)
        self.create_new_tab(self.resized_paths)
        if err_msg:
            self.msg.set(err_msg)

    def create_new_tab(self, image_paths:set):
        """
        新しいタブの作成
        タブ名を「リサイズ画像n」とする
        """
        tab_name_resize = "リサイズ画像"
        # 複数の結果に対応するためタブ名を変える
        x = 2
        tab_name = tab_name_resize
        while tab_name in self.frame_children:
            tab_name = f"{tab_name_resize}{x}"
            x += 1

        self.frame4images2 = self.create_frame4images(self.note, tab_name)
        self.note.select(len(self.note.tabs()) - 1)     # 追加したタブを表示
        self.open_files_get_images_set2frame(parent=self.frame4images2
                                            , file_paths_=tuple(image_paths)
                                            , tab_name=tab_name)

    def break_upload(self, event=None):
        self.btn_break.state(["pressed"])
        self.do_break = True    # 中断フラグをオンにする

    def upload_images(self, event=None):
        """
        選択された画像をアップロード
        """
        th = threading.Thread(target=self.th_upload_images)
        th.start()

    def th_upload_images(self, event=None):
        """
        選択された画像をアップロード
        """
        self.do_break = False   # 中断フラグの初期化
        self.btn_upload.config(state="disable") # アップロードボタンを押下不可にします
        self.btn_break.config(state="active")  # 中断ボタンを押下可にします
        self.msg.set("アップロードを開始します")
        self.update_idletasks()
        self.uploaded_url = {}
        w = self.note.nametowidget(self.note.select())  # get current tab widget
        paths = list(w.checked_image_paths)
        if not paths:
            self.msg.set("選択された画像がありません")
            self.btn_upload.config(state="active")  # アップロードボタンを押下可にします
            self.btn_break.config(state="disable")  # 中断ボタンを押下不可にします
            return
        # はてなフォトライフのフォルダを指定
        if self.var_dict["use_hatena_folder"].get():
            folder_ = "Hatena Blog"     # デフォルトフォルダ
        else:
            folder_ = self.var_dict["folder"].get()
            if not folder_:                 # 空の場合は
                folder_ = "Hatena Blog"     # デフォルトフォルダ

        # 1画像ずつ呼び出しても複数画像で呼び出しても内部的に1画像ずつ処理するので1画像ずつ呼び出す
        for i, path_ in enumerate(paths):
            uploaded_url_1path = self.upload_ui.upload_image_to_hatena(paths=[path_], folder=folder_)
            if uploaded_url_1path:
                self.uploaded_url.update(uploaded_url_1path)    # 辞書に辞書を追加
                self.set_label_gb_in_frame_children(path_, "lightgreen")
            else:
                self.set_label_gb_in_frame_children(path_, "red")
            self.msg.set(f"{i+1} / {len(paths)} 件、アップロードが完了しました")
            self.update_idletasks()
            # 中断の確認
            if self.do_break:
                self.msg.set(f"{i+1} / {len(paths)} 件、アップロードしたところで中断しました")
                break;
        self.btn_upload.config(state="active")  # アップロードボタンを押下可にします
        self.btn_break.config(state="disable")  # 中断ボタンを押下不可にします

    def check_selected(self, event=None):
        """
        選択されたタブを確認 for debug
        """
        w = self.note.nametowidget(self.note.select())  # get current tab widget
        for path_ in w.checked_image_paths:
            print(f"selected widgets:{path_}")

    def select_all(self, event=None):
        """
        要素をすべて選択する
        """
        self.set_all_checkbox(True)

    def deselection(self, event=None):
        """
        要素をすべて選択解除する
        """
        self.set_all_checkbox(False)

    def set_all_checkbox(self, on_off_flag:bool):
        """
        チェックボックスのチェック状態をすべて設定する
		Args:
			bool: 設定値
        """
        tab_name = self.note.tab("current", "text")
        for child_ in self.frame_children.get(tab_name):    # self.frame_childrenはタブごとのFrameの集まり
            for item_ in child_.winfo_children():           # FrameにはCheckbuttonとLabel
                if type(item_) == tk.Checkbutton:
                    w = self.note.nametowidget(self.note.select())  # get current tab widget
                    if on_off_flag:
                        item_.select()
                        w.checked_image_paths.add(item_.cget("text"))
                    else:
                        item_.deselect()
                        w.checked_image_paths.discard(item_.cget("text"))

    def set_label_gb_in_frame_children(self, image_path:str, color:str):
        """
        image_pathをtextオプション持つチェックボックスを含むフレームのラベルの背景を変える
		Args:
			bool: 設定値
        """
        tab_name = self.note.tab("current", "text")
        for child_ in self.frame_children.get(tab_name):    # self.frame_childrenはタブごとのFrameの集まり
            for item_ in child_.winfo_children():           # FrameにはCheckbuttonとLabel
                if type(item_) == tk.Checkbutton:
                    is_same_path = item_.cget("text") == image_path  # 引数と同じパスか判断
                elif type(item_) == tk.Label:
                    label_ = item_
            if is_same_path:
                label_.config(background = color)
                label_.update()   # update_idletasksでは更新されない
                return

    def copy_image_url(self):
        """
        チェックされている画像のはてなフォトライフの画像のurlを取得し、
        画面の設定項目の指示に従って加工し、クリップボートにコピーする。
        """
        clip_strings = []
        self.msg.set("")
        settings_dict = {key: value.get() for key, value in self.var_dict.items()}  # 設定をウィジェット変数から値に変換
        tab_name = self.note.tab("current", "text")
        w = self.note.nametowidget(self.note.select())      # get current tab widget
        for child_ in self.frame_children.get(tab_name):    # self.frame_childrenはタブごとのFrameの集まり
            for item_ in child_.winfo_children():           # FrameにはCheckbuttonとLabel
                if type(item_) == tk.Checkbutton:
                    selected = item_.cget("text") in w.checked_image_paths  # 選択されている画像か判断
                    path_ = item_.cget("text")
                elif type(item_) == tk.Label:
                    uploaded = item_.winfo_rgb(item_.cget("background")) == item_.winfo_rgb("lightgreen")
            if uploaded and selected:
                clip_strings.append(self.get_image_url(path_, settings_dict))
        if clip_strings:
            pyperclip.copy(os.linesep.join(clip_strings))   # クリップボードにコピー
            self.msg.set("コピーしました")
        else:
            self.msg.set("コピーするものがありません")

    def get_image_url(self, file_name:str, settings_dict:dict) -> str:
        """
        画像(file_name)のはてなフォトライフの画像url情報を取得し、
        画面の設定項目の指示に従って加工し返す
		Args:
			str:    画像のファイル名(パス)
            dict:   画面の設定項目
        Returns:
            str:    加工した画像のurl
        """
        result = ""
        isfoto = settings_dict.get("foto", False)
        istitle = settings_dict.get("add_title")
        isonly_url = settings_dict.get("only_url", False)
        isoption = settings_dict.get("add_options", "")
        url_or_foto = self.uploaded_url.get(file_name)  # タプルが返る(url, foto)
        s1 = url_or_foto[isfoto]
        title_ = os.path.splitext(os.path.basename(file_name))[0]
        if isfoto:  # fotolife記法の編集
            # [f:id:はてなID:画像番号:title="タイトル"]
            s1 = s1.replace(":image", ":plain") # :imageはfotolifeが起動するので:plainに置換
            if istitle:
                s1 = s1 + f':title="{title_}"'
            if isoption:
                s1 = s1 + isoption
            if not isonly_url:
                s1 = f"[{s1}]"
        else:
            # ![](url "タイトル")
            if istitle:
                s1 = f'{s1} "{title_}"'
            if not isonly_url:
                s1 = f"![]({s1})"
        result = s1
        return result

class ImageOp():
    """
    画像データの操作を行う
    """
    def __init__(self):
        self.msg = ""   # メッセージ受渡し用
        # 対象拡張子	辞書(key:拡張子、値:表示文字)
        self.extensions = {".png .jpg .gif .webp":"画像", ".png":"PNG", 
                            ".jpg":"JPEG", ".gif":"GIF", ".webp":"WebP"}

    def get_images(self, file_names:tuple, thumbnail_xy = 160) -> Tuple[list, list, list, str]:
        """
        画像ファイルを読みデータを返す
        Args:
            str:    ファイル名
        Returns:
            columns1(list):     列名 
            rows1(list):        行データ(行リストの列リスト)
                                ファイル名, 幅(px), 高さ(px), サイズ(kB), 画像情報 EXIF, 位置情報 GPS
            self.images(list):  画像データ
            msg1(str):          エラーメッセージ(空文はエラーなし)
        """
        msg1 = ""
        columns1 = ["ファイル名", "幅(px)", "高さ(px)", "サイズ(kB)", "画像情報 EXIF", "位置情報 GPS"]
        try:
            self.images = []    # selfでないとうまくいかない。理由はローカル変数だと関数終了後gcされるため
            rows1 = []
            for file_name in file_names:   # パス名で回す
                # basename = os.path.basename(file_name)
                f = os.path.normpath(file_name)
                wrap_file_name = f.replace("\\", "\\\n")
                # 画像のサイズ
                file_size = os.path.getsize(file_name)
                # 画像の取得
                image1 = Image.open(file_name)
                # ファイルサイズの取得
                image_size = image1.size
                # Exif情報の取得
                exif_dict = image1.getexif()
                exif = [TAGS.get(k, "Unknown")+ f": {str(v)}" for k, v in exif_dict.items()]
                exif_str = "\n".join(exif)
                # GPS情報の取得
                gps_dict = exif_dict.get_ifd(34853)
                gps = [GPSTAGS.get(k, "Unknown") + f": {str(v)}" for k, v in gps_dict.items()]
                gps_str = "\n".join(gps)
                # 縮小
                image1.thumbnail((thumbnail_xy, thumbnail_xy), Image.BICUBIC) # image1が直接縮小される
                # サムネイルの大きさを統一(そうしないとチェックボックスの位置がまちまちになるため)
                # ベース画像の作成と縮小画像の貼り付け(中央寄せ)
                base_image = Image.new('RGBA', (thumbnail_xy, thumbnail_xy), (255, 0, 0, 0))  # 透明なものにしないとgifの色が変わる
                horizontal = int((base_image.size[0] - image1.size[0]) / 2)
                vertical = int((base_image.size[1] - image1.size[1]) / 2)
                # print(f"size:{image1.size} h,v:{horizontal},{vertical}, base:{base_image.size}")  # debug
                base_image.paste(image1, (horizontal, vertical))
                image1 = base_image
                # PhotoImageへ変換
                image1 = ImageTk.PhotoImage(image1)
                # 列データと画像データを追加
                self.images.append(image1)
                # 列データ(ファイル名、幅、高さ、ファイルサイズ、exif情報、gps情報)
                rows1.append([f, image_size[0], image_size[1], 
                                "{:.1f}".format(file_size/1024), exif_str, gps_str])
        except Exception as e:
            msg1 = e
            print(f"error:{e}")
        finally:
            return columns1, rows1, self.images, msg1

if __name__ == '__main__':
    root = TkinterDnD.Tk()      # トップレベルウィンドウの作成  tkinterdnd2の適用
    root.title("画像ツール")      # タイトル
    root.geometry("1000x702")    # サイズ
    listview = ListView(root)   # ListViewクラスのインスタンス作成
    root.drop_target_register(DND_FILES)            # ドロップ受け取りを登録
    # root.dnd_bind("<<Drop>>", listview.open_files_get_images_set2frame)    # ドロップ後に実行するメソッドを登録
    root.dnd_bind("<<Drop>>", lambda event: listview.open_files_get_images_set2frame(event=event, parent=listview.frame4images))    # ドロップ後に実行するメソッドを登録
    # コマンドライン引数からドラッグ＆ドロップされたファイル情報を取得
    if len(sys.argv) > 1:
        file_paths_ = tuple(sys.argv[1:])
        listview.open_files_get_images_set2frame(parent=listview.frame4images, file_paths_=file_paths_)			# オープン処理の実行
    root.mainloop()