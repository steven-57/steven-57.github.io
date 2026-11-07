# -*- coding: utf-8 -*-
import hashlib
import io
import json
import os
import posixpath
import re
import shutil
import urllib.parse
import zipfile

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from lxml import etree

source = "sources"
target = ""
image = os.path.join(target, "images")
import datetime
from PIL import Image


def getimgdata(name: str, path: str):
    filename = os.path.join("images", name, path)
    img = Image.open(filename)
    return {"path": path, "width": img.width, "height": img.height}


def extract_image(docx_zip, info, image_folder, max_width=1200):
    """依 Word 中的裁切/旋轉/翻轉設定輸出 webp，回傳檔名"""
    stem = posixpath.splitext(posixpath.basename(info["media"]))[0]
    suffix = ""
    if info["crop"]:
        suffix += "_c" + "-".join(map(str, info["crop"]))
    if info["rot"]:
        suffix += f"_r{info['rot']}"
    if info["flipH"]:
        suffix += "_fh"
    if info["flipV"]:
        suffix += "_fv"
    webp_img = stem + suffix + ".webp"
    webp_path = os.path.join(image_folder, webp_img)
    if os.path.exists(webp_path):
        return webp_img
    with Image.open(io.BytesIO(docx_zip.read(info["media"]))) as im:
        im.load()
        if info["crop"]:
            l, t, r, b = info["crop"]
            w, h = im.size
            box = (round(w * l / 100000), round(h * t / 100000),
                   round(w * (1 - r / 100000)), round(h * (1 - b / 100000)))
            box = (max(box[0], 0), max(box[1], 0), min(box[2], w), min(box[3], h))
            if box[2] > box[0] and box[3] > box[1]:
                im = im.crop(box)
        if info["flipH"]:
            im = im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if info["flipV"]:
            im = im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        if info["rot"]:
            # Word 的 rot 為順時針，PIL 為逆時針
            im = im.rotate(-info["rot"], expand=True)
        if im.width > max_width:
            ratio = max_width / im.width
            im = im.resize((max_width, int(im.height * ratio)), Image.Resampling.LANCZOS)
        if im.mode != "RGB":
            im = im.convert("RGB")
        im.save(webp_path, 'WEBP', quality=80)
    return webp_img


def get_file_hash(file_path):
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()


def clean_html_with_soup(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    # 重新格式化 HTML 去除多餘空白
    html_content = soup.prettify()
    cleaned_html = re.sub(r'\n\s*', '', html_content)
    return cleaned_html.strip()


def parse_docx_with_lxml(filepath):
    styles = []
    stylemap = {}

    def get_class(style):
        if style in stylemap:
            return stylemap[style]
        stylemap[style] = f"style{len(styles)}"
        styles.append(f".style{len(styles)} {{{style}}}")
        return stylemap[style]

    data = []
    parser = etree.XMLParser(huge_tree=True)
    # unzip docx
    with zipfile.ZipFile(filepath) as docx_zip:
        with docx_zip.open('word/document.xml') as f:
            tree = etree.parse(f, parser=parser)
        with docx_zip.open('word/_rels/document.xml.rels') as f:
            rels_tree = etree.parse(f, parser=parser)
    rels = {}
    for rel in rels_tree.getroot():
        target_path = rel.get("Target", "")
        if rel.get("TargetMode") == "External":
            continue
        rels[rel.get("Id")] = posixpath.normpath(posixpath.join("word", target_path))

    # 定義 namespaces
    namespaces = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
        "wpg": "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup",
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    }

    def pic_info(pic):
        blip = pic.xpath("./pic:blipFill/a:blip", namespaces=namespaces)
        if not blip:
            return None
        rid = blip[0].get(f"{{{namespaces['r']}}}embed")
        if rid not in rels:
            return None
        info = {"media": rels[rid], "rot": 0, "flipH": False, "flipV": False, "crop": None}
        xfrm = pic.xpath("./pic:spPr/a:xfrm", namespaces=namespaces)
        if xfrm:
            info["rot"] = int(xfrm[0].get("rot", "0")) // 60000 % 360
            info["flipH"] = xfrm[0].get("flipH") in ("1", "true")
            info["flipV"] = xfrm[0].get("flipV") in ("1", "true")
        src = pic.xpath("./pic:blipFill/a:srcRect", namespaces=namespaces)
        if src:
            crop = tuple(int(src[0].get(k, "0")) for k in ("l", "t", "r", "b"))
            if any(crop):
                info["crop"] = crop
        return info

    paragraphs = tree.xpath("//w:p", namespaces=namespaces)

    for p in paragraphs:
        # mc:Fallback 內是舊版相容用的重複內容，略過
        pics = [pic_info(pic) for pic in p.xpath(".//pic:pic[not(ancestor::mc:Fallback)]", namespaces=namespaces)]
        pics = [x for x in pics if x]
        cnt = len(pics)
        gp = bool(p.xpath(".//wpg:wgp[not(ancestor::mc:Fallback)]", namespaces=namespaces))

        o = {"txt": "".join(p.xpath(".//w:t/text()", namespaces=namespaces)), "l": []}

        runs = p.xpath(".//w:r", namespaces=namespaces)
        for run in runs:
            text = "".join(run.xpath(".//w:t/text()", namespaces=namespaces))
            style = ""

            # 字型大小（w:szCs）
            szcs = run.xpath(".//w:szCs", namespaces=namespaces)
            if szcs:
                val = szcs[0].get(f"{{{namespaces['w']}}}val")
                if val:
                    style += f"font-size:{val}px;"

            # 顏色（w:color）
            color = run.xpath(".//w:color", namespaces=namespaces)
            if color:
                val = color[0].get(f"{{{namespaces['w']}}}val")
                if val:
                    style += f"color:#{val};"

            # 字型（w:rFonts）
            fonts = run.xpath(".//w:rFonts", namespaces=namespaces)
            if fonts:
                font_vals = []
                for attr in ['ascii', 'hAnsi', 'cs', 'eastAsia']:
                    val = fonts[0].get(f"{{{namespaces['w']}}}{attr}")
                    if val:
                        font_vals.append(f'"{val}"')
                if font_vals:
                    style += f"font-family:{' '.join(font_vals)};"

            o["l"].append([text, get_class(style)])

        data.append([o, cnt, gp, pics])

    return data, styles


