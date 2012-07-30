// This file contains some simple methods to handle creation and manipulation of
// jstree objects

// Note: We specify the parent node's id with a preceeding underscore.
// This naming is taken care of on the server side.
function removeParents(element, index, array) {
  return (element[0] !== "_");
}

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

// We sort the commits in reverse chronological order
function commitTreeConfig(TreeModel) {
  return $.extend(treeConfig(TreeModel), {
    "plugins" : ["themes", "json_data", "ui", "checkbox", "sort", "contextmenu"],
    "sort": function (a, b) {
      return $(a).attr("date") < $(b).attr("date") ? 1 : -1;
    },
    "contextmenu" : {
      items: function ($node) {
        return {
          infoItem : {
            "label" : "Info",
            "submenu" :{
              dateItem : {
                "label" : ($node).attr("prettydate"),
              },
              authorItem : {
                "label" : "Author: " + ($node).attr("author"),
              },
            }
          },
          gotoItem : {
            "label" : "Go to gerrit",
            "action" : function(obj) {
              // We open the gerrit link in a new tab
              patchid = ($node).attr("id")
              if (patchid[0] === '_') { // This is a parent node
                children = ($node).children("ul").children("li");
                patchid = (children).attr("id");
              }
              var url = "https://gerrit.chromium.org/gerrit/#q," + patchid + ",n,z";
              window.open(url, '_blank');
              window.focus();
            },
            //"_disabled" : ($node).attr("id")[0] === "_" ? true : false,
            "_disabled" : false,
          },
        }
      }
    }

  })
};


// -----------------------------------------------------------------------------
// A function that is called whenever any tree is updated
function TreeHandler() {

  //var txt = document.getElementById("tabs11");
  //txt.innerHTML = MetricState.toString() + ConfigState.toString() +
  //                FileState.toString() + CommitState.toString();

  // To remove the parent node information before sending the request
  // We put together a url for drilldown - separated by commas (no spaces)
  var metrics = MetricState.join(",");
  var configs = ConfigState.join(",");
  var files = FileState.filter(removeParents).join(",");
  var commits = CommitState.filter(removeParents).join(",");
  var drillurl = "/drilldown/" + metrics + "/" + configs + "/" + files + "/" + commits;
  //$("#tabs11").text(drillurl);

  $.ajax({
    type: "GET",
    url: drillurl,
    success: function(response){
      //$("#result").text(response); // for debugging;
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

  StatisticFiller();
  //ChartFiller();
};

// ---------------------------------------------------------------------------
function initTree(divName, ContentsList, StateList){
  // Triggered when a name is clicked, rather than a checkbox
  // simply calls code below

  if (divName === "#treeView4") {
    // We handle sorting a bit differently on the commit tree
    $(divName).jstree(commitTreeConfig(ContentsList));
  }
  else {
    $(divName).jstree(treeConfig(ContentsList));
  }

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

      // We do a few extras when it is a parent node
      // if we are checking this, we adjust the children accordingly.
      var id, childrenCount, children;
      if (tagName == "A") {
        id = $(divName).jstree('get_selected').attr('id');
        children = $("#" + id).children("ul").children("li");
      }
      else {
        id = d.rslt.attr("id");
        children = d.rslt.children("ul").children("li");
      }
      var childrenCount = children.length;
      var checked = $("#" + id + ".jstree-checked").length!=0;

      if (checked && (childrenCount > 0)) {
        children.each(function() {
          $(divName).jstree("check_node", this);
        });
      }
      else if (!checked && (childrenCount > 0)) {
        children.each(function() {
          $(divName).jstree("uncheck_node", this);
        });
      }

      StateList.length = 0;
      // Get all selected nodes (by name)
      $(divName).jstree("get_checked").each(function(key, value){
        val = $(value).attr('id');
        StateList.push(val);
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
      nodeID = node.attr("id");
      if (OldStateList.indexOf(nodeID) != -1) {
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
  $("#resetbutton").click(function(){
    $("#treeView1").jstree("uncheck_all");
    MetricState = [];
    $("#treeView2").jstree("uncheck_all");
    ConfigState = [];
    $("#treeView3").jstree("uncheck_all");
    FileState = [];
    $("#treeView4").jstree("uncheck_all");
    CommitState = [];

    // We also clear out the appropriate tabs.
    $('#tabs11').html('Please select a valid run.');
    $('#tabs12').html('');
    $('#tabs2').html('');
    $('#tabs3').html('');

    TreeHandler();
  });

  // We load the initial trees with all options
  TreeHandler();

};

// We create the trees and the tabs to start.
$(document).ready(function () {

  // Note: remove height to turn off vertical animation
  //$( "#tabs" ).tabs({event: "mouseover", fx: { height: 'toggle', opacity: 'toggle'} });
  $( "#tabs" ).tabs({event: "mouseover", fx: {} });
  initTrees();

});



