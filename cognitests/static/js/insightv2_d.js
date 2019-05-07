var Scene;
var greyMat;
var redMat;
var orangeMat;
var yellowMat;
var greenMat;

function showInsightDevInfo(data) {
    $('#AF3two').css('background-color', numberToColor(data["AF3"]));
    $('#AF4two').css('background-color', numberToColor(data["AF4"]));
    $('#T7two').css('background-color', numberToColor(data["T7"]));
    $('#T8two').css('background-color', numberToColor(data["T8"]));
    $('#Pztwo').css('background-color', numberToColor(data["Pz"]));
    $("#insight-AF3").attr("src", "../../static/img/insightV2/af3-" + data["AF3"] + ".png");
    $("#insight-AF4").attr("src", "../../static/img/insightV2/af4-" + data["AF4"] + ".png");
    $("#insight-T7").attr("src", "../../static/img/insightV2/t7-" + data["T7"] + ".png");
    $("#insight-T8").attr("src", "../../static/img/insightV2/t8-" + data["T8"] + ".png");
    $("#insight-Pz").attr("src", "../../static/img/insightV2/pz-" + data["Pz"] + ".png");

    try {
        Scene.getMeshByName('AF3Front').material = numberToMaterial(data["AF3"]);
        Scene.getMeshByName('AF4Front').material = numberToMaterial(data["AF4"]);
        Scene.getMeshByName('T7Front').material = numberToMaterial(data["T7"]);
        Scene.getMeshByName('T8Front').material = numberToMaterial(data["T8"]);
        Scene.getMeshByName('PzFront').material = numberToMaterial(data["Pz"]);
    }
    catch (err) {
    }
    var array = [data["AF3"], data["AF4"], data["T7"], data["T8"], data["Pz"]];
    checkQuality(array, data["Battery"]);
}
function showEpocDevInfo(data) {

    $('#AF3two').css('background-color', numberToColor(data["AF3"]));
    $('#AF4two').css('background-color', numberToColor(data["AF4"]));
    $('#T7two').css('background-color', numberToColor(data["T7"]));
    $('#T8two').css('background-color', numberToColor(data["T8"]));
    $('#Pztwo').css('background-color', numberToColor(data["Pz"]));
    $("#epocplus-AF3").attr("src", "../../static/img/epocplus/af3-" + data["AF3"] + ".png");
    $("#epocplus-AF4").attr("src", "../../static/img/epocplus/af4-" + data["AF4"] + ".png");
    $("#epocplus-F3").attr("src", "../../static/img/epocplus/f3-" + data["F3"] + ".png");
    $("#epocplus-F4").attr("src", "../../static/img/epocplus/f4-" + data["F4"] + ".png");
    $("#epocplus-F7").attr("src", "../../static/img/epocplus/f7-" + data["F7"] + ".png");
    $("#epocplus-F8").attr("src", "../../static/img/epocplus/f8-" + data["F8"] + ".png");
    $("#epocplus-FC5").attr("src", "../../static/img/epocplus/fc5-" + data["FC5"] + ".png");
    $("#epocplus-FC6").attr("src", "../../static/img/epocplus/fc6-" + data["FC6"] + ".png");
    $("#epocplus-O1").attr("src", "../../static/img/epocplus/o1-" + data["O1"] + ".png");
    $("#epocplus-O2").attr("src", "../../static/img/epocplus/o2-" + data["O2"] + ".png");
    $("#epocplus-P7").attr("src", "../../static/img/epocplus/p7-" + data["P7"] + ".png");
    $("#epocplus-P8").attr("src", "../../static/img/epocplus/p8-" + data["P8"] + ".png");
    $("#epocplus-T7").attr("src", "../../static/img/epocplus/t7-" + data["T7"] + ".png");
    $("#epocplus-T8").attr("src", "../../static/img/epocplus/t8-" + data["T8"] + ".png");
    try {
        Scene.getMeshByName('AF3Front').material = numberToMaterial(data["AF3"]);
        Scene.getMeshByName('AF4Front').material = numberToMaterial(data["AF4"]);
        Scene.getMeshByName('F3Front').material = numberToMaterial(data["F3"]);
        Scene.getMeshByName('F4Front').material = numberToMaterial(data["F4"]);
        Scene.getMeshByName('F7Front').material = numberToMaterial(data["F7"]);
        Scene.getMeshByName('F8Front').material = numberToMaterial(data["F8"]);
        Scene.getMeshByName('FC5Front').material = numberToMaterial(data["FC5"]);
        Scene.getMeshByName('FC6Front').material = numberToMaterial(data["FC6"]);
        Scene.getMeshByName('O1Front').material = numberToMaterial(data["O1"]);
        Scene.getMeshByName('O2Front').material = numberToMaterial(data["O2"]);
        Scene.getMeshByName('P7Front').material = numberToMaterial(data["P7"]);
        Scene.getMeshByName('P8Front').material = numberToMaterial(data["P8"]);
        Scene.getMeshByName('T7Front').material = numberToMaterial(data["T7"]);
        Scene.getMeshByName('T8Front').material = numberToMaterial(data["T8"]);
    }
    catch (err) {
    }
    var array = [data["AF3"], data["AF4"], data["F3"], data["F4"], data["F7"], data["F8"], data["FC5"],
        data["FC6"], data["O1"], data["O2"], data["P7"], data["P8"], data["T7"], data["T8"]];
    checkQuality(array, data["Battery"]);
}
function checkQuality(array, battery) {
    var quality = document.getElementById("quality");
    var numQuality = calcQuality(array);
    quality.innerHTML = numQuality.toString() + "%";
    quality.style.color = qualityToColor(numQuality);
    document.getElementById("battery").src = '../../static/img/battery' + battery + ".png";
}

function calcQuality(array) {
    var total = 0;
    var percent = 100 / array.length;
    for (var i = 0; i < array.length; i++) {
        total += (parseInt(array[i]) / 4) * percent;
    }
    return Math.round(total);
}
function qualityToColor(number) {
    if (number == 0 || isNaN(number))
        return 'red';
    var num = Math.ceil(number / 25);
    return numberToColor(num);
}
function numberToColor(number) {
    switch (number) {
        case 0.0:
            return 'grey';
            break;
        case 1.0:
            return 'red';
            break;
        case 2.0:
            return '#fe9a2d';
            break;
        case 3.0:
            return '#e5d01d';
            break;
        case 4.0:
            return 'lime';
            break;
        default:
            return 'grey';

    }
}
function numberToMaterial(number) {
    switch (number) {
        case 0.0:
            return greyMat;
            break;
        case 1.0:
            return redMat;
            break;
        case 2.0:
            return orangeMat;
            break;
        case 3.0:
            return yellowMat;
            break;
        case 4.0:
            return greenMat;
            break;
        default:
            return greyMat;
    }
}
