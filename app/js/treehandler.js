// This file contains some simple methods to handle creation and manipulation of
// jstree objects

// Some global variables to help 
var num = 0;
var state1 = new Array(); // Contains the info of all things that are selected 
                          // via checkbox in tree1
var state2 = new Array(); // All the things selected via checkbox in tree2
var state3 = new Array(); // tree3 data


// Here is some test data. 
var treeModel = [
{"data":"Confirm Application","attr":{"id":"10"},"children":null},{"data":"Things","attr":{"id":"20"},"children":[{"data":"Thing 1","attr":{"id":"21"},"children":null},{"data":"Thing 2","attr":{"id":"22"},"children":null},{"data":"Thing 3","attr":{"id":"23"},"children":null},{"data":"Thing 4","attr":{"id":"24"},"children":[{"data":"Thing 4.1","attr":{"id":"241"},"children":null},{"data":"Thing 4.2","attr":{"id":"242"},"children":null},{"data":"Thing 4.3","attr":{"id":"243"},"children":null}]}]},{"data":"Colors","attr":{"id":"40"},"children":[{"data":"Red","attr":{"id":"41"},"children":null},{"data":"Green","attr":{"id":"42"},"children":null},{"data":"Blue","attr":{"id":"43"},"children":null},{"data":"Yellow","attr":{"id":"44"},"children":null}]}];


// The configuration for checkboxes.
var treeConfig = {
  core : {},
  themes : {
    dots : false,
    icons : false, 
  },
  json_data : {
    data : treeModel
  },
  "plugins" : ["themes", "json_data", "ui", "checkbox"], 
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
};

////////////////////////////////////////////////////////////////////////////////
// A function to bind tree operations to events
function initTree(){

  // Clears out all trees
  $("#clearer").click(function(){
    $("#treeView1").jstree("uncheck_all");
    state1 = []; // empty it out
    document.getElementById('tabs1').innerHTML = "<p>" + state1.toString() + "</p>";
    $("#treeView2").empty();
    state2 = [];
    document.getElementById('tabs2').innerHTML = "<p>" + state2.toString() + "</p>";
    $("#treeView3").empty();
    state3 = [];
  });


  // Triggered when a name is clicked, rather than a checkbox
  // simply calls code below
  $("#treeView1").bind("select_node.jstree", function (event, data) {
    // `data.rslt.obj` is the jquery extended node that was clicked
    data.inst.change_state(data.rslt.obj);
    $("#treeView1").trigger('change_state.jstree', data); // yay!
  });

  // The code to recognize a state change - when a checkbox changes
  $("#treeView1").bind("change_state.jstree", function (e, d) {
    var tagName = d.args[0].tagName;
    var refreshing = d.inst.data.core.refreshing;
    if ((tagName == "A" || tagName == "INS") &&
      (refreshing != true && refreshing != "undefined")) {

      // If there is a state change, we modify the state Array
      state1 = [];

      // Get all selected nodes (by name)
      $("#treeView1").jstree("get_checked").each(function(key, value){
        state1.push($(value).children("a").text());
      });

      document.getElementById('tabs1').innerHTML = "<p>" + state1.toString() + "</p>";

      // We add or remove the second tree as necessary
      if (state1.length > 0){

        if (state2.length == 0) {
          $("#treeView2").jstree(treeConfig);
          $("#treeView2").bind("change_state.jstree", function (e, d) {
            var tagName = d.args[0].tagName;
            var refreshing = d.inst.data.core.refreshing;
            if ((tagName == "A" || tagName == "INS") &&
              (refreshing != true && refreshing != "undefined")) {

              state2 = [];

              $("#treeView2").jstree("get_checked").each(function(key, value){
                state2.push($(value).children("a").text());
              });

              document.getElementById('tabs2').innerHTML = "<p>" + state2.toString() + "</p>";

              // We add or remove the third tree as necessary
              if (state2.length > 0){

                if (state3.length == 0) {
                  $("#treeView3").jstree(treeConfig);
                  $("#treeView3").bind("change_state.jstree", function (e, d) {
                    var tagName = d.args[0].tagName;
                    var refreshing = d.inst.data.core.refreshing;
                    if ((tagName == "A" || tagName == "INS") &&
                      (refreshing != true && refreshing != "undefined")) {
                      state3 = [];
                      $("#treeView3").jstree("get_checked").each(function(key, value){
                        state3.push($(value).children("a").text());
                      });
                    }
                  });
                  $("#treeView3").bind("select_node.jstree", function (event, data) {
                    data.inst.change_state(data.rslt.obj);
                    $("#treeView3").trigger('change_state.jstree', data); // yay!
                  });
                }
              }
              else { // We need to destroy the third tree (if exists)
                $("#treeView3").empty();
                state3 = [];
              }
            }
          });
          $("#treeView2").bind("select_node.jstree", function (event, data) {
            data.inst.change_state(data.rslt.obj);
            $("#treeView2").trigger('change_state.jstree', data); // yay!
          });

        }
      }
      else { // We need to destroy the second tree (if exists)
        $("#treeView2").empty();
        state2 = [];
        document.getElementById('tabs2').innerHTML = "<p>" + state2.toString() + "</p>";
        $("#treeView3").empty();
        statd3 = [];
      }
    }
  });

};


// We create tree1 and the tabs to start (others will be added as we go along).
$(document).ready(function () {
  $("#treeView1").jstree(treeConfig);
  $( "#tabs" ).tabs({ fx: { height: 'toggle', opacity: 'toggle'} });
  initTree();
});


