# 使い方

## 1. 必要なものをインストール

### Python仮想環境を作成

Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Mac / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### ライブラリをインストール

```bash
pip install playwright beautifulsoup4
playwright install chromium
```

---

## 2. スクリプトを配置

`bookmeter_to_booklog.py`

を好きなフォルダに置く。

---

## 3. 実行

```bash
python bookmeter_to_booklog.py
```

---

## 4. ユーザーIDを入力

読書メーターのURLが:

```text
https://bookmeter.com/users/123456
```

なら、

```text
123456
```

だけ入力する。

---

## 5. レビュー取得するか選択

```text
レビューも取得しますか？ (y/N):
```

* `y` → レビューも取得
* Enter → 読了日と本情報のみ取得

---

## 6. ブラウザでログイン

Chromiumブラウザが開くので、読書メーターにログイン。

ログイン後、ターミナルに戻って Enter。

---

## 7. 完了

同じフォルダに:

```text
booklog_import.csv
```

が生成される。

Shift-JIS / ヘッダーなし / ブクログ対応形式。

---

## 8. ブクログにインポート

ブクログの:

```text
設定 → データ管理 → CSVインポート
```

から `booklog_import.csv` をアップロード。

---

## 注意

* `playwright-profile/` フォルダにログイン状態が保存される
* レビュー取得は時間がかかる
* 読書メーター側のHTML変更で動かなくなる可能性あり
* 絵文字など一部文字はShift-JIS変換時に置換される場合あり
