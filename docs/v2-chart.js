/* Trading-style canvas chart: observed OHLC + scientifically labelled model forecast overlays.
   Self-contained and file:// compatible. No synthetic "future candles". */
(function(global){"use strict";
class ForecastChart {
 constructor(canvas,tooltip){
  this.canvas=canvas;
  this.tooltip=tooltip;
  this.candles=global.CRL_HISTORY.candles;
  this.originIdx=this.candles.findIndex(c=>c.date==="2024-12-31");
  if(this.originIdx<0||this.candles[this.originIdx].close!==93576)throw Error("Historical candle origin mismatch");
  this.view={start:0,count:61};
  this.state={result:null,day:0,view:"all",reveal:false,threshold:.10,horizon:30};
  this.cursor=null;this.drag=null;this.pinch=null;this.pointers=new Map();
  this.selectedPath=null;this.onSelectPath=null;this.axis=null;this.crosshairPrice=null;
  this.manualPriceRange=null;this.lastDragAt=0;this.suppressNextClick=false;
  this.drawQueued=false;this.renderFrame=null;this.inertiaFrame=null;
  this.zoomTarget=null;this.zoomFrame=null;
  this.reduceMotion=!!global.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  canvas.tabIndex=0;
  canvas.style.touchAction="none";
  canvas.addEventListener("wheel",e=>this.onWheel(e),{passive:false});
  canvas.addEventListener("pointerdown",e=>this.onPointerDown(e));
  canvas.addEventListener("pointermove",e=>this.onPointerMove(e));
  canvas.addEventListener("pointerup",e=>this.onPointerUp(e));
  canvas.addEventListener("pointercancel",e=>this.onPointerUp(e,true));
  canvas.addEventListener("lostpointercapture",e=>this.onPointerUp(e,true));
  canvas.addEventListener("pointerleave",()=>{if(!this.drag&&!this.pinch){this.cursor=null;this.crosshairPrice=null;this.tooltip.style.display="none";this.queueDraw();}});
  canvas.addEventListener("dblclick",e=>{if(this.inPriceAxis(this.local(e))){this.resetPriceScale();}else this.resetZoom();});
  canvas.addEventListener("click",e=>{
    if(this.suppressNextClick){this.suppressNextClick=false;return;}
    this.selectAt(e);
  });
  canvas.addEventListener("keydown",e=>this.onKey(e));
  if("ResizeObserver" in global){
    this.ro=new ResizeObserver(()=>this.queueDraw());this.ro.observe(canvas);
  }else global.addEventListener("resize",()=>this.queueDraw());
 }
 local(e){
   const rect=this.canvas.getBoundingClientRect();
   return {x:e.clientX-rect.left,y:e.clientY-rect.top};
 }
 get plotWidth(){return Math.max(10,this.canvas.clientWidth-13-77);}
 get totalBars(){return Math.max(this.candles.length,this.originIdx+this.state.horizon+1);}
 inPriceAxis(pos){return pos.x>=this.canvas.clientWidth-77&&pos.x<=this.canvas.clientWidth&&pos.y>=22&&pos.y<=this.canvas.clientHeight-94;}
 queueDraw(){
   if(this.drawQueued)return;
   this.drawQueued=true;
   this.renderFrame=global.requestAnimationFrame(()=>{this.drawQueued=false;this.renderFrame=null;this.draw();});
 }
 stopInertia(){if(this.inertiaFrame!==null){global.cancelAnimationFrame(this.inertiaFrame);this.inertiaFrame=null;}}
 stopZoom(){
   if(this.zoomFrame!==null){global.cancelAnimationFrame(this.zoomFrame);this.zoomFrame=null;}
   this.zoomTarget=null;
 }
 smoothZoomAt(factor,px){
   this.stopInertia();
   if(!this.zoomTarget)this.zoomTarget={...this.view};
   const target=this.zoomTarget;
   const f=Math.max(0,Math.min(1,(px-13)/this.plotWidth));
   const old=target.count;
   target.count=Math.max(12,Math.min(this.totalBars+14,old*factor));
   target.start+=f*(old-target.count);
   const maxStart=Math.max(-4,this.totalBars-target.count+7);
   target.start=Math.max(-4,Math.min(maxStart,target.start));
   if(this.zoomFrame===null)this.zoomFrame=global.requestAnimationFrame(()=>this.animateZoom());
 }
 animateZoom(){
   if(!this.zoomTarget){this.zoomFrame=null;return;}
   const target=this.zoomTarget;
   const amount=this.reduceMotion?1:.3;
   this.view.count+=(target.count-this.view.count)*amount;
   this.view.start+=(target.start-this.view.start)*amount;
   this.clampView();
   this.queueDraw();
   if(Math.abs(target.count-this.view.count)<.01&&Math.abs(target.start-this.view.start)<.01){
     this.view={...target};this.zoomFrame=null;this.zoomTarget=null;this.queueDraw();
   }else this.zoomFrame=global.requestAnimationFrame(()=>this.animateZoom());
 }
 clampView(){
   const n=this.totalBars;
   this.view.count=Math.max(12,Math.min(n+14,this.view.count));
   const low=-4,high=Math.max(low,n-this.view.count+7);
   this.view.start=Math.max(low,Math.min(high,this.view.start));
 }
 panByPixels(dx){
   this.stopInertia();this.stopZoom();
   this.view.start-=dx/this.plotWidth*this.view.count;
   this.clampView();this.queueDraw();
 }
 zoomAt(factor,px){
   if(!Number.isFinite(factor)||factor<=0)return;
   this.stopInertia();this.stopZoom();
   const fraction=Math.max(0,Math.min(1,(px-13)/this.plotWidth));
   const previous=this.view.count;
   this.view.count=Math.max(12,Math.min(this.totalBars+14,previous*factor));
   this.view.start+=fraction*(previous-this.view.count);
   this.clampView();this.queueDraw();
 }
 zoomPriceAt(factor,y){
   if(!this.axis||!Number.isFinite(factor)||factor<=0)return;
   const a=this.axis,loc=Math.max(0,Math.min(1,(a.bottom-y)/(a.bottom-a.top)));
   const source=this.manualPriceRange||{min:a.min,max:a.max};
   const ref=source.min+(source.max-source.min)*loc;
   const span=(source.max-source.min)*factor;
   this.manualPriceRange={min:ref-loc*span,max:ref+(1-loc)*span};
   this.queueDraw();
 }
 onWheel(e){
   const point=this.local(e);
   e.preventDefault();
   const multiplier=e.deltaMode===1?16:e.deltaMode===2?this.canvas.clientHeight:1;
   const dx=e.deltaX*multiplier,dy=e.deltaY*multiplier;
   if(this.inPriceAxis(point)){
     this.zoomPriceAt(Math.exp(Math.max(-.45,Math.min(.45,dy*.002))),point.y);
   }else if((Math.abs(dx)>Math.abs(dy)*.68&&!e.ctrlKey)||e.shiftKey){
     this.panByPixels(e.shiftKey&&dx===0?-dy:dx);
   }else{
     this.smoothZoomAt(Math.exp(Math.max(-.5,Math.min(.5,dy*.0015))),point.x);
   }
   this.cursor=point;
   this.queueDraw();
 }
 onPointerDown(e){
   if(e.pointerType==="mouse"&&e.button!==0)return;
   this.stopInertia();this.stopZoom();
   const pos=this.local(e),now=global.performance.now();
   this.pointers.set(e.pointerId,{...pos,type:e.pointerType});
   try{this.canvas.setPointerCapture(e.pointerId);}catch(_err){}
   if(this.pointers.size>=2){
     const pts=Array.from(this.pointers.values()).slice(0,2);
     const cx=(pts[0].x+pts[1].x)/2,cy=(pts[0].y+pts[1].y)/2;
     this.pinch={distance:Math.max(10,Math.hypot(pts[1].x-pts[0].x,pts[1].y-pts[0].y)),
       centerX:cx,centerY:cy,start:{...this.view},scale:this.manualPriceRange?{...this.manualPriceRange}:null};
     this.drag=null;this.cursor=null;this.suppressNextClick=true;return;
   }
   this.drag={id:e.pointerId,startX:pos.x,startY:pos.y,lastX:pos.x,lastTime:now,
     velocity:0,active:false,mode:this.inPriceAxis(pos)?"price":"pan",
     start:{...this.view},priceRange:this.manualPriceRange?{...this.manualPriceRange}:this.axis?{min:this.axis.min,max:this.axis.max}:null};
   this.cursor=pos;
   this.queueDraw();
 }
 onPointerMove(e){
   const pos=this.local(e),now=global.performance.now();
   if(this.pointers.has(e.pointerId))this.pointers.set(e.pointerId,{...pos,type:e.pointerType});
   if(this.pointers.size>=2&&this.pinch){
     const pts=Array.from(this.pointers.values()).slice(0,2);
     const dist=Math.max(10,Math.hypot(pts[1].x-pts[0].x,pts[1].y-pts[0].y));
     const centerX=(pts[0].x+pts[1].x)/2;
     const f=Math.max(0,Math.min(1,(this.pinch.centerX-13)/this.plotWidth));
     const currentF=Math.max(0,Math.min(1,(centerX-13)/this.plotWidth));
     const orig=this.pinch.start;
     this.view.count=Math.max(12,Math.min(this.totalBars+14,orig.count*this.pinch.distance/dist));
     // Pinch center may translate as well as zoom. Keep the original date below the fingers.
     const dateAtStart=orig.start+f*orig.count;
     this.view.start=dateAtStart-currentF*this.view.count;
     this.clampView();this.queueDraw();return;
   }
   const drag=this.drag;
   if(drag&&drag.id===e.pointerId){
     const total=Math.hypot(pos.x-drag.startX,pos.y-drag.startY);
     if(total>3)drag.active=true;
     if(drag.active&&drag.mode==="pan"){
       this.view.start=drag.start.start-(pos.x-drag.startX)/this.plotWidth*this.view.count;
       this.clampView();
       const elapsed=Math.max(1,now-drag.lastTime);
       const velocity=(drag.lastX-pos.x)/this.plotWidth*this.view.count/elapsed;
       if(elapsed<130)drag.velocity=drag.velocity*.35+velocity*.65;
     }else if(drag.active&&drag.mode==="price"&&drag.priceRange&&this.axis){
       const base=drag.priceRange,oldSpan=base.max-base.min;
       const factor=Math.exp(Math.max(-2,Math.min(2,(pos.y-drag.startY)*.009)));
       const span=oldSpan*factor,frac=Math.max(0,Math.min(1,(this.axis.bottom-drag.startY)/(this.axis.bottom-this.axis.top)));
       const anchor=base.min+oldSpan*frac;
       this.manualPriceRange={min:anchor-span*frac,max:anchor+span*(1-frac)};
     }
     drag.lastX=pos.x;drag.lastTime=now;
     this.cursor=pos;this.canvas.style.cursor=drag.mode==="price"?"ns-resize":"grabbing";this.queueDraw();return;
   }
   if(e.pointerType!=="touch"){this.cursor=pos;this.canvas.style.cursor=this.inPriceAxis(pos)?"ns-resize":"crosshair";}
   this.queueDraw();
 }
 onPointerUp(e,cancel=false){
   const drag=this.drag;
   const wasPinching=!!this.pinch;
   this.pointers.delete(e.pointerId);
   try{if(this.canvas.hasPointerCapture(e.pointerId))this.canvas.releasePointerCapture(e.pointerId);}catch(_err){}
   if(wasPinching){
     this.suppressNextClick=true;
     if(this.pointers.size<2){this.pinch=null;this.drag=null;}
   }else if(drag&&drag.id===e.pointerId){
     if(drag.active){
       this.suppressNextClick=true;
       if(!cancel&&drag.mode==="pan"&&!this.reduceMotion&&global.performance.now()-drag.lastTime<85){
         this.startInertia(drag.velocity);
       }
     }
     this.drag=null;
   }
   this.canvas.style.cursor="crosshair";
   if(cancel||e.pointerType==="touch"){this.cursor=null;this.tooltip.style.display="none";}
   this.queueDraw();
 }
 startInertia(initialVelocity){
   if(!Number.isFinite(initialVelocity)||Math.abs(initialVelocity)<.004)return;
   let v=Math.max(-.14,Math.min(.14,initialVelocity)),previous=null;
   const tick=time=>{
     const dt=previous===null?16:Math.max(0,Math.min(40,time-previous));
     previous=time;
     const before=this.view.start;
     this.view.start+=v*dt;this.clampView();
     v*=Math.exp(-dt/150);
     this.queueDraw();
     if(Math.abs(v)<.0003||Math.abs(before-this.view.start)<1e-9){
       this.inertiaFrame=null;return;
     }
     this.inertiaFrame=global.requestAnimationFrame(tick);
   };
   this.inertiaFrame=global.requestAnimationFrame(tick);
 }
 onKey(e){
   const key=e.key;
   if(!["ArrowLeft","ArrowRight","ArrowUp","ArrowDown","+","=","-","Home","End","Escape"].includes(key))return;
   e.preventDefault();
   if(key==="ArrowLeft")this.panByPixels(this.plotWidth*.14);
   if(key==="ArrowRight")this.panByPixels(-this.plotWidth*.14);
   if(key==="ArrowUp"||key==="+"||key==="=")this.zoomAt(.8,13+this.plotWidth/2);
   if(key==="ArrowDown"||key==="-")this.zoomAt(1.25,13+this.plotWidth/2);
   if(key==="Home")this.resetZoom();
   if(key==="End")this.fitFullYear();
   if(key==="Escape")this.resetPriceScale();
 }
 resetPriceScale(){this.manualPriceRange=null;this.queueDraw();}
 selectAt(e){
   const {result,view,day}=this.state;
   if(!result||view==="all"||!this.axis)return;
   const a=this.axis,idx=Math.round((e.offsetX-a.pad.l)/a.graphW*this.view.count+this.view.start-.5);
   const d=idx-this.originIdx;
   if(d<0||d>Math.floor(day)||d>result.settings.horizon)return;
   const paths=result.models[view].paths.slice(0,16);let closest=-1,dist=Infinity;
   for(let k=0;k<paths.length;k++){
     const gap=Math.abs(a.y(paths[k].values[d])-e.offsetY);
     if(gap<dist){dist=gap;closest=k;}
   }
   this.selectedPath=dist<=19?{model:view,index:closest}:null;
   if(typeof this.onSelectPath==="function")this.onSelectPath(this.selectedPath);
   this.queueDraw();
 }
 fitFullYear(){
   this.stopInertia();this.stopZoom();this.view={start:0,count:this.candles.length};
   this.manualPriceRange=null;this.clampView();this.draw();
 }
 resetZoom(){
   this.stopInertia();this.stopZoom();
   this.view={start:0,count:Math.max(61,this.originIdx+this.state.horizon+1)};
   this.manualPriceRange=null;this.clampView();this.draw();
 }
 update(changes){
   Object.assign(this.state,changes);
   this.clampView();this.draw();
 }
 draw(){
  const c=this.canvas,w=c.clientWidth,h=c.clientHeight;if(!w||!h)return;
  const dpr=Math.min(2,global.devicePixelRatio||1);const pixelW=Math.round(w*dpr),pixelH=Math.round(h*dpr);
  if(c.width!==pixelW||c.height!==pixelH){c.width=pixelW;c.height=pixelH;}
  const g=c.getContext("2d");g.setTransform(dpr,0,0,dpr,0,0);g.clearRect(0,0,w,h);
  const pad={l:13,r:77,t:22,b:37};const P={top:pad.t,bottom:h-94};const volumeTop=h-82,volumeBottom=h-35;
  const graphW=w-pad.l-pad.r,x=i=>pad.l+((i-this.view.start+.5)/this.view.count)*graphW;
  const barW=Math.max(2,Math.min(18,graphW/this.view.count*.65));
  const leftIndex=Math.floor(this.view.start)-1,rightIndex=Math.ceil(this.view.start+this.view.count)+1;
  const {result,day,view,reveal,threshold,horizon}=this.state;
  const displayed=view==="all"?["gbm","markov","ewma"]:[view];
  const values=[];
  for(let i=Math.max(0,leftIndex);i<=Math.min(this.candles.length-1,rightIndex);i++){
    if(i<=this.originIdx||reveal){let row=this.candles[i];values.push(row.low,row.high);}
  }
  if(result)for(let m of displayed){let bs=result.models[m].bands;for(let d=0;d<bs.length;d++){const i=this.originIdx+d;if(i>=leftIndex&&i<=rightIndex)values.push(bs[d][0],bs[d][4]);}}
  // Autoscale to visible candles and the displayed forecast. A far-away loss
  // threshold must not compress real BTC candles into a tiny flat line.
  if(this.originIdx>=leftIndex&&this.originIdx<=rightIndex)values.push(93576);
  if(!values.length)values.push(93576*.9,93576*1.1);
  let min=Math.min(...values),max=Math.max(...values);
  const span=Math.max(300,max-min);
  min-=span*.07;max+=span*.07;
  if(this.manualPriceRange){min=this.manualPriceRange.min;max=this.manualPriceRange.max;}
  const y=v=>P.bottom-(v-min)/(max-min)*(P.bottom-P.top);
  const priceAtY=py=>min+(P.bottom-py)/(P.bottom-P.top)*(max-min);
  this.axis={y,priceAtY,pad,graphW,min,max,top:P.top,bottom:P.bottom};
  const regionStart=Math.max(pad.l,x(this.originIdx)+barW/2);
  g.fillStyle="#192b43";g.globalAlpha=.33;g.fillRect(regionStart,P.top,Math.max(0,w-pad.r-regionStart),volumeBottom-P.top);g.globalAlpha=1;
  g.font="11px ui-sans-serif,system-ui,sans-serif";g.textBaseline="middle";g.textAlign="right";
  for(let k=0;k<=5;k++){const val=min+(max-min)*k/5,yy=y(val);g.strokeStyle="#233348";g.lineWidth=1;g.beginPath();g.moveTo(pad.l,yy);g.lineTo(w-pad.r,yy);g.stroke();g.fillStyle="#90a6bb";g.fillText(Math.round(val).toLocaleString("en-US"),w-8,yy);}
  g.fillStyle="#748da5";g.fillText("USDT",w-10,13);
  let maxVolume=1;for(let i=Math.max(0,leftIndex);i<=Math.min(this.candles.length-1,rightIndex);i++)if(i<=this.originIdx||reveal)maxVolume=Math.max(maxVolume,this.candles[i].volume);
  g.fillStyle="#90a7bd";g.textAlign="left";g.font="10px ui-sans-serif,system-ui";g.fillText("VOLUME",pad.l,volumeTop+3);
  for(let i=Math.max(0,leftIndex);i<=Math.min(this.candles.length-1,rightIndex);i++){
   if(i>this.originIdx&&!reveal)continue;
   const row=this.candles[i],xx=x(i);if(xx<pad.l-18||xx>w-pad.r+18)continue;
   const up=row.close>=row.open,col=up?"#31cbaa":"#e37686";
   const height=(row.volume/maxVolume)*30;
   g.fillStyle=up?"#267d72a0":"#9c4d5f99";g.fillRect(xx-barW/2,volumeBottom-height,barW,height);
   g.lineWidth=Math.max(1,barW*.16);g.strokeStyle=col;g.beginPath();g.moveTo(xx,y(row.high));g.lineTo(xx,y(row.low));g.stroke();
   g.fillStyle=col;g.fillRect(xx-barW/2,Math.min(y(row.open),y(row.close)),barW,Math.max(1.6,Math.abs(y(row.open)-y(row.close))));
  }
  // Forecast fan and median: percentile bands include ALL simulated paths, never just visible traces.
  const colors={gbm:"#66b2ff",markov:"#f0c274",ewma:"#42d6b9"};
  const dmax=Math.min(horizon,day);
  if(result&&dmax>.001){
   for(let m of displayed){
    const model=result.models[m],band=model.bands;const maxWhole=Math.floor(dmax);const fractional=dmax-maxWhole;
    const samples=view==="all"?4:16;const visible=model.paths.slice(0,samples);
    const interpolate=(d,col)=>{if(d<=maxWhole)return band[d][col];return band[maxWhole][col]*(1-fractional)+band[Math.min(maxWhole+1,band.length-1)][col]*fractional;};
    function iterate(fn){for(let d=0;d<=maxWhole;d++)fn(d,d);if(fractional>0)fn(dmax,dmax);}
    // The fan represents 5th–95th price percentiles, NOT a forecast-mean confidence interval.
    g.save();g.beginPath();iterate((d,ix)=>{const xx=x(this.originIdx+d),yy=y(interpolate(ix,4));if(d===0)g.moveTo(xx,yy);else g.lineTo(xx,yy);});
    for(let d=dmax;d>=0;){const ix=d;g.lineTo(x(this.originIdx+ix),y(interpolate(ix,0)));if(d===dmax&&fractional>0)d=maxWhole;else d--;}
    g.closePath();g.fillStyle=colors[m];g.globalAlpha=view==="all"?.065:.17;g.fill();g.restore();
    if(view!=="all"){
      g.save();g.strokeStyle=colors[m];g.globalAlpha=.24;g.lineWidth=.9;
      for(let obj of visible){const path=obj.values;g.beginPath();iterate((d,ix)=>{let ix0=Math.floor(ix),frac=ix-ix0;const price=path[ix0]*(1-frac)+path[Math.min(ix0+1,path.length-1)]*frac;const xx=x(this.originIdx+d),yy=y(price);d===0?g.moveTo(xx,yy):g.lineTo(xx,yy);});g.stroke();}
      g.restore();
    }
    g.save();g.strokeStyle=colors[m];g.lineWidth=view==="all"?2.3:3;g.lineJoin="round";g.lineCap="round";
    g.beginPath();iterate((d,ix)=>{const xx=x(this.originIdx+d),yy=y(interpolate(ix,2));d===0?g.moveTo(xx,yy):g.lineTo(xx,yy);});g.stroke();g.restore();
   }
  }
  // Emphasize the individually selected simulated trajectory; model states color Markov segments.
  if(result&&this.selectedPath&&displayed.includes(this.selectedPath.model)&&dmax>.001){
    const {model,index}=this.selectedPath,record=result.models[model].paths[index];
    if(record){const end=Math.floor(dmax);g.save();g.lineWidth=2.9;g.lineCap="round";
      for(let d=1;d<=end;d++){
        g.strokeStyle=model==="markov"?(record.states[d-1]===0?"#36d9b2":"#ff8090"):"#f4fcff";
        g.beginPath();g.moveTo(x(this.originIdx+d-1),y(record.values[d-1]));g.lineTo(x(this.originIdx+d),y(record.values[d]));g.stroke();
      }
      g.fillStyle="#fff";g.beginPath();g.arc(x(this.originIdx+end),y(record.values[end]),4,0,Math.PI*2);g.fill();g.restore();
    }
  }
  // Investment threshold as a constant price level.
  const limit=93576*(1-threshold);
  const limitY=y(limit);if(limitY>=P.top&&limitY<=P.bottom){
    g.save();g.setLineDash([6,5]);g.strokeStyle="#ed8c98";g.lineWidth=1.15;g.beginPath();g.moveTo(pad.l,limitY);g.lineTo(w-pad.r,limitY);g.stroke();g.restore();
    g.fillStyle="#ff9fa9";g.textAlign="right";g.font="10px ui-sans-serif,system-ui";g.fillText("LOSS "+Math.round(threshold*100)+"%",w-8,limitY-12);
  }
  // The point of transition is always real and date labelled. The observed 2025
  // candles may extend beyond the forecast, which deliberately stops at its horizon.
  const sep=x(this.originIdx+.5);g.save();g.setLineDash([3,5]);g.strokeStyle="#88a9c6";g.lineWidth=1.3;g.beginPath();g.moveTo(sep,P.top);g.lineTo(sep,volumeBottom);g.stroke();g.restore();
  if(sep>0&&sep<w){g.textAlign="center";g.fillStyle="#b5cbdd";g.font="10px ui-sans-serif,system-ui";g.fillText("FORECAST ORIGIN",Math.max(80,Math.min(w-110,sep+59)),P.top+10);}
  // Month/date ticks.
  const n=Math.max(this.candles.length,this.originIdx+horizon+1),stride=Math.max(1,Math.ceil(this.view.count/7));g.textAlign="center";g.fillStyle="#9aaec1";g.font="10px ui-sans-serif,system-ui";
  for(let i=0;i<n;i+=stride){const xx=x(i);if(xx<22||xx>w-pad.r)continue;const date=new Date(Date.UTC(2024,11,1+i)).toISOString().slice(5,10);g.fillText(date,xx,h-17);}
  // Full crosshair: the right-hand price label is the exact inverse of the
  // vertical pixel coordinate, with the same scale as the actual candles.
  const cursor=this.cursor;
  const cursorInTime=!!cursor&&cursor.x>=pad.l&&cursor.x<=w-pad.r;
  const cursorInPrice=!!cursor&&cursor.y>=P.top&&cursor.y<=P.bottom;
  this.crosshairPrice=cursorInPrice?priceAtY(cursor.y):null;
  if(cursorInTime||cursorInPrice){
    g.save();
    g.setLineDash([4,4]);
    g.strokeStyle="#abc7df95";
    g.lineWidth=1;
    if(cursorInTime){
      g.beginPath();g.moveTo(cursor.x,P.top);g.lineTo(cursor.x,volumeBottom);g.stroke();
    }
    if(cursorInPrice){
      g.beginPath();g.moveTo(pad.l,cursor.y);g.lineTo(w-pad.r,cursor.y);g.stroke();
    }
    g.restore();
    if(cursorInPrice){
      const price=priceAtY(cursor.y);
      const value=price.toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2});
      const labelTop=Math.max(P.top+1,Math.min(P.bottom-22,cursor.y-11));
      g.fillStyle="#327ca4";
      g.fillRect(w-pad.r,labelTop,pad.r,22);
      g.strokeStyle="#76b9df";
      g.strokeRect(w-pad.r+.5,labelTop+.5,pad.r-1,21);
      g.font="700 11px ui-sans-serif,system-ui";
      g.textBaseline="middle";
      g.textAlign="right";
      g.fillStyle="#ffffff";
      g.fillText(value,w-5,labelTop+11);
    }
    if(cursorInTime){
      const index=Math.round((cursor.x-pad.l)/graphW*this.view.count+this.view.start-.5);
      const date=new Date(Date.UTC(2024,11,1+index)).toISOString().slice(0,10);
      const dateX=Math.min(w-pad.r-44,Math.max(pad.l+44,cursor.x));
      g.fillStyle="#294b66";
      g.fillRect(dateX-42,h-32,84,23);
      g.textAlign="center";
      g.font="700 10px ui-sans-serif,system-ui";
      g.fillStyle="#effaff";
      g.fillText(date,dateX,h-20);
      const parts=[date];
      if(index>=0&&index<this.candles.length&&(index<=this.originIdx||reveal)){
        const row=this.candles[index];
        parts.push("OBSERVED Binance daily candle",
          "O "+row.open.toLocaleString()+"   H "+row.high.toLocaleString(),
          "L "+row.low.toLocaleString()+"   C "+row.close.toLocaleString());
      }else if(index>this.originIdx&&result&&index<=this.originIdx+Math.floor(dmax)){
        parts.push("SIMULATED closing-price percentiles");
        for(let m of displayed){
          const b=result.models[m].bands[index-this.originIdx];
          parts.push(m.toUpperCase()+" median "+Math.round(b[2]).toLocaleString()+" USDT",
            "  5th–95th "+Math.round(b[0]).toLocaleString()+" – "+Math.round(b[4]).toLocaleString());
        }
      }else parts.push("Future region · no observed candle displayed");
      this.tooltip.textContent=parts.join("\n");
      this.tooltip.style.display="block";
      this.tooltip.style.left=Math.max(6,Math.min(w-235,cursor.x+12))+"px";
      this.tooltip.style.top=Math.max(7,Math.min(h-132,cursor.y+10))+"px";
    }else this.tooltip.style.display="none";
  }else this.tooltip.style.display="none";
 }
}
global.CRLForecastChart=ForecastChart;
})(window);
