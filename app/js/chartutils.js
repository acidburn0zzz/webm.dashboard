// chartutils.js
// This file contains several functions used to draw charts common to both
// index.html and commit_view.html


// The dialog argument is a boolean to distinguish between commit_view (T) and
// index.html (F)
// Note that "#chartdiv", "#configInfo", "#status" are shared across both.
// "#chartdialog" is only used in commit_view.html
// "#commitInfo", '#tabs2' are only for index.html

// ----------------------------------------------------------------------------
// This is used in the commit viewer (commit_viewer.html and commit_view.html)
function ChartFiller_Commit(metric, config, file, commit, baseline, chartdiv, dialogdiv, tablediv, configdiv, statusdiv) {
  var dist_responses = new Array();
  var bar_responses = new Array();

  // Wait until all data is fetched to generate graphs
  $(document).ajaxStop(function() {
    $(this).unbind("ajaxStop");
    if (dist_responses.length > 0) {
      drawChart(dist_responses, chartdiv, dialogdiv, tablediv, configdiv, statusdiv);
    }

    if (bar_responses.length > 0) {
      drawChart2(bar_responses, chartdiv, dialogdiv, tablediv, configdiv, statusdiv);
    }
  });

  // Add the baseline to the list of commits, if one is set
  var commits = [commit, baseline];

  // one series per commit
  if (bar_responses.length == 0 && !is_distortion(metric))
    for (var t = 0; t < commits.length; t++)
      bar_responses[t] = new Array();

  for (var t = 0; t < commits.length; t++) {

    // We put together a url
    var commit = commits[t];
    metricurl = "/metric-data/" + metric + "/" + config + "/" + file + "/" + commit

    // pretty-up commit hash
    if (commit === baseline)
      commit = commit.slice(0,9) + " (Baseline)";
    else
      commit = commit.slice(0,9);

    // Build a more readable version of the series name
    var series_name = []

    if (is_distortion(metric)) {
      series_name.push(commit);
      series_name = {label: series_name.join(" "), commit: commit};
      FetchMetric(metricurl, series_name, dist_responses);
    } else {
      series_name.push(file);
      series_name = {label: series_name.join(" "), commit: commit};
      FetchMetric(metricurl, series_name, bar_responses[t]);
    }
  }
}



///////////////////////////////////////////////////////////////////////////////
// Functions used in index.html, commit_viewer.html, and commit_view.html