line_max = 4


def count_line(cnt):
    if cnt <= line_max:
        return cnt
    v = 1
    while (cnt - 1 + v) // v > line_max:
        v += 1
    return (cnt - 1 + v) // v


def render(name: str, years: dict):
    print(name)
    cmds = []
    if os.path.exists(os.path.join(source, name + '.json')):
        with open(os.path.join(source, name + '.json'), encoding="utf8") as f:
            cmds = json.load(f)["cmds"]
    img_cmd = {}
    para_cmd = []
    for cmd in cmds:
        match cmd["type"]:
            case "eximg":
                base_name = os.path.splitext(cmd["img"])[0]
                img_cmd[base_name] = cmd
            case "addele":
                if cmd["place"] == "text_para":
                    para_cmd.append(cmd)
            case "changetag":
                if cmd["place"] == "text_para":
                    para_cmd.append(cmd)
    data, styles = parse_docx_with_lxml(os.path.join(source, name + '.docx'))
    image_folder = os.path.join(image, name)
    os.makedirs(image_folder, exist_ok=True)
    imgs = []
    used_files = set()
    with zipfile.ZipFile(os.path.join(source, name + '.docx')) as docx_zip:
        for _, _, _, pics in data:
            for info in pics:
                img = extract_image(docx_zip, info, image_folder)
                imgs.append(img)
                used_files.add(img)
    # 移除不再使用的舊圖片
    for f in os.listdir(image_folder):
        if f not in used_files:
            os.remove(os.path.join(image_folder, f))
    it = 0
    out = []
    okbr = True
    wait_eximg = None
    for o, cnt, gp, pics in data:
        if o["txt"]:
            o["tag"] = "p"
            for cmd in para_cmd:
                if cmd["place"] == "text_para" and cmd["target"] in o["txt"]:
                    if cmd["type"] == "addele" and cmd["pos"] == "before" and "html" in cmd:
                        out.append({"html": cmd["html"]})
                    if cmd["type"] == "changetag":
                        o["tag"] = cmd["tag"]
            if wait_eximg:
                o["eximg"] = getimgdata(name, wait_eximg[0])
                o["eximg_style"] = wait_eximg[1]
                wait_eximg = None
            out.append(o)
            for cmd in para_cmd:
                if cmd["place"] == "text_para" and cmd["target"] in o["txt"]:
                    if cmd["type"] == "addele" and cmd["pos"] == "after" and "html" in cmd:
                        out.append({"html": cmd["html"]})
            okbr = True
        else:
            if okbr:
                out.append({"html": "<br>"})
        true_cnt = 0
        if gp:
            out.append({"html": '<div class="image-container">'})
        sp = count_line(cnt)
        for idx in range(cnt):
            if it >= len(imgs):
                break
            base_img_name = os.path.splitext(imgs[it])[0].split("_")[0]
            cmd = img_cmd.get(base_img_name, None)
            if cmd:
                if cmd["type"] == "eximg":
                    if cmd["target"] == "after":
                        wait_eximg = [imgs[it], cmd.get("style", "")]
                    if cmd["target"] == "before":
                        out[-1]["eximg"] = imgs[it]
                        o["eximg_style"] = cmd.get("style", "")
            else:
                out.append({"img": getimgdata(name, imgs[it])})
                true_cnt += 1
            it += 1
            if cnt > idx + 1 and idx % sp == sp - 1:
                out.append({"html": '</div>'})
                out.append({"html": '<div class="image-container">'})
        if gp:
            out.append({"html": '</div>'})
        if true_cnt:
            out.append({"html": "<br><br>"})
            okbr = False
    with open(os.path.join(target, name + ".html"), "w", encoding="utf8") as f:
        res = env.get_template('page.html').render(
            data=out, name=name, goodname=urllib.parse.quote_plus(name), styles=styles, years=years)
        f.write(clean_html_with_soup(res))


