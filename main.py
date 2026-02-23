import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import pandas as pd
import zipfile
import os
import platform

st.set_page_config(page_title="画像一括生成ツール", layout="wide")
st.title("🚀 複数画像・ロゴ・文字 一括合成ツール")

# --- 1. フォント設定 ---
def get_system_fonts():
    current_os = platform.system()
    if current_os == "Darwin": # Mac
        return {"ヒラギノ角ゴ": "/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc", "ヒラギノ明朝": "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc"}
    elif current_os == "Windows": # Win
        return {"メイリオ": "C:\\Windows\\Fonts\\meiryo.ttc", "MS ゴシック": "C:\\Windows\\Fonts\\msgothic.ttc"}
    return {"デフォルト": None}

SYSTEM_FONTS = get_system_fonts()

# --- 2. 画像合成用の共通関数 ---
def process_synthesis(text, bg_source, logo_source=None):
    img = Image.open(bg_source).convert("RGBA")
    img = img.resize((out_w, out_h))

    if logo_source:
        logo = Image.open(logo_source).convert("RGBA")
        aspect = logo.height / logo.width
        logo = logo.resize((l_w, int(l_w * aspect)))
        img.paste(logo, (l_x, l_y), logo)

    draw = ImageDraw.Draw(img)
    font_path = SYSTEM_FONTS[f_name]
    font = ImageFont.truetype(font_path, f_size) if font_path else ImageFont.load_default()
    draw.text((t_x, t_y), str(text), fill=f_color, font=font, anchor="mm")

    return img

# --- 3. サイドバー設定 ---
st.sidebar.header("共通デザイン設定")
f_name = st.sidebar.selectbox("フォント選択", list(SYSTEM_FONTS.keys()))
f_size = st.sidebar.number_input("文字サイズ", value=60)
f_color = st.sidebar.color_picker("文字色", "#FFFFFF")
t_x = st.sidebar.number_input("文字 X位置", value=540)
t_y = st.sidebar.number_input("文字 Y位置", value=540)

st.sidebar.divider()
st.sidebar.write("ロゴの配置設定")
l_x = st.sidebar.number_input("ロゴ X位置", value=10)
l_y = st.sidebar.number_input("ロゴ Y位置", value=10)
l_w = st.sidebar.number_input("ロゴ 幅", value=150)

out_w = st.sidebar.number_input("出力幅", value=1080)
out_h = st.sidebar.number_input("出力高", value=1080)

# --- 4. メインエリア：素材の準備 ---
st.header("1. 素材の準備（ファイル名取得）")
st.info("ここに画像をアップロードすると、ファイル名の一覧が表示されます。CSV作成に活用してください。")

col_a, col_b = st.columns(2)
with col_a:
    temp_bg_files = st.file_uploader("背景用：ファイル名を取得したい画像を選択", type=["jpg", "png"], accept_multiple_files=True, key="bg_tmp")
with col_b:
    temp_logo_files = st.file_uploader("ロゴ用：ファイル名を取得したい画像を選択", type=["jpg", "png"], accept_multiple_files=True, key="logo_tmp")

# --- ★新機能：ファイル名書き出しエリア ---
if temp_bg_files or temp_logo_files:
    st.subheader("📋 コピペ用ファイル名リスト")
    c1, c2 = st.columns(2)
    with c1:
        if temp_bg_files:
            bg_names = "\n".join([f.name for f in temp_bg_files])
            st.text_area("背景画像ファイル名（CSVの bg_name 列へ）", value=bg_names, height=150)
    with c2:
        if temp_logo_files:
            logo_names = "\n".join([f.name for f in temp_logo_files])
            st.text_area("ロゴ画像ファイル名（CSVの logo_name 列へ）", value=logo_names, height=150)

st.divider()

# --- 5. メインエリア：本番アップロードと合成 ---
st.header("2. 合成の実行")
csv_file = st.file_uploader("指示CSVをアップロード", type="csv")

if csv_file and (temp_bg_files):
    try:
        df = pd.read_csv(csv_file)
    except UnicodeDecodeError:
        csv_file.seek(0)
        df = pd.read_csv(csv_file, encoding='cp932')

    st.write("CSVデータプレビュー:", df.head())

    bg_dict = {f.name: f for f in temp_bg_files}
    logo_dict = {f.name: f for f in temp_logo_files} if temp_logo_files else {}

    # プレビュー
    st.subheader("📋 プレビュー")
    preview_row = st.number_input("確認する行番号", min_value=0, max_value=len(df)-1, value=0)
    row = df.iloc[preview_row]
    bg_n = row['bg_name']
    lg_n = row.get('logo_name')
    txt = row['text_data']

    if bg_n in bg_dict:
        p_img = process_synthesis(txt, bg_dict[bg_n], logo_dict.get(lg_n) if lg_n else None)
        st.image(p_img, width=500, caption=f"行 {preview_row} のプレビュー")
    else:
        st.error(f"背景画像 '{bg_n}' が見つかりません。上の『1.素材の準備』で正しく選ばれているか確認してください。")

    if st.button("🔥 一括生成を開始"):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_f:
            for i, r in df.iterrows():
                b_n = r['bg_name']
                l_n = r.get('logo_name')
                t = r['text_data']
                if b_n in bg_dict:
                    res_img = process_synthesis(t, bg_dict[b_n], logo_dict.get(l_n) if l_n else None)
                    img_bytes = io.BytesIO()
                    res_img.save(img_bytes, format='PNG')
                    zip_f.writestr(f"result_{i}_{b_n}", img_bytes.getvalue())

        st.success("一括生成完了！")
        st.download_button("📥 ZIPダウンロード", zip_buffer.getvalue(), "images.zip")
