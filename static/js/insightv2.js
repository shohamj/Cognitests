var Scene;
var greyMat;
var redMat;
var orangeMat;
var yellowMat;
var greenMat;

function showDevInfo(data) {
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
    var quality = document.getElementById("quality");
    var numQuality = calcQuality(array);
    quality.innerHTML = numQuality.toString() + "%";
    quality.style.color = qualityToColor(numQuality);
    document.getElementById("battery").src = '../../static/img/battery' + data["Battery"] + ".png";
};

function calcQuality(arr) {
    var total = 0;
    for (var i = 0; i < arr.length; i++)
        total += (parseInt(arr[i]) * 20) / 4;
    return total;
};

function qualityToColor(number) {
    if (number == 0 || isNaN(number))
        return 'red'
    var num = Math.ceil(number / 25);
    return numberToColor(num);
};

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
};


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
};

