/* Trading-style canvas chart: observed OHLC + scientifically labelled model forecast overlays.
   Self-contained and file:// compatible. No synthetic "future candles". */
(function(global){"use strict";
class ForecastChart {
 constructor(canvas,tooltip){
  this.canvas=canvas;this.tooltip=tooltip;this.candles=global.CRL_HISTORY.candles;
  this.originIdx=this.candles.findIndex(c=>c.date==="2024-12-31");
  if(this.originIdx<0||this.candles[this.originIdx].close!==93576)throw Error("Historical candle origin mismatch");
  this.view={start:0,count:61};this.cursor=null;this.drag=null;this.selectedPath=null;this.onSelectPath=null;
  this.state={result:null,day:0,view:"all",reveal:false,threshold:.10,horizon:30};
  this.canvas.addEventListener("wheel",e=>{e.preventDefault();const b=this.canvas.getBoundingClientRect();let anchor=(e.clientX-b.left-55)/Math.max(10,b.width-135);anchor=Math.max(0,Math.min(1,anchor));const old=this.view.count;let next=Math.max(16,Math.min(115,old*(e.deltaY>0?1.13:.87)));this.view.start+=anchor*(old-next);this.view.count=next;this.clampView();this.draw();},{passive:false});
  this.canvas.addEventListener("pointerdown",e=>{this.drag={x:e.clientX,start:this.view.start};this.canvas.setPointerCapture(e.pointerId);});
  this.canvas.addEventListener("pointermove",e=>{const b=this.canvas.getBoundingClientRect();const x=e.clientX-b.left,y=e.clientY-b.top;if(this.drag){this.view.start=this.drag.start-(e.clientX-this.drag.x)/(b.width-135)*this.view.count;this.clampView();this.cursor=null;}else this.cursor={x,y};this.draw();});
  this.canvas.addEventListener("pointerup",()=>{this.drag=null;});
  this.canvas.addEventListener("pointercancel",()=>{this.drag=null;});
  this.canvas.addEventListener("pointerleave",()=>{this.cursor=null;this.drag=null;this.tooltip.style.display="none";this.draw();});
  this.canvas.addEventListener("dblclick",()=>this.resetZoom());
  this.canvas.addEventListener("click",e=>this.selectAt(e));
  if("ResizeObserver" in global){this.ro=new ResizeObserver(()=>this.draw());this.ro.observe(canvas);}else global.addEventListener("resize",()=>this.draw());
 }
 selectAt(e){
  const {result,view,day}=this.state;
  if(!result||view==="all"||!this.axis)return;
  const a=this.axis,idx=Math.round((e.offsetX-a.pad.l)/a.graphW*this.view.count+this.view.start-.5);
  const d=idx-this.originIdx;
  if(d<0||d>Math.floor(day)||d>result.settings.horizon)return;
  const paths=result.models[view].paths.slice(0,16);let closest=-1,dist=Infinity;
  for(let k=0;k<paths.length;k++){const gap=Math.abs(a.y(paths[k].values[d])-e.offsetY);if(gap<dist){dist=gap;closest=k;}}
  this.selectedPath=dist<=19?{model:view,index:closest}:null;
  if(typeof this.onSelectPath==="function")this.onSelectPath(this.selectedPath);
  this.draw();
 }
 resetZoom(){this.view={start:0,count:Math.max(61,this.originIdx+this.state.horizon+1)};this.clampView();this.draw();}
 clampView(){const n=Math.max(this.candles.length,this.originIdx+this.state.horizon+1);this.view.start=Math.max(-.3,Math.min(n-this.view.count+.3,this.view.start));}
 update(changes){Object.assign(this.state,changes);this.clampView();this.draw();}
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
  if(!values.length)values.push(93576*.75,93576*1.25);
  values.push(93576,93576*(1-threshold));
  let min=Math.min(...values),max=Math.max(...values);const span=Math.max(250,max-min);min-=span*.095;max+=span*.095;
  const y=v=>P.bottom-(v-min)/(max-min)*(P.bottom-P.top);
  this.axis={y,pad,graphW};
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
  // The point of transition is always real and date labelled.
  const sep=x(this.originIdx+.5);g.save();g.setLineDash([3,5]);g.strokeStyle="#88a9c6";g.lineWidth=1.3;g.beginPath();g.moveTo(sep,P.top);g.lineTo(sep,volumeBottom);g.stroke();g.restore();
  if(sep>0&&sep<w){g.textAlign="center";g.fillStyle="#b5cbdd";g.font="10px ui-sans-serif,system-ui";g.fillText("FORECAST ORIGIN",Math.max(80,Math.min(w-110,sep+59)),P.top+10);}
  // Month/date ticks.
  const n=Math.max(this.candles.length,this.originIdx+horizon+1),stride=Math.max(1,Math.ceil(this.view.count/7));g.textAlign="center";g.fillStyle="#9aaec1";g.font="10px ui-sans-serif,system-ui";
  for(let i=0;i<n;i+=stride){const xx=x(i);if(xx<22||xx>w-pad.r)continue;const date=new Date(Date.UTC(2024,11,1+i)).toISOString().slice(5,10);g.fillText(date,xx,h-17);}
  if(this.cursor&&this.cursor.x>=pad.l&&this.cursor.x<=w-pad.r){
   const index=Math.round((this.cursor.x-pad.l)/graphW*this.view.count+this.view.start-.5),cx=x(index);
   g.save();g.setLineDash([3,4]);g.strokeStyle="#b6c7d7aa";g.beginPath();g.moveTo(cx,P.top);g.lineTo(cx,volumeBottom);if(this.cursor.y>=P.top&&this.cursor.y<P.bottom){g.moveTo(pad.l,this.cursor.y);g.lineTo(w-pad.r,this.cursor.y);}g.stroke();g.restore();
   const date=new Date(Date.UTC(2024,11,1+index)).toISOString().slice(0,10);
   let parts=[date];
   if(index>=0&&index<this.candles.length&&(index<=this.originIdx||reveal)){
    const row=this.candles[index];parts.push("OBSERVED Binance daily candle","O "+row.open.toLocaleString()+"   H "+row.high.toLocaleString(),"L "+row.low.toLocaleString()+"   C "+row.close.toLocaleString());
   }else if(index>this.originIdx&&result&&index<=this.originIdx+Math.floor(dmax)){
    parts.push("SIMULATED close percentiles");
    for(let m of displayed){const b=result.models[m].bands[index-this.originIdx];parts.push(m.toUpperCase()+" median "+Math.round(b[2]).toLocaleString()+" USDT","  5th–95th "+Math.round(b[0]).toLocaleString()+" – "+Math.round(b[4]).toLocaleString());}
   }else parts.push("Future region · no actual candle displayed");
   this.tooltip.textContent=parts.join("\n");this.tooltip.style.display="block";this.tooltip.style.left=Math.max(6,Math.min(w-235,this.cursor.x+12))+"px";this.tooltip.style.top=Math.max(7,Math.min(h-120,this.cursor.y+10))+"px";
  }else this.tooltip.style.display="none";
 }
}
global.CRLForecastChart=ForecastChart;
})(window);
