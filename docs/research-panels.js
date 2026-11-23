"use strict";
/* CryptoRisk Lab research panels. Read-only presentation on top of the verified
   Monte Carlo engine in index.html. Never modify existing calibrated parameters. */
(function(){
 const el=id=>document.getElementById(id);
 const historicalPanel=el("historicalPanel");
 let candles=[], historicalLoaded=false;
 const money=n=>Number(n).toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2});
 const cl=(c)=>c>=0?"#16816b":"#b76045";
 const drawCanvas=(node)=>{
   const width=node.clientWidth||800, height=node.clientHeight||260,dpr=window.devicePixelRatio||1;
   if(node.width!==Math.round(width*dpr)||node.height!==Math.round(height*dpr)){
     node.width=Math.round(width*dpr);node.height=Math.round(height*dpr);
   }
   const ctx=node.getContext("2d");
   ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,width,height);
   return {ctx,width,height};
 };
 async function loadCandles(){
   try{
     const response=await fetch("./btc-historical.json",{cache:"force-cache"});
     if(!response.ok)throw Error("HTTP "+response.status);
     const json=await response.json();
     const data=json.candles;
     if(!Array.isArray(data)||data.length<50||!data.every(c=>c.low<=c.open&&c.open<=c.high&&c.low<=c.close&&c.close<=c.high))throw Error("Invalid OHLC data");
     const origin=data.find(c=>c.date==="2024-12-31");
     if(!origin||Math.abs(origin.close-GBM.initialPrice)>0.01)throw Error("Calibration-origin mismatch");
     candles=data;historicalLoaded=true;
     el("historicalStatus").textContent="Binance spot BTC/USDT · daily UTC · 1 Dec 2024–31 Jan 2025 · observed prices";
     drawCandles();
   }catch(err){
     el("historicalStatus").textContent="Historical chart unavailable in this context. Open the published GitHub Pages site.";
     console.warn("Historical OHLC:",err);
   }
 }
 function drawCandles(){
   if(!historicalLoaded)return;
   const canvas=el("historicalCandles"),{ctx,width:w,height:h}=drawCanvas(canvas);
   const pad={l:76,r:18,t:22,b:43},plotW=Math.max(30,w-pad.l-pad.r),plotH=h-pad.t-pad.b;
   const lo=Math.min(...candles.map(c=>c.low)),hi=Math.max(...candles.map(c=>c.high)),range=hi-lo||1;
   const min=lo-range*.07,max=hi+range*.07;
   const x=i=>pad.l+(i+.5)*plotW/candles.length;
   const y=v=>pad.t+(max-v)/(max-min)*plotH;
   ctx.font="12px system-ui";ctx.fillStyle="#506460";ctx.textAlign="left";
   ctx.fillText("BTC price (USDT)",12,14);
   for(let tick=0;tick<=4;tick++){
     const val=min+(max-min)*tick/4,p=y(val);
     ctx.strokeStyle="#e4ebe4";ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(pad.l,p);ctx.lineTo(w-pad.r,p);ctx.stroke();
     ctx.fillStyle="#667b72";ctx.textAlign="right";ctx.fillText(Math.round(val).toLocaleString(),pad.l-9,p+4);
   }
   const originIdx=candles.findIndex(c=>c.date==="2024-12-31");
   ctx.fillStyle="rgba(8,127,118,.06)";ctx.fillRect(x(originIdx),pad.t,w-pad.r-x(originIdx),plotH);
   ctx.save();ctx.setLineDash([5,4]);ctx.strokeStyle="#758b7e";ctx.beginPath();ctx.moveTo(x(originIdx),pad.t);ctx.lineTo(x(originIdx),h-pad.b);ctx.stroke();ctx.restore();
   const barWidth=Math.max(2,Math.min(10,(plotW/candles.length)*.63));
   candles.forEach((c,i)=>{
     const color=cl(c.close-c.open),cx=x(i);
     ctx.strokeStyle=color;ctx.lineWidth=1.4;ctx.beginPath();ctx.moveTo(cx,y(c.high));ctx.lineTo(cx,y(c.low));ctx.stroke();
     ctx.fillStyle=color;ctx.fillRect(cx-barWidth/2,Math.min(y(c.open),y(c.close)),barWidth,Math.max(1.5,Math.abs(y(c.open)-y(c.close))));
   });
   for(const i of [0,originIdx,candles.length-1]){
     ctx.fillStyle="#506460";ctx.textAlign=i===0?"left":i===candles.length-1?"right":"center";
     ctx.fillText(candles[i].date.slice(5),x(i),h-13);
   }
   const january=candles.find(c=>c.date==="2025-01-30");
   if(january){
     const returnPct=(january.close/GBM.initialPrice-1)*100;
     el("historicalOutcome").textContent="Historical comparison: BTC close on 30 Jan 2025 was "+money(january.close)+" USDT ("+(returnPct>=0?"+":"")+returnPct.toFixed(2)+"% versus 31 Dec 2024). This is one actual outcome, not a simulated prediction.";
   }
 }
 const P=[
 [MARKOV.probabilityNextCalm[0],1-MARKOV.probabilityNextCalm[0]],
 [MARKOV.probabilityNextCalm[1],1-MARKOV.probabilityNextCalm[1]]
 ];
 function futureStateProbs(start,horizon){
   const out=[[start===0?1:0,start===1?1:0]];
   for(let d=1;d<=horizon;d++){
     const prev=out[d-1];
     out.push([prev[0]*P[0][0]+prev[1]*P[1][0],prev[0]*P[0][1]+prev[1]*P[1][1]]);
   }
   return out;
 }
 function regimeMetrics(){
   el("calmStay").textContent=(100*P[0][0]).toFixed(2)+"%";
   el("volatileStay").textContent=(100*P[1][1]).toFixed(2)+"%";
   el("calmDuration").textContent=(1/(1-P[0][0])).toFixed(2)+" days";
   el("volatileDuration").textContent=(1/(1-P[1][1])).toFixed(2)+" days";
   const horizon=Number(el("horizon").value),start=Number(document.querySelector('input[name="initialRegime"]:checked').value);
   const points=futureStateProbs(start,horizon);
   const {ctx,width:w,height:h}=drawCanvas(el("regimeChart"));
   const left=48,right=w-16,top=18,bottom=h-39;
   const x=d=>left+(right-left)*d/horizon,y=p=>bottom-(bottom-top)*p;
   ctx.font="12px system-ui";ctx.fillStyle="#506460";
   for(const p of [0,.25,.5,.75,1]){
     ctx.strokeStyle="#e4ebe4";ctx.beginPath();ctx.moveTo(left,y(p));ctx.lineTo(right,y(p));ctx.stroke();
     ctx.textAlign="right";ctx.fillText(Math.round(p*100)+"%",left-9,y(p)+4);
   }
   const draw=(index,color,dash)=>{
     ctx.beginPath();ctx.setLineDash(dash);ctx.strokeStyle=color;ctx.lineWidth=2.8;
     points.forEach((p,d)=>d?ctx.lineTo(x(d),y(p[index])):ctx.moveTo(x(d),y(p[index])));
     ctx.stroke();ctx.setLineDash([]);
   };
   draw(0,"#087f76",[]);draw(1,"#a35326",[7,3]);
   ctx.fillStyle="#506460";ctx.textAlign="center";
   for(const day of [0,Math.round(horizon/2),horizon])ctx.fillText("Day "+day,x(day),h-12);
   el("day30Regime").textContent="On day "+horizon+": Calm "+(100*points[horizon][0]).toFixed(1)+"%, Volatile "+(100*points[horizon][1]).toFixed(1)+"%. These are theoretical Markov probabilities, not price forecasts.";
 }
 let replayDay=0,replayTimer=null;
 function stopReplay(){if(replayTimer!==null){clearInterval(replayTimer);replayTimer=null;}el("replayPlay").textContent="Play";}
 function replayPaths(){
   const prices=simulation?.displayPaths?.markov?.[0];
   const states=prices?.regimes;
   return prices&&states&&states.length===prices.length?{prices,states}:null;
 }
 function updateReplay(){
   const sample=replayPaths();
   const slider=el("replayDay");const horizon=simulation?.settings?.horizon||Number(el("horizon").value);
   slider.max=String(horizon);replayDay=Math.max(0,Math.min(replayDay,horizon));slider.value=String(replayDay);
   el("replayDayText").textContent="Day "+replayDay+" / "+horizon;
   if(!sample){
     el("replayDescription").textContent="Start the simulation to generate a replayable Markov scenario.";
     el("replayPlay").disabled=true;drawReplay(null);return;
   }
   el("replayPlay").disabled=false;
   const price=sample.prices[replayDay],value=simulation.settings.investment*price/GBM.initialPrice,state=sample.states[replayDay];
   el("replayDescription").textContent="Simulated BTC: "+money(price)+" USDT · Investment: "+money(value)+" USDT · P/L: "+(value>=simulation.settings.investment?"+":"")+money(value-simulation.settings.investment)+" USDT · "+(state===0?"Calm":"Volatile")+" regime";
   el("replayRegime").textContent=state===0?"CALM":"VOLATILE";
   el("replayRegime").className=state===0?"state-calm":"state-volatile";
   drawReplay(sample.prices);
 }
 function drawReplay(prices){
   const {ctx,width:w,height:h}=drawCanvas(el("replayChart"));
   ctx.font="12px system-ui";ctx.fillStyle="#506460";
   if(!prices){ctx.fillText("No replay available before simulation starts",18,35);return;}
   const left=70,right=w-19,top=24,bottom=h-35;
   const lo=Math.min(...prices),hi=Math.max(...prices),span=hi-lo||1;
   const y=p=>bottom-(bottom-top)*((p-lo+span*.08)/(span*1.16));
   const x=d=>left+(right-left)*d/(prices.length-1);
   for(let k=0;k<=4;k++){
     const val=lo+span*k/4;
     ctx.strokeStyle="#e4ebe4";ctx.beginPath();ctx.moveTo(left,y(val));ctx.lineTo(right,y(val));ctx.stroke();
     ctx.fillStyle="#506460";ctx.textAlign="right";ctx.fillText(Math.round(val).toLocaleString(),left-8,y(val)+4);
   }
   ctx.beginPath();ctx.strokeStyle="#087f76";ctx.lineWidth=2.6;
   for(let d=0;d<=replayDay;d++)d?ctx.lineTo(x(d),y(prices[d])):ctx.moveTo(x(d),y(prices[d]));
   ctx.stroke();ctx.fillStyle="#087f76";ctx.beginPath();ctx.arc(x(replayDay),y(prices[replayDay]),4,0,Math.PI*2);ctx.fill();
   ctx.fillStyle="#506460";ctx.textAlign="center";ctx.fillText("Simulated day "+replayDay,x(replayDay),h-10);
 }
 function handleNewRun(){
   stopReplay();replayDay=0;updateReplay();regimeMetrics();
 }
 el("replayPlay").addEventListener("click",()=>{
   const sample=replayPaths();if(!sample)return;
   if(replayTimer!==null){stopReplay();return;}
   if(replayDay>=sample.prices.length-1)replayDay=0;
   el("replayPlay").textContent="Pause";
   replayTimer=setInterval(()=>{
     const latest=replayPaths();
     if(!latest){stopReplay();updateReplay();return;}
     replayDay++;updateReplay();
     if(replayDay>=latest.prices.length-1)stopReplay();
   },230);
 });
 el("replayDay").addEventListener("input",e=>{stopReplay();replayDay=Number(e.target.value);updateReplay();});
 // These actions run after the original engine's handlers.
 el("startBtn").addEventListener("click",()=>requestAnimationFrame(updateReplay));
 el("pauseBtn").addEventListener("click",updateReplay);
 el("resetBtn").addEventListener("click",handleNewRun);
 document.querySelectorAll("#horizon, #initialRegime input, #pathCount input, #investment, #volatilityScale, #seed").forEach(node=>{
   node.addEventListener("change",handleNewRun);
 });
 // One-time, rate-limited observation. No mutation of original simulation.
 let lastCompletion=-1;
 const monitor=setInterval(()=>{
   if(!document.contains(historicalPanel)){clearInterval(monitor);return;}
   const count=simulation?.completed??0;
   if(count!==lastCompletion && (count===1 || count>=simulation?.settings?.pathCount || lastCompletion<0)){
     lastCompletion=count;updateReplay();
   }
 },450);
 window.addEventListener("resize",()=>{drawCandles();regimeMetrics();updateReplay();});
 el("validationNote").textContent="Historical fixed-parameter evaluation · 335 overlapping 30-day origins in 2025 · 62 observed ≥10% losses, 8 observed ≥20% losses, 0 observed ≥35% losses. Regime model improvement is descriptive and not statistically confirmed after multiplicity correction.";
 regimeMetrics();updateReplay();loadCandles();
})();