function drawChart(data_in, chartdiv, dialogdiv, tablediv, configdiv, statusdiv) {
  var numCurves = data_in.length;
  var view;
  var data2;

  // We have at least one curve
  data_in1 = data_in[0].response;

  var data1 = new google.visualization.DataTable();
  data1.addColumn('number', 'Bitrate');
  data1.addColumn('number', 'target bitrate');
  data1.addColumn('number', data_in[0].series_name.label);
  data1.addRows(data_in1.data);
  view = new google.visualization.DataView(data1);

  for (var i = 1; i < numCurves; i++){
    data_in2 = data_in[i].response.data;
    data2 = new google.visualization.DataTable();
    data2.addColumn('number', 'Bitrate');
    data2.addColumn('number', 'target bitrate');
    data2.addColumn('number',  data_in[i].series_name.label);

    data2.addRows(data_in2);

    // Join the two tables into one view
    leftColumns = range(2, i + 1);
    view = new google.visualization.data.join(view, data2, 'full', [[0,0], [1,1]], leftColumns, [2]);

  }

  // Set chart options
  chartOptions['vAxis'] = {title: data_in1.yaxis};
  chartOptions['hAxis'] = {title: 'Bitrate'};
  chartOptions['pointSize'] = 2;
  chartOptions['lineWidth'] = 1;
  chartOptions['interpolateNulls'] = true;
  chartOptions['title'] = 'Rate Distortion Curves';
  var tableOptions = {width: 'automatic'};

  // We filter out target_bitrate for the sake of the chart
  chart_view = new google.visualization.DataView(view);
  chart_view.hideColumns([1]);

  // Instantiate and draw our chart, passing in some options.
  var chart = new google.visualization.LineChart(document.getElementById(chartdiv));

  if (dialogdiv)
    $('#' + dialogdiv).dialog({height: 600, width: 800}).dialog('open');
  chart.draw(chart_view, chartOptions);

  if (tablediv){
    var table = new google.visualization.Table(document.getElementById("tabs2"));
    table.draw(view, tableOptions);
  }

  if (!dialogdiv){
    $(window).resize(function() {
      chart.draw(chart_view, chartOptions);
      statusbar = document.getElementById('status');
      statusbar.style.display = 'none';
    });
  }

  // Add our selection handler.
  if (configdiv)
    google.visualization.events.addListener(chart, 'select', selectHandler);
  if (statusdiv)
    google.visualization.events.addListener(chart, 'onmouseover', chartMouseOver);

  // The selection handler.
  function selectHandler() {
    var selection = chart.getSelection();
    chart.setSelection();
    for (var i = 0; i < selection.length; i++) {
      var item = selection[i];
      var commits = new Array();
      var baseline = '';

      // If we click something in the legend
      if (item.column != null && item.row == null) {
        // We get all the series labels
        for (var j = 0; j < numCurves; j++){
          var commit = data_in[j].series_name.label;
          var lastchar = commit[commit.length-1];
          if (lastchar === ')')
            baseline = data_in[j].commit;
          else
            commits.push(data_in[j].commit);
        }

        if (dialogdiv)
          linkToBaseline(baseline);
        if (tablediv) { // only relevant for index.html
          $("#commitInfo").dialog('close');
          $("#commitInfo").html("Loading...");
          $("#commitInfo").load("/commit-info/"+commits.join(',')+"/"+baseline);
          $('#commitInfo').dialog('open');
        }
      }

      // If we click on a data point
      else if (item.column != null && item.row != null) {
        var metric = data_in[item.column - 1].metric;
        var config = data_in[item.column - 1].config;
        var filename = data_in[item.column - 1].filename;
        var commit = data_in[item.column - 1].commit;
        var bitrate = view.getValue(item.row, 1);

        // We need metric, file, config, and commit for this data point
        var url = metric + "/" + config + '/' + filename + '/' + commit + '/' +
                  bitrate;

        $('#' + configdiv).dialog('close');
        $('#' + configdiv).html("Loading...");
        $('#' + configdiv).load("/config-info/" + url);
        $('#' + configdiv).dialog('open');
      }

    }
  }

  function chartMouseOver(e){
    pointDifference(e.row, e.column)
  }

  function pointDifference(row, col){
    // ported over from visualmetrics.py
    if(!row || !col)
      return;

    var cols = chart_view.getNumberOfColumns();
    var rows = chart_view.getNumberOfRows();

    var sel_bitrate = chart_view.getValue(row, 0 );
    var sel_metric = chart_view.getValue(row, col);

    var message = "At " + sel_metric.toFixed(2) + " decibels, <em>"
    message = message + chart_view.getColumnLabel(col) + "</em> is <ul>"

    for( var i=1;i<cols;++i){

      var metric_greatest_thats_less = 0;
      var rate_greatest_thats_less = 0;
      var metric_smallest_thats_greater = 999;
      var rate_smallest_thats_greater = 0;

      if(i==col)
        continue;

      // find the lowest metric for this column thats greater than sel_metric and
      // the highest metric for this column thats less than the metric
      for(var line_count = 0; line_count < rows; ++line_count) {
        this_metric = chart_view.getValue(line_count, i)
        this_rate = chart_view.getValue(line_count, 0)
        if(!this_metric)
          continue;

        if(this_metric > metric_greatest_thats_less &&
           this_metric < sel_metric) {
          metric_greatest_thats_less = this_metric;
          rate_greatest_thats_less = this_rate;
        }
        if(this_metric < metric_smallest_thats_greater &&
          this_metric > sel_metric) {
          metric_smallest_thats_greater = this_metric;
          rate_smallest_thats_greater = this_rate;
        }
      }

      if(rate_smallest_thats_greater == 0 || rate_greatest_thats_less == 0) {
        message = message + " <li> Couldn't find a point on both sides.</li>"
      }
      else
      {
        metric_slope = ( rate_smallest_thats_greater - rate_greatest_thats_less) /
            ( metric_smallest_thats_greater - metric_greatest_thats_less);

        projected_rate = ( sel_metric - metric_greatest_thats_less) *
            metric_slope + rate_greatest_thats_less;

        difference = 100 * (projected_rate / sel_bitrate - 1);


        if (difference > 0)
          message = message + "<li>  " + difference.toFixed(2) +
                    "% smaller than <em>" +
                    chart_view.getColumnLabel(i) + "</em></li> "
        else
          message = message + "<li>  " + -difference.toFixed(2) +
                    "% bigger than <em>" +
                    chart_view.getColumnLabel(i) + "</em></li> "
      }

    }
    message = message + "</ul>"
    statusbar = document.getElementById(statusdiv);
    statusbar.innerHTML = "<p>" + message + "</p>";
    statusbar.style.display = 'block';
  }

}



