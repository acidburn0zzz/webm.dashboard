// This file contains some simple methods to handle creation and manipulation of
// jstree objects

// Here is some test data.
var MetricList = ["Time(us)", "AVGPsnr", "GLPsnrP", "target_bitrate", "DxFPS", "GLBPsnr", "VPXSSIM", "CxFPS", "Bitrate", "AVPsnrP"];

var ConfigList = ["tmp", "rt6", "good"];

var FileList = ["30MBljXxg3M_640x360_545kb_500.ivf", "ykSZMaZl2fY_854x480_1321kb_500.ivf", "iurBQbs8iy8_640x360_545kb_500.ivf", "mad900_cif.y4m", "v60oNUoHBYM_640x360_545kb_500.ivf", "ykSZMaZl2fY_1920x1080_3622kb_500.ivf", "tfZ5mvf8g68_1920x1080_3622kb_500.ivf", "jwPxfIeHkYc_1280x720_2046kb_500.ivf", "x5DyBkYKqnM_1280x720_2046kb_500.ivf", "JsRtH7JaLuI_854x480_1321kb_500.ivf", "dP15zlyra3c_854x480_1321kb_500.ivf", "j5-yKhDd64s_1920x1080_3622kb_500.ivf", "YLDbGqJ2KYk_640x360_545kb_500.ivf", "FNkTFao5_UI_854x480_1321kb_500.ivf", "YHe3ag3i8v8_1280x720_2046kb_500.ivf", "ykSZMaZl2fY_1280x720_2046kb_500.ivf", "nTDNLUzjkpg_1280x720_2046kb_500.ivf", "rZseBpPufLI_640x360_545kb_500.ivf", "dP15zlyra3c_640x360_545kb_500.ivf", "gNYZH9kuaYM_1280x720_2046kb_500.ivf", "idLG6jh23yE_854x480_1321kb_500.ivf", "tempete_cif.y4m", "flower_cif.y4m", "3hgcy6bsg4g_1280x720_2046kb_500.ivf", "Oe3St1GgoHQ_1280x720_2046kb_500.ivf", "7zxxUU3OQ7o_854x480_1321kb_500.ivf", "nTDNLUzjkpg_640x360_545kb_500.ivf", "FNkTFao5_UI_1280x720_2046kb_500.ivf", "tnOjNtjVM-Q_640x360_545kb_500.ivf", "JsRtH7JaLuI_640x360_545kb_500.ivf", "Cl5Pfc5TyO0_854x480_1321kb_500.ivf", "idLG6jh23yE_1280x720_2046kb_500.ivf", "gNYZH9kuaYM_640x360_545kb_500.ivf", "3hgcy6bsg4g_854x480_1321kb_500.ivf", "RM9o4VnfHJU_854x480_1321kb_500.ivf", "ice_cif.y4m", "qybUFnY7Y8w_1280x720_2046kb_500.ivf", "1HusfmSh_xE_640x360_545kb_500.ivf", "nCgQDjiotG0_854x480_1321kb_500.ivf", "txqiwrbYGrs_640x360_545kb_500.ivf", "washdc_422_cif.y4m", "RM9o4VnfHJU_1280x720_2046kb_500.ivf", "crew_cif.y4m", "LjMkNrX60mA_640x360_545kb_500.ivf", "idLG6jh23yE_640x360_545kb_500.ivf", "cRdxXPV9GNQ_854x480_1321kb_500.ivf", "071KqJu7WVo_640x360_545kb_500.ivf", "owGykVbfgUE_1280x720_2046kb_500.ivf", "Cl5Pfc5TyO0_640x360_545kb_500.ivf", "b_AF99dZEow_1280x720_2046kb_500.ivf", "x5DyBkYKqnM_854x480_1321kb_500.ivf", "tfZ5mvf8g68_854x480_1321kb_500.ivf", "nCgQDjiotG0_640x360_545kb_500.ivf", "qybUFnY7Y8w_640x360_545kb_500.ivf", "3hgcy6bsg4g_640x360_545kb_500.ivf", "4pH6TNcpt58_1280x720_2046kb_500.ivf", "4pH6TNcpt58_640x360_545kb_500.ivf", "hZxJzhIPTTg_1280x720_2046kb_500.ivf", "LjMkNrX60mA_854x480_1321kb_500.ivf", "tfZ5mvf8g68_1280x720_2046kb_500.ivf", "LMSC0hE1nkU_640x360_545kb_500.ivf", "dP15zlyra3c_1280x720_2046kb_500.ivf", "7zxxUU3OQ7o_1920x1080_3622kb_500.ivf", "uBFfWd_-1MA_640x360_545kb_500.ivf", "mobile_cif.y4m", "x5DyBkYKqnM_640x360_545kb_500.ivf", "071KqJu7WVo_1280x720_2046kb_500.ivf", "highway_cif.y4m", "txqiwrbYGrs_854x480_1321kb_500.ivf", "nTBEsPII8FI_640x360_545kb_500.ivf", "lEXZ2hfD3bU_1920x1080_3622kb_500.ivf", "7zxxUU3OQ7o_1280x720_2046kb_500.ivf", "tfZ5mvf8g68_640x360_545kb_500.ivf", "cRdxXPV9GNQ_1280x720_2046kb_500.ivf", "hIs3k4iKFjM_1280x720_2046kb_500.ivf", "lEXZ2hfD3bU_640x360_545kb_500.ivf", "uQITWbAaDx0_1920x1080_3622kb_500.ivf", "bus_cif.y4m", "uBFfWd_-1MA_1280x720_2046kb_500.ivf", "j5-yKhDd64s_854x480_1321kb_500.ivf", "nTDNLUzjkpg_854x480_1321kb_500.ivf", "hIs3k4iKFjM_854x480_1321kb_500.ivf", "RM9o4VnfHJU_1920x1080_3622kb_500.ivf", "lEXZ2hfD3bU_1280x720_2046kb_500.ivf", "YLDbGqJ2KYk_854x480_1321kb_500.ivf", "ykSZMaZl2fY_640x360_545kb_500.ivf", "nTBEsPII8FI_854x480_1321kb_500.ivf", "silent_cif.y4m", "uQITWbAaDx0_1280x720_2046kb_500.ivf", "gNYZH9kuaYM_854x480_1321kb_500.ivf", "LjMkNrX60mA_1280x720_2046kb_500.ivf", "RM9o4VnfHJU_640x360_545kb_500.ivf", "nCgQDjiotG0_1280x720_2046kb_500.ivf", "dP15zlyra3c_1920x1080_3622kb_500.ivf", "idLG6jh23yE_1920x1080_3622kb_500.ivf", "jwPxfIeHkYc_854x480_1321kb_500.ivf", "30MBljXxg3M_854x480_1321kb_500.ivf", "4pH6TNcpt58_854x480_1321kb_500.ivf", "j5-yKhDd64s_640x360_545kb_500.ivf", "qybUFnY7Y8w_1920x1080_3622kb_500.ivf", "1HusfmSh_xE_854x480_1321kb_500.ivf", "v60oNUoHBYM_854x480_1321kb_500.ivf", "JM0v4M7WrS8_640x360_545kb_500.ivf", "30MBljXxg3M_1280x720_2046kb_500.ivf", "stefan_cif.y4m", "cRdxXPV9GNQ_640x360_545kb_500.ivf", "uBFfWd_-1MA_854x480_1321kb_500.ivf", "b_AF99dZEow_640x360_545kb_500.ivf", "x5DyBkYKqnM_1920x1080_3622kb_500.ivf", "071KqJu7WVo_1920x1080_3622kb_500.ivf", "coastguard_cif.y4m", "LMSC0hE1nkU_854x480_1321kb_500.ivf", "foreman_cif.y4m", "iurBQbs8iy8_854x480_1321kb_500.ivf", "hall_monitor_cif.y4m", "YHe3ag3i8v8_854x480_1321kb_500.ivf", "news_cif.y4m", "071KqJu7WVo_854x480_1321kb_500.ivf", "Oe3St1GgoHQ_640x360_545kb_500.ivf", "LMSC0hE1nkU_1280x720_2046kb_500.ivf", "LMSC0hE1nkU_1920x1080_3622kb_500.ivf", "nTBEsPII8FI_1280x720_2046kb_500.ivf", "qybUFnY7Y8w_854x480_1321kb_500.ivf", "bridge-close_cif.y4m", "lEXZ2hfD3bU_854x480_1321kb_500.ivf", "hIs3k4iKFjM_640x360_545kb_500.ivf", "tnOjNtjVM-Q_854x480_1321kb_500.ivf", "owGykVbfgUE_640x360_545kb_500.ivf", "Oe3St1GgoHQ_854x480_1321kb_500.ivf", "7zxxUU3OQ7o_640x360_545kb_500.ivf", "YHe3ag3i8v8_640x360_545kb_500.ivf", "hZxJzhIPTTg_854x480_1321kb_500.ivf", "FNkTFao5_UI_640x360_545kb_500.ivf", "hIs3k4iKFjM_1920x1080_3622kb_500.ivf", "1HusfmSh_xE_1280x720_2046kb_500.ivf", "b_AF99dZEow_854x480_1321kb_500.ivf", "football_422_cif.y4m", "uQITWbAaDx0_854x480_1321kb_500.ivf", "hZxJzhIPTTg_640x360_545kb_500.ivf", "uQITWbAaDx0_640x360_545kb_500.ivf", "4pH6TNcpt58_1920x1080_3622kb_500.ivf", "owGykVbfgUE_854x480_1321kb_500.ivf", "j5-yKhDd64s_1280x720_2046kb_500.ivf", "jwPxfIeHkYc_640x360_545kb_500.ivf", "paris_cif.y4m", "GsbHPyNHKwQ_640x360_545kb_500.ivf", "JM0v4M7WrS8_854x480_1321kb_500.ivf", "akiyo_cif.y4m"];

