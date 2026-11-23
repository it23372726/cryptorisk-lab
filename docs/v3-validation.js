/* CryptoRisk Lab 2026 holdout: observed BTC closes and notebook-independent,
 * research-ledger model probabilities. Data is immutable. Simulation sliders
 * DO NOT change historic forecasts. No OHLC candles are fabricated for 2026.
 */
(function(global){"use strict";
const data=global.CRL_EVIDENCE_2026,$=id=>global.document.getElementById(id);
if(!data){const target=$("holdoutProvenance");if(target)target.textContent="2026 evidence file unavailable.";return;}
const codes=["historical","gbm","markov","ewma","adaptive_gbm","garch"];
const named={historical:"Historical frequency",gbm:"Constant GBM",markov:"Original Markov",
 ewma:"EWMA",adaptive_gbm:"Adaptive GBM",garch:"Gaussian GARCH(1,1)"};
const colors={historical:"#8faabc",gbm:"#63aafd",markov:"#efbd6a",ewma:"#35d4ac",
 adaptive_gbm:"#a59cff",garch:"#f39bd4"};
const thresholds=[10,20,35];
const fields=data.columns;
const raw=data.records;
if(raw.length!==274||data.n!==274||fields.length!==30)throw Error("2026 holdout ledger incomplete");
const ix=Object.fromEntries(fields.map((f,i)=>[f,i]));
const rows=raw.map((a,i)=>{
 if(a.length!==fields.length)throw Error("2026 row size mismatch "+i);
 return {
   origin:a[ix.origin],target:a[ix.target],close:a[ix.btc_origin],future:a[ix.btc_target],
   ret:a[ix.realized_return],regime:a[ix.regime],rollingSigma:a[ix.rolling30_sigma],
   ewmaVar:a[ix.ewma_nextvar],garchVar:a[ix.garch_nextvar_pct2],
   events:Object.fromEntries(thresholds.map(t=>[t,a[ix["event_"+t]]])),
   prob:Object.fromEntries(codes.map(m=>[m,Object.fromEntries(thresholds.map(t=>[t,a[ix[m+"_p"+t]]]))]))
 };
});
const dateAt=(s,days=0)=>new Date(Date.parse(s+"T00:00:00Z")+days*86400000).toISOString().slice(0,10);
const actualByDate=new Map();
for(let i=0;i<rows.length;i++){
 const r=rows[i];
 if(r.target!==dateAt(r.origin,30))throw Error("Not a 30-day outcome: "+r.origin);
 if(i&&r.origin!==dateAt(rows[i-1].origin,1))throw Error("Missing 2026 forecast origin");
 for(const [date,p] of [[r.origin,r.close],[r.target,r.future]]){
   if(actualByDate.has(date)&&Math.abs(actualByDate.get(date)-p)>.011)
     throw Error("Conflicting observed Binance BTC close "+date);
   actualByDate.set(date,p);
 }
 for(let t of thresholds){
   if(r.events[t]!==Number(1-r.future/r.close>=t/100))throw Error("Outcome contradicts BTC observed price");
   if(codes.some(m=>!Number.isFinite(r.prob[m][t])||r.prob[m][t]<0||r.prob[m][t]>1))
     throw Error("Invalid frozen forecast probability");
 }
}
if(rows[0].origin!=="2026-01-01"||rows.at(-1).origin!=="2026-10-01"||
 actualByDate.size!==304||!actualByDate.has("2026-10-31"))
 throw Error("2026 observed daily close coverage incomplete");
for(let t of thresholds)for(let m of codes){
 const events=rows.reduce((x,r)=>x+r.events[t],0);
 const bs=rows.reduce((sum,r)=>sum+(r.prob[m][t]-r.events[t])**2,0)/rows.length;
 const stat=data.scores[String(t)];
 if(events!==stat.events||Math.abs(bs-stat.models[m].brier)>1e-9)
   throw Error("2026 browser Brier score differs from frozen research ledger: "+m+" "+t);
}
const state={index:0,threshold:10,day:0,playing:false,frame:null,lastTime:null,hoverTimeline:null,hoverPrice:null};
const mm=global.matchMedia?.("(prefers-reduced-motion: reduce)");
const fmt=x=>Number(x).toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2});
const percent=x=>(100*x).toFixed(2)+"%";
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
function setText(id,value){$(id).textContent=value;}
function historicalPath(){
 const r=rows[state.index],a=[];
 for(let day=0;day<=30;day++){
  const date=dateAt(r.origin,day),price=actualByDate.get(date);
  if(!Number.isFinite(price))throw Error("Actual daily BTC close missing: "+date);
  a.push({date,price});
 }
 return a;
}
function stopPlayback(){
 if(state.frame!==null)global.cancelAnimationFrame(state.frame);
 state.frame=null;state.playing=false;state.lastTime=null;
}
function switchDate(i){
 const next=clamp(Math.round(i),0,rows.length-1);
 stopPlayback();state.index=next;state.day=0;state.hoverPrice=null;
 $("holdoutDateSlider").value=String(next);
 render();
}
function switchThreshold(t){
 if(!thresholds.includes(t))return;
 state.threshold=t;state.hoverTimeline=null;
 global.document.querySelectorAll("[data-holdout-threshold]").forEach(b=>
   b.setAttribute("aria-pressed",String(Number(b.dataset.holdoutThreshold)===t)));
 render();
}
function findEvent(){
 const t=state.threshold;
 const next=rows.findIndex((r,i)=>i>state.index&&r.events[t]);
 const first=rows.findIndex(r=>r.events[t]);
 if(next>=0)switchDate(next);else if(first>=0)switchDate(first);
}
function setReplay(d){
 state.day=clamp(Math.round(d),0,30);state.hoverPrice=null;
 $("holdoutReplaySlider").value=String(state.day);
 updateControls();drawPrice();
}
function playTick(time){
 if(!state.playing)return;
 if(state.lastTime===null)state.lastTime=time;
 const elapsed=time-state.lastTime;
 if(elapsed>=170){
   const step=Math.max(1,Math.floor(elapsed/170));
   state.lastTime=time;setReplay(state.day+step);
 }
 if(state.day>=30){stopPlayback();updateControls();return;}
 state.frame=global.requestAnimationFrame(playTick);
}
function togglePlayback(){
 if(state.playing){stopPlayback();updateControls();return;}
 if(state.day===30)setReplay(0);
 if(mm?.matches){setReplay(30);return;}
 state.playing=true;state.lastTime=null;
 updateControls();state.frame=global.requestAnimationFrame(playTick);
}
function render(){
 updateControls();renderModelBars();renderScores();drawTimeline();drawPrice();
}
function updateControls(){
 const r=rows[state.index],t=state.threshold,happened=!!r.events[t],loss=(1-r.future/r.close)*100;
 setText("holdoutDate",r.origin);
 setText("holdoutTarget","Actual 30-day outcome: "+r.target);
 $("holdoutPrev").disabled=state.index===0;
 $("holdoutNext").disabled=state.index===rows.length-1;
 $("holdoutFindLoss").disabled=data.scores[String(t)].events===0;
 setText("holdoutOutcome",happened?"YES · LOSS OCCURRED":"NO · LOSS DID NOT OCCUR");
 $("holdoutOutcome").style.color=happened?"#ffabb4":"#71ddc4";
 $("holdoutActual").className="v3-actual "+(happened?"v3-actual--loss":"v3-actual--safe");
 setText("holdoutActual","Actual 30-day BTC return: "+(loss<=0?"+":"−")+Math.abs(loss).toFixed(2)+
  "%. The ≥"+t+"% terminal-loss event "+(happened?"occurred.":"did not occur."));
 setText("holdoutDay","Day "+state.day+" / 30");
 setText("holdoutStartPrice",fmt(r.close)+" USDT");
 setText("holdoutFinalPrice",state.day===30?fmt(r.future)+" USDT":"Hidden");
 setText("holdoutReturn",state.day===30?(r.ret>=0?"+":"")+percent(r.ret):"Hidden");
 setText("holdoutRegime",r.regime===0?"Calm":"Volatile");
 setText("holdoutPlay",state.playing?"Ⅱ Pause replay":"▶ Play actual outcome");
 const path=historicalPath();
 setText("holdoutReplayNote",state.day===30
  ?"Actual "+r.target+" BTC close: "+fmt(r.future)+" USDT. These observed prices were not used to generate the prior forecasts."
  :"Actual prices revealed through "+path[state.day].date+": "+fmt(path[state.day].price)+
    " USDT. Later closes remain concealed in the price chart; predictions come from the frozen ledger.");
}
function renderModelBars(){
 const r=rows[state.index],t=state.threshold;
 $("holdoutModelBars").innerHTML=codes.map(m=>{
  const p=r.prob[m][t];
  return '<div class="v3-bar-row"><div class="v3-bar-line"><span>'+named[m]+'</span>'+
   '<strong>'+percent(p)+'</strong></div><div class="v3-bar-track"><div class="v3-bar-fill" '+
   'style="width:'+Math.max(.25,Math.min(100,p*100))+'%;background:'+colors[m]+'"></div></div></div>';
 }).join("");
}
function renderScores(){
 const t=state.threshold,info=data.scores[String(t)],ordered=[...codes].sort((a,b)=>info.models[a].brier-info.models[b].brier);
 const biggest=Math.max(...codes.map(m=>info.models[m].brier),1e-10);
 setText("holdoutSample",info.events+" actual ≥"+t+"% loss events in "+info.n+
  " overlapping 30-day windows ("+percent(info.frequency)+"). Lower Brier score is better.");
 $("holdoutScoreBars").innerHTML=ordered.map(m=>{
   const x=info.models[m].brier;
   return '<div class="v3-score-row"><span>'+named[m]+'</span><div class="v3-bar-track"><div class="v3-bar-fill" '+
   'style="width:'+(100*x/biggest).toFixed(3)+'%;background:'+colors[m]+'"></div></div><strong>'+
   x.toFixed(6)+'</strong></div>';
 }).join("");
 $("holdoutScoreTable").querySelector("tbody").innerHTML=ordered.map(m=>'<tr><td>'+named[m]+
  '</td><td>'+percent(info.models[m].mean_probability)+'</td><td>'+info.models[m].brier.toFixed(6)+'</td></tr>').join("");
 const tests=["adaptive_gbm_minus_gbm","garch_minus_gbm"];
 const rowsHTML=tests.map(key=>{
   const bs=data.scores["10"].differences[key],test=data.primary[key];
   return '<tr><td>'+named[key.split("_minus_")[0]]+'</td><td>'+(bs.mean>=0?"+":"")+
     bs.mean.toFixed(6)+'</td><td>['+bs.ci95[0].toFixed(5)+', '+bs.ci95[1].toFixed(5)+
     ']</td><td>'+test.holm_adjusted_p.toFixed(4)+'</td></tr>';
 }).join("");
 $("holdoutInferenceTable").querySelector("tbody").innerHTML=rowsHTML;
 setText("holdoutInferenceHeadline",tests.some(k=>data.primary[k].claim_supported)
  ?"At least one candidate met the prespecified superiority test."
  :"Neither Adaptive GBM nor GARCH established better ≥10% loss forecasts than constant GBM.");
 const count2025=global.CRL_VALIDATION?.scores?.["10"]?.models;
 if(count2025){
  setText("holdout2025Lead","Markov · "+count2025.markov.brier.toFixed(6));
 }
 const lowest=Object.entries(data.scores["10"].models).sort((a,b)=>a[1].brier-b[1].brier)[0];
 setText("holdout2026Lead",named[lowest[0]]+" · "+lowest[1].brier.toFixed(6));
 setText("holdoutBestHeadline",named[lowest[0]]+" · "+lowest[1].brier.toFixed(6));
 setText("holdoutEventHeadline",data.scores["10"].events+" / 274");
}
function stage(canvas){
 const w=canvas.clientWidth,h=canvas.clientHeight;
 if(!w||!h)return null;
 const dpr=Math.min(global.devicePixelRatio||1,2),pw=Math.round(w*dpr),ph=Math.round(h*dpr);
 if(canvas.width!==pw||canvas.height!==ph){canvas.width=pw;canvas.height=ph;}
 const ctx=canvas.getContext("2d");
 ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
 ctx.font="11px ui-sans-serif,system-ui";ctx.textBaseline="middle";
 return {ctx,w,h};
}
function polyline(g,points,color,width=2,alpha=1){
 if(!points.length)return;
 g.save();g.strokeStyle=color;g.globalAlpha=alpha;g.lineWidth=width;g.lineJoin="round";g.lineCap="round";
 g.beginPath();points.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.stroke();g.restore();
}
function drawTimeline(){
 const canvas=$("holdoutProbabilityChart"),a=stage(canvas);if(!a)return;
 const {ctx:g,w,h}=a,t=state.threshold,left=53,right=17,top=27,bottom=h-35;
 const width=w-left-right,height=bottom-top,x=i=>left+i/273*width;
 const all=rows.flatMap(r=>codes.filter(m=>m!=="historical").map(m=>r.prob[m][t]));
 const ceiling=Math.max(.025,Math.min(1,Math.max(...all)*1.13));
 const y=p=>bottom-p/ceiling*height;
 g.textAlign="right";g.fillStyle="#9ab4c9";
 for(let k=0;k<=4;k++){
  const p=ceiling*(1-k/4),yy=y(p);
  g.strokeStyle="#2b4357";g.lineWidth=1;g.beginPath();g.moveTo(left,yy);g.lineTo(w-right,yy);g.stroke();
  g.fillText((100*p).toFixed(0)+"%",left-7,yy);
 }
 for(let i=0;i<=6;i++){
  const idx=Math.round(273*i/6);
  g.textAlign="center";g.fillStyle="#92afc4";g.fillText(rows[idx].origin.slice(5),x(idx),h-18);
 }
 g.fillStyle="#fa8598";
 for(let i=0;i<rows.length;i++)if(rows[i].events[t])g.fillRect(x(i)-1,bottom-8,2,8);
 for(let m of codes.filter(m=>m!=="historical")){
  polyline(g,rows.map((r,i)=>[x(i),y(r.prob[m][t])]),colors[m],m==="garch"?1.9:1.5,.90);
 }
 for(let idx of [state.index,state.hoverTimeline].filter((v,i,a)=>v!==null&&a.indexOf(v)===i)){
  const xx=x(idx);
  g.save();g.setLineDash([4,4]);g.strokeStyle=idx===state.index?"#e4f6ff":"#8bafc6a8";
  g.beginPath();g.moveTo(xx,top);g.lineTo(xx,bottom);g.stroke();g.restore();
  if(idx===state.index)for(let m of codes.filter(m=>m!=="historical")){
   g.fillStyle=colors[m];g.beginPath();g.arc(xx,y(rows[idx].prob[m][t]),3,0,2*Math.PI);g.fill();
  }
 }
 g.font="700 11px ui-sans-serif,system-ui";g.fillStyle="#e8f7ff";g.textAlign="center";
 g.fillText(rows[state.index].origin,clamp(x(state.index),left+46,w-right-46),13);
}
function drawPrice(){
 const canvas=$("holdoutPriceChart"),a=stage(canvas);if(!a)return;
 const {ctx:g,w,h}=a,r=rows[state.index],t=state.threshold;
 const dataPoints=historicalPath(),revealed=dataPoints.slice(0,state.day+1);
 const left=65,right=73,top=25,bottom=h-39,width=w-left-right,height=bottom-top,x=i=>left+i/30*width;
 let min=Math.min(r.close,...revealed.map(p=>p.price)),max=Math.max(r.close,...revealed.map(p=>p.price));
 const realSpan=Math.max(300,max-min),limit=r.close*(1-t/100);
 const visibleThreshold=limit>=min-realSpan*.8;
 if(visibleThreshold)min=Math.min(min,limit);
 const span=Math.max(700,max-min);
 min-=span*.10;max+=span*.10;
 const y=p=>bottom-(p-min)/(max-min)*height;
 g.font="10px ui-sans-serif,system-ui";g.textAlign="right";
 for(let k=0;k<=5;k++){
  const yy=top+(bottom-top)*k/5,val=max-(max-min)*k/5;
  g.strokeStyle="#293d52";g.beginPath();g.moveTo(left,yy);g.lineTo(w-right,yy);g.stroke();
  g.fillStyle="#9bb7ce";g.fillText(Math.round(val).toLocaleString("en-US"),w-8,yy);
 }
 for(let day=0;day<=30;day+=5){
  g.textAlign="center";g.fillStyle="#97b2c9";g.fillText("D"+day,x(day),h-17);
 }
 g.save();g.setLineDash([5,5]);g.strokeStyle="#66cdb59a";
 g.beginPath();g.moveTo(left,y(r.close));g.lineTo(w-right,y(r.close));g.stroke();
 if(limit>=min&&limit<=max){
  g.strokeStyle="#fa8b9e";g.beginPath();g.moveTo(left,y(limit));g.lineTo(w-right,y(limit));g.stroke();
  g.textAlign="right";g.fillStyle="#ff9eaa";g.fillText("−"+t+"%",w-5,y(limit)-10);
 }else{
  g.textAlign="left";g.fillStyle="#ff9eaa";g.fillText("−"+t+"% boundary below visible scale",left+7,top+12);
 }
 g.restore();
 polyline(g,revealed.map((p,i)=>[x(i),y(p.price)]),"#f3faff",2.6,1);
 g.fillStyle="#e9f9ff";g.beginPath();g.arc(x(state.day),y(revealed.at(-1).price),3.6,0,2*Math.PI);g.fill();
 const d=state.hoverPrice;
 if(d!==null){
  const xx=x(d),isVisible=d<=state.day,price=isVisible?dataPoints[d].price:null;
  g.save();g.setLineDash([4,4]);g.strokeStyle="#bddef4";
  g.beginPath();g.moveTo(xx,top);g.lineTo(xx,bottom);g.stroke();g.restore();
  const label=(isVisible?"BTC "+fmt(price)+" USDT":"PRICE HIDDEN");
  g.textAlign="center";g.font="700 11px ui-sans-serif,system-ui";g.fillStyle="#f2f8ff";
  g.fillText(dataPoints[d].date+" · "+label,clamp(xx,left+90,w-right-90),top+12);
  if(isVisible){g.fillStyle="#fff";g.beginPath();g.arc(xx,y(price),4,0,2*Math.PI);g.fill();}
 }
 g.textAlign="right";g.font="10px ui-sans-serif,system-ui";g.fillStyle="#a3bdd0";
 g.fillText("USDT",w-9,12);
}
const modelLegend=codes.filter(m=>m!=="historical").map(m=>
 '<span><i style="background:'+colors[m]+'"></i>'+named[m]+'</span>').join("")+
 '<span><i style="background:#fa8598"></i>Actual ≥threshold loss dates</span>';