function drawChart2(data_in, chartdiv, dialogdiv, tablediv, configdiv, statusdiv) {
  // We make a candlestick chart

  function find_min_avg_max(arr) {
    var min_ele = arr[0];
    var max_ele = arr[0];
    var sum = 0;
    var count = 0;
    for (var k = 0; k < arr.length; k++) {
      count += 1;
      sum += arr[k];
      if (arr[k] < min_ele)
        min_ele = arr[k];
      else if (arr[k] > max_ele)
        max_ele = arr[k];
    }
    // we assume arr.length >= 1
    return [min_ele, sum/count, sum/count, max_ele];
  }

  var mat = [[]]

  // series labels, one per commit
  mat[0][0] = "unused";
  for (var series = 0; series < data_in.length; series++) {
    var series_name = data_in[series][0].series_name;
    for (var i = 0; i<4; i++)
      mat[0][series*4 + i + 1] = series_name.commit;
  }

  // one table row per file
  for (var rowidx = 0; rowidx < data_in[0].length; rowidx++) {
    var row_label = data_in[0][rowidx].series_name.label;
    var row = new Array(row_label);

    // four columns per series (commit)
    for (var series = 0; series < data_in.length; series++) {
      var series_data = data_in[series][rowidx].response.data;
      var comparr = [];
      for (var i = 0; i < series_data.length; i++) {
        comparr[i] = series_data[i][0];
      }
      row = row.concat(find_min_avg_max(comparr));
    }
    mat[rowidx+1] = row;
  }

  // Convert to a data table and format for display
  var formatter = new google.visualization.NumberFormat(
      {fractionDigits: 3});
  var data1 = new google.visualization.arrayToDataTable(mat, false);
  for (var i = 1; i < mat[1].length; i++)
      formatter.format(data1, i);
  view = new google.visualization.DataView(data1);

  // Set chart options
  chartOptions['title'] = 'Performance';
  chartOptions['vAxis'] = {title: data_in[0][0].response.yaxis};
  var tableOptions = {width: 'automatic'};

  // Instantiate and draw our chart, passing in some options.
  var chart2 = new google.visualization.CandlestickChart(document.getElementById(chartdiv));
  if (dialogdiv)
    $('#' + dialogdiv).dialog({height: 600, width: 800}).dialog('open');
  chart2.draw(view, chartOptions);

  if (tablediv) {
    var table2 = new google.visualization.Table(document.getElementById(tablediv));
    table2.draw(view, tableOptions);
  }

  // We now add a function to resize the chart when the page is resized
  if (!dialogdiv) {
    $(window).resize(function() {
      chart2.draw(view, chartOptions);
    });
  }

  // Add our selection handler.
  if (configdiv)
    google.visualization.events.addListener(chart2, 'select', selectHandler);

  // The selection handler.
  function selectHandler() {
    var selection = chart2.getSelection();
    chart2.setSelection();

    for (var i = 0; i < selection.length; i++) {
      var item = selection[i];
      var commits = new Array();
      var baseline = '';

      // If we click something in the legend
      if (item.column != null && item.row == null) {
        for (var j = 0; j < data_in.length; j++){
          var series_name = data_in[j][0].series_name;
          var commit = series_name.commit;
          var lastchar = commit[commit.length-1];
          if (lastchar === ')')
            baseline = data_in[j][0].commit;
          else
            commits.push(data_in[j][0].commit);
        }
        if (dialogdiv)
          linkToBaseline(baseline);
        else if (tablediv) { // only relevant for index.html
          $("#commitInfo").dialog('close');
          $("#commitInfo").html("Loading...");
          $("#commitInfo").load("/commit-info/"+commits.join(',')+"/"+baseline);
          $('#commitInfo').dialog('open');
        }

      }

      // If we click on a data point
      else if (item.column != null && item.row != null) {
        var commit_start = view.getColumnLabel(item.column).slice(0,9);
        var filename = view.getValue(item.row, 0);
        var commit;
        var metric;
        var config;

        // Is there a better way of corresponding points and thier set-ups?
        for (var j = 0; j < data_in.length; j++) {
          // here data_in[j] is an array of objects - each array being one commit
          for (var k = 0; k < data_in[j].length; k++){
            var obj = data_in[j][k];
            if (obj.commit.slice(0,9) === commit_start){
              metric = obj.metric;
              commit = obj.commit;
              config = obj.config;
              break;
            }
          }
        }

        // We need metric, file, config, and commit for this data point
        var url = metric + "/" + config + '/' + filename + '/' + commit + '/' + '';

        $('#' + configdiv).dialog('close');
        $('#' + configdiv).html("Loading...");
        $('#' + configdiv).load("/config-info/" + url);
        $('#' + configdiv).dialog('open');
      }
    }
  }
}


