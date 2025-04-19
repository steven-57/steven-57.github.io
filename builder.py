# -*- coding: utf-8 -*-
import hashlib
import os
import json
import re
import shutil

import docx
import docx2txt
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
import urllib.parse
import zipfile
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

def parse_docx_with_lxml(filepath,get_class):
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

    return data

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
                img_cmd[cmd["img"]] = cmd
            case "addele":
                if cmd["place"] == "text_para":
                    para_cmd.append(cmd)
            case "changetag":
                if cmd["place"] == "text_para":
                    para_cmd.append(cmd)
    styles = []
    stylemap = {}
    data = []
    def get_class(style):
        if style in stylemap:
            return stylemap[style]
        stylemap[style] = f"style{len(styles)}"
        styles.append(f".style{len(styles)} {{{style}}}")
        return stylemap[style]
    """
    doc = docx.Document(os.path.join(source, name + '.docx'))
    for i, para in enumerate(doc.paragraphs):
        txt = para._p.xml
        cnt = txt.count("<pic:nvPicPr>")
        gp = "<wpg:wgp>" in txt
        o = {"txt": para.text, "l": []}
        for run in para.runs:
            xml = run._r.xml
            style = ""
            if "w:szCs" in xml:
                L = xml.find("\"", xml.find("w:szCs"))
                R = xml.find("\"", L + 1)
                style += f"font-size:{xml[L + 1:R]}px;"
            if "w:color" in xml:
                L = xml.find("\"", xml.find("w:color"))
                R = xml.find("\"", L + 1)
                style += f"color:#{xml[L + 1:R]};"
            if "w:rFonts" in xml:
                R = xml.find("w:rFonts")
                END = xml.find(">", R)
                fonts = []
                while R < END:
                    L = xml.find("\"", R + 1)
                    R = xml.find("\"", L + 1)
                    if L == -1:
                        break
                    if R < END:
                        fonts.append(f'"{xml[L + 1:R]}"')
                style += f"font-family:{' '.join(fonts)};"
            o["l"].append([run.text, get_class(style)])
        data.append([o, cnt, gp])
        """
    data = parse_docx_with_lxml(os.path.join(source, name + '.docx'),get_class)
    image_folder = os.path.join(image, name)
    if not os.path.exists(image_folder):
        os.makedirs(image_folder)
        docx2txt.process(os.path.join(source, name + '.docx'), image_folder)
    all_imgs = os.listdir(image_folder)
    all_imgs.sort(key=lambda x: int(x[5:x.find('.')]))
    imgs = []
    used_hash = set()
    for img in all_imgs:
        hash_val = get_file_hash(os.path.join(image_folder, img))
        if hash_val in used_hash:
            continue
        used_hash.add(hash_val)
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
        for _ in range(cnt):
            if it >= len(imgs):
                break
            cmd = img_cmd.get(imgs[it], None)
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
                    o["img"] = name[:-5] + tp
                    shutil.copyfile(os.path.join(source, name[:-5] + tp), os.path.join(image, name[:-5] + tp))
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