$("holdoutLegend").innerHTML=modelLegend;
global.document.querySelectorAll("[data-holdout-threshold]").forEach(b=>b.addEventListener("click",()=>switchThreshold(Number(b.dataset.holdoutThreshold))));
$("holdoutPrev").addEventListener("click",()=>switchDate(state.index-1));
$("holdoutNext").addEventListener("click",()=>switchDate(state.index+1));
$("holdoutFindLoss").addEventListener("click",findEvent);
$("holdoutDateSlider").addEventListener("input",e=>switchDate(Number(e.target.value)));
$("holdoutPlay").addEventListener("click",togglePlayback);
$("holdoutReveal").addEventListener("click",()=>{stopPlayback();setReplay(30);});
$("holdoutHide").addEventListener("click",()=>{stopPlayback();setReplay(0);});
$("holdoutReplaySlider").addEventListener("input",e=>{stopPlayback();setReplay(Number(e.target.value));});
$("holdoutProbabilityChart").addEventListener("pointermove",e=>{
 const b=e.target.getBoundingClientRect(),fraction=clamp((e.clientX-b.left-53)/(b.width-53-17),0,1);
 state.hoverTimeline=Math.round(fraction*273);
 const r=rows[state.hoverTimeline],t=state.threshold;
 setText("holdoutChartHover",r.origin+" · "+codes.filter(m=>m!=="historical").map(m=>named[m]+": "+percent(r.prob[m][t])).join(" · ")+
  " · Actual event: "+(r.events[t]?"Yes":"No"));
 drawTimeline();
});
$("holdoutProbabilityChart").addEventListener("pointerleave",()=>{
 state.hoverTimeline=null;setText("holdoutChartHover","Click or use the date slider to inspect a forecast date.");drawTimeline();
});
$("holdoutProbabilityChart").addEventListener("click",e=>{
 const b=e.target.getBoundingClientRect(),fraction=clamp((e.clientX-b.left-53)/(b.width-53-17),0,1);
 switchDate(Math.round(fraction*273));
});
$("holdoutProbabilityChart").addEventListener("keydown",e=>{
 if(e.key==="ArrowLeft"){e.preventDefault();switchDate(state.index-1);}
 if(e.key==="ArrowRight"){e.preventDefault();switchDate(state.index+1);}
});
$("holdoutPriceChart").addEventListener("pointermove",e=>{
 const b=e.target.getBoundingClientRect(),fraction=clamp((e.clientX-b.left-65)/(b.width-65-73),0,1);
 state.hoverPrice=Math.round(fraction*30);drawPrice();
});
$("holdoutPriceChart").addEventListener("pointerleave",()=>{state.hoverPrice=null;drawPrice();});
if(global.ResizeObserver){
 const ro=new ResizeObserver(()=>{drawTimeline();drawPrice();});
 ro.observe($("holdoutProbabilityChart"));ro.observe($("holdoutPriceChart"));
}else global.addEventListener("resize",()=>{drawTimeline();drawPrice();});
render();
global.CRLHoldout2026={
 evidence:data,rows,get state(){return {...state};},
 selectDate:switchDate,selectThreshold:switchThreshold,reveal:setReplay,
 getHistoricalClose:date=>actualByDate.get(date)
};
})(window);
