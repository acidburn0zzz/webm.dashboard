// This file contains some simple methods to handle creation and manipulation of
// jstree objects

// The default configuration for checkboxes.
function treeConfig(TreeModel) {
  return {
    core : {
      animation : 0,
    },
    themes : {
      dots : false,
      icons : false,
    },
    json_data : {
      data : TreeModel
    },
    "plugins" : ["themes", "json_data", "ui", "checkbox", "sort"],
    "checkbox" : {
      two_state: true,
      real_checkboxes: true,
      real_checkboxes_names: function (n) {
        var nid = 0;
        $(n).each(function (data) {
          nid = $(this).attr("nodeid");
        });
        return (["check_" + nid, nid]);
      },
    },
  }
};

// -----------------------------------------------------------------------------
// A function that is called whenever any tree is updated
function TreeHandler() {
  var txt = document.getElementById("tabs1");
  txt.innerHTML = MetricState.toString() + ConfigState.toString() +
                  FileState.toString() + CommitState.toString();


  // We put together a url for drilldown - separated by commas (no spaces)
  var metrics = MetricState.join(",");
  var configs = ConfigState.join(",");
  var files = FileState.join(",");
  var commits = CommitState.join(",");

  $.ajax({
    type: "GET",
    url: "/drilldown/" + metrics + "/" + configs + "/" + files + "/" + commits,
    success: function(response){
      // $("#result").text(response); // for debugging;
      drillArray = eval(response);
      newMetricList = drillArray[0];
      newConfigList = drillArray[1];
      newFileList = drillArray[2];
      newCommitList = drillArray[3];

      // Now we update all the trees
      oldMetricState = MetricState.slice(0);
      oldConfigState = ConfigState.slice(0);
      oldFileState = FileState.slice(0);
      oldCommitState = CommitState.slice(0);

      // TODO (rlawler): Do we need to load all trees for each request?
      resetTree("#treeView1", newMetricList, MetricState, oldMetricState);
      resetTree("#treeView2", newConfigList, ConfigState, oldConfigState);
      resetTree("#treeView3", newFileList, FileState, oldFileState);
      resetTree("#treeView4", newCommitList, CommitState, oldCommitState);
    }
  });

  ChartFiller();
};

// ---------------------------------------------------------------------------
function initTree(divName, ContentsList, StateList){
  // Triggered when a name is clicked, rather than a checkbox
  // simply calls code below
  $(divName).jstree(treeConfig(ContentsList));
  $(divName).bind("select_node.jstree", function (event, data) {
    // `data.rslt.obj` is the jquery extended node that was clicked
    data.inst.change_state(data.rslt.obj);
    $(divName).trigger('change_state.jstree', data);
  });

  // The code to recognize a state change - when a checkbox changes
  $(divName).bind("change_state.jstree", function (e, d) {
    var tagName = d.args[0].tagName;
    var refreshing = d.inst.data.core.refreshing;
    if ((tagName == "A" || tagName == "INS") &&
      (refreshing != true && refreshing != "undefined")) {
      // If there is a state change, we modify the state Array
      StateList.length = 0;
      // Get all selected nodes (by name)
      $(divName).jstree("get_checked").each(function(key, value){
        // We strip the 2 leading characters (ascii code 160)
        val = $(value).children("a").text();
        StateList.push(val.slice(2, val.length));
      });
      TreeHandler();
    }
  });

};

// Called when trees are updated (via drilldown)
function resetTree(divName, ContentsList, StateList, OldStateList) {
  currentTree = $.jstree._reference(divName);
  var openList = [];

  if (currentTree){
    node = currentTree._get_node(currentTree.get_container());
    node = currentTree._get_next(node);
    while (node) {
      if (currentTree.is_open(node)){
        nodeName = node.children("a").text();
        openList.push(nodeName);
      }
      node = currentTree._get_next(node);
    }
  }

  $(divName).empty();
  initTree(divName, ContentsList, StateList);

  // Make sure we recheck the appropriate boxes and open the right nodes
  $(divName).bind("loaded.jstree", function () {
    currentTree = $.jstree._reference(divName);
    // we reopen the right nodes
    node = currentTree._get_node(currentTree.get_container());
    node = currentTree._get_next(node);
    while (node) {
      nodeName = node.children("a").text();
      if (nodeName.length < 1)
        break;
      if (openList.indexOf(nodeName) != -1) {
        currentTree.open_node(node);
      }
      node = currentTree._get_next(node);
    }

    // we step through the tree to re-check nodes
    node = currentTree._get_node(currentTree.get_container());
    node = currentTree._get_next(node);
    while (node) {
      nodeName = node.children("a").text();
      nodeName = nodeName.slice(2, nodeName.length);
      if (nodeName.length < 1)
        break;
      if (OldStateList.indexOf(nodeName) != -1) {
        $(divName).jstree("check_node", node);
      }
      node = currentTree._get_next(node);
    }
  });
};

// ---------------------------------------------------------------------------
// Handle the bindings of a tree in the given div with the given global state
function initTrees(){

  // Clears out all trees when a button is clicked
  // TODO (rlawler): Figure out a way to avoid duplicating these calls
  $("#clearer").click(function(){
    $("#treeView1").jstree("uncheck_all");
    MetricState = [];
    $("#treeView2").jstree("uncheck_all");
    ConfigState = [];
    $("#treeView3").jstree("uncheck_all");
    FileState = [];
    $("#treeView4").jstree("uncheck_all");
    CommitState = [];
    TreeHandler();
  });

  // We load the initial trees with all options
  TreeHandler();

};

// We create the trees and the tabs to start.
$(document).ready(function () {

  // Note: remove height to turn off vertical animation
  $( "#tabs" ).tabs({ fx: { height: 'toggle', opacity: 'toggle'} });
  initTrees();
});



