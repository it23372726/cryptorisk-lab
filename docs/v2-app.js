/* CryptoRisk Lab v2 application controller: asynchronous simulation, playback, numerical checks. */
(function(){"use strict";
const $=id=>document.getElementById(id),core=window.CRLCore;
if(!window.CRL_HISTORY||!core||!window.CRLForecastChart){document.body.textContent="CryptoRisk Lab failed to initialize its local assets.";throw Error("Missing local assets");}
const chart=new window.CRLForecastChart($("mainChart"),$("chartTooltip"));
chart.onSelectPath=()=>renderPathInspector();
const modelNames=core.models;
const modelIds={gbm:"Gbm",markov:"Markov",ewma:"Ewma",adaptive_gbm:"Adaptive",garch:"Garch"};
const modelLabels={gbm:"GBM",markov:"Markov",ewma:"EWMA",adaptive_gbm:"Adaptive GBM",garch:"GARCH"};
const modelColors={gbm:"#64aafa",markov:"#f0bd6a",ewma:"#3cd7ad",adaptive_gbm:"#a59cff",garch:"#f39bd4"};
let result=null,runner=null,token=0,phase="ready",paused=false,day=0,view="all",actual=false,animating=false,frame=null,lastFrame=null;
const pct=v=>(100*v).toFixed(2)+"%",money=v=>v.toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2}),int=v=>Number(v).toLocaleString("en-US");
function option(name){return document.querySelector('input[name="'+name+'"]:checked')?.value;}
function readSettings(){return {investment:Number($("investment").value),horizon:Number($("horizon").value),paths:Number(option("paths")),threshold:Number($("threshold").value)/100,volatility:Number($("volatility").value),regime:Number(option("regime")),seed:Number($("seed").value),lambda:Number($("decay").value)};}
function labels(){
 const s=readSettings();
 $("investmentOut").textContent=Number.isFinite(s.investment)?int(s.investment)+" USDT":"Invalid";
 $("horizonOut").textContent=s.horizon+" days";$("pathsOut").textContent=int(s.paths);$("thresholdOut").textContent=Math.round(s.threshold*100)+"%";
 $("volatilityOut").textContent=s.volatility.toFixed(2)+"×";$("decayOut").textContent=s.lambda.toFixed(2);
 document.querySelectorAll(".thresholdName").forEach(e=>e.textContent=String(Math.round(s.threshold*100)));
 $("dayScrub").max=String(s.horizon);$("dayLabel").textContent="Day "+Math.floor(day)+" / "+s.horizon;
}
function setStatus(txt){$("runStatus").textContent=txt;}
function setRunBtns(){const isComputing=phase==="computing",hasResult=!!result;
 $("startBtn").textContent=isComputing?"Generating paths…":"▶ Run simulation";
 $("startBtn").disabled=isComputing;
 $("pauseBtn").disabled=!(isComputing||hasResult);
 $("pauseBtn").textContent=paused?"Resume":"Pause";
 $("playBtn").disabled=!hasResult;$("restartPlayback").disabled=!hasResult;$("dayScrub").disabled=!hasResult;
 $("playBtn").textContent=animating&&!paused?"Ⅱ Pause":"▶ Play";
}
function clearResults(){
 token++;if(runner)runner.cancel();runner=null;if(frame!==null)cancelAnimationFrame(frame);frame=null;
 phase="ready";paused=false;animating=false;day=0;lastFrame=null;result=null;chart.selectedPath=null;
 $("computeBar").style.width="0%";setStatus("Ready. Press Run simulation to generate paths.");
 for(let m of modelNames){
  $("kpi"+modelIds[m]).textContent="—";
  $("kpi"+modelIds[m]+"Ci").textContent=m==="ewma"?"Dynamic variance · 2024 state":m==="adaptive_gbm"?"Last 30 pre-origin returns":m==="garch"?"Frozen GARCH coefficients and variance":"Run to estimate probability";
  document.querySelectorAll('[data-model="'+m+'"]').forEach(e=>e.textContent="—");
 }
 $("verifyStatus").textContent="Run a simulation to execute browser-side structural and risk-ordering checks.";
 $("insight").innerHTML="<strong>Explore how risk evolves.</strong> Run a reproducible experiment to animate projected paths and price-percentile fans.";
 chart.update({result:null,day:0,horizon:readSettings().horizon,threshold:readSettings().threshold,view,reveal:actual});
 drawDistribution();updatePlay();renderPathInspector();setRunBtns();
}
function changeSettings(){
 // User inputs are part of the reproducible experiment; editing them invalidates old outputs.
 labels();clearResults();
}
function bindControlPairs(rangeId,numberId){
 const a=$(rangeId),b=$(numberId);
 a.addEventListener("input",()=>{b.value=a.value;changeSettings();});
 b.addEventListener("input",()=>{if(Number(b.value)>=Number(b.min)&&Number(b.value)<=Number(b.max)){a.value=b.value;changeSettings();}else labels();});
 b.addEventListener("change",()=>{b.value=String(Math.min(Number(b.max),Math.max(Number(b.min),Number(b.value)||Number(b.min))));a.value=b.value;changeSettings();});
}
bindControlPairs("horizon","horizonNumber");bindControlPairs("threshold","thresholdNumber");
for(let id of ["investment","volatility","seed","decay"]){
 $(id).addEventListener(id==="volatility"||id==="decay"?"input":"change",changeSettings);
}
document.querySelectorAll('input[name="paths"],input[name="regime"]').forEach(e=>e.addEventListener("change",changeSettings));
function simulate(){
 clearResults();
 let s=readSettings();
 try{runner=core.createRunner(s);}catch(e){setStatus("Invalid settings: "+e.message);return;}
 phase="computing";paused=false;let own=token;setStatus("Computing five independent Monte Carlo path ensembles…");
 setRunBtns();
 function nextBatch(){
  if(own!==token||phase!=="computing"||!runner)return;
  if(paused)return;
  try{let r=runner.step(s.paths>=30000?100:180);
   const progress=Math.min(100,100*r.done/r.total);
   $("computeBar").style.width=progress+"%";
   setStatus("Computing: "+int(r.done)+" / "+int(r.total)+" paths per model · "+Math.round(progress)+"%");
   if(!r.complete){requestAnimationFrame(nextBatch);return;}
   result=runner.finish();runner=null;phase="ready";renderResults();day=0;animating=true;lastFrame=null;
   setStatus("Five-model simulation completed. Playing generated paths.");
   setRunBtns();renderDay();frame=requestAnimationFrame(animate);
  }catch(e){clearResults();setStatus("Simulation failed: "+e.message);console.error(e);}
 }
 requestAnimationFrame(nextBatch);
}
function normalCdf(z){const x=Math.abs(z),t=1/(1+.2316419*x);
 const p=1-Math.exp(-.5*x*x)/Math.sqrt(2*Math.PI)*(((((1.330274429*t-1.821255978)*t)+1.781477937)*t-.356563782)*t+.319381530)*t;
 return z>=0?p:1-p;
}
function verify(){
 const v=core.verifyResult(result),s=result.settings;
 const p=normalCdf((Math.log(.9)-core.CAL.gbm.mu*s.horizon)/(core.CAL.gbm.sigma*s.volatility*Math.sqrt(s.horizon)));
 const o=result.models.gbm.prob["0.100"].p;
 const sem=Math.sqrt(Math.max(1e-8,p*(1-p)/s.paths));
 if(Math.abs(o-p)>4*sem+.005)v.errors.push("GBM analytical 10% loss-probability check");
 const passes=v.errors.length===0;
 $("verifyStatus").textContent=(passes?"PASS":"CHECK")+" · "+int(s.paths)+" paths/model · numerical structure, percentile order, VaR/ES order and analytical GBM loss probability "+(passes?"verified.":": "+v.errors.join("; "))+" EWMA initial variance exported from executed research notebook.";
}
function renderResults(){
 let s=result.settings;
 for(let m of modelNames){
  const o=result.models[m],id=modelIds[m],hit=o.prob[s.threshold.toFixed(3)];
  $("kpi"+id).textContent=pct(hit.p);
  $("kpi"+id+"Ci").textContent="MC 95% interval "+pct(hit.low)+" – "+pct(hit.high)+(m==="ewma"?" · notebook state":"");
  const vals={p10:pct(o.prob["0.100"].p),p20:pct(o.prob["0.200"].p),p35:pct(o.prob["0.350"].p),custom:pct(hit.p),var:money(o.var95),es:money(o.es95),touch:pct(o.touch),dd:pct(o.drawdown)};
  for(let [k,v] of Object.entries(vals)){const cell=document.querySelector('[data-model="'+m+'"][data-metric="'+k+'"]');if(cell)cell.textContent=v;}
 }
 const summary=modelNames.map(m=>modelLabels[m]+" "+pct(result.models[m].prob[s.threshold.toFixed(3)].p)).join(" · ");
 $("insight").innerHTML="<strong>Five-model scenario.</strong> Terminal loss ≥ "+Math.round(s.threshold*100)+"%: "+summary+
   ". These are model-dependent simulated risks, not claims of 2026 predictive accuracy. Frozen 2022–2024 parameters, 31 Dec 2024 origin.";
 verify();drawDistribution();
}
function updatePlay(){
 let h=result?.settings.horizon||readSettings().horizon;
 $("dayLabel").textContent="Day "+(Number.isInteger(day)?day:day.toFixed(1))+" / "+h;
 $("dayScrub").value=String(day);
 let model=result?.models.markov.paths[0],r=model?.states;
 let k=Math.min(h,Math.max(0,Math.floor(day)));
 $("regimeStatus").textContent=result&&r?"Sample Markov path: "+(r[k]===0?"CALM":"VOLATILE"):"";
 $("chartMode").textContent=result?"Animated forecast · "+int(result.settings.paths)+" paths per model"+(actual?" · observed 2025 revealed (through 31 Dec)":""):"Historical candles only · simulation not started";
 setRunBtns();
}
function renderPathInspector(){
 const e=$("pathInspector"),selected=chart.selectedPath;
 if(!result||!selected||view==="all"||selected.model!==view){
   e.textContent=result?"Select a single model above and click one of its faint individual trajectories to inspect that simulated outcome.":"Choose one model, run the simulation and click a trajectory to inspect its daily prices and losses.";
   return;
 }
 const obj=result.models[selected.model].paths[selected.index],prices=obj?.values;
 if(!prices){e.textContent="No sample trajectory available.";return;}
 const d=Math.min(result.settings.horizon,Math.max(0,Math.floor(day))),price=prices[d],investment=result.settings.investment,
 value=investment*price/core.origin,pnl=value-investment;
 let peak=prices[0],worst=0,touched=false;
 for(let i=0;i<=d;i++){peak=Math.max(peak,prices[i]);worst=Math.max(worst,(peak-prices[i])/peak);if(prices[i]<=core.origin*(1-result.settings.threshold))touched=true;}
 const state=selected.model==="markov"?(obj.states[d]===0?" · Calm state":" · Volatile state"):"";
 e.textContent=selected.model.toUpperCase()+" path "+(selected.index+1)+" · Day "+d+
 " · BTC "+money(price)+" USDT · Investment "+money(value)+" USDT · P/L "+(pnl>=0?"+":"")+money(pnl)+
 " USDT · Max drawdown so far "+pct(worst)+" · Threshold touched: "+(touched?"Yes":"No")+state;
}
function updateActualSummary(){
 const candles=window.CRL_HISTORY.candles,last=candles[candles.length-1];
 if(!last)return;
 const annual=(last.close/core.origin-1)*100;
 $("actual2025Summary").textContent=actual
  ?"Observed Binance BTC/USDT close "+last.date+": "+money(last.close)+" USDT ("+
   (annual>=0?"+":"")+annual.toFixed(2)+"% from the 31 Dec 2024 forecast origin). "+
   "The displayed forecast stops at its selected "+readSettings().horizon+"-day horizon, "+
   "even when the observed candles continue through the full 2025 year."
  :"Historical data through "+last.date+" is available. Reveal actual 2025 for the year-long view; "+
   "forecasts remain limited to the selected horizon.";
}
function renderDay(){chart.update({result,day,view,reveal:actual,threshold:readSettings().threshold,horizon:readSettings().horizon});updatePlay();renderPathInspector();updateActualSummary();}
function animate(now){
 if(!animating||paused||!result){frame=null;return;}
 const dt=lastFrame===null?0:Math.min(80,now-lastFrame);lastFrame=now;
 day=Math.min(result.settings.horizon,day+dt/1000*4*Number($("speed").value));
 renderDay();
 if(day>=result.settings.horizon){animating=false;setStatus("Playback complete · all risk metrics calculated from "+int(result.settings.paths)+" paths per model.");setRunBtns();frame=null;return;}
 frame=requestAnimationFrame(animate);
}
function togglePause(){
 if(phase==="computing"){
  paused=!paused;
  if(!paused){setStatus("Resuming Monte Carlo computation");requestAnimationFrame(()=>{let own=token; // Progress work is scheduled by nextBatch from the run; restart via an explicit stored callback.
    if(own===token&&typeof activeBatch==="function")activeBatch();
  });}else setStatus("Computation paused.");
 }else if(result){if(animating&&!paused){paused=true;lastFrame=null;setStatus("Playback paused at day "+Math.floor(day));}else{paused=false;animating=true;lastFrame=null;setStatus("Playing simulated daily paths");frame=requestAnimationFrame(animate);}}
 setRunBtns();
}
let activeBatch=null;
// Wrap simulation to expose a safe continuation callback when pausing during batch generation.
function run(){
 clearResults();let s=readSettings();
 try{runner=core.createRunner(s);}catch(e){setStatus("Invalid settings: "+e.message);return;}
 phase="computing";paused=false;const own=token;setStatus("Generating five reproducible Monte Carlo ensembles…");setRunBtns();
 activeBatch=()=>{if(own!==token||phase!=="computing"||!runner||paused)return;
  try{
   let r=runner.step(s.paths>=30000?120:200);
   $("computeBar").style.width=(100*r.done/r.total)+"%";
   setStatus("Computing: "+int(r.done)+" / "+int(r.total)+" paths per model");
   if(!r.complete){requestAnimationFrame(activeBatch);return;}
   result=runner.finish();runner=null;activeBatch=null;phase="ready";day=0;animating=true;lastFrame=null;
   renderResults();if(window.matchMedia&&window.matchMedia("(prefers-reduced-motion: reduce)").matches){day=s.horizon;animating=false;setStatus("Simulation complete. Automatic motion disabled by accessibility preference; use the day scrubber.");renderDay();}else{setStatus("Five-model simulation complete. Animating "+int(s.paths)+" paths per model.");renderDay();frame=requestAnimationFrame(animate);}
  }catch(e){clearResults();setStatus("Simulation error: "+e.message);console.error(e);}
 };
 requestAnimationFrame(activeBatch);
}
$("startBtn").addEventListener("click",run);
$("pauseBtn").addEventListener("click",()=>{
 if(phase==="computing"){paused=!paused;if(!paused&&activeBatch)requestAnimationFrame(activeBatch);setStatus(paused?"Computation paused":"Computing Monte Carlo paths");setRunBtns();return;}
 if(!result)return;
 if(animating&&!paused){paused=true;lastFrame=null;setStatus("Playback paused");}
 else{paused=false;animating=true;lastFrame=null;frame=requestAnimationFrame(animate);}
 setRunBtns();
});
$("resetBtn").addEventListener("click",clearResults);
$("playBtn").addEventListener("click",()=>{
 if(!result)return;
 if(animating&&!paused){paused=true;lastFrame=null;setStatus("Playback paused");}
 else{if(day>=result.settings.horizon)day=0;paused=false;animating=true;lastFrame=null;frame=requestAnimationFrame(animate);}
 setRunBtns();renderDay();
});
$("restartPlayback").addEventListener("click",()=>{if(!result)return;day=0;paused=false;animating=true;lastFrame=null;if(frame!==null)cancelAnimationFrame(frame);renderDay();frame=requestAnimationFrame(animate);});
$("dayScrub").addEventListener("input",e=>{if(!result)return;paused=true;animating=false;if(frame!==null)cancelAnimationFrame(frame);frame=null;day=Number(e.target.value);lastFrame=null;renderDay();setStatus("Inspecting simulated day "+day.toFixed(1));});
$("speed").addEventListener("change",()=>{lastFrame=null;});
document.querySelectorAll("[data-view]").forEach(b=>b.addEventListener("click",()=>{view=b.dataset.view;chart.selectedPath=null;document.querySelectorAll("[data-view]").forEach(x=>x.setAttribute("aria-pressed",String(x===b)));renderDay();}));
$("resetView").addEventListener("click",()=>chart.resetZoom());
function revealActual2025(visible){
 actual=visible;
 $("revealBtn").setAttribute("aria-pressed",String(actual));
 $("revealBtn").textContent=actual?"Hide actual 2025":"Reveal actual 2025";
 renderDay();
 if(actual)chart.fitFullYear();else chart.resetZoom();
}
$("revealBtn").addEventListener("click",()=>revealActual2025(!actual));
$("fitYear").addEventListener("click",()=>revealActual2025(true));
function drawDistribution(){
 const c=$("distribution"),w=c.clientWidth,h=c.clientHeight;if(!w||!h)return;
 const ratio=Math.min(2,window.devicePixelRatio||1),g=c.getContext("2d");c.width=Math.round(w*ratio);c.height=Math.round(h*ratio);g.setTransform(ratio,0,0,ratio,0,0);g.clearRect(0,0,w,h);
 const pad={l:46,r:12,t:21,b:42},W=w-pad.l-pad.r,H=h-pad.t-pad.b,colors=modelColors;
 g.font="11px system-ui";g.textBaseline="middle";g.textAlign="right";
 let values=result?modelNames.flatMap(m=>result.models[m].returns):[];
 let minReturn=Infinity,maxReturn=-Infinity;for(let v of values){if(v<minReturn)minReturn=v;if(v>maxReturn)maxReturn=v;}
 const lo=result?Math.max(-95,Math.floor(minReturn/10)*10):-65,hi=result?Math.min(400,Math.ceil(maxReturn/10)*10):70;
 const span=Math.max(30,hi-lo),bins=44,B=span/bins,hists={},x=v=>pad.l+(v-lo)/span*W;
 let maxP=.1;
 if(result){
  for(let m of modelNames){
   const a=new Array(bins).fill(0);
   for(let r of result.models[m].returns){let i=Math.min(bins-1,Math.max(0,Math.floor((r-lo)/span*bins)));a[i]++;}
   hists[m]=a.map(v=>v/result.models[m].returns.length);maxP=Math.max(maxP,...hists[m]);
  }
 }
 for(let i=0;i<=4;i++){const Y=pad.t+H*i/4;g.strokeStyle="#283849";g.beginPath();g.moveTo(pad.l,Y);g.lineTo(w-pad.r,Y);g.stroke();g.fillStyle="#92a8bb";g.fillText(((1-i/4)*maxP*100).toFixed(0)+"%",pad.l-7,Y);}
 for(let i=0;i<=5;i++){const v=lo+span*i/5;g.textAlign="center";g.fillStyle="#95abbc";g.fillText(Math.round(v)+"%",x(v),h-18);}
 if(result){for(let m of modelNames){g.fillStyle=colors[m];g.globalAlpha=.28;hists[m].forEach((p,i)=>{const bh=H*p/maxP;g.fillRect(pad.l+i*W/bins,pad.t+H-bh,Math.max(1,W/bins-1),bh);});}g.globalAlpha=1;}
 const cut=-100*readSettings().threshold,X=x(cut);
 if(X>=pad.l&&X<=w-pad.r){g.save();g.setLineDash([4,4]);g.strokeStyle="#f09aa1";g.beginPath();g.moveTo(X,pad.t);g.lineTo(X,pad.t+H);g.stroke();g.restore();g.textAlign="left";g.fillStyle="#f6a6a9";g.font="10px system-ui";g.fillText("LOSS LIMIT",Math.max(pad.l,Math.min(w-90,X+4)),pad.t+8);}
 g.textAlign="right";g.fillStyle="#9eb6ca";g.fillText("TERMINAL RETURN",w-12,h-4);
}
const dialog=$("helpDialog");
$("helpOpen").addEventListener("click",()=>dialog.showModal());
$("helpClose").addEventListener("click",()=>dialog.close());
dialog.addEventListener("click",e=>{if(e.target===dialog)dialog.close();});
const sections=["simulation","comparison","validation","validation2026","methodology"];
if("IntersectionObserver" in window){const observer=new IntersectionObserver(entries=>{for(let e of entries)if(e.isIntersecting){document.querySelectorAll(".nav a").forEach(a=>a.classList.toggle("active",a.hash==="#"+e.target.id));}},{rootMargin:"-20% 0px -65% 0px"});sections.forEach(id=>observer.observe($(id)));}
window.addEventListener("resize",drawDistribution);
labels();clearResults();chart.resetZoom();updateActualSummary();
window.CRLApp={get result(){return result;},get phase(){return phase;},get chart(){return chart;}};
})();