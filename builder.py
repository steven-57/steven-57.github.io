# -*- coding: utf-8 -*-
import hashlib
import json
import os
import re
import shutil
import urllib.parse
import zipfile

import docx2txt
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

    # 定義 namespaces
    namespaces = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
        "wpg": "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup"
    }

    paragraphs = tree.xpath("//w:p", namespaces=namespaces)

    for p in paragraphs:
        xml_string = etree.tostring(p, encoding="unicode")
        cnt = xml_string.count("<pic:nvPicPr>")
        gp = "<wpg:wgp>" in xml_string

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

        data.append([o, cnt, gp])

    return data, styles


line_max = 4


def count_line(cnt):
    if cnt <= line_max:
        return cnt
    v = 1
    while (cnt - 1 + v) // v > line_max:
        v += 1
    return (cnt - 1 + v) // v


def render(name: str):
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
    if not os.path.exists(image_folder):
        os.makedirs(image_folder)
        docx2txt.process(os.path.join(source, name + '.docx'), image_folder)
    all_imgs = os.listdir(image_folder)
    all_imgs.sort(key=lambda x: int(x[5:x.find('.')]))
    imgs = []
    used_hash = set()
    for img in all_imgs:
        img_path = os.path.join(image_folder, img)
        hash_val = get_file_hash(img_path)
        if hash_val in used_hash:
            continue
        used_hash.add(hash_val)

        if not img.endswith('.webp'):
            try:
                with Image.open(img_path) as im:
                    max_width = 1200
                    if im.width > max_width:
                        ratio = max_width / im.width
                        new_height = int(im.height * ratio)
                        im = im.resize((max_width, new_height), Image.Resampling.LANCZOS)
                    
                    webp_img = os.path.splitext(img)[0] + '.webp'
                    webp_path = os.path.join(image_folder, webp_img)
                    if im.mode in ("RGBA", "P"): 
                        im = im.convert("RGB")
                    im.save(webp_path, 'WEBP', quality=80)
                
                os.remove(img_path)
                img = webp_img
            except Exception as e:
                print(f"Error optimizing {img}: {e}")

        imgs.append(img)
    it = 0
    out = []
    okbr = True
    wait_eximg = None
    for o, cnt, gp in data:
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
            base_img_name = os.path.splitext(imgs[it])[0]
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
            data=out, name=name, goodname=urllib.parse.quote_plus(name), styles=styles)
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
            render(name[:-5])
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
    for o in l:
        print(o["order"], o["name"])
    with open(os.path.join(target, "index.html"), "w", encoding="utf8") as f:
        f.write(env.get_template('index.html').render(data=l))
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