// -----------------------------------------------------------------------------
function drawTimeSeriesChart(data_in, chartdiv, dialogdiv, tablediv, configdiv, statusdiv) {
  var numCurves = data_in.length;
  var view;
  var data2;

  data_in1 = data_in[0].response;

  for (var j = 0; j < data_in1.data.length; j++) {
    data_in1.data[j][0] = new Date(data_in1.data[j][0][0], data_in1.data[j][0][1],
                              data_in1.data[j][0][2], data_in1.data[j][0][3],
                              data_in1.data[j][0][4], data_in1.data[j][0][5]);
  }

  var data1 = new google.visualization.DataTable();
  var to_graph = {}
  data1.addColumn('datetime', 'Datetime');
  data1.addColumn('string', 'Commit Id');
  data1.addColumn('number', data_in[0].series_name.label);
  data1.addRows(data_in1.data);
  data1.sort(0);
  view = new google.visualization.DataView(data1);

  for (var i = 1; i < numCurves; i++){
    data_in2 = data_in[i].response.data;

    for (var j = 0; j < data_in2.length; j++) {
      data_in2[j][0] = new Date(data_in2[j][0][0], data_in2[j][0][1],
                                data_in2[j][0][2], data_in2[j][0][3],
                                data_in2[j][0][4], data_in2[j][0][5]);
    }
    data2 = new google.visualization.DataTable();
    data2.addColumn('datetime', 'Datetime');
    data2.addColumn('string', 'Commit Id');
    data2.addColumn('number',  data_in[i].series_name.label);
    data2.addRows(data_in2);
    data2.sort(0);
    leftColumns = range(2, i + 1);
    view = new google.visualization.data.join(view, data2, 'full', [[0,0], [1,1]], leftColumns, [2]);
  }

  chart_view = new google.visualization.DataView(view);
  // We filter out the 2nd column (commit data) to display
  chart_view.hideColumns([1]);

  chartOptions['title'] ='Time Series';
  chartOptions['vAxis'] = {title: data_in1.yaxis};
  chartOptions['hAxis'] = {title: 'Date'};
  chartOptions['pointSize'] = 2;
  chartOptions['lineWidth'] = 1;
  chartOptions['interpolateNulls'] = true;

  var tableOptions = {width: 'automatic'};

  var chart = new google.visualization.LineChart(document.getElementById(chartdiv));
  chart.draw(chart_view, chartOptions);

  if (tablediv) {
    var table = new google.visualization.Table(document.getElementById(tablediv));
    table.draw(view, tableOptions);
  }

  if (!dialogdiv) {
    $(window).resize(function() {
      chart.draw(chart_view, chartOptions);
    });
  }

  // Add our selection handler.
  if (configdiv && !dialogdiv) // This chart is never used by Commit Viewer,
                               // but just to be safe ...
    google.visualization.events.addListener(chart, 'select', selectHandler);

  // The selection handler.
  // Loop through all items in the selection and concatenate
  // a single message from all of them.
  var selected_commits = Array();
  function selectHandler() {
    var selection = chart.getSelection();
    if(!selection.length)
      selected_commits.length = 0;
    else
    for (var i = 0; i < selection.length; i++) {
      var item = selection[i];
      if (item.row != null && item.column != null) {
        selected_commits.push(view.getFormattedValue(item.row, 1));
      }
    }

    if (selected_commits.length){
      $("#commitInfo").html("Loading...");
      $("#commitInfo").load("/commit-info/"+selected_commits.join(",")+"/");
      $('#commitInfo').dialog('open');
    }
    else {
      $('#commitInfo').dialog('close');
    }
  }
  $("#commitInfo").bind("dialogclose", function(event, ui) {
    selected_commits.length = 0;
    chart.setSelection();
  });

}


////////////////////////////////////////////////////////////////////////////////
// ONLY FOR INDEX.HTML - the divs referenced here are all applicable for index.html
//------------------------------------------------------------------------------
function StatisticFiller() {
  // This function is reponsible for filling a table with the composite metrics
  // for each file

  // We ask the backend for a chart to display - based on metric, fileset,
  // config, and commit selected.

  var metrics = MetricState.join(",");
  var configs = ConfigState.join(",");
  var files = FileState.filter(removeParents).join(",");
  var commits = CommitState.filter(removeParents).join(",");
  var compurl = "/average-improvement/" + metrics + "/" + configs + "/" + files + "/" + commits;

  if ((MetricState.length * ConfigState.length *
      FileState.filter(removeParents).length *
      CommitState.filter(removeParents).length) == 0) {
    $("#commitInfo").dialog('close');
    $("#configInfo").dialog('close');
    $('#tabs11').html("Please select a valid run.");
    $('#tabs2').html("");
    $('#githistory').html("");
    $('#chartdiv').html("");
    return;
  }

  $('#tabs11').html("Loading...");
  $('#chartdiv').html("");

  // What baseline should the curves be compared to?
  $.ajax({
    type: "GET",
    url: compurl,
    success: function(response){
      if (response.data.length > 0) {
        ImprovementTable(response);
      }
    },
  });

}

