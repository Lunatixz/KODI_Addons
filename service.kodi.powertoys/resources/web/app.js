(function(){
'use strict';

// ── Method catalogue ────────────────────────────────────────────────────
var METHODS=[
  {cat:'Video Library',items:[
    {m:'VideoLibrary.Scan',label:'Scan for new content',params:{}},
    {m:'VideoLibrary.Clean',label:'Clean library (remove unavailable)',params:{}},
    {m:'VideoLibrary.GetMovies',label:'List movies',params:{properties:['label','year','file']}},
    {m:'VideoLibrary.GetTVShows',label:'List TV shows',params:{properties:['label','file']}},
    {m:'VideoLibrary.RefreshMovie',label:'Refresh a movie',params:{movieid:1,ignorenfo:false}},
    {m:'VideoLibrary.RefreshTVShow',label:'Refresh a TV show',params:{tvshowid:1,ignorenfo:false,refreshepisodes:true}},
    {m:'VideoLibrary.RemoveMovie',label:'Remove a movie',params:{movieid:1}},
    {m:'VideoLibrary.RemoveEpisode',label:'Remove an episode',params:{episodeid:1}},
    {m:'VideoLibrary.GetMovieDetails',label:'Get movie details',params:{movieid:1,properties:['title','rating','plot']}},
    {m:'VideoLibrary.GetTVShowDetails',label:'Get TV show details',params:{tvshowid:1,properties:['title','rating','plot']}}
  ]},
  {cat:'Audio Library',items:[
    {m:'AudioLibrary.Scan',label:'Scan music library',params:{}},
    {m:'AudioLibrary.Clean',label:'Clean music library',params:{}},
    {m:'AudioLibrary.GetArtists',label:'List artists',params:{properties:['artist']}},
    {m:'AudioLibrary.GetAlbums',label:'List albums',params:{properties:['title','artist']}}
  ]},
  {cat:'Input',items:[
    {m:'Input.ExecuteAction',label:'Execute a remote action',params:{action:'back'}},
    {m:'Input.ExecuteAction',label:'Take screenshot',params:{action:'screenshot'}},
    {m:'Input.SendText',label:'Send text input',params:{text:'Hello',done:true}},
    {m:'Input.ButtonEvent',label:'Send button press/release',params:{button:'left',keymap:'KB'}},
    {m:'Input.Click',label:'Click at coordinates',params:{x:960,y:540}},
    {m:'Input.Back',label:'Go back',params:{}},
    {m:'Input.Up',label:'Navigate up',params:{}},
    {m:'Input.Down',label:'Navigate down',params:{}},
    {m:'Input.Left',label:'Navigate left',params:{}},
    {m:'Input.Right',label:'Navigate right',params:{}},
    {m:'Input.Select',label:'Select / OK',params:{}},
    {m:'Input.Home',label:'Go home',params:{}},
    {m:'Input.Info',label:'Show info',params:{}},
    {m:'Input.ContextMenu',label:'Open context menu',params:{}},
    {m:'Input.Menu',label:'Open menu',params:{}}
  ]},
  {cat:'System',items:[
    {m:'System.Shutdown',label:'Shutdown Kodi',params:{}},
    {m:'System.Reboot',label:'Reboot Kodi',params:{}},
    {m:'System.Suspend',label:'Suspend / sleep',params:{}},
    {m:'System.Hibernate',label:'Hibernate',params:{}},
    {m:'System.Quit',label:'Quit Kodi',params:{}},
    {m:'System.GetProperties',label:'Get system properties',params:{properties:['system.version','system.friendlyname']}},
    {m:'System.EjectOpticalDrive',label:'Eject disc',params:{}}
  ]},
  {cat:'GUI',items:[
    {m:'GUI.ActivateWindow',label:'Open a window',params:{window:'videos'}},
    {m:'GUI.SetFullScreen',label:'Toggle fullscreen',params:{fullscreen:true}},
    {m:'GUI.ShowNotification',label:'Show notification',params:{title:'PowerToys',message:'Hello!'}},
    {m:'GUI.GetProperties',label:'Get GUI properties',params:{properties:['currentwindow','fullscreen']}}
  ]},
  {cat:'Files',items:[
    {m:'Files.GetSources',label:'List media sources',params:{media:'video'}},
    {m:'Files.GetDirectory',label:'Browse a folder',params:{directory:'/media/',media:'files',sort:{method:'label',order:'ascending'}}},
    {m:'Files.Download',label:'Download a file',params:{path:'/media/test.mkv',destination:'special://temp/test.mkv'}},
    {m:'Files.Copy',label:'Copy a file',params:{file:'a',destination:'b'}},
    {m:'Files.Move',label:'Move a file',params:{file:'a',destination:'b'}},
    {m:'Files.Delete',label:'Delete a file',params:{file:'/media/test.txt'}},
    {m:'Files.GetFileDetails',label:'Get file details',params:{file:'/media/test.mkv',properties:['size','lastmodified']}}
  ]},
  {cat:'Add-ons',items:[
    {m:'Addons.ExecuteAddon',label:'Run an add-on',params:{addonid:'plugin.video.example'}},
    {m:'Addons.OpenAddon',label:'Open an add-on',params:{addonid:'plugin.video.example'}},
    {m:'Addons.GetAddonDetails',label:'Get add-on details',params:{addonid:'plugin.video.example',properties:['name','version','summary']}}
  ]},
  {cat:'Profiles',items:[
    {m:'Profiles.LoadProfile',label:'Switch profile',params:{profile:'Master user',prompt:false}},
    {m:'Profiles.GetProfiles',label:'List profiles',params:{properties:['thumbnail','lockdate']}}
  ]},
  {cat:'Player',items:[
    {m:'Player.Open',label:'Play a media file',params:{file:'special://movies/example.mkv'}},
    {m:'Player.GetItem',label:'Get now playing info',params:{properties:['title','showtitle','season','episode']}}
  ]},
  {cat:'PowerToys',items:[
    {m:'PowerToys.Wake',label:'Wake all configured devices (WOL)',params:{}}
  ]},
  {cat:'Application',items:[
    {m:'Application.SetVolume',label:'Set volume',params:{volume:50}},
    {m:'Application.GetProperties',label:'Get app properties',params:{properties:['volume','muted','name']}},
    {m:'Application.Quit',label:'Quit Kodi',params:{}}
  ]},
  {cat:'Custom JSON-RPC',items:[
    {m:'__custom__',label:'Enter any JSON-RPC method…',params:{}}
  ]}
];

// ── Builder state ───────────────────────────────────────────────────────
var stack=[];

function $(id){return document.getElementById(id)}
function esc(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML}

// ── schema-driven param controls (IDs/enums from the live Kodi instance) ──
var ID_OPTS={movieid:'movies',tvshowid:'tvshows',episodeid:'episodes',seasonid:'seasons',
  artistid:'artists',albumid:'albums',addonid:'addons',directory:'sources',
  profile:'profiles',profileid:'profiles',playlistid:'playlists',playerid:'players'};
// curated fallbacks for value sets some Kodi builds do not enumerate via introspect
// (schema enums always win when present; Custom value... is always available)
var CURATED={
  sortmethod:['none','label','date','year','size','file','path','drive','checksum','smartplaylist',
    'ignorecase','codec','artistsortname','albumsortname','songsortname','sorttitle','tracknumber',
    'discnumber','duration','title','artist','albumartist','album','genre','dateadded','lastplayed',
    'count','random','spread','userrating','max','min'],
  sortorder:['ascending','descending'],
  media:['music','video','files','artists','albums','songs','images','videos'],
  action:['left','right','up','down','select','back','parentdir','previousmenu','info','contextmenu',
    'queue','pageup','pagedown','firstpage','lastpage','number0','number1','number2','number3','number4',
    'number5','number6','number7','number8','number9','stepforward','stepback','smallstepforward',
    'smallstepback','bigstepforward','bigstepback','play','pause','stop','playpause','record',
    'fastforward','rewind','skipnext','skipprevious','channelup','channeldown','previouschannel',
    'mute','volumeup','volumedown','red','green','yellow','blue','white','screenshot','fullscreen'],
  window:['home','videos','music','pictures','programs','systeminfo','filemanager','settings',
    'settingscategory','playercontrols','visualisation','slideshow','loginscreen','profiles',
    'fullscreenvideo','fullscreenmusic','visualisationpresetsettings','favourites','addonbrowser','weather']
};
// param name -> curated key (sort sub-fields are literally named method/order)
var CURATED_KEY={method:'sortmethod',order:'sortorder'};
var schemaCache={},optCache={},jsonMode=false,currentMethod='',lastQrUrl='';

function fetchSchema(method){
  if(schemaCache[method])return Promise.resolve(schemaCache[method]);
  return fetch('/api/v1/schema?method='+encodeURIComponent(method))
    .then(function(r){ if(!r.ok) throw new Error('schema '+r.status); return r.json(); })
    .then(function(s){ schemaCache[method]=s; return s; });
}

function fetchOptions(kind, arg){
  var key=kind+':'+(arg||'');
  if(kind!=='players' && optCache[key]) return Promise.resolve(optCache[key]);
  var url='/api/v1/options?kind='+kind+(arg?'&tvshowid='+encodeURIComponent(arg):'');
  return fetch(url)
    .then(function(r){ if(!r.ok) throw new Error('options '+r.status); return r.json(); })
    .then(function(d){ if(kind!=='players') optCache[key]=d.options; return d.options; });
}

function setJsonMode(on){
  var form=$('params-form'), ta=$('params-editor'), btn=$('toggle-json');
  if(on){
    var def={}; try{ def=collectFormValues(false); }catch(e){}
    ta.value=JSON.stringify(def,null,2);
    jsonMode=true;
    form.style.display='none'; ta.style.display=''; btn.textContent='Edit as form';
  } else {
    var defaults={}; try{ defaults=JSON.parse(ta.value||'{}'); }catch(e){}
    jsonMode=false;
    form.style.display=''; ta.style.display='none'; btn.textContent='Edit as JSON';
    if(currentMethod && currentMethod!=='__custom__') renderParams(currentMethod, defaults);
  }
}

function renderParams(method, defaults){
  var form=$('params-form');
  form.innerHTML='<div class="loading">Loading parameter info&hellip;</div>';
  fetchSchema(method).then(function(sc){
    if(currentMethod!==method) return;  // user moved on
    var opt=$('method-select').selectedOptions[0];
    if(sc.description && opt) $('method-desc').textContent=(opt.dataset.label||'')+' \u2014 '+sc.description;
    form.innerHTML='';
    if(!sc.params || !sc.params.length){
      form.innerHTML='<div class="pf-row"><span class="loading">No parameters for this method.</span></div>';
      return;
    }
    sc.params.forEach(function(p){
      form.appendChild(paramRow(p, defaults && Object.prototype.hasOwnProperty.call(defaults,p.name) ? defaults[p.name] : undefined));
    });
    wireCascades(form);
  }).catch(function(){
    if(currentMethod!==method) return;
    setJsonMode(true);  // introspect unavailable - raw JSON fallback
    $('method-desc').textContent='Parameter info unavailable - edit params as JSON.';
  });
}

function paramRow(p, def){
  var row=document.createElement('div'); row.className='pf-row';
  var ptype=(typeof p.type==='string' && p.type) ? p.type : 'string';  // guard: never stringify schema objects
  row.dataset.name=p.name; row.dataset.type=ptype;
  row.dataset.required=p.required?'1':'';
  var lab=document.createElement('span'); lab.className='pf-label';
  lab.innerHTML=esc(p.name)+(p.required?' <span class="req">*</span>':'')+' <span class="ptype">'+esc(ptype)+'</span>';
  row.appendChild(lab);
  if(p.description){ var d=document.createElement('div'); d.className='pf-desc'; d.textContent=p.description; row.appendChild(d); }
  row.appendChild(buildControl(p, def));
  return row;
}

function buildControl(p, def){
  if(ID_OPTS[p.name]) return buildOptionsSelect(p, def, ID_OPTS[p.name]);
  if(p.itemsEnum) return buildEnumSet(p, def);   // checkbox list (properties etc.)
  var enumList=p.enum||CURATED[p.name]||(CURATED_KEY[p.name]?CURATED[CURATED_KEY[p.name]]:null)||null;
  if(enumList && p.type!=='boolean') return buildSelect(p, def, enumList);
  if(p.type==='boolean') return buildBool(p, def);
  if(p.type==='integer'||p.type==='number') return buildNumber(p, def);
  if(p.type==='object'&&p.fields) return buildFieldset(p, def);  // structured object (sort/limits)
  if(p.type==='object'||p.type==='array') return buildJsonBox(p, def);
  return buildText(p, def);
}

function buildEnumSet(p, def){
  // multi-select checkbox grid for string-list params (properties)
  var wrap=document.createElement('div');
  wrap.className='pf-enumset';
  wrap.dataset.param=p.name;
  var pre=Array.isArray(def)?def.map(String):[];
  p.itemsEnum.forEach(function(v){
    var l=document.createElement('label'); l.className='pf-chk';
    var cb=document.createElement('input'); cb.type='checkbox'; cb.value=String(v);
    if(pre.indexOf(String(v))>=0) cb.checked=true;
    l.appendChild(cb);
    l.appendChild(document.createTextNode(' '+String(v)));
    wrap.appendChild(l);
  });
  return wrap;
}

function buildFieldset(p, def){
  // typed sub-controls for structured objects (sort, limits, ...) - empty fields omit
  var wrap=document.createElement('div');
  wrap.className='pf-fields';
  wrap.dataset.hasfields='1';
  p.fields.forEach(function(f){
    var cell=document.createElement('div');
    cell.className='pf-field';
    cell.dataset.fname=f.name; cell.dataset.ftype=f.type||'string';
    var lab=document.createElement('span'); lab.className='pf-label';
    lab.innerHTML=esc(f.name)+(f.required?' <span class="req">*</span>':'')+' <span class="ptype">'+esc(f.type||'string')+'</span>';
    cell.appendChild(lab);
    if(f.description){ var d=document.createElement('div'); d.className='pf-desc'; d.textContent=f.description; cell.appendChild(d); }
    var fdef=(def && typeof def==='object') ? def[f.name] : undefined;
    // children always optional: only filled values go into the object
    cell.appendChild(buildControl({name:f.name, type:f.type, enum:f.enum, required:false}, fdef));
    wrap.appendChild(cell);
  });
  return wrap;
}

function buildSelect(p, def, values){
  var s=document.createElement('select'); s.dataset.param=p.name;
  function add(v,label){ var o=document.createElement('option'); o.value=String(v); o.textContent=label; s.appendChild(o); return o; }
  if(!p.required) add('','(none)');
  var found=false;
  values.forEach(function(v){ var o=add(v,String(v)); if(def!=null && String(def)===String(v)){ o.selected=true; found=true; } });
  if(def!=null && def!=='' && !found) add(def,String(def)).selected=true;  // prefill survives even if not in the enum
  add('__custom__','Custom value\u2026');
  s.addEventListener('change',function(){
    if(s.value==='__custom__'){
      var v=window.prompt('Enter a custom value for '+p.name+':');
      if(v!=null && v!==''){ add(v,v); s.value=v; } else s.value='';
    }
  });
  return s;
}

function buildOptionsSelect(p, def, kind){
  var s=document.createElement('select'); s.dataset.param=p.name; s.dataset.kind=kind;
  var needsShow=(kind==='episodes'||kind==='seasons');
  var hasShowSel=needsShow && document.querySelector('#params-form select[data-param="tvshowid"]');
  if(hasShowSel && !document.querySelector('#params-form select[data-param="'+p.name+'"]')){
    // cascade: populate after a show is picked (wireCascades hooks the change)
    s.disabled=true;
    var o=document.createElement('option'); o.value=''; o.textContent='Select a show first\u2026'; s.appendChild(o);
  } else {
    var o0=document.createElement('option'); o0.value=''; o0.textContent=p.required?'Loading\u2026':'(none)';
    s.appendChild(o0);
    s.disabled=true;
    fetchOptions(kind, null).then(function(opts){ fillOptions(s, opts, def, p); })
      .catch(function(){ s.disabled=false; s.innerHTML=''; var o=document.createElement('option'); o.value=''; o.textContent='Load failed'; s.appendChild(o); });
  }
  s.addEventListener('change',function(){
    if(s.value==='__custom__'){
      var v=window.prompt('Enter a custom value for '+p.name+':');
      if(v!=null && v!==''){ var o=document.createElement('option'); o.value=v; o.textContent=v; s.appendChild(o); s.value=v; }
      else s.value='';
    }
  });
  return s;
}

function fillOptions(s, opts, def, p){
  s.innerHTML='';
  if(!p.required){ var o0=document.createElement('option'); o0.value=''; o0.textContent='(none)'; s.appendChild(o0); }
  var found=false;
  opts.forEach(function(it){
    var o=document.createElement('option');
    o.value=String(it.value);
    if(it.name!=null) o.dataset.nm=it.name;   // profiles.LoadProfile wants the NAME
    o.textContent=it.label;
    s.appendChild(o);
    if(def!=null && String(def)===String(it.value)){ o.selected=true; found=true; }
  });
  if(def!=null && def!=='' && !found){   // prefill survives even when not in the live list
    var od=document.createElement('option'); od.value=String(def); od.textContent=String(def);
    od.selected=true; s.appendChild(od);
  }
  var oc=document.createElement('option'); oc.value='__custom__'; oc.textContent='Custom value\u2026'; s.appendChild(oc);
  s.disabled=false;
}

function wireCascades(form){
  var showSel=form.querySelector('select[data-param="tvshowid"]');
  if(!showSel) return;
  var dep=form.querySelector('select[data-param="episodeid"], select[data-param="seasonid"]');
  if(!dep) return;
  function reload(){
    var kind=dep.dataset.kind;
    if(!showSel.value){
      dep.disabled=true; dep.innerHTML='';
      var o=document.createElement('option'); o.value=''; o.textContent='Select a show first\u2026'; dep.appendChild(o);
      return;
    }
    dep.disabled=true;
    var keep=dep.value;
    fetchOptions(kind, showSel.value).then(function(opts){
      fillOptions(dep, opts, null, {name:dep.dataset.param, required:dep.dataset.required==='1'});
      dep.disabled=false;
      if(keep) dep.value=keep;
    }).catch(function(){ dep.disabled=false; });
  }
  showSel.addEventListener('change', reload);
  reload();
}

function buildBool(p, def){
  var s=document.createElement('select'); s.dataset.param=p.name;
  function add(v,l){ var o=document.createElement('option'); o.value=v; o.textContent=l; s.appendChild(o); }
  if(!p.required) add('','(none)');
  add('false','No'); add('true','Yes');
  if(def===true||def==='true') s.value='true';
  else if(def===false||def==='false') s.value='false';
  else if(p.required) s.value='false';
  return s;
}

function buildNumber(p, def){
  var i=document.createElement('input');
  i.type='number'; i.dataset.param=p.name;
  if(p.type==='integer') i.step='1';
  if(def!=null) i.value=String(def);
  return i;
}

function buildJsonBox(p, def){
  var t=document.createElement('textarea'); t.rows=3; t.dataset.param=p.name;
  if(def!=null && typeof def!=='string') t.value=JSON.stringify(def,null,2);
  else if(typeof def==='string') t.value=def;
  else t.value=(p.type==='array'?'[]':'{}');
  return t;
}

function buildText(p, def){
  var i=document.createElement('input');
  i.type='text'; i.dataset.param=p.name;
  if(def!=null) i.value=String(def);
  return i;
}

function collectFormValues(enforce){
  var out={};
  var rows=$('params-form').querySelectorAll('.pf-row');
  Array.prototype.forEach.call(rows, function(row){
    var name=row.dataset.name; if(!name) return;
    var required=row.dataset.required==='1';
    var type=row.dataset.type||'string';
    try{
      // checkbox multi-select (properties-style string lists)
      var cbwrap=row.querySelector('.pf-enumset');
      if(cbwrap){
        var checked=Array.prototype.filter.call(cbwrap.querySelectorAll('input[type=checkbox]'), function(c){return c.checked;})
          .map(function(c){return c.value;});
        if(!checked.length){ if(enforce && required) throw new Error('Required parameter missing: '+name); return; }
        out[name]=checked;
        return;
      }
      // structured object (sort/limits) - only filled sub-fields go in
      var fwrap=row.querySelector('.pf-fields');
      if(fwrap){
        var obj={};
        Array.prototype.forEach.call(fwrap.querySelectorAll('.pf-field'), function(cell){
          var c2=cell.querySelector('select,input,textarea'); if(!c2) return;
          var fn=cell.dataset.fname, ft=cell.dataset.ftype||'string';
          var raw=c2.value;
          if(raw==='' || raw==null || raw==='__custom__') return;
          var v;
          if(ft==='boolean') v=(raw==='true');
          else if(ft==='integer'){ v=parseInt(raw,10); if(isNaN(v)) throw new Error('Not a valid integer: '+fn); }
          else if(ft==='number'){ v=parseFloat(raw); if(isNaN(v)) throw new Error('Not a valid number: '+fn); }
          else if(ft==='object'||ft==='array') v=JSON.parse(raw);
          else v=raw;
          obj[fn]=v;
        });
        if(!Object.keys(obj).length){ if(enforce && required) throw new Error('Required parameter missing: '+name); return; }
        out[name]=obj;
        return;
      }
      var ctrl=row.querySelector('select,input,textarea'); if(!ctrl) return;
      var raw=ctrl.value;
      if(raw==='' || raw==null || raw==='__custom__'){
        if(enforce && required) throw new Error('Required parameter missing: '+name);
        return;
      }
      var val;
      if(type==='boolean') val=(raw==='true');
      else if(type==='integer'){ val=parseInt(raw,10); if(isNaN(val)) throw new Error('Not a valid integer: '+name); }
      else if(type==='number'){ val=parseFloat(raw); if(isNaN(val)) throw new Error('Not a valid number: '+name); }
      else if(type==='object'||type==='array'){
        val=JSON.parse(raw);
        if(type==='array' && !Array.isArray(val)) throw new Error(name+' must be a JSON array');
      } else {
        val=raw;
        if(ctrl.tagName==='SELECT' && ctrl.dataset.kind==='profiles' && name==='profile'){
          var opt=ctrl.options[ctrl.selectedIndex];   // LoadProfile takes the profile name
          if(opt && opt.dataset.nm!=null && opt.dataset.nm!=='') val=opt.dataset.nm;
        }
      }
      out[name]=val;
    }catch(e){ if(enforce) throw e; }
  });
  return out;
}


function initBuilder(){
  var sel=$('method-select');
  METHODS.forEach(function(group){
    var og=document.createElement('optgroup');og.label=group.cat;
    group.items.forEach(function(item){
      var o=document.createElement('option');o.value=item.m;o.textContent=item.label;
      o.dataset.params=JSON.stringify(item.params);o.dataset.label=item.label;
      og.appendChild(o);
    });
    sel.appendChild(og);
  });
  sel.addEventListener('change',onMethodChange);
  onMethodChange();
  $('add-cmd').addEventListener('click',addCommand);
  $('clear-stack').addEventListener('click',function(){stack=[];renderStack()});
  $('gen-qr').addEventListener('click',generateQR);
  $('toggle-json').addEventListener('click',function(){ setJsonMode(!jsonMode); });
  $('share-qr').addEventListener('click',function(){
    if(!lastQrUrl || !navigator.share) return;
    navigator.share({title:'Kodi PowerToys',text:'Kodi action link',url:lastQrUrl}).catch(function(){});
  });
}

function onMethodChange(){
  var sel=$('method-select');var opt=sel.selectedOptions[0];
  if(!opt)return;
  currentMethod=opt.value;
  $('method-desc').textContent=opt.dataset.label||'';
  var params=JSON.parse(opt.dataset.params||'{}');
  $('params-editor').value=JSON.stringify(params,null,2);
  if(currentMethod==='__custom__'){
    setJsonMode(true);
    $('method-desc').textContent='Custom JSON-RPC method \u2014 edit params as JSON.';
    return;
  }
  setJsonMode(false);  // renders the typed form (defaults from textarea/catalogue)
}

function addCommand(){
  var sel=$('method-select');var opt=sel.selectedOptions[0];
  if(!opt)return;
  var method=opt.value;
  if(method==='__custom__'){
    var m=window.prompt('Enter JSON-RPC method name (e.g. VideoLibrary.Scan):');
    if(!m)return;method=m;
  }
  var params;
  try{
    params = jsonMode ? JSON.parse($('params-editor').value||'{}') : collectFormValues(true);
  }catch(e){
    alert(e.message || 'Invalid params');
    return;
  }
  stack.push({jsonrpc:'2.0',method:method,params:params,id:stack.length+1});
  renderStack();
}

function renderStack(){
  var ol=$('cmd-stack');ol.innerHTML='';
  if(stack.length===0){$('stack-card').style.display='none';$('preview-card').style.display='none';$('qr-card').style.display='none';return}
  $('stack-card').style.display='';
  $('preview-card').style.display='';
  stack.forEach(function(cmd,i){
    var li=document.createElement('li');
    var info=document.createElement('div');info.className='cmd-info';
    var m=document.createElement('div');m.className='cmd-method';m.textContent=cmd.method;
    var p=document.createElement('div');p.className='cmd-params';p.textContent=JSON.stringify(cmd.params);
    info.appendChild(m);info.appendChild(p);
    var btn=document.createElement('button');btn.className='cmd-remove';btn.textContent='✕';btn.title='Remove';
    btn.addEventListener('click',function(){stack.splice(i,1);renderStack()});
    li.appendChild(info);li.appendChild(btn);ol.appendChild(li);
  });
  $('json-preview').textContent=JSON.stringify(stack,null,2);
}

function generateQR(){
  if(stack.length===0)return;
  var json=JSON.stringify(stack);
  var b64=btoa(unescape(encodeURIComponent(json))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
  var url=location.origin+'/run/'+b64;
  lastQrUrl=url;
  $('qr-card').style.display='';
  $('qr-url').textContent=url;
  // Web Share API - Android shows the native share sheet; hidden where unsupported
  $('share-qr').style.display = navigator.share ? '' : 'none';
  var container=$('qr-container');container.innerHTML='';
  try{
    // battle-tested qrcodejs - auto-selects version/EC, handles block interleaving
    // (the old hand-rolled encoder emitted malformed codes above ~44 bytes)
    new QRCode(container,{text:url,width:300,height:300,correctLevel:QRCode.CorrectLevel.M});
  }catch(e){container.textContent='QR generation failed: '+e.message}
}

// ── Landing page (QR scan target) ──────────────────────────────────────
function initLanding(){
  var path=location.pathname;
  var match=path.match(/^\/run\/(.+)$/);
  if(!match)return false;
  var encoded=match[1];
  var commands;
  try{
    var b64=encoded.replace(/-/g,'+').replace(/_/g,'/');
    while(b64.length%4)b64+='=';
    commands=JSON.parse(decodeURIComponent(escape(atob(b64))));
  }catch(e){
    document.getElementById('landing-view').innerHTML='<div class="card"><h2>Invalid QR Code</h2><p class="hint">Could not decode commands from this URL.</p></div>';
    document.getElementById('landing-view').style.display='';
    return true;
  }
  if(!Array.isArray(commands))commands=[commands];

  document.getElementById('builder-view').style.display='none';
  document.getElementById('landing-view').style.display='';

  var ol=document.getElementById('landing-cmds');
  commands.forEach(function(cmd){
    var li=document.createElement('li');
    var m=document.createElement('div');m.className='cmd-method';m.textContent=cmd.method;
    var p=document.createElement('div');p.className='cmd-params';p.textContent=JSON.stringify(cmd.params||{});
    li.appendChild(m);li.appendChild(p);
    ol.appendChild(li);
  });

  fetch('/api/v1/instances').then(function(r){return r.json()}).then(function(data){
    var container=document.getElementById('instance-list');
    (data.instances||[]).forEach(function(inst,i){
      var label=document.createElement('label');
      var cb=document.createElement('input');cb.type='checkbox';cb.checked=true;cb.value=JSON.stringify({ip:inst.ip,port:inst.port,self:inst.self});
      var name=document.createElement('span');name.className='instance-name';name.textContent=inst.label;
      label.appendChild(cb);label.appendChild(name);
      if(inst.self){var badge=document.createElement('span');badge.className='instance-self';badge.textContent='THIS';label.appendChild(badge)}
      container.appendChild(label);
    });
  }).catch(function(){
    document.getElementById('instance-list').innerHTML='<p class="hint">Could not discover instances. Make sure the web server is enabled on each Kodi device.</p>';
  });

  document.getElementById('exec-btn').addEventListener('click',function(){executeCommands(commands)});
  return true;
}

function executeCommands(commands){
  var checkboxes=document.querySelectorAll('#instance-list input[type=checkbox]:checked');
  if(checkboxes.length===0){alert('Select at least one instance');return}
  var instances=[];checkboxes.forEach(function(cb){instances.push(JSON.parse(cb.value))});
  var btn=document.getElementById('exec-btn');btn.disabled=true;btn.textContent='Executing…';
  var resultsDiv=document.getElementById('exec-results');resultsDiv.innerHTML='';

  fetch('/exec',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({commands:commands,instances:instances})})
  .then(function(r){return r.json()})
  .then(function(data){
    btn.disabled=false;btn.textContent='Execute';
    (data.results||[]).forEach(function(res){
      var div=document.createElement('div');
      div.className='result-item '+(res.status==='ok'?'result-ok':'result-error');
      if(res.status==='ok'){
        var okCount=(res.responses||[]).filter(function(r2){return r2&&r2.result}).length;
        div.textContent='✓ '+res.instance+' — '+okCount+'/'+(res.responses||[]).length+' commands succeeded';
      }else{
        div.textContent='✗ '+res.instance+' — '+res.error;
      }
      resultsDiv.appendChild(div);
    });
  })
  .catch(function(e){
    btn.disabled=false;btn.textContent='Execute';
    var div=document.createElement('div');div.className='result-item result-error';div.textContent='Request failed: '+e.message;
    resultsDiv.appendChild(div);
  });
}

// ── Boot ────────────────────────────────────────────────────────────────
if(!initLanding())initBuilder();
})();
