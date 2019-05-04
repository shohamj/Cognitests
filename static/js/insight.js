function showDevInfo(data) {
    $('.insight #AF3').css('background-color', numberToColor(data["AF3"]));
    $('.insight #AF4').css('background-color', numberToColor(data["AF4"]));
    $('.insight #T7').css('background-color', numberToColor(data["T7"]));
    $('.insight #T8').css('background-color', numberToColor(data["T8"]));
    $('.insight #Pz').css('background-color', numberToColor(data["Pz"]));
    var array = [data["AF3"], data["AF4"], data["T7"], data["T8"], data["Pz"]];
    var quality = document.getElementById("quality");
    var numQuality = calcQuality(array);
    quality.innerHTML = numQuality.toString() + "%";
    quality.style.color = qualityToColor(numQuality);
    document.getElementById("battery").src = '../../static/img/battery' + data["battery"] + ".png";
    document.getElementById("signal").src = '../../static/img/signal' + data["signal"] + ".png";
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
    console.log("numberToColor:", number)
    switch (number) {
        case 0.0:
            return 'grey';
            break;
        case 1.0:
            return 'red';
            break;
        case 2.0:
            return 'orange';
            break;
        case 3.0:
            return 'yellow';
            break;
        case 4.0:
            return 'lime';
            break;
        default:
            return 'grey';

    }
};
