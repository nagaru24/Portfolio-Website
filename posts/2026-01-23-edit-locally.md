---
title: "ローカル環境セッティング"
date: "2026-01-23"
tags: ["Web App", "VS Code", "GitHub", "PythonAnywhere"]
summary: "自分のパソコンで安全に編集する"
# cover: "/static/blog/2026-01-23/.png"
---

<br>
このWebsiteは件の<a href="https://nagaru24k.pythonanywhere.com/workout" target="_blank" rel="noopener noreferrer">Workout Dashboard</a>も含めて、PythonAnywhereのサーバーで運営されています。  
月一でログインすれば無料で使えますが、限られたFile Storageでやりくりしないといけません。  
今後このブログやテックノートを続けていったり、同じレポにアプリを作ったりしていけば、近い将来、必ずhit the limitしてしまいます。無料で使えるよさげなデプロイ先をご存じでしたら、ぜひ教えてください。  
<br>
今回は自分のパソコンのVS CodeでWeb Appのコード編集するための環境設定方法をまとめたいと思います。  
ワークフローとしては、ローカルマシンで編集/テスト → GitHubのレポにプッシュ → PythonAnywhereにプル/リロード、といった感じです。  
<br>

## VS Code
1. プロジェクトフォルダを作成し、既存のアプリケーションファイルを入れる。  
PAのソースコードから持ってくる場合は、bash(PA)で`zip -r your_backup.zip folder_name/`でzipファイルを入手。 
GitHubのレポから持ってくる場合は、<a href="https://download-directory.github.io/" target="_blank" rel="noopener noreferrer">ココ</a>からレポのダウンロード。
2. ローカルとPA間の環境の違いをGitに載せないために、.gitignoreの作成。
3. Gitを初期化し、最初のコミット。  
`git init`  
`git add .`  
`git commit -m "initial commit"`  
4. GitHubでレポ作成。remoteを追加してpush。  
`git remote add origin [the repo url]`  
`git branch -M main`  
`git push -u origin main`  
<br><br>

## PythonAnywhere
1. アカウント作成後、bashでクローン。  
`cd ~`  
`git clone https://github.com/username/your-repo.git`  
`cd ~/your-repo`  
2. Web Appの追加、Pythonのバージョン選択を含めたManual Configuration。
3. WSGI fileを編集し、Web Appを読み込ませる。  
<br><br>

## 設定完了！
1. 好きなようにコーディング & Port 5000(flask)や8000などでチェック。
2. GitHubにpush。  
`git add .`  
`git commit -m "update"`  
`git push`
3. PAでpull。そしてリロード。  
`cd ~/your-repo`  
`git pull`  
もしうまくいかなければ、statusチェックやリセットを試みて、再度pull。  
`git status` →　`git log -1`  
`git reset --hard HEAD` → `git clean -fd`