---
title: "新規端末でのローカル編集"
date: "2026-06-13"
tags: ["Web App", "VS Code", "GitHub", "PythonAnywhere"]
summary: "新PC購入後タスク"
# cover: "/static/blog/2026-06-13/.png"
---

<br>
最後の記事から数ヵ月たってしまいました。  
長かった学生生活を終えて、アメリカで社会の一員として働き始め、お金にも余裕ができてきた今日この頃です。  
そこで先日、新たにPCを我が家にお出迎えして、ローカルの編集環境をセッティングを試みましたが、結構忘れてしまっていました、、。  
<br>
今回は以前<a href="https://nagaru24k.pythonanywhere.com/blog/2026-01-23-edit-locally" target="_blank" rel="noopener noreferrer">ローカル環境セッティング</a>と銘打ったVS Codeでの環境設定方法の続編として、既存のアプリケーションを新規端末でローカル編集できるようにするための手順を簡単にまとめました。  
前回よりも簡単にできたのは僕が成長したからなのか、普通に手順が楽ちんなのか、、後者です。  
<br><br>

## Prep
プロジェクトフォルダを作成し、既存のアプリケーションファイルを入れる。  
PAのソースコードから持ってくる場合は、bash(PA)で`zip -r your_backup.zip folder_name/`でzipファイルを入手。 
GitHubのレポから持ってくる場合は、<a href="https://download-directory.github.io/" target="_blank" rel="noopener noreferrer">ココ</a>からレポのダウンロード。
<br><br>

## VS Code
1. 作成したプロジェクトフォルダを開く。  
2. GitとPythonをインストールしていなければ、対応するバージョンを以下から入手。  
Git: <a href="https://gitforwindows.org/" target="_blank" rel="noopener noreferrer">Git for Windows</a>　　Python: <a href="https://www.python.org/downloads/" target="_blank" rel="noopener noreferrer">Python Downloads</a>  
Gitに関して、イニシャルコミット時に適当なメールと名前を求められるかもしれないが、指示に従って入力する。  
Ex: `git config --global user.name "nagaru24"`　　`git config --global user.email "uranus24k@gmail.com"`  
Pyrhonはインストール時に適当にYesを選択し続けると、最新版をインストールしてしまうので、ちゃんと文章を読むこと。Pythonのバージョンは`python --version`で確認。  
3. `git remote add origin https://github.com/nagaru24/Portfolio-Website`で該当GitHubレポのリモートを追加してローカル環境に読み込む。  
4. `python -m venv venv`で仮想環境を作成する。  
5. `.\venv\Scripts\Activate.ps1`で作成した仮想環境に入る。  
もし、エラーが出たら、`Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process`で一時的な実行許可をした後、再試行。   
6. `pip install -r requirements.txt`で必要なライブラリを確認/インストール。  
僕の場合のようにPythonのアプリの場合、`pyhton -m pip install -r requirements.txt`じゃないと動かないかもしれない。  
7. `python flask_app.py`などでアプリを起動してみる。もし、足りないパッケージがあれば、`python -m install ___`でインストールしていく。  
8. Flaskアプリのポート(5000)を聞いてテストなどしたければ、`$env:FLASK_APP="flask_app.py"; flask run --port 5000`を実行する。  
9. コーディング後、コミットして、GitHubのレポにプッシュ。
<br><br>

## GitHub
1. ローカル環境の設定がちゃんとマージされているか確認。  
2. プッシュした内容がちゃんと反映されているか確認。
<br><br>

## PyrhonAnywhere
1. GitHubレポから`git pull`でソースコードを引いてくる。  
2. リロード後、テスト環境と同じ変更が反映されるか確認。  
