// search.js
// Contains utilities to search for a commit

function ChartFillerCaller(input) {
  input = input.split(',');
  var metric = input[0];
  var config = input[1];
  var filename = input[2];
  var commit = input[3];
  var baseline = input[4];

  $("#chartdialog").dialog('option', 'title', input.slice(0, 3).join(', '));
  ChartFiller_Commit(metric, config, filename, commit, baseline, 'chartdiv',
                     'chartdialog', null, 'configInfo', 'status');
}

function linkToBaseline(baseline) {
  // Note: with js, there is no way to force this to open in a new tab, rather
  // than a window.
  var url = "/commit_viewer/" + baseline;
  newWindow = window.open(url, '_blank');
  newWindow.focus();
}


function searchcommits(form){

  // We let all input checking happen on the backend
  var searchFor = form.query.value;
  url = "/commit_viewer/" + searchFor;
  window.location = url;
}

function linkToBaseline(baseline) {
  // Note: with js, there is no way to force this to open in a new tab, rather
  // than a window.
  var url = "/commit_viewer/" + baseline;
  newWindow = window.open(url, '_blank');
  newWindow.focus();
}

/* Insert into an html page with the following:
    <div class="modal hide fade" id="searchModal" tabindex="-1" role="dialog" aria-labelledby="searchModalLabel" aria-hidden="true">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-hidden="true">×</button>
        <h3 id="searchModalLabel">Search for Commits</h3>
      </div>
      <div class="modal-body">

      <div id="searchCommand" style="float:left">Please enter a commit to display, or an email to look for:</div>
      <form name="myform">
      <input type='text' name='query' />
      <input type='button' id="submitButton" value="Search" onClick="javascript: searchcommits(this.form)">
      </form>

      </div>
    </div>
*/
