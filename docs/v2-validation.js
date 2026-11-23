/* Predictions vs Reality: authentic notebook-exported 2025 evaluation.
 * Does not refit the frozen model, alter the existing simulation, or use 2025
 * future returns for predicted values. 30-day price fans are independently
 * simulated ILLUSTRATIONS using known origin states; archival probabilities
 * remain the only values used for scoring. Runs offline with file://.
 */
(function(global){"use strict";
const data=global.CRL_VALIDATION, core=global.CRLCore, history=global.CRL_HISTORY;
const $=id=>document.getElementById(id);
if(!data||!core||!history){
 const msg=$("rvDataProvenance");
 if(msg)msg.textContent="Verified per-origin notebook data has not been bundled. Historical forecast explorer is unavailable in this build.";
 return;
}
const rows=data.rows,thresholds=data.meta.thresholds,models=["gbm","markov","ewma"];
const labels={gbm:"GBM",markov:"Original Markov",ewma:"EWMA",historical:"Historical frequency"};
const colors={gbm:"#63aafd",markov:"#efbd6a",ewma:"#35d4ac",historical:"#a5b5c9"};
const fmt=n=>Number(n).toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2});
const pct=n=>(Number(n)*100).toFixed(2)+"%";
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const dateUTC=(date,offset=0)=>new Date(new Date(date+"T00:00:00Z").getTime()+offset*86400000).toISOString().slice(0,10);
const reducedMotion=!!global.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
if(rows.length!==335||rows[0].date!=="2025-01-01"||rows.at(-1).date!=="2025-12-01")throw Error("Notebook forecast-origin export failed structural checks");
if(history.candles.length!==396)throw Error("Observed 2025 historical candles missing");
const byDate=new Map(history.candles.map((r,i)=>[r.date,i]));
for(const [i,r] of rows.entries()){
 if(r.end!==dateUTC(r.date,30))throw Error("Forecast window violates 30-day horizon at "+i);
 const start=history.candles[byDate.get(r.date)],end=history.candles[byDate.get(r.end)];
 if(!start||!end||Math.abs(start.close-r.price)>.011||Math.abs(end.close-r.future)>.011)
   throw Error("Notebook forecast outcome disagrees with bundled real BTC candles at "+r.date);
 const event=thresholds.map(t=>Number(1-r.future/r.price>=t/100));
 if(r.events.some((e,j)=>e!==event[j]))throw Error("Actual outcome mismatch at "+r.date);
}
const state={index:0,threshold:10,revealDay:0,view:"all",playing:false,lastTick:null,frame:null,hoverIndex:null,hoverDay:null};
const fanCache=new Map();
const bandN=1800;
function rng(seed){let x=seed>>>0;return ()=>{x=(x+0x6d2b79f5)|0;let t=Math.imul(x^(x>>>15),x|1);t^=t+Math.imul(t^(t>>>7),t|61);return ((t^(t>>>14))>>>0)/4294967296;};}
function normal(uniform){
 let spare=null;
 return ()=>{if(spare!==null){const x=spare;spare=null;return x;}
   let u=0;while(!u)u=uniform();
   const v=uniform(),k=Math.sqrt(-2*Math.log(u));
   spare=k*Math.sin(2*Math.PI*v);
   return k*Math.cos(2*Math.PI*v);
 };
}
function bandsFor(index){
 if(fanCache.has(index))return fanCache.get(index);
 const row=rows[index],c=core.CAL,H=30,fan={};
 for(const [m,model] of models.entries()){
   const byDay=Array.from({length:H+1},()=>new Float64Array(bandN));
   const gaussian=normal(rng((0x9e3779b9+(index*0x85ebca6b)^(m*0xc2b2ae35))>>>0));
   const transitions=rng((0x7f4a7c15^(index*11939)^(m*137))>>>0);
   byDay[0].fill(row.price);
   for(let k=0;k<bandN;k++){
     let price=row.price,variance=row.variance,regime=row.regime;
     for(let day=1;day<=H;day++){
       let r=0;
       if(model==="gbm")r=c.gbm.mu+c.gbm.sigma*gaussian();
       else if(model==="markov"){
         r=c.markov.mu[regime]+c.markov.sigma[regime]*gaussian();
         regime=transitions()<c.markov.nextCalm[regime]?0:1;
       }else{
         r=c.ewma.mu+Math.sqrt(Math.max(variance,0))*gaussian();
         variance=.90*variance+.10*(r-c.ewma.mu)**2;
       }
       price*=Math.exp(r);
       byDay[day][k]=price;
     }
   }
   fan[model]=byDay.map(arr=>{
     arr.sort();
     return [.05,.25,.50,.75,.95].map(q=>core.quantile(arr,q));
   });
 }
 fanCache.set(index,fan);
 if(fanCache.size>8)fanCache.delete(fanCache.keys().next().value);
 return fan;
}
function realPath(row){
 const i=byDate.get(row.date);
 return history.candles.slice(i,i+31);
}
function stopReplay(){
 if(state.frame!==null)global.cancelAnimationFrame(state.frame);
 state.frame=null;state.playing=false;state.lastTick=null;
}
function origin(i){
 state.index=clamp(Math.round(i),0,rows.length-1);
 state.revealDay=0;state.hoverDay=null;
 stopReplay();
 $("rvDateSlider").value=String(state.index);
 $("rvReplaySlider").value="0";
 render();
}
function selectThreshold(t){
 if(!thresholds.includes(t))return;
 state.threshold=t;
 document.querySelectorAll("[data-rv-threshold]").forEach(b=>b.setAttribute("aria-pressed",String(Number(b.dataset.rvThreshold)===t)));
 render();
}
function updateUI(){
 const row=rows[state.index],j=thresholds.indexOf(state.threshold),actual=row.events[j]===1;
 $("rvOrigin").textContent=row.date;
 $("rvEnd").textContent="30-day outcome: "+row.end;
 $("rvPrev").disabled=state.index===0;
 $("rvNext").disabled=state.index===334;
 $("rvFindEvent").disabled=data.scores[String(state.threshold)].events===0;
 $("rvActualStatus").textContent=actual?"YES · LOSS OCCURRED":"NO · LOSS DID NOT OCCUR";
 $("rvActualStatus").style.color=actual?"#ff9aa9":"#64dfb8";
 const actualLoss=(1-row.future/row.price)*100;
 $("rvOutcome").className="rv-outcome "+(actual?"rv-outcome--loss":"rv-outcome--safe");
 $("rvOutcome").textContent="Actual 30-day return: "+(actualLoss<=0?"+":"−")+Math.abs(actualLoss).toFixed(2)+"%"+(actual?" · Loss ≥"+state.threshold+"% happened.":" · Loss ≥"+state.threshold+"% did not happen.");
 $("rvPredictionExplanation").textContent="These are notebook-recorded 30-day forecasts for "+row.date+", scored against a binary "+(actual?"YES":"NO")+" event. A single result cannot establish model accuracy.";
 const colorsMap={gbm:colors.gbm,markov:colors.markov,ewma:colors.ewma,historical:colors.historical};
 $("rvPredictionBars").innerHTML=["gbm","markov","ewma","historical"].map(m=>{
   const p=row.p[m][j],label=labels[m];
   return '<div class="rv-bar-row"><div class="rv-bar-head"><span>'+label+'</span><strong>'+pct(p)+'</strong></div>'+
    '<div class="rv-bar-track"><div class="rv-bar-fill" style="width:'+clamp(p*100,0,100)+'%;background:'+colorsMap[m]+'"></div></div></div>';
 }).join("");
 $("rvRegime").textContent=row.regime===0?"Calm":"Volatile";
 $("rvStartPrice").textContent=fmt(row.price)+" USDT";
 $("rvDayLabel").textContent="Day "+state.revealDay+" / 30";
 $("rvPlay").textContent=state.playing?"Ⅱ Pause actual replay":"▶ Play actual outcome";
 const complete=state.revealDay===30;
 $("rvFinalPrice").textContent=complete?fmt(row.future)+" USDT":"Hidden until day 30";
 const ret=row.future/row.price-1;
 $("rvReturn").textContent=complete?((ret>=0?"+":"")+pct(ret)):"Hidden until day 30";
 $("rvReturn").className=complete?(ret>=0?"rv-positive":"rv-negative"):"";
 const shownPrice=realPath(row)[state.revealDay].close;
 $("rvReplayStatus").textContent=complete
   ?"Actual outcome revealed: "+row.end+" BTC close "+fmt(row.future)+" USDT. Forecasts were calculated without using these future prices."
   :"Actual closes revealed through day "+state.revealDay+": "+fmt(shownPrice)+" USDT. Future observed prices remain concealed on the replay.";
 $("rvReplaySlider").value=String(state.revealDay);
 $("rvDataProvenance").textContent=data.meta.origins+" forecast dates. "+data.meta.source+
   ". Original Markov forecast uses "+data.meta.markovPathsPerState.toLocaleString()+" Monte Carlo paths per initial state; "+
   "EWMA uses "+data.meta.ewmaPathsPerOrigin.toLocaleString()+" paths per forecast origin. The 2025 windows overlap and were evaluated retrospectively.";
}
function updateScores(){
 const key=String(state.threshold),summary=data.scores[key];
 $("rvScoreSummary").textContent="Observed loss events: "+summary.events+" / "+data.meta.origins+
   " windows ("+pct(summary.observed)+"). This compares the full year, not just the selected forecast.";
 const order=["historical","gbm","markov","ewma"];
 const biggest=Math.max(...order.map(m=>summary.models[m].brier));
 $("rvScoreBars").innerHTML=order.map(m=>{
   const v=summary.models[m].brier;
   return '<div class="rv-score-row"><span>'+labels[m]+'</span><div class="rv-bar-track"><div class="rv-bar-fill" style="width:'+
     (v/biggest*100).toFixed(3)+'%;background:'+colors[m]+'"></div></div><strong>'+v.toFixed(6)+'</strong></div>';
 }).join("");
 $("rvScoreTable").querySelector("tbody").innerHTML=order.map(m=>
   "<tr><td>"+labels[m]+"</td><td>"+pct(summary.models[m].mean)+"</td><td>"+summary.models[m].brier.toFixed(6)+"</td></tr>"
 ).join("");
 const markov=summary.models.markov.brier,gbm=summary.models.gbm.brier;
 const diff=markov-gbm,ci=data.bootstrap.find(x=>x.threshold===">="+state.threshold+"%"&&x.compared==="Original Markov"&&x.reference==="GBM");
 $("rvBrierDifference").textContent="Original Markov − GBM Brier difference: "+(diff>=0?"+":"")+diff.toFixed(6)+". "+(diff<0?"Markov scored slightly lower historically.":"GBM scored lower historically.");
 if(state.threshold===35){
   $("rvEvidenceText").textContent="No 35% terminal losses occurred in the 335 observed windows. Scores at this extreme threshold do not demonstrate useful extreme-loss detection.";
 }else if(ci){
   const overlapsZero=ci.low<=0&&ci.high>=0;
   $("rvEvidenceText").textContent="30-day block-bootstrap 95% interval: ["+ci.low.toFixed(6)+", "+ci.high.toFixed(6)+
     "]. "+(overlapsZero?"The interval crosses zero, so the Markov-versus-GBM advantage is not conclusive.":"The interval excludes zero, but overlapping windows, modelling assumptions and selection require cautious interpretation.")+
     " The historical-frequency baseline is included as a benchmark, not another volatility model.";
 }else{
   $("rvEvidenceText").textContent="Model forecasts come from the same historical test windows. Evaluate forecast accuracy with repeated proper scoring rules, not the prediction nearest to a single outcome.";
 }
}
function fitCanvas(canvas){
 const w=canvas.clientWidth,h=canvas.clientHeight,ratio=Math.min(2,global.devicePixelRatio||1);
 if(!w||!h)return null;
 const W=Math.round(w*ratio),H=Math.round(h*ratio);
 if(canvas.width!==W||canvas.height!==H){canvas.width=W;canvas.height=H;}
 const g=canvas.getContext("2d");
 g.setTransform(ratio,0,0,ratio,0,0);g.clearRect(0,0,w,h);
 g.textBaseline="middle";g.font="11px ui-sans-serif,system-ui";
 return {g,w,h};
}
function line(g,pts,color,width=2,alpha=1){
 if(!pts.length)return;
 g.save();g.strokeStyle=color;g.globalAlpha=alpha;g.lineWidth=width;g.lineJoin="round";g.lineCap="round";
 g.beginPath();
 pts.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));
 g.stroke();g.restore();
}
function drawTimeline(){
 const c=$("rvTimelineChart"),stage=fitCanvas(c);if(!stage)return;
 const {g,w,h}=stage,j=thresholds.indexOf(state.threshold);
 const left=51,right=18,top=21,bottom=h-35,width=w-left-right,height=bottom-top;
 const x=i=>left+i/334*width;
 const maxP=Math.max(.02,...rows.flatMap(row=>models.map(m=>row.p[m][j])))*1.16;
 const upper=Math.min(1,Math.max(.06,maxP));
 const y=p=>bottom-p/upper*height;
 g.textAlign="right";g.fillStyle="#9db2c7";
 for(let k=0;k<=4;k++){
   let yy=top+k/4*height,val=upper*(1-k/4);
   g.strokeStyle="#263b50";g.lineWidth=1;g.beginPath();g.moveTo(left,yy);g.lineTo(w-right,yy);g.stroke();
   g.fillText((val*100).toFixed(0)+"%",left-7,yy);
 }
 for(let k=0;k<=6;k++){
   let idx=Math.round(334*k/6),xx=x(idx);
   g.textAlign="center";g.fillStyle="#9aacbd";g.fillText(rows[idx].date.slice(5),xx,h-15);
 }
 const eventY=bottom-4;
 g.fillStyle="#ee8291";for(let i=0;i<rows.length;i++)if(rows[i].events[j]){
   const xx=x(i);g.fillRect(xx-1,eventY-8,2,8);
 }
 for(let model of models)line(g,rows.map((r,i)=>[x(i),y(r.p[model][j])]),colors[model],model==="ewma"?2:1.8,.9);
 const ix=state.index,xx=x(ix);
 g.save();g.strokeStyle="#e7f4ff";g.setLineDash([4,4]);g.lineWidth=1;g.beginPath();g.moveTo(xx,top);g.lineTo(xx,bottom);g.stroke();g.restore();
 for(let model of models){
   g.fillStyle=colors[model];g.beginPath();g.arc(xx,y(rows[ix].p[model][j]),3.7,0,2*Math.PI);g.fill();
 }
 g.textAlign="center";g.font="700 11px ui-sans-serif,system-ui";
 g.fillStyle="#dae9f8";g.fillText(rows[ix].date,clamp(xx,left+46,w-right-46),top-10);
 if(state.hoverIndex!==null&&state.hoverIndex!==ix){
   const hx=x(state.hoverIndex);g.strokeStyle="#a2b6c86a";g.beginPath();g.moveTo(hx,top);g.lineTo(hx,bottom);g.stroke();
 }
}
function drawReplay(){
 const canvas=$("rvReplayChart"),stage=fitCanvas(canvas);if(!stage)return;
 const {g,w,h}=stage,row=rows[state.index],actual=realPath(row),fan=bandsFor(state.index);
 const left=64,right=80,top=25,bottom=h-42,width=w-left-right,height=bottom-top;
 const x=d=>left+d/30*width;
 const chosen=state.view==="all"?models:[state.view];
 const values=[row.price];
 for(let model of chosen)for(let band of fan[model]){values.push(band[0],band[4]);}
 for(let i=0;i<=state.revealDay;i++)values.push(actual[i].close);
 let min=Math.min(...values),max=Math.max(...values),range=Math.max(200,max-min);
 min-=range*.075;max+=range*.075;
 const y=price=>bottom-(price-min)/(max-min)*height;
 const thresholdPrice=row.price*(1-state.threshold/100);
 if(thresholdPrice>=min&&thresholdPrice<=max){
   g.save();g.setLineDash([5,5]);g.strokeStyle="#ec7e8b80";g.beginPath();g.moveTo(left,y(thresholdPrice));g.lineTo(w-right,y(thresholdPrice));g.stroke();g.restore();
   g.font="10px ui-sans-serif,system-ui";g.fillStyle="#f49fa8";g.textAlign="right";g.fillText("−"+state.threshold+"%",w-5,y(thresholdPrice)-9);
 }
 g.font="11px ui-sans-serif,system-ui";g.fillStyle="#a2b7c7";g.textAlign="right";
 for(let k=0;k<=5;k++){
   const v=min+(max-min)*k/5,yy=y(v);
   g.strokeStyle="#263a4f";g.beginPath();g.moveTo(left,yy);g.lineTo(w-right,yy);g.stroke();
   g.fillText(Math.round(v).toLocaleString("en-US"),w-9,yy);
 }
 g.textAlign="center";
 for(let d=0;d<=30;d+=5){
   const xx=x(d);g.fillStyle="#9bb4ca";g.fillText("Day "+d,xx,h-17);
 }
 const paintFan=(m,alpha)=>{
   const arr=fan[m];
   g.save();g.fillStyle=colors[m];g.globalAlpha=alpha;g.beginPath();
   arr.forEach((b,d)=>d?g.lineTo(x(d),y(b[4])):g.moveTo(x(d),y(b[4])));
   for(let d=30;d>=0;d--)g.lineTo(x(d),y(arr[d][0]));
   g.closePath();g.fill();g.restore();
   if(state.view!=="all"){
     g.save();g.globalAlpha=.09;g.fillStyle=colors[m];g.beginPath();
     arr.forEach((b,d)=>d?g.lineTo(x(d),y(b[3])):g.moveTo(x(d),y(b[3])));
     for(let d=30;d>=0;d--)g.lineTo(x(d),y(arr[d][1]));
     g.closePath();g.fill();g.restore();
   }
 };
 chosen.forEach(m=>paintFan(m,state.view==="all"?.05:.17));
 for(let m of chosen)line(g,fan[m].map((b,d)=>[x(d),y(b[2])]),colors[m],state.view==="all"?2:2.6);
 const actualPts=[];
 for(let d=0;d<=state.revealDay;d++)actualPts.push([x(d),y(actual[d].close)]);
 if(actualPts.length>1){
   line(g,actualPts,"#f5f9ff",2.8,1);
   g.fillStyle="#fff";g.beginPath();g.arc(x(state.revealDay),y(actual[state.revealDay].close),4.2,0,2*Math.PI);g.fill();
 }else{g.fillStyle="#fff";g.beginPath();g.arc(x(0),y(actual[0].close),4,0,2*Math.PI);g.fill();}
 if(state.hoverDay!==null){
   const d=state.hoverDay,xx=x(d);
   g.save();g.setLineDash([3,4]);g.strokeStyle="#c3d5e8a3";g.beginPath();g.moveTo(xx,top);g.lineTo(xx,bottom);g.stroke();g.restore();
   g.fillStyle="#d3e9f7";g.textAlign="left";g.font="10px ui-sans-serif,system-ui";
   const medians=chosen.map(m=>m.toUpperCase()+" median "+fmt(fan[m][d][2])).join(" · ");
   const observed=d<=state.revealDay?" · Actual "+fmt(actual[d].close):" · Actual hidden";
   const txt="Day "+d+" · "+dateUTC(row.date,d)+" · "+medians+observed;
   $("rvReplayStatus").textContent=txt;
 }else updateReplayStatus();
 g.textAlign="right";g.fillStyle="#a4bcd1";g.fillText("USDT",w-7,13);
}
function updateReplayStatus(){
 const row=rows[state.index],shown=realPath(row)[state.revealDay];
 if(state.revealDay===30){
   $("rvReplayStatus").textContent="Actual day-30 closing price: "+fmt(row.future)+" USDT ("+row.end+"). Forecast bands were generated from origin information only.";
 }else{
   $("rvReplayStatus").textContent="Actual closes revealed through day "+state.revealDay+": "+fmt(shown.close)+" USDT. Future observed prices remain concealed.";
 }
}
function render(){
 updateUI();updateScores();drawTimeline();drawReplay();
}
function showDay(d){
 state.revealDay=clamp(Math.round(d),0,30);
 state.hoverDay=null;
 $("rvReplaySlider").value=String(state.revealDay);
 updateUI();drawReplay();
}
function tick(ts){
 if(!state.playing)return;
 if(state.lastTick===null)state.lastTick=ts;
 const elapsed=ts-state.lastTick;
 if(elapsed>=185){
   const steps=Math.max(1,Math.floor(elapsed/185));
   state.lastTick=ts;showDay(state.revealDay+steps);
 }
 if(state.revealDay>=30){stopReplay();updateUI();return;}
 state.frame=global.requestAnimationFrame(tick);
}
function togglePlay(){
 if(state.playing){stopReplay();updateUI();return;}
 if(state.revealDay>=30)showDay(0);
 if(reducedMotion){showDay(30);return;}
 state.playing=true;state.lastTick=null;
 updateUI();state.frame=global.requestAnimationFrame(tick);
}
$("rvPrev").addEventListener("click",()=>origin(state.index-1));
$("rvNext").addEventListener("click",()=>origin(state.index+1));
$("rvDateSlider").addEventListener("input",e=>origin(Number(e.target.value)));
document.querySelectorAll("[data-rv-threshold]").forEach(b=>b.addEventListener("click",()=>selectThreshold(Number(b.dataset.rvThreshold))));
$("rvFindEvent").addEventListener("click",()=>{
 const j=thresholds.indexOf(state.threshold);
 const found=rows.findIndex((r,i)=>i>state.index&&r.events[j]===1);
 const first=rows.findIndex(r=>r.events[j]===1);
 if(found>=0)origin(found);
 else if(first>=0)origin(first);
 else $("rvOutcome").textContent="No ≥"+state.threshold+"% loss events occurred in this evaluation sample.";
});
document.querySelectorAll("[data-rv-model]").forEach(b=>b.addEventListener("click",()=>{
 state.view=b.dataset.rvModel;
 document.querySelectorAll("[data-rv-model]").forEach(x=>x.setAttribute("aria-pressed",String(x===b)));
 drawReplay();
}));
$("rvPlay").addEventListener("click",togglePlay);
$("rvReveal").addEventListener("click",()=>{stopReplay();showDay(30);});
$("rvHide").addEventListener("click",()=>{stopReplay();showDay(0);});
$("rvReplaySlider").addEventListener("input",e=>{stopReplay();showDay(Number(e.target.value));});
$("rvTimelineChart").addEventListener("click",e=>{
 const b=$("rvTimelineChart").getBoundingClientRect(),fraction=clamp((e.clientX-b.left-51)/(b.width-51-18),0,1);
 origin(Math.round(fraction*334));
});
$("rvTimelineChart").addEventListener("pointermove",e=>{
 const b=$("rvTimelineChart").getBoundingClientRect(),fraction=clamp((e.clientX-b.left-51)/(b.width-51-18),0,1);
 state.hoverIndex=Math.round(fraction*334);
 const r=rows[state.hoverIndex],t=thresholds.indexOf(state.threshold);
 $("rvTimelineHover").textContent=r.date+" · GBM "+pct(r.p.gbm[t])+" · Markov "+pct(r.p.markov[t])+
   " · EWMA "+pct(r.p.ewma[t])+" · Actual event: "+(r.events[t]?"Yes":"No");
 drawTimeline();
});
$("rvTimelineChart").addEventListener("pointerleave",()=>{state.hoverIndex=null;$("rvTimelineHover").textContent="Click any date in the chart to inspect its historical forecast.";drawTimeline();});
$("rvReplayChart").addEventListener("pointermove",e=>{
 const b=$("rvReplayChart").getBoundingClientRect();
 state.hoverDay=clamp(Math.round((e.clientX-b.left-64)/(b.width-64-80)*30),0,30);
 drawReplay();
});
$("rvReplayChart").addEventListener("pointerleave",()=>{state.hoverDay=null;drawReplay();});
if("ResizeObserver" in global){
 const ro=new ResizeObserver(()=>{drawTimeline();drawReplay();});
 ro.observe($("rvTimelineChart"));ro.observe($("rvReplayChart"));
}else global.addEventListener("resize",()=>{drawTimeline();drawReplay();});
render();
global.CRLValidation={data,rows,get state(){return {...state};},chooseOrigin:origin,chooseThreshold:selectThreshold,getForecastBands:bandsFor,showDay};
})(window);
