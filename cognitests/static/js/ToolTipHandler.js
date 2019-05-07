var showVerticalHoverLine = true;
var chartDivId = "myDiv";
var chartDiv = document.getElementById(chartDivId);

/**ToolTipHandler.js*/
function ToolTipHandler(myDivId) {
    var _this = this;

    //timer for count time until hide the tooltip
    _this.hideTimerId = undefined;

    //append tooltip html to dom and save the span and the table element as member
    _this.toolTipSpan = $('<span class="own_tooltip"></span>');

    _this.toolTipTable = $(
        '<table>' +
        '  <tbody>' +
        '<tr><td colspan="3"><strong>13.09.17</strong></td></tr>' +
        '	<tr class="tooltip_entry">' +
        '	  <td><div class="tooltip_square" style="background:green"></div></td>' +
        '	  <td>Temp</td>' +
        '	  <td class="tooltip_value_col"><strong>38.876</strong></td>' +
        '	</tr>' +
        '  </tbody>' +
        '</table>'
    );
    _this.toolTipTable.appendTo(_this.toolTipSpan);
    _this.toolTipSpan.appendTo('body');
    _this.chartDivId = myDivId;

    //add event listener for coordinate mouse position
    function onMouseUpdate(e) {
        _this.xMouse = e.pageX;
        _this.yMouse = e.pageY;
    }

    document.addEventListener('mousemove', onMouseUpdate, false);
    document.addEventListener('mouseenter', onMouseUpdate, false);
}

/**
 * fills the toolTipTable with the given data and shows it at the given xy position. If no xy-Position is provided it shows the tooltip near to the mouse-cursor
 */
ToolTipHandler.prototype.showTooltip = function (data, xPosition = null, yPosition = null) {
    var _this = this;

    //clear timer for unhiding, because no unhiding is needed
    if (_this.hideTimerId != null) {
        window.clearTimeout(_this.hideTimerId);
        _this.hideTimerId = undefined;
    }

    //group measurements for date
    var xYData = {};//map: one date for more y values
    $.each(data.x, function (index, xValue) {
        yArray = xYData[xValue];
        if (yArray == null) {
            //there is not already an entry: create one
            yArray = [];
            xYData[xValue] = yArray;
        }
        yArray.push(data.y[index]);
    });

    //clear the table from old values
    _this.toolTipTable.empty();

    //iterate over each group (grouped by date)
    $.each(xYData, function (date, yArray) {
        //append date
        _this.toolTipTable.append('<tr><td colspan="3"><strong class="own_tooltip_date">' + date + '</strong></td></tr>');
        //append measurements for this date
        $.each(yArray, function (index, yValue) {
            //console.log(yValue);
            _this.toolTipTable./*find("tbody").*/append(//cause append without tbody don't works in jquery 2.1.4..
                '	<tr>' +
                '	  <td><div class="tooltip_square" style="background:' + yValue.color + '"></div></td>' +
                (yValue.customhoverinfo.includes("y") ? '	  <td>' + yValue.valueName + '</td>' : '') +
                (yValue.customhoverinfo.includes("y") ? '	  <td class="tooltip_value_col"><strong>' + yValue.yValue + '</strong></td>' : '') +
                (yValue.customhoverinfo.includes("text") ? '	  <td>' + yValue.text + '</td>' : '') +
                '	</tr>'
            );
        });

    });

    //set x,y position if it is not given
    if (xPosition == null || yPosition == null) {
        xPosition = _this.xMouse + 30;
        yPosition = _this.yMouse + 30;
    }

    //check if tooltip is to far right: do if to left
    var bodyWidth = $(document.body).width();
    var tooltipWidth = _this.toolTipSpan.width();
    var isToFarRight = tooltipWidth + xPosition > bodyWidth;
    if (isToFarRight) {
        xPosition = xPosition - 60 - tooltipWidth;
    }

    //check if tooltip is to far bottom: do it to top of cursor
    var bodyHeight = $(document.body).height();
    var tooltipHeight = _this.toolTipSpan.height();
    var isToFarBottom = tooltipHeight + yPosition > bodyHeight;
    if (isToFarBottom) {
        yPosition = yPosition - 60 - tooltipHeight;
    }

    //set position of tooltip and make it visible
    _this.toolTipSpan.css({top: yPosition, left: xPosition, position: 'absolute'});
    _this.toolTipSpan.show(0);
};

