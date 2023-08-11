var main = $("#main_area");
var actdict = {};

function initindex() {
    if (main.find("h1,h2,h3,h4,h5,h6,p,pre,ol,ul").first().prop("tagName") != "H1") {
        main.prepend($("<h1></h1>").text($("title").text()));
    }
    main.find("h1,h2,h3,h4,h5,h6,p,pre,ol,ul").addClass("a_content");
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
    });
    let index = $("#indexbar");
    let createul = () => $('<ul class="nav"></ul>');
    let createcollapse = () => $('<div class="collapse collapse_for_header"></div>');
    let createli = (id,name) => $('<li><a href="#' + id + '" class="text-truncate" smoothhashscroll>' + name + '</a></li>');
    let p0 = createul();
    index.append(p0);
    let p1 = p0;
    let p2 = p0;
    let l1 = null;
    let l2 = null;
    $(".a_header").each(function() {
        let id = $(this).attr("id");
        let name = $(this).text();
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
}

function update_inview() {
    $(".a_content").each(function() {
        let rect = this.getBoundingClientRect();
        let inView = rect.top >= 0 && rect.left >= 0 && rect.bottom <= $(window).height() && rect.right <= $(window).width();
        if (inView&&this.parentNode.tagName=="DETAILS"){
            inView = inView&&this.parentNode.open;
        }
        if (inView != $(this).hasClass("a_content_inview")) {
            if (inView) $(this).addClass("a_content_inview");
            else $(this).removeClass("a_content_inview");
        }

    });
    $(".a_header_targeted").removeClass("a_header_targeted");
    let o = $(".a_content_inview:first");
    let target = o.attr("connectedheader");
    if (o.hasClass("a_header")) target = o.attr("id");
    if (target) document.getElementById(target).classList.add("a_header_targeted");
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

function initspoiler(){
    //init template
    let spoilermap = {};
    $(".spoiler_template").each(function() {
        let tttt = $(this);
        spoilermap[tttt.find("summary").text()]=tttt;
        tttt.removeClass("spoiler_template");
    });
    $(".spoiler_repeat").each(function(){
        let tttt = $(this);
        let myname = tttt.text();
        let got = spoilermap[myname];
        if (got){
            tttt.after(got.clone());
        }
    }).remove();
    for (let o in spoilermap) spoilermap[o].remove();
    $("details").next().filter("br").remove();
}
//table style
main.find("table").addClass("table").addClass("table-striped").addClass("table-bordered");
//remove empty
main.find("h1,h2,h3,h4,h5,h6,p,pre,ol,ul").each(function(){
    if ($(this).text()=="")$(this).remove();
});
//init index
if (!(location.href.endsWith("/") || location.href.endsWith("/index"))) {
    initindex();
    initspoiler();
}
//init view detect
$(window).on('DOMContentLoaded load resize scroll', update_inview);
// margin-top
main.css("margin-top",($("#top_area").height()+4)+"px");
$("#indexbar").css("margin-top",($("#top_area").height()+24)+"px");
// a setting
$("a").each(function(){
    let to = $(this).attr("href");
    if (((to.includes(".")&&(!to.startsWith(".")))||to.startsWith("http://")||to.startsWith("https://"))&&(!to.includes("littleorange666.github.io"))){
        $(this).attr("target","_blank");
    }
})