if __name__ == '__main__':
    env = Environment(loader=FileSystemLoader('templates'))
    l = []
    T = max(os.path.getmtime(r"templates\base.html"),
            os.path.getmtime(r"templates\page.html"))
    IT = max(os.path.getmtime(r"templates\base.html"),
             os.path.getmtime(r"templates\index.html"))
    for name in os.listdir(source):
        if name[0] != "~" and name.endswith(".docx"):
            o = {"name": name[:-5]}
            t = os.path.getmtime(os.path.join(source, name))
            json_file = os.path.join(source, name[:-5] + ".json")
            t = max(t, os.path.getmtime(json_file))
            with open(json_file) as f:
                o["order"] = json.load(f)["order"]
            o["time"] = max(t, T)
            if os.path.exists(os.path.join(source, name[:-5] + ".txt")):
                with open(os.path.join(source, name[:-5] + ".txt"), encoding="utf8") as f:
                    o["description"] = f.read()
            for tp in (".jpg", ".jpeg", ".png"):
                if os.path.exists(os.path.join(source, name[:-5] + tp)):
                    img_path = os.path.join(source, name[:-5] + tp)
                    webp_img = name[:-5] + ".webp"
                    o["img"] = webp_img
                    try:
                        with Image.open(img_path) as im:
                            max_width = 800
                            if im.width > max_width:
                                ratio = max_width / im.width
                                new_height = int(im.height * ratio)
                                im = im.resize((max_width, new_height), Image.Resampling.LANCZOS)
                            if im.mode in ("RGBA", "P"): 
                                im = im.convert("RGB")
                            im.save(os.path.join(image, webp_img), 'WEBP', quality=80)
                    except Exception as e:
                        print(f"Error optimizing cover {img_path}: {e}")
                        o["img"] = name[:-5] + tp
                        shutil.copyfile(img_path, os.path.join(image, name[:-5] + tp))
                    break
            l.append(o)
    l.sort(key=lambda a: a["order"])
    years_dict = {}
    for o in l:
        print(o["order"], o["name"])
        year = str(abs(o["order"]))[:4]
        if year not in years_dict:
            years_dict[year] = []
        years_dict[year].append(o)
        
    for o in l:
        render(o["name"], years_dict)
        
    with open(os.path.join(target, "index.html"), "w", encoding="utf8") as f:
        f.write(env.get_template('index.html').render(data=l, years=years_dict))
    sitemap = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
"""
    sitemap += f"""<url>
<loc>https://steven-57.github.io/index</loc>
<lastmod>{datetime.date.fromtimestamp(IT)}</lastmod>
</url>
"""
    for o in l:
        sitemap += f"""<url>
<loc>https://steven-57.github.io/{urllib.parse.quote_plus(o["name"])}</loc>
<lastmod>{datetime.date.fromtimestamp(o["time"])}</lastmod>
</url>
"""
    sitemap += "</urlset>"
    with open("sitemap.xml", "w") as f:
        f.write(sitemap)
