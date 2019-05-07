//***********************Full Screen********************************************
var isFullScreen = false;
document.addEventListener('webkitfullscreenchange', exitHandler);
document.addEventListener('mozfullscreenchange', exitHandler);
document.addEventListener('MSFullscreenChange', exitHandler);
document.addEventListener('fullscreenchange', exitHandler);

var last_cursor = 'auto';

function whenFullScreen() {
    isFullScreen = true;
    elem.style.display = "";
    document.body.style.cursor = last_cursor;
}

function openFullScreen() {
    var xhttp = new XMLHttpRequest();
    xhttp.open("GET", "/fullScreenOn", true);
    xhttp.send();
    elem = document.getElementById("text");
    if (elem.requestFullscreen) {
        elem.requestFullscreen();
        whenFullScreen();
    } else if (elem.mozRequestFullScreen) { /* Firefox */
        elem.mozRequestFullScreen();
        whenFullScreen();
    } else if (elem.webkitRequestFullscreen) { /* Chrome, Safari & Opera */
        elem.webkitRequestFullscreen();
        whenFullScreen();
    } else if (elem.msRequestFullscreen) { /* IE/Edge */
        elem.msRequestFullscreen();
        whenFullScreen();
    }

}

function closeFullScreen() {
    var xhttp = new XMLHttpRequest();
    xhttp.open("GET", "/fullScreenOff", true);
    xhttp.send();
    if (document.cancelFullScreen) {
        document.cancelFullScreen();
    } else if (document.mozCancelFullScreen) {
        document.mozCancelFullScreen();
    } else if (document.webkitCancelFullScreen) {
        document.webkitCancelFullScreen();
    } else if (document.msExitFullscreen) {
        document.msExitFullscreen();
    }
}

function exitHandler() {
    if (!document.fullscreenElement && !document.webkitIsFullScreen && !document.mozFullScreen && !document.msFullscreenElement) {
        isFullScreen = false;
        elem.style.display = "none";
        last_cursor = document.body.style.cursor;
        document.body.style.cursor = 'auto';
    }
}

$(document).keyup(function (e) {
    if (e.key === "Escape") { // escape key maps to keycode `27`
        closeFullScreen()
    }
});


var d = new Date();
var n = d.getTime();

//******************************Task Itself****************************************

function setGridContent(data) {
    console.log("setGridContent", data);
    document.getElementById("top").innerHTML = data["top"];
    document.getElementById("mid").innerHTML = data["mid"];
    document.getElementById("bot").innerHTML = data["bot"];
    var d = new Date();
    console.log(d.getTime() - n);
    n = d.getTime();

}

function setIAPSContent(data) {
    document.getElementById("iaps_image").src = "images/" + data["src"];
}

function setGridVisibility(display) {
    if (display !== "none") {
        document.body.style.cursor = 'none';
    }
    document.getElementById("grid").style.display = display;
}

function setIAPSContentVisibility(display) {
    if (display !== "none") {
        document.body.style.cursor = 'none';
    }
    document.getElementById("iaps_image").style.display = display;
}

function setInstructionVisibility(display) {
    document.getElementById("ins").style.display = display;
    document.getElementById("ins_container").style.display = display;
}

function setWaitScreenVisibility(display) {
    if (display !== "none") {
        document.body.style.cursor = 'none';
    }
    document.getElementById("wait").style.display = display;
}

function setIAPSWaitScreenVisibility(display) {
    console.log(display);
    if (display !== "none") {
        document.body.style.cursor = 'none';
    }
    document.getElementById("iaps_wait").style.display = display;
}

function setIAPSEmotionVisibility(display) {
    if (display !== "none") {
        document.body.style.cursor = 'none';
    }
    document.getElementById("iaps_emotion").style.display = display;
}

function setIAPSKeyChoosingVisibility(display) {
    ignoreMouseClicks = false;
    if (display !== "none") {
        document.body.style.cursor = 'auto';
        ignoreMouseClicks = true;
    }
    document.getElementById("iaps_key_choosing").style.display = display;
}

function setEndScreenVisibility(display) {
    if (display !== "none") {
        document.body.style.cursor = 'auto';
    }
    document.getElementById("end").style.display = display;
}

function setInstructionsData(data) {
    $("#ins h2").html(data.title);
    $("#ins ul").empty();
    data.paragraphs.forEach(function (elem) {
        $("#ins ul").append(`<li style="text-align:right">
                                    <h5>` + elem.replace(/(?:\r\n|\r|\n)/g, '<br>') + `</h5>
                                </li>
                                `)
    })

}

//****************************************************************
function closeTask() {
    socket.emit("evCloseTask");
    closeFullScreen();
    window.location.href = '/'
}

function openDataWindow() {
    window.open("/data");
}