var CommitList = ["ce328b855f951e5a9fd0d9d92df09d65ea0d8be9", "7fed3832e7703628cd5ac595c4cb1f9c0ee5c7ce", "815e1e9fe4ede2bc8e0e9b58cc58f84822a02f89", "9c8ad79fdc8af25988dd071703a51d379f2849ce", "eb8b4d9a99146d9494d8d28402deb1fb4fe3202f", "9dc95b0a122b5f519117c0be6525d980c32f507e", "fc6ce744a606872c6d8001deabaab0b819326214", "a31a58d19a89a75e15f17ec48235b9ac742d87bc", "46639567a02e4fda20a93a3ff12a2bf41c8dc86c", "0a49747b01401900272ccf0dfbb6481429707ad5", "79327be6c729ed73cb339630b0ab770e3c54a4ab", "bead039d4d316092bca20e62df001f92a86067d2", "fd9df44a054260aef0aaf3d8acda61d35e3b001b", "c7ca3808322e4ff6a26d2184137c1dfa94f97024", "4ce6928d5b048ce5f82a97cd3d56267432fdc634", "9aa2bd8a036b09b862f297a6ab56264233677451", "05239f0c41780ee22ba7273f03edf6e7210ed58b", "1fae7018a87611c594b413a168a42c835740db2e", "811d0ff20977968f1958314cb96f04181c2f3e61", "3245d463c4a3e44185722c1e108d20576cd3f9f8", "f212a98ee7ebafefe02714a6d4b423080b211275", "3c9dd6c3ef2ead74641ceb56366b5d034e69c7fd", "cd0bf0e40720e5d6924e319096160dd48362708f", "6614563b8f851adebdb25cc9ffca28b871e34616", "a91b42f0229ad9b9809b8245a92155154d6164f8", "8767ac3bc790467ed342850c52ac28bba6d777ef", "d75eb7365357ec45626452756308d4327fa66911", "405499d835a4a01fe09bc5ea01a2e7e77aaef8da", "eb16f00cf25e54f08c5a9ec25a8780ca708a2c3a", "15ea268d629544885db363dfb5d1609404d5e9b0", "d283d9bb307fe2e93107a4271bb984d8cd6c6736", "4fbd0227f5a22183f880fcf0cf93f3799c65c37b", "8b0cf5f79d4c3812ae3d23f2ddc124afcf79b070", "062864f4cc2179b6f222ae337538c18bfd08037a", "a609be5633144e2538752c698da34c1bde90820f", "63fc44dfa5c459c3736498f1f6e618cff3c56eeb", "1689564bb5c0f03bb2f35244bf40bcf58c9fec35", "510e0ab4679ef76f1d7c5ed1b792f8012444f0cc", "458f4fedd2d32ca5b7185df44656c4ccba2bae8d", "ad479a9b3d510617f1400d2b168bd1594d422d67", "27000ed6d9bf6cdb1c7aa3d55e6751b2c4de39c0", "7a49accd0b65453057762929efc7eed93deba043", "538865dfa516a3a08aa63ee7eab49197d326898a", "a87fb0da5bbe6c7367f8364934b414466625a96f", "4ab3175b123b6804029efc14f98d87c491e130d1", "71a7501bcf6ada5068d102c03ae597023e986538", "de368fd0b5fe5d749afcf7b09273abf57f3d1fa6", "0c483d6b683fa4313cf7dadf448a707fe32714a4", "e6df50031e63d812c841a40d2522c487f78ed8ce", "4645c89889aba53a1665934a42f082a23832f493", "6b6f367c3d25bdd87f80a8e5b5380963733c6f0a", "5bc7b3a68e8c9098d8c8b21dae7c5cabde030e46", "db67dcba6a0f10b79b261b9f7ba084b3d937c2bc", "dfa9e2c5ea4a4282d931e382c327fc2d149ebcf8", "404e998eb7dafe370d2208869be29f9fbcaafd49", "f357e5e2f7e20af9343528add52fda63c948367f", "55c3963c8828552b16473f0c8df370d501f27922", "db8f0d2ca90929ac3e6fb63ef05651a71dd574ba", "69aad3a7206161a0eac854ed1fcfd12bae31fa43", "2f2302f8d5e41862e517f34544f9bcd8c8edeaad", "d9f898ab6dbf2e5f9f031b808c13c204254c0a21", "d889035fe6802b64567c2ed250c1dff0eb377acf", "bdc9262a6d16e222c1a25735b84b4c79920ac4bb", "52ec78be7d6c8f103e63a76e3e14ded48ccd5cd7", "d7e09b6adad349b6efab2b707fb2c7670b887fc8", "b1bfd0ba8715e58631aaa253540838387fb895bd", "222c72e50f0118600cd07f4888ea7182f12666c2", "6ea5bb85cd1547b846f4c794e8684de5abcf9f62", "d1abe62d1c5455b32631688d61043f0fd2df44e7", "120a46402620d0cac84e69f02166667ffb34a650", "0030303b6949ba2d3391f3ae400213acc0e80db7", "77119a5cd84ec70a961061ba63a8f093a0d29874", "23d68a5f3004960d1a50702e6d76323d5ea0a721", "6b2792b0e0189fa3f7d75b2ac885417606225656", "e5aaac24bb9f06ccd44505b0af6116b9ca3bd73f", "112bd4e2b48317a85ba93c513ef79528aca1bb71", "fea3556e20f63ed1a03daa45804f724e70705aa0", "05bde9d4a4b575aaadd9b6f5d0f82826b1cb4900", "4be062bbc3466cfd542a7485f5a2a8eadac4f24e", "2cbd9620880a4335aef7e4b6befe1d334893930f", "5d1d9911cbf77f2eb4a1bc30179c0256f0304e12", "33d9ea547120529cb385a8c8d066b916f59aec12"];

MetricList.sort();
ConfigList.sort();
FileList.sort();
CommitList.sort();


// The configuration for checkboxes.
function treeConfig(TreeModel) {
  return {
    core : {},
    themes : {
      dots : false,
      icons : false,
    },
    json_data : {
      data : TreeModel
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
  }
};


// A function that is called whenever any tree is updated
function TreeHandler() {
  var txt = document.getElementById("tabs1");
  txt.innerHTML = MetricState.toString() + ConfigState.toString() +
                  FileState.toString() + CommitState.toString();
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


// ---------------------------------------------------------------------------
// Handle the bindings of a tree in the given div with the given global state
function initTrees(){

  // Clears out all trees when a button is clicked
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

  initTree("#treeView1", MetricList, MetricState);
  initTree("#treeView2", ConfigList, ConfigState);
  initTree("#treeView3", FileList, FileState);
  initTree("#treeView4", CommitList, CommitState);

};

// We create the trees and the tabs to start.
$(document).ready(function () {
  $( "#tabs" ).tabs({ fx: { height: 'toggle', opacity: 'toggle'} });
  initTrees();
});



