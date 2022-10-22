# Python-blog-image-tool

## 概要 Description
はてなブログ向け画像ツール

## 特徴 Features
はてなブログの各記事に掲載する写真や画像を変換して、アップロードして、画像のURLをコピーできる。


【特徴】
- 画像のサイズ変更ができる
- 画像のミラー反転ができる
- 画像を左または右に回転できる
- 画像に文字透かしを入れられる
- 画像を はてなフォトライフにアップロードできる
- アップロードした画像のURLをコピーできる
- 設定を保存できる

## 依存関係 Requirement

- Python 3.8.5
- Pillow 8.3.0
- TkinterDnD2 0.3.0
- Requests 2.25.1
- pyperclip 1.8.2
- Repository [Python-Image-resize-sig](../../../Python-Image-resize-sig)	1.0.1
- Repository [Python-fotolife-Upload](../../../Python-fotolife-Upload)	1.0.1
- Repository [Python-TOML-util](../../../Python-TOML-util)	1.0.0
- Repository [Python-tkinter-libs](../../../Python-tkinter-libs)	1.0.1

## 使い方 Usage

    blog_image_tool.exe を実行
	または
    blog_image_tool.exe に表示したいファイルをドラッグアンドドロップ


## インストール方法 Installation

- pip install Pillow
- pip install tkinterdnd2
- pip install pyperclip
- pip install requests
- pip install tomli
- pip install tomli-w
- ソースと同じフォルダにコピー Copy to same folder as source
	- image_resize_sig.py
	- fotolifeUpload.py
	- toml_file_util.py
	- tkinter_libs.py

## プログラムの説明サイト Program description site

[はてなブログ向け画像ツールの作り方【Python】 - プログラムでおかえしできるかな](https://juu7g.hatenablog.com/entry/Python/blog/image-tool)

## 作者 Authors
juu7g

## ライセンス License
このソフトウェアは、MITライセンスのもとで公開されています。LICENSE.txtを確認してください。  
This software is released under the MIT License, see LICENSE.txt.

