# -*- coding: utf-8 -*-
import os
import json
import shutil

import docx
import docx2txt
from jinja2 import Environment, FileSystemLoader
import urllib.parse

source = "sources"
target = ""
image = os.path.join(target, "images")
import datetime
from PIL import Image


def getimgdata(name: str, path: str):
    filename = os.path.join("images", name, path)
    img = Image.open(filename)
    return {"path": path, "width": img.width, "height": img.height}


def render(name: str):
    print(name)
    doc = docx.Document(os.path.join(source, name + '.docx'))
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
    data = []
    for i, para in enumerate(doc.paragraphs):
        cnt = 0
        txt = para._p.xml
        if 'graphicData' in txt:
            x = txt.find('graphicData')
            while x != -1:
                cnt += 1
                x = txt.find('graphicData', x + 1)
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
            o["l"].append([run.text, style])
        data.append([o, cnt // 2])
    image_folder = os.path.join(image, name)
    if not os.path.exists(image_folder):
        os.makedirs(image_folder)
        docx2txt.process(os.path.join(source, name + '.docx'), image_folder)
    imgs = os.listdir(image_folder)
    imgs.sort(key=lambda x: int(x[5:x.find('.')]))
    it = 0
    out = []
    okbr = True
    wait_eximg = None
    for o, cnt in data:
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
        for _ in range(cnt):
            if it>=len(imgs):
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
        if true_cnt:
            out.append({"html": "<br><br>"})
            okbr = False
    with open(os.path.join(target, name + ".html"), "w", encoding="utf8") as f:
        f.write(env.get_template('page.html').render(data=out, name=name, goodname=urllib.parse.quote_plus(name)))


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
        print(o["order"],o["name"])
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