// -----------------------------------------------------------------------------
function ImprovementTable(data_in) {
  var baseline = data_in.baseline
  data_in = data_in.data

  numCol = data_in.length;
  var data1 = new google.visualization.DataTable();
  var view;
  var data2;

  var formatter = new google.visualization.NumberFormat(
      {suffix: '%', fractionDigits: 3});

  var formatter2 = new google.visualization.TableColorFormat();
  formatter2.addRange("OVERALL", "OVERALM", '#999');

  // We fill our table
  data1.addColumn('string', 'Filename');
  data1.addColumn('number', data_in[0].col);
  data1.addRows(data_in[0].data);
  formatter.format(data1, 1);
  formatter2.format(data1, 0);

  // Make it a chart
  view = new google.visualization.DataView(data1);

  for (var i = 1; i < numCol; i++){
    data2 = new google.visualization.DataTable();
    data2.addColumn('string', 'Filename');
    data2.addColumn('number',  data_in[i].col);
    data2.addRows(data_in[i].data);
    formatter.format(data2, 1);
    formatter2.format(data1, 0);

    // A list of numbers from 1 to i
    leftColumns = range(1, i);

    // Join the two tables into one view
    view = new google.visualization.data.join(view, data2, 'full', [[0,0]], leftColumns, [1]);
  }
  var tableOptions = {width: 'automatic', allowHtml: 'true'};

  var table = new google.visualization.Table(document.getElementById("tabs11"));
  google.visualization.events.addListener(table, 'select', selectHandler);
  google.visualization.events.addListener(table, 'sort', headerHandler);
  google.visualization.events.addListener(table, 'ready', setupHandler);
  table.draw(view, tableOptions);

  var commitstr = CommitState.join(',');
  var commits = CommitState.filter(removeParents).join(",");
  $("#githistory").html("Loading...");
  $("#githistory").load("/history/"+baseline+","+commits);

  $('#container').show();
  $("#commitInfo").dialog('close');
  $("#configInfo").dialog('close');
  $('#chartdiv').html("Please select a file (or files) to view graph.");
  $('#status').html("");

  // We add some bindings to allow for selecting rows of the table
  // Add our selection handler

  function setupHandler() {
    // We now select any default values (in FileTableState)
    if (!tableinit)
      // If we are not preselecting anything.
      return;

    var numRows = data_in[0].data.length;
    var rows_to_select = [];
    for (var i = 0; i < numRows; i++) {
      for (var j = 0; j < FileTableState.length; j++) {
        if (view.getValue(i, 0) === FileTableState[j])
          rows_to_select.push({row: i});
      }
    }
    tableinit = false;
    table.setSelection(rows_to_select);
    selectHandler();
  }

  // The selection handler
  // Loop through all items in the selection and add them to FileTableState
  function selectHandler() {

    FileTableState.length = 0; // Clear out the global array

    var selection = table.getSelection();
    for (var i = 0; i < selection.length; i++) {
      var item = selection[i];

      // We get the name of the file selected
      if (item.row != null && item.column != null) {
        var str = view.getFormattedValue(item.row, item.column);
      } else if (item.row != null) {
        var str = view.getFormattedValue(item.row, 0);
      } else if (item.column != null) {
        var str = view.getFormattedValue(0, item.column);
      }

      FileTableState.push(str);
    }

    ChartFiller(baseline);
    if (selection.length == 0) {
      // We get rid of tables that are no longer relevant
      $("#commitInfo").dialog('close');
      $("#configInfo").dialog('close');
      $('#chartdiv').html("Please select a file (or files) to view graph.");
      $('#status').html("");
      $('#tabs2').html("");
    }
  }

  // Called when a header is clicked (not a row)
  function headerHandler(event) {
    if (commitstr[0] === '~') {
      return; // We return early when we are doing a time series
    }
    $("#commitInfo").dialog('close');
    $("#commitInfo").html("Loading...");
    $("#commitInfo").load("/commit-info/"+commitstr+"/"+baseline);
    $('#commitInfo').dialog('open');
  }
}