ToolTipHandler.prototype.hideTooltip = function () {
    var _this = this;

    //clear timer if exists
    if (_this.hideTimerId != null) {
        window.clearTimeout(_this.hideTimerId);
    }
    //start timer for unhiding
    _this.hideTimerId = window.setTimeout(function () {
        //hide tooltip
        _this.toolTipSpan.hide(0);
        //console.log("hide tooltip: "+_this.hideTimerId);
        _this.hideTimerId = undefined;
    }, 200);
};

ToolTipHandler.prototype.drawBobbel = function (xInPx, yInPx, color, bobbelId) {
    var _this = this;
    var existingBobbel = $("#" + _this.chartDivId + " #" + bobbelId)[0];
    if (existingBobbel == null) {
        //create bobbel!
        var circle = Plotly.d3.select("#" + _this.chartDivId + " .scatterlayer").append("circle")
            .attr("cx", xInPx)
            .attr("cy", yInPx)
            .attr("class", "hover_measure_bobbel")
            .attr("fill", color)
            .attr("r", "5px")
            .attr("id", bobbelId)
        ;
    }
    else {
        //set new position to bobbel
        $(existingBobbel).attr("cx", xInPx);
        $(existingBobbel).attr("cy", yInPx);
        $(existingBobbel).attr("visibility", "visible");
    }
};

/**
 * removes the span&table from the dom and delete the intern holder objects.
 */
ToolTipHandler.prototype.delete = function () {
    this.toolTipSpan.remove();
};

ToolTipHandler.prototype.drawVerticalLine = function (xInPx) {
    var _this = this;

    var boundingRect = $("#" + _this.chartDivId + " .cartesianlayer")[0].getBoundingClientRect();
    var yLength = boundingRect.bottom - boundingRect.top;

    //show hoverline (create of modify an existing one)
    var hoverLine = $("#" + _this.chartDivId + " .vertical_hover_line");
    if (hoverLine.length == 0) {
        //append hoverLine
        var path = Plotly.d3.select("#" + _this.chartDivId + " .scatterlayer").append("path")
            .attr("d", "M" + xInPx + ",0V" + yLength)
            .attr("stroke", "rgb(180, 180, 180)")
            .attr("stroke-width", "1px")
            .attr("class", "vertical_hover_line")
            .attr("stroke-opacity", "1");
    }
    else {
        //modify existing hoverline: coordinate and visibility
        $(hoverLine[0])
            .attr("d", "M" + xInPx + ",0V" + yLength)
            .attr("visibility", "visible");
    }
};


//create tooltipHandler
var toolTipHandler = new ToolTipHandler(chartDivId);

//create hover function
var lineChartHoverFunc = function (data) {
    var lastBobbelXInPx = null;//for remembering last x value for displaying vertical line after loop
    var calcdata = chartDiv.calcdata;
    var measurePoints = [];//container for yValues
    var xValues = [];//container for xValues
    console.log(data);
    //iterate over each hovered data point
    data.points.forEach(function (p) {
        xValues.push(p.x);//value is formatted by plotly
        //console.log(p);
        //its a linechart: use the color of the line
        try {
            var color = p.data.customcolor[p.pointIndex];
        }
        catch (err) {
            var color = p.fullData.line.color;
        }
        measurePoints.push({
            color: color,
            valueName: p.data.name,
            yValue: p.y,
            text: p.text,
            customhoverinfo: p.data.customhoverinfo
        });

        //append marker bobbel for each point
        if (showVerticalHoverLine) {
            var xMSVal = calcdata[p.curveNumber][p.pointNumber].x;
            var xInPx = p.xaxis.c2p(xMSVal);
            lastBobbelXInPx = xInPx;
            var yInPx = p.yaxis.l2p(calcdata[p.curveNumber][p.pointNumber].y);
            toolTipHandler.drawBobbel(xInPx, yInPx, color, p.curveNumber);
        }
    });

    //append vertical line
    if (showVerticalHoverLine) {
        toolTipHandler.drawVerticalLine(lastBobbelXInPx);
    }

    //show the data in tooltip
    toolTipHandler.showTooltip({x: xValues, y: measurePoints});
};

var lineChartUnHoverFunc = function (data) {
    //remove hoverline and bobbels
    if (showVerticalHoverLine) {
        $("#" + chartDivId + " .vertical_hover_line").attr("visibility", "hidden");
        $("#" + chartDivId + " .hover_measure_bobbel").attr("visibility", "hidden");
    }

    //hide the tooltip
    toolTipHandler.hideTooltip();
};

//add the hover and unhover function to the plot
