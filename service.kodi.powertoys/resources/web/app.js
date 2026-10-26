(function(){
'use strict';

// ── Minimal QR encoder (byte mode, EC level M) ──────────────────────────
var QR=(function(){
  var EXP=new Array(512),LOG=new Array(256);
  (function(){var x=1;for(var i=0;i<255;i++){EXP[i]=x;LOG[x]=i;x<<=1;if(x&256)x^=0x11d}for(var i=255;i<512;i++)EXP[i]=EXP[i-255]})();
  function gm(a,b){return(a&&b)?EXP[LOG[a]+LOG[b]]:0}
  function rsGen(n){var g=[1];for(var i=0;i<n;i++){var ng=new Array(g.length+1);for(var j=0;j<ng.length;j++)ng[j]=0;for(var j=0;j<g.length;j++){ng[j]^=gm(g[j],EXP[i]);ng[j+1]^=g[j]}g=ng}return g}
  function rsEnc(data,n){var g=rsGen(n);var buf=data.slice();for(var i=0;i<n;i++)buf.push(0);for(var i=0;i<data.length;i++){var f=buf[i];if(!f)continue;for(var j=0;j<g.length;j++)buf[i+j]^=gm(g[j],f)}return buf.slice(data.length)}

  var ECB_M=[0,10,16,26,18,24,16,18,22,22,26,30,22,22,24,24,28,28,26,26,26,26,28,28,28,28,28,28,28,28,28,28,28,28,28,28,28,28,28,28,28];
  var TOTAL_CW=[0,26,44,70,100,134,172,196,242,292,346,404,466,532,581,655,733,815,901,991,1085,1156,1258,1364,1474,1588,1706,1828,1921,2051,2185,2323,2465,2611,2761,2876,3034,3196,3362,3532,3706];
  var ALIGN=[[],[6,18],[6,22],[6,26],[6,30],[6,34],[6,22,38],[6,24,42],[6,26,46],[6,28,50],[6,30,54],[6,32,58],[6,34,62],[6,26,46,66],[6,26,48,70],[6,26,50,74],[6,30,54,78],[6,30,56,82],[6,30,58,86],[6,34,62,90],[6,28,50,72,94],[6,26,50,74,98],[6,30,54,78,102],[6,28,54,80,106],[6,32,58,84,110],[6,30,58,86,114],[6,34,62,90,118],[6,26,50,74,98,122],[6,30,54,78,102,126],[6,26,52,78,104,130],[6,30,56,82,108,134],[6,34,60,86,112,138],[6,30,58,86,114,142],[6,34,62,90,118,146],[6,30,54,78,102,126,150],[6,24,50,76,102,128,154],[6,28,54,80,106,132,158],[6,32,58,84,110,136,162],[6,26,54,82,110,138,166],[6,30,58,86,114,142,170]];

  function dataCap(v){return TOTAL_CW[v]-ECB_M[v]}

  function encode(text){
    var bytes=[];for(var i=0;i<text.length;i++){var c=text.charCodeAt(i);if(c<128)bytes.push(c);else if(c<2048){bytes.push(192|(c>>6),128|(c&63))}else{bytes.push(224|(c>>12),128|((c>>6)&63),128|(c&63))}}
    var ver=1;while(ver<40&&dataCap(ver)*8<4+8+bytes.length*8+4)ver++;
    var cc=dataCap(ver);
    var bits=[];function put(val,len){for(var i=len-1;i>=0;i--)bits.push((val>>i)&1)}
    put(4,4);put(bytes.length,ver<10?8:16);
    for(var i=0;i<bytes.length;i++)put(bytes[i],8);
    var rem=cc*8-bits.length;put(0,Math.min(4,rem));while(bits.length%8)bits.push(0);
    var pad=[0xEC,0x11],pi=0;while(bits.length<cc*8){put(pad[pi++%2],8)}
    var data=[];for(var i=0;i<bits.length;i+=8){var b=0;for(var j=0;j<8;j++)b=(b<<1)|bits[i+j];data.push(b)}
    var ec=rsEnc(data,ECB_M[ver]);var all=data.concat(ec);

    var size=17+4*ver;var m=[];for(var r=0;r<size;r++){m[r]=[];for(var c=0;c<size;c++)m[r][c]=null}
    function setF(r,c,v){if(r>=0&&r<size&&c>=0&&c<size)m[r][c]=v}
    function finder(r,c){for(var dr=-1;dr<=7;dr++)for(var dc=-1;dc<=7;dc++){var rr=r+dr,cc2=c+dc;if(rr<0||rr>=size||cc2<0||cc2>=size)continue;setF(rr,cc2,(dr>=0&&dr<=6&&(dc===0||dc===6))||(dc>=0&&dc<=6&&(dr===0||dr===6))||(dr>=2&&dr<=4&&dc>=2&&dc<=4))}}
    finder(0,0);finder(0,size-7);finder(size-7,0);
    for(var i=8;i<size-8;i++){setF(6,i,i%2===0);setF(i,6,i%2===0)}
    var ap=ALIGN[ver];
    for(var i=0;i<ap.length;i++)for(var j=0;j<ap.length;j++){
      if((i===0&&j===0)||(i===0&&j===ap.length-1)||(i===ap.length-1&&j===0))continue;
      var r=ap[i],c=ap[j];
      for(var dr=-2;dr<=2;dr++)for(var dc=-2;dc<=2;dc++)setF(r+dr,c+dc,(Math.abs(dr)===2||Math.abs(dc)===2||(dr===0&&dc===0)))
    }
    for(var i=0;i<9;i++){setF(8,i,i<6?true:null);setF(i,8,i<6?true:null)}
    setF(8,7,true);setF(7,8,true);
    for(var i=0;i<8;i++){setF(8,size-1-i,i<7?true:null);setF(size-1-i,8,i<7?true:null)}
    if(ver>=7){for(var i=0;i<18;i++){var r=Math.floor(i/3),c=size-11+i%3;setF(r,c,((ver>>(17-i))&1)===1)}}

    var reserved=[];for(var r=0;r<size;r++){reserved[r]=[];for(var c=0;c<size;c++)reserved[r][c]=m[r][c]!==null}

    var bitIdx=0;function nextBit(){if(bitIdx>=all.length*8)return 0;var byte=all[bitIdx>>3];var bit=(byte>>(7-(bitIdx&7)))&1;bitIdx++;return bit}
    var up=true;
    for(var col=size-1;col>0;col-=2){if(col===6)col--;
      for(var i=0;i<size;i++){var row=up?size-1-i:i;
        for(var dc=0;dc<2;dc++){var c=col-dc;if(!reserved[row][c])m[row][c]=nextBit()^0}
      }up=!up}

    var bestMask=0,bestPen=Infinity,bestM=null;
    for(var mask=0;mask<8;mask++){
      var t=[];for(var r=0;r<size;r++){t[r]=[];for(var c=0;c<size;c++){t[r][c]=m[r][c];if(!reserved[r][c]&&maskFn(mask,r,c))t[r][c]^=1}}
      var pen=penalty(t,size);
      if(pen<bestPen){bestPen=pen;bestMask=mask;bestM=t}
    }
    var result=bestM;
    var fmt=bestMask<<3|1;var rem2=fmt;for(var i=0;i<10;i++)rem2=(rem2<<1)^(((rem2>>9)&1)*0x537);var fmtBits=((fmt<<10)|rem2)^0x5412;
    for(var i=0;i<15;i++){var bit=((fmtBits>>i)&1)===1;
      if(i<6)setF(i,8,bit);else if(i<8)setF(i+1,8,bit);else setF(size-15+i,8,bit);
      if(i<8)setF(8,size-i-1,bit);else if(i<9)setF(8,15-i,bit);else setF(8,15-i,bit)}
    setF(size-8,8,true);
    return result;
  }

  function maskFn(m,r,c){switch(m){case 0:return(r+c)%2===0;case 1:return r%2===0;case 2:return c%3===0;case 3:return(r+c)%3===0;case 4:return(Math.floor(r/2)+Math.floor(c/3))%2===0;case 5:return(r*c)%2+(r*c)%3===0;case 6:return((r*c)%2+(r*c)%3)%2===0;case 7:return((r+c)%2+(r*c)%3)%2===0}return false}

  function penalty(m,size){
    var p=0;
    for(var r=0;r<size;r++){var run=1;for(var c=1;c<size;c++){if(m[r][c]===m[r][c-1])run++;else{if(run>=5)p+=3+(run-5);run=1}}if(run>=5)p+=3+(run-5)}
    for(var c=0;c<size;c++){var run=1;for(var r=1;r<size;r++){if(m[r][c]===m[r-1][c])run++;else{if(run>=5)p+=3+(run-5);run=1}}if(run>=5)p+=3+(run-5)}
    for(var r=0;r<size-1;r++)for(var c=0;c<size-1;c++){var v=m[r][c];if(v===m[r][c+1]&&v===m[r+1][c]&&v===m[r+1][c+1])p+=3}
    var pat=[true,false,true,true,true,false,true,false,false,false,false];var pat2=[false,false,false,false,true,false,true,true,true,false,true];
    for(var r=0;r<size;r++)for(var c=0;c<=size-11;c++){var ok=true,ok2=true;for(var i=0;i<11;i++){if(m[r][c+i]!==pat[i])ok=false;if(m[r][c+i]!==pat2[i])ok2=false}if(ok||ok2)p+=40}
    for(var c=0;c<size;c++)for(var r=0;r<=size-11;r++){var ok=true,ok2=true;for(var i=0;i<11;i++){if(m[r+i][c]!==pat[i])ok=false;if(m[r+i][c]!==pat2[i])ok2=false}if(ok||ok2)p+=40}
    var dark=0;for(var r=0;r<size;r++)for(var c=0;c<size;c++)if(m[r][c])dark++;
    var pct=Math.abs(dark*100/(size*size)-50);p+=Math.floor(pct/5)*10;
    return p;
  }

  return{encode:encode};
})();

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
    {m:'Files.GetDirectory',label:'Browse a folder',params:{directory:'/media/',media:'files'}},
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
}

function onMethodChange(){
  var sel=$('method-select');var opt=sel.selectedOptions[0];
  if(!opt)return;
  var m=opt.value;
  $('method-desc').textContent=opt.dataset.label||'';
  var params=JSON.parse(opt.dataset.params||'{}');
  $('params-editor').value=JSON.stringify(params,null,2);
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
  try{params=JSON.parse($('params-editor').value||'{}')}catch(e){alert('Invalid JSON in params');return}
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
  $('qr-card').style.display='';
  $('qr-url').textContent=url;
  var container=$('qr-container');container.innerHTML='';
  try{
    var matrix=QR.encode(url);
    var n=matrix.length;var scale=Math.max(4,Math.floor(400/n));var canvasSize=n*scale;
    var canvas=document.createElement('canvas');canvas.width=canvasSize;canvas.height=canvasSize;
    var ctx=canvas.getContext('2d');
    ctx.fillStyle='#fff';ctx.fillRect(0,0,canvasSize,canvasSize);
    ctx.fillStyle='#000';
    for(var r=0;r<n;r++)for(var c=0;c<n;c++)if(matrix[r][c])ctx.fillRect(c*scale,r*scale,scale,scale);
    container.appendChild(canvas);
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
