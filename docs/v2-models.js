/* CryptoRisk Lab: five-model independent browser Monte Carlo engine.
 * GBM/Markov parameters and EWMA origin variances exported from the executed
 * 2022–2024 notebook in scripts/verify_notebook.py, CI run 45210897502.
 * No 2025 return is used to initialize these forecasts.
 * Historical fixed 2025 scoring remains separate from interactive scenarios. */
(function(global){"use strict";
const origin=93576, models=["gbm","markov","ewma","adaptive_gbm","garch"];
const CAL={
  gbm:{mu:0.0006149477738712015,sigma:0.028459921644738977},
  markov:{
    mu:[0.0011709082452031764,0.0002649261708609547],
    sigma:[0.02453708413230616,0.032033470949311985],
    nextCalm:[499/540,41/541]
  },
  ewma:{mu:0.0006149477738712015,lambda:0.90},
  // Gaussian GARCH(1,1), fitted once to 2022–2024 log-return residuals
  // expressed in percent: h is measured in percent-return-squared.
  garch:{mu:0.0006149477738712015,omega:1.7429241072532673,alpha:0.1689729613867537,
         beta:0.6255015699659665,nextVar:5.547208876802669}
};
const EWMA_ORIGIN_VARIANCES=Object.freeze({
  "0.80":0.0003385110048979631,
  "0.81":0.00034928014258714195,
  "0.82":0.00036035738638005193,
  "0.83":0.00037173898177332527,
  "0.84":0.0003834231240189628,
  "0.85":0.00039541392305402775,
  "0.86":0.0004077278720769488,
  "0.87":0.0004204037243933131,
  "0.88":0.00043351659254548853,
  "0.89":0.0004471964502066686,
  "0.90":0.0004616494175752784,
  "0.91":0.000477176183632026,
  "0.92":0.0004941741802628649,
  "0.93":0.0005130976452044896,
  "0.94":0.000534335804161528,
  "0.95":0.0005579735603284235,
  "0.96":0.0005834826264815467,
  "0.97":0.0006096972012096493,
  "0.98":0.0006364032658109027,
  "0.99":0.0006696850129181795
});
function ewmaWarmStart(lambda){
 const key=Number(lambda).toFixed(2),v=EWMA_ORIGIN_VARIANCES[key];
 if(!Number.isFinite(v)||v<=0)throw Error("EWMA decay has no audited notebook variance: "+key);
 return v;
}
function adaptiveWarmStart(){
 // Original scenario is anchored at 31 December 2024. A 30-observation
 // rolling sample SD can be computed only from 2–31 December 2024 candles.
 const a=global.CRL_HISTORY?.candles;
 if(!a||a.length<31||a[30].date!=="2024-12-31"||a[30].close!==origin)
   throw Error("Adaptive GBM requires audited 2024-12-31 origin history");
 const daily=[];
 for(let k=1;k<=30;k++)daily.push(Math.log(a[k].close/a[k-1].close));
 const avg=daily.reduce((p,v)=>p+v,0)/30;
 const sampleVariance=daily.reduce((p,v)=>p+(v-avg)**2,0)/29;
 const sigma=Math.sqrt(sampleVariance);
 if(!Number.isFinite(sigma)||sigma<=0)throw Error("Invalid 30-return adaptive GBM variance");
 return sigma;
}
function rng(seed){let x=seed>>>0;return ()=>{x=(x+0x6d2b79f5)|0;let t=Math.imul(x^(x>>>15),x|1);t^=t+Math.imul(t^(t>>>7),t|61);return ((t^(t>>>14))>>>0)/4294967296;};}
function normal(gen){let spare=null;return ()=>{if(spare!==null){let v=spare;spare=null;return v;}let u=0;while(!u)u=gen();let v=gen();let R=Math.sqrt(-2*Math.log(u));spare=R*Math.sin(2*Math.PI*v);return R*Math.cos(2*Math.PI*v);};}
function clamp(x,a,b){return Math.max(a,Math.min(b,x));}
function isValid(s){return Number.isInteger(s.seed)&&s.seed>=1&&s.seed<=2147483647&&Number.isInteger(s.paths)&&s.paths>=100&&s.paths<=30000&&Number.isInteger(s.horizon)&&s.horizon>=7&&s.horizon<=90&&s.investment>=100&&s.investment<=1e7&&s.threshold>=.01&&s.threshold<=.6&&s.volatility>=.5&&s.volatility<=2&&[0,1].includes(s.regime)&&s.lambda>=.8&&s.lambda<=.99;}
function quantile(sorted,q){let t=(sorted.length-1)*q;let lo=Math.floor(t),hi=Math.ceil(t);return sorted[lo]*(1-(t-lo))+sorted[hi]*(t-lo);}
function summary(paths,s){
 const losses=[],ends=[],dailyTouches={n:0},byDay=Array.from({length:s.horizon+1},()=>[]);
 let maxDrawSum=0,touchCount=0;
 for(let obj of paths){
   const a=obj.values;const final=a.at(-1);const loss=s.investment*(1-final/origin);
   losses.push(loss);ends.push(100*(final/origin-1));
   let peak=a[0],maxdd=0,touched=false;
   for(let d=0;d<a.length;d++){
     const price=a[d];byDay[d].push(price);peak=Math.max(peak,price);
     maxdd=Math.max(maxdd,(peak-price)/peak);
     if(price<=origin*(1-s.threshold))touched=true;
   }
   maxDrawSum+=maxdd;if(touched)touchCount++;
 }
 const sorted=[...losses].sort((a,b)=>a-b);
 const v95=quantile(sorted,.95);
 const tail=sorted.filter(x=>x>=v95);
 const bands=byDay.map(vals=>{vals.sort((a,b)=>a-b);return [quantile(vals,.05),quantile(vals,.25),quantile(vals,.5),quantile(vals,.75),quantile(vals,.95)];});
 const proportions={};
 for(let t of [.1,.2,.35,s.threshold]){const n=losses.filter(l=>l>=s.investment*t).length;const p=n/paths.length;proportions[t.toFixed(3)]={p,low:clamp(p-1.96*Math.sqrt(p*(1-p)/paths.length),0,1),high:clamp(p+1.96*Math.sqrt(p*(1-p)/paths.length),0,1),hits:n};}
 return {n:paths.length,paths:paths.slice(0,28),bands,losses,returns:ends,prob:proportions,touch:touchCount/paths.length,drawdown:maxDrawSum/paths.length,var95:v95,es95:tail.reduce((a,b)=>a+b,0)/tail.length};
}
function createRunner(settings){
 const s={...settings};if(!isValid(s))throw Error("Invalid simulation settings");
 const seeds={gbm:0x4ab1259,markov:0x9e3779b9,ewma:0xc2b2ae35,adaptive_gbm:0x5d31b07f,garch:0x29d6af13};
 let state={done:0,total:s.paths,complete:false,cancelled:false,settings:s,raw:Object.fromEntries(models.map(m=>[m,[]])),rngs:{}};
 for(let m of models){
   const stream=rng((s.seed^seeds[m])>>>0);
   state.rngs[m]={z:normal(stream),u:m==="markov"?rng((s.seed^0x7f4a7c15)>>>0):null};
 }
 const warm=ewmaWarmStart(s.lambda),rollingSigma=adaptiveWarmStart(),garchWarm=CAL.garch.nextVar;
 function path(m){
  const a=new Float32Array(s.horizon+1);a[0]=origin;
  const states=m==="markov"?new Uint8Array(s.horizon+1):null;
  const {z,u}=state.rngs[m];let regime=s.regime,v=warm,garchVar=garchWarm; if(states)states[0]=regime;
  for(let d=1;d<=s.horizon;d++){
    let ret=0;
    if(m==="gbm")ret=CAL.gbm.mu+CAL.gbm.sigma*s.volatility*z();
    if(m==="markov"){
      ret=CAL.markov.mu[regime]+CAL.markov.sigma[regime]*s.volatility*z();
    }
    if(m==="ewma"){
      ret=CAL.ewma.mu+Math.sqrt(Math.max(0,v))*s.volatility*z();
      // Normalize the simulated scaled shock before updating the base variance.
      v=s.lambda*v+(1-s.lambda)*((ret-CAL.ewma.mu)/s.volatility)**2;
    }
    if(m==="adaptive_gbm")ret=CAL.gbm.mu+rollingSigma*s.volatility*z();
    if(m==="garch"){
      const innovationPct=Math.sqrt(Math.max(0,garchVar))*z();
      ret=CAL.garch.mu+innovationPct/100*s.volatility;
      // Scenario multiplier is not an estimated GARCH parameter.
      // Filter updates with the unscaled innovation to preserve frozen fit.
      garchVar=CAL.garch.omega+CAL.garch.alpha*innovationPct*innovationPct+
               CAL.garch.beta*garchVar;
    }
    a[d]=a[d-1]*Math.exp(ret);
    if(m==="markov"){
      regime=u()<CAL.markov.nextCalm[regime]?0:1;
      states[d]=regime;
    }
  }
  return {values:a,states};
 }
 return {
   state,
   step(batch=150){
     if(state.cancelled)return state;
     const remaining=Math.min(Math.max(1,batch),s.paths-state.done);
     for(let k=0;k<remaining;k++)for(let m of models)state.raw[m].push(path(m));
     state.done+=remaining;state.complete=state.done===s.paths;
     return state;
   },
   finish(){
     if(state.cancelled||!state.complete)throw Error("Simulation not complete");
     const outputs={};
     for(let m of models)outputs[m]=summary(state.raw[m],s);
     // Drop all unneeded paths after aggregation to keep the application responsive.
     state.raw=null;
     return {settings:s,models:outputs,warmVariance:warm,adaptiveSigma:rollingSigma,
             garchWarmVariance:garchWarm,origin,experimentalEWMAWarmStart:false,
             modelCalibration:"Frozen 2022–2024, forecast origin 2024-12-31"};
   },
   cancel(){state.cancelled=true;state.raw=null;}
 };
}
function verifyResult(result){
 const s=result.settings,errors=[];
 for(let m of models){let x=result.models[m];if(x.n!==s.paths)errors.push(m+": path count");if(!Number.isFinite(x.var95)||!Number.isFinite(x.es95)||x.es95<x.var95)errors.push(m+": VaR/ES");for(let b of x.bands)if(b.some((v,i)=>!Number.isFinite(v)||(i>0&&v<b[i-1])))errors.push(m+": percentile order");for(let key of ["0.100","0.200","0.350"]){let p=x.prob[key]?.p;if(!Number.isFinite(p)||p<0||p>1)errors.push(m+": probability "+key);}}
 return {ok:errors.length===0,errors};
}
global.CRLCore={models,CAL,origin,createRunner,verifyResult,ewmaWarmStart,adaptiveWarmStart,quantile,EWMA_ORIGIN_VARIANCES};
})(window);
