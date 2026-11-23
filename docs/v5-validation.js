/* Horizon-aware Predictions vs Reality: original 30-day models preserved, added
 * Adaptive GBM/GARCH flagged exploratory, and 2026 frozen holdout independent.
 * Actual observed daily closes only. No future-data leakage in replay scales.
 */
(function(global){"use strict";
const $=id=>global.document.getElementById(id);
const datasets={2025:global.CRL_EVIDENCE_2025,2026:global.CRL_EVIDENCE_2026};
const horizons=Object.freeze([7,14,30,60,90]);
const extended=global.CRL_HORIZON_EVIDENCE;
if(!extended||extended.horizons.join(",")!==horizons.join(","))
 throw Error("Audited multi-horizon research results missing or incomplete");
if(!datasets[2025]||!datasets[2026])
 throw Error("Historical 2025 and 2026 model forecast evidence required");
const codes=["historical","gbm","markov","ewma","adaptive_gbm","garch"];
const named={historical:"Historical frequency",gbm:"Constant GBM",markov:"Original Markov",
 ewma:"EWMA",adaptive_gbm:"Adaptive GBM",garch:"Gaussian GARCH(1,1)"};
const colors={historical:"#8faabc",gbm:"#63aafd",markov:"#efbd6a",ewma:"#35d4ac",
 adaptive_gbm:"#a59cff",garch:"#f39bd4"};
const thresholds=[10,20,35];
const dateAt=(s,days=0)=>new Date(Date.parse(s+"T00:00:00Z")+days*86400000).toISOString().slice(0,10);
function inspectEvidence(data,year,h){
 const fields=data.columns,raw=data.records,n=({2025:{7:358,14:351,30:335,60:305,90:275},
  2026:{7:297,14:290,30:274,60:244,90:214}})[year][h];
 if(raw.length!==n||data.n!==n||fields.length!==30)
   throw Error(year+" "+h+"-day scientific ledger incomplete");
 const ix=Object.fromEntries(fields.map((f,i)=>[f,i]));
 const rows=raw.map((a,i)=>{
   if(a.length!==fields.length)throw Error(year+" row size mismatch "+i);
   return {
     origin:a[ix.origin],target:a[ix.target],close:a[ix.btc_origin],future:a[ix.btc_target],
     ret:a[ix.realized_return],regime:a[ix.regime],rollingSigma:a[ix.rolling30_sigma],
     ewmaVar:a[ix.ewma_nextvar],garchVar:a[ix.garch_nextvar_pct2],
     events:Object.fromEntries(thresholds.map(t=>[t,a[ix["event_"+t]]])),
     prob:Object.fromEntries(codes.map(m=>[m,Object.fromEntries(thresholds.map(t=>[t,a[ix[m+"_p"+t]]]))]))
   };
 });
 const actualByDate=new Map();
 for(let i=0;i<rows.length;i++){
   const r=rows[i];
   if(r.target!==dateAt(r.origin,h))throw Error(year+": not a "+h+"-day outcome "+r.origin);
   if(i&&r.origin!==dateAt(rows[i-1].origin,1))throw Error(year+": missing origin");
   for(const [date,p] of [[r.origin,r.close],[r.target,r.future]]){
     if(actualByDate.has(date)&&Math.abs(actualByDate.get(date)-p)>.011)
       throw Error(year+": conflicting observed close "+date);
     actualByDate.set(date,p);
   }
   for(let t of thresholds){
     if(r.events[t]!==Number(1-r.future/r.close>=t/100))throw Error(year+": outcome mismatch");
     if(codes.some(m=>!Number.isFinite(r.prob[m][t])||r.prob[m][t]<0||r.prob[m][t]>1))
       throw Error(year+": invalid probabilities");
   }
 }
 if(rows[0].origin!==data.originStart||rows.at(-1).origin!==data.originEnd||
    !actualByDate.has(data.finalObserved)||actualByDate.size!==n+h)
   throw Error(year+": incomplete real daily close coverage");
 for(let t of thresholds)for(let m of codes){
   const events=rows.reduce((x,r)=>x+r.events[t],0);
   const bs=rows.reduce((sum,r)=>sum+(r.prob[m][t]-r.events[t])**2,0)/rows.length;
   const stat=data.scores[String(t)];
   if(events!==stat.events||Math.abs(bs-stat.models[m].brier)>1e-9)
     throw Error(year+": browser Brier parity failure "+m+" "+t);
 }
 return {data,rows,actualByDate};
}
const inspected={2025:{},2026:{}};
for(const year of [2025,2026]){
 for(const h of horizons){
  if(h===30){inspected[year][h]=inspectEvidence(datasets[year],year,h);continue;}
  const frozen=extended.years[String(year)][String(h)];
  if(!frozen||frozen.n<=0||!frozen.rows)throw Error("Missing archived "+year+"/"+h+" forecast");
  const incoming={columns:extended.fields,records:frozen.rows,scores:frozen.scores,
    n:frozen.n,originStart:String(year)+"-01-01",originEnd:frozen.originEnd,
    finalObserved:extended.yearEnd[String(year)]};
  inspected[year][h]=inspectEvidence(incoming,year,h);
 }
}
const state={year:2025,horizon:30,index:0,threshold:10,day:0,playing:false,frame:null,lastTime:null,hoverTimeline:null,hoverPrice:null};
let {data,rows,actualByDate}=inspected[2025][30];
const mm=global.matchMedia?.("(prefers-reduced-motion: reduce)");
const fmt=x=>Number(x).toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2});
const percent=x=>(100*x).toFixed(2)+"%";
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
function setText(id,value){$(id).textContent=value;}
function historicalPath(){
 const r=rows[state.index],a=[];
 for(let day=0;day<=state.horizon;day++){
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
function metadata(){
 const year=state.year,h=state.horizon,is2025=year===2025,original=h===30;
 const hDetails=extended.years[String(year)][String(h)];
 global.document.querySelectorAll("[data-validation-year]").forEach(b=>{
   const chosen=Number(b.dataset.validationYear);
   b.setAttribute("aria-pressed",String(chosen===year));
   const count=inspected[chosen][h].rows.length;
   b.querySelector("span").textContent=count+" completed "+h+"-day forecasts"+(h===30?" · original benchmark":" · exploratory");
 });
 global.document.querySelectorAll("[data-validation-horizon]").forEach(b=>
   b.setAttribute("aria-pressed",String(Number(b.dataset.validationHorizon)===h)));
 $("holdoutDateSlider").max=String(rows.length-1);
 $("holdoutDateSlider").value=String(state.index);
 $("holdoutReplaySlider").max=String(h);
 $("holdoutReplaySlider").value=String(state.day);
 setText("validationYearTag",year+" · "+(original?(is2025?"ORIGINAL + EXPLORATORY":"FROZEN HOLDOUT"):"EXPLORATORY HORIZON"));
 setText("validationHorizonTag",h+" DAYS · "+(original?"ORIGINAL":"EXPLORATORY"));
 setText("validationPeriodDates",rows.length+" forecasts · "+h+"-day complete outcomes · "+(is2025?"2025":"Jan–Oct 2026"));
 setText("holdoutDateLeft","1 January "+year);
 setText("holdoutDateRight",rows.at(-1).origin);
 setText("holdoutOriginCount",rows.length+" complete origins");
 for(let letter of ["A","B","C","D","E","F","G"])setText("validationHorizonDays"+letter,String(h));
 setText("validationYearStatus",
  original?
   (is2025?"2025 original 30-day GBM, Markov and EWMA probabilities remain unchanged; the added Adaptive GBM/GARCH 2025 models are post-hoc exploratory."
          :"2026 original fixed-protocol 30-day retrospective holdout, including its original Holm-adjusted primary comparisons."):
   (year+" · "+h+"-day exploratory retrospective evaluation. All five model forecasts use information available through each origin only. This is not new independent statistical confirmation."));
 setText("holdoutProvenance",
  original?
   (is2025?"Original 2025 30-day notebook values are preserved. Added 2025 Adaptive GBM/GARCH forecasts are post-hoc exploratory."
         :"Original independent 2026 30-day scores, forecast probabilities and Holm-adjusted inference are unchanged."):
   ("All "+h+"-day forecasts are newly generated exploratory historical evidence. 2022–2024 fitted parameters are frozen; no later returns initialize any forecast. Original 30-day findings remain unchanged."));
 setText("holdoutNewModelStatus",original&&!is2025?
  "No established superiority over GBM":"Exploratory · not confirmatory");
 setText("holdoutInferenceContext",original&&!is2025?
  "Original 2026 primary 30-day comparison: paired 30-day moving-block bootstrap, 3,000 resamples and Holm correction. Negative Brier difference favors the candidate.":
  "Exploratory "+h+"-day historical comparisons, with descriptive paired "+h+"-day block-bootstrap intervals. Outcomes overlap and intervals are not evidence of a new confirmatory hypothesis test.");
 $("holdoutInferenceTable").querySelector("thead th:last-child").textContent=original&&!is2025?"Holm p":"Status";
 syncIndicator();
}
function syncIndicator(){
 const custom=Number($("horizon")?.value);
 const matched=horizons.includes(custom);
 const same=matched&&custom===state.horizon;
 $("validationHorizonSync").dataset.mismatch=String(!same);
 setText("validationHorizonSync",same?
   "Simulation and historical evaluation both use "+state.horizon+" days. Historical evidence is independently archived, not generated from the scenario sliders.":
   matched?
   "Simulation is set to "+custom+" days; historical evidence shows "+state.horizon+" days. Selecting either audited horizon will synchronize the two controls.":
   "Simulation uses a custom "+custom+"-day horizon. No audited historical backtest exists for exactly "+custom+" days; the historical charts explicitly remain at "+state.horizon+" days. Choose 7, 14, 30, 60 or 90 days for a direct comparison.");
}
function activate(year,h){
 if(!inspected[year]?.[h])return;
 stopPlayback();
 state.year=year;state.horizon=h;state.index=0;state.day=0;
 state.hoverTimeline=null;state.hoverPrice=null;
 ({data,rows,actualByDate}=inspected[year][h]);
 metadata();render();
}
function setYear(year){activate(year,state.horizon);}
function setHorizon(h,source="history"){
 if(!horizons.includes(h))return;
 if(state.horizon!==h)activate(state.year,h);
 if(source==="history" && Number($("horizon").value)!==h){
  $("horizon").value=String(h);
  $("horizonNumber").value=String(h);
  $("horizon").dispatchEvent(new Event("input",{bubbles:true}));
 }
 syncIndicator();
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
 state.day=clamp(Math.round(d),0,state.horizon);state.hoverPrice=null;
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
 if(state.day>=state.horizon){stopPlayback();updateControls();return;}
 state.frame=global.requestAnimationFrame(playTick);
}
function togglePlayback(){
 if(state.playing){stopPlayback();updateControls();return;}
 if(state.day===state.horizon)setReplay(0);
 if(mm?.matches){setReplay(state.horizon);return;}
 state.playing=true;state.lastTime=null;
 updateControls();state.frame=global.requestAnimationFrame(playTick);
}
function render(){
 updateControls();renderModelBars();renderScores();drawTimeline();drawPrice();
}
function updateControls(){
 const r=rows[state.index],t=state.threshold,happened=!!r.events[t],loss=(1-r.future/r.close)*100;
 setText("holdoutDate",r.origin);
 setText("holdoutTarget","Actual "+state.horizon+"-day outcome: "+r.target);
 $("holdoutPrev").disabled=state.index===0;
 $("holdoutNext").disabled=state.index===rows.length-1;
 $("holdoutFindLoss").disabled=data.scores[String(t)].events===0;
 setText("holdoutOutcome",happened?"YES · LOSS OCCURRED":"NO · LOSS DID NOT OCCUR");
 $("holdoutOutcome").style.color=happened?"#ffabb4":"#71ddc4";
 $("holdoutActual").className="v3-actual "+(happened?"v3-actual--loss":"v3-actual--safe");
 setText("holdoutActual","Actual "+state.horizon+"-day BTC return: "+(loss<=0?"+":"−")+Math.abs(loss).toFixed(2)+
  "%. The ≥"+t+"% terminal-loss event "+(happened?"occurred.":"did not occur."));
 setText("holdoutDay","Day "+state.day+" / "+state.horizon);
 setText("holdoutStartPrice",fmt(r.close)+" USDT");
 setText("holdoutFinalPrice",state.day===state.horizon?fmt(r.future)+" USDT":"Hidden");
 setText("holdoutReturn",state.day===state.horizon?(r.ret>=0?"+":"")+percent(r.ret):"Hidden");
 setText("holdoutRegime",r.regime===0?"Calm":"Volatile");
 setText("holdoutPlay",state.playing?"Ⅱ Pause replay":"▶ Play actual outcome");
 const path=historicalPath();
 setText("holdoutReplayNote",state.day===state.horizon
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
  " overlapping "+state.horizon+"-day windows ("+percent(info.frequency)+"). Lower Brier score is better.");
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
   const bs=data.scores["10"].differences[key];
   const status=state.year===2026&&state.horizon===30?data.primary[key].holm_adjusted_p.toFixed(4):"Exploratory";
   return '<tr><td>'+named[key.split("_minus_")[0]]+'</td><td>'+(bs.mean>=0?"+":"")+
     bs.mean.toFixed(6)+'</td><td>['+bs.ci95[0].toFixed(5)+', '+bs.ci95[1].toFixed(5)+
     ']</td><td>'+status+'</td></tr>';
 }).join("");
 $("holdoutInferenceTable").querySelector("tbody").innerHTML=rowsHTML;
 setText("holdoutInferenceHeadline",state.year===2026&&state.horizon===30?
  "Neither new adaptive model established better ≥10% 30-day forecasts than constant GBM.":
  "Exploratory horizon comparisons do not establish statistically proven superiority.");
 const lowest=Object.entries(info.models).sort((a,b)=>a[1].brier-b[1].brier)[0];
 setText("holdoutBestLabel","LOWEST ≥"+t+"% BRIER SCORE");
 setText("holdoutEventLabel","ACTUAL ≥"+t+"% LOSS EVENTS");
 setText("holdoutBestHeadline",named[lowest[0]]+" · "+lowest[1].brier.toFixed(6));
 setText("holdoutEventHeadline",info.events+" / "+rows.length);
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
 const width=w-left-right,height=bottom-top,x=i=>left+i/(rows.length-1)*width;
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
  const idx=Math.round((rows.length-1)*i/6);
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
 const left=65,right=73,top=25,bottom=h-39,width=w-left-right,height=bottom-top,x=i=>left+i/state.horizon*width;
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
 for(let day=0;day<=state.horizon;day+=state.horizon<=14?Math.max(1,Math.round(state.horizon/7)):state.horizon<=30?5:state.horizon<=60?10:15){
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
global.document.querySelectorAll("[data-validation-year]").forEach(b=>b.addEventListener("click",()=>{setYear(Number(b.dataset.validationYear));global.document.querySelectorAll(".nav a").forEach(a=>a.classList.toggle("active",a.hash==="#validation"));}));
global.document.querySelectorAll("[data-holdout-threshold]").forEach(b=>b.addEventListener("click",()=>switchThreshold(Number(b.dataset.holdoutThreshold))));
$("holdoutPrev").addEventListener("click",()=>switchDate(state.index-1));
$("holdoutNext").addEventListener("click",()=>switchDate(state.index+1));
$("holdoutFindLoss").addEventListener("click",findEvent);
$("holdoutDateSlider").addEventListener("input",e=>switchDate(Number(e.target.value)));
$("holdoutPlay").addEventListener("click",togglePlayback);
$("holdoutReveal").addEventListener("click",()=>{stopPlayback();setReplay(state.horizon);});
$("holdoutHide").addEventListener("click",()=>{stopPlayback();setReplay(0);});
$("holdoutReplaySlider").addEventListener("input",e=>{stopPlayback();setReplay(Number(e.target.value));});
$("holdoutProbabilityChart").addEventListener("pointermove",e=>{
 const b=e.target.getBoundingClientRect(),fraction=clamp((e.clientX-b.left-53)/(b.width-53-17),0,1);
 state.hoverTimeline=Math.round(fraction*(rows.length-1));
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
 switchDate(Math.round(fraction*(rows.length-1)));
});
$("holdoutProbabilityChart").addEventListener("keydown",e=>{
 if(e.key==="ArrowLeft"){e.preventDefault();switchDate(state.index-1);}
 if(e.key==="ArrowRight"){e.preventDefault();switchDate(state.index+1);}
});
$("holdoutPriceChart").addEventListener("pointermove",e=>{
 const b=e.target.getBoundingClientRect(),fraction=clamp((e.clientX-b.left-65)/(b.width-65-73),0,1);
 state.hoverPrice=Math.round(fraction*state.horizon);drawPrice();
});
$("holdoutPriceChart").addEventListener("pointerleave",()=>{state.hoverPrice=null;drawPrice();});
if(global.ResizeObserver){
 const ro=new ResizeObserver(()=>{drawTimeline();drawPrice();});
 ro.observe($("holdoutProbabilityChart"));ro.observe($("holdoutPriceChart"));
}else global.addEventListener("resize",()=>{drawTimeline();drawPrice();});
global.document.querySelectorAll("[data-validation-horizon]").forEach(b=>b.addEventListener("click",()=>setHorizon(Number(b.dataset.validationHorizon),"history")));
global.document.addEventListener("input",e=>{
 if((e.target?.id==="horizon"||e.target?.id==="horizonNumber")){
  const h=Number(e.target.value);
  if(horizons.includes(h))setHorizon(h,"simulation");
  else if(h>=7&&h<=90)syncIndicator();
 }
});
setYear(2025);
global.CRLValidationUnified={
 get evidence(){return data;},get rows(){return rows;},get state(){return {...state};},selectYear:setYear,selectHorizon:setHorizon,
 selectDate:switchDate,selectThreshold:switchThreshold,reveal:setReplay,
 getHistoricalClose:date=>actualByDate.get(date),getYearEvidence:(year,h=30)=>inspected[year][h],horizons
};
})(window);
