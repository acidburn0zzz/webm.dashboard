// This file contains several functions that are commonly used across the
// dashboard

function is_distortion(metric)
{
  return (['CxFPS', 'DxFPS'].indexOf(metric) == -1);
};

function range(start, end)
{
  var foo = [];
  for (var i = start; i <= end; i++)
    foo.push(i);
  return foo;
}

function FetchMetric(metricurl, series_name, responses) {
  var split_lst = metricurl.split('/');
  $.ajax({
    type: "GET",
    url: metricurl,
    success: function(response){
      responses.push({response: response, series_name: series_name,
                      metric: split_lst[2], config: split_lst[3],
                      filename: split_lst[4], commit: split_lst[5]});
    },
    error: function(xhr, ajaxOptions, thrownError) {
        // Nothing for now
    },
  });
}
