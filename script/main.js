var main = $("#main_area");
var actdict = {};
var $body = (window.opera) ? (document.compatMode == "CSS1Compat" ? $('html') : $('body')) : $('html,body');

function initindex() {
    if (main.find("h1,h2,h3,h4,h5,h6,p,pre,ol,ul").first().prop("tagName") != "H1") {
        main.prepend($("<h1></h1>").text($("title").text()));
    }
    main.find("h1,h2,h3,h4,h5,h6,p,pre,ol,ul,img").addClass("a_content");
    main.find("h1,h2,h3").addClass("a_header");
    let header = "";
    let count = 0;
    $(".a_content").each(function() {
        if ($(this).hasClass("a_header")) {
            header = "header_"+(++count);
            $(this).attr("id", header);
        } else {
            $(this).attr("connectedheader", header);
        }
        watcher.observe(this);
    });
    let index = $("#indexbar");
    let createul = () => $('<ul class="nav"></ul>');
    let createcollapse = () => $('<div class="collapse collapse_for_header"></div>');
    let createli = (id,name) => $('<li><a data-href="#' + id + '" class="text-truncate a_index" href>' + name + '</a></li>');
    let p0 = createul();
    index.append(p0);
    let p1 = p0;
    let p2 = p0;
    let l1 = null;
    let l2 = null;
    $(".a_header").each(function() {
        let id = $(this).attr("id");
        let name = $(this).text().trim();
        let l = createli(id,name);
        let pp2 = createcollapse();
        switch ($(this).prop("tagName")) {
            case "H1":
                p0.append(l);
                p1 = createul();
                p2 = createul();
                pp2.append(p2);
                p1.append(pp2);
                l2 = l1 = l;
                l.append(p1);
                actdict[id] = [l];
                break;
            case "H2":
                p1.append(l);
                p2 = createul();
                pp2.append(p2);
                l.append(pp2);
                l2 = l;
                actdict[id] = [l, l1];
                break;
            case "H3":
                p2.append(l);
                actdict[id] = [l, l1, l2];
                break;
        }
    });
    $("a.a_index").on("click", function(event){
        event.preventDefault();
        let link = $(this).data("href");
        history.replaceState({}, "", link);
        let target_top = $(link).offset().top;
        $body.scrollTop(target_top);
    });
}
function onEnterView(entries, observer) {
    for (let entry of entries) {
        if (entry.isIntersecting) {
            $(entry.target).addClass("a_content_inview");
        }else{
            $(entry.target).removeClass("a_content_inview");
        }
    }
    let o = $(".a_content_inview:first");
    let target = o.attr("connectedheader");
    if (o.hasClass("a_header")) target = o.attr("id");
    if (target) {
        $(".a_header_targeted").removeClass("a_header_targeted");
        $("#"+target).addClass("a_header_targeted");
    }
    $(".activated").removeClass("activated");
    $(".a_header_targeted").each(function() {
        for (let o of actdict[$(this).attr("id")]) {
            o.addClass("activated");
        }
    });
    $(".collapse_for_header").each(function() {
        let showing = $(this).parent().hasClass("activated");
        if (showing != $(this).hasClass("show")) {
            if (showing) $(this).addClass("show");
            else $(this).removeClass("show");
        }
    });
}
const base_url = "https://steven-57.github.io/images/";
function img_onEnterView(entries, observer) {
    for (let entry of entries) {
        if (entry.isIntersecting) {
            const img = entry.target;
            img.setAttribute('src', base_url+img.dataset.src);
            img.removeAttribute('data-src');
            observer.unobserve(img);
        }
    }
}
const watcher = new IntersectionObserver(onEnterView);
const img_watcher = new IntersectionObserver(img_onEnterView);
var max_width = document.body.clientWidth*0.6;
for (let group of document.querySelectorAll('.image-container')) {
    let images = $(group).find('img');
    let min_height = 10000;
    for (let image of images) {
        let height = +$(image).data("height");
        if (height<min_height) min_height = height;
    }
    let total_width = 0;
    for (let image of images) {
        let width = +$(image).data("width");
        total_width += width;
    }
    let mul = 1;
    if (total_width>max_width) mul = max_width/total_width;
    for (let image of images) {
        let w = +$(image).data("width");
        let h = +$(image).data("height");
        let my_mul = mul*height/h;
        $(image).data("width",w*my_mul);
        $(image).data("height",h*my_mul);
    }
}
for (let image of document.querySelectorAll('img[data-src]')) {
    let width = +$(image).data("width");
    let height = +$(image).data("height");
    if (width>max_width) {
        height = height/width*max_width;
        width = max_width;
    }
    $(image).css("height",height+"px");
    $(image).css("width",width+"px");
    img_watcher.observe(image);
}
if (!(location.href.endsWith("/") || location.href.endsWith("/index"))) {
    initindex();
}
main.css("margin-top",($("#top_area").height()+4)+"px");
$("#indexbar").css("margin-top",($("#top_area").height()+24)+"px");
$("a").each(function(){
    let to = $(this).attr("href");
    if (((to.includes(".")&&(!to.startsWith(".")))||to.startsWith("http://")||to.startsWith("https://"))&&(!to.includes("steven-57.github.io"))){
        $(this).attr("target","_blank");
    }
})