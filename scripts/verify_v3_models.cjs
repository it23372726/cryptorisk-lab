/* Standalone scientific stress test for the five-model browser engine.
 * Run with Node, no server, no dependencies. Tests the MAXIMUM permitted
 * 30,000 paths/model and 90-day horizon, with frozen 2024 model origin.
 */
"use strict";
const assert=require("node:assert/strict");
global.window=global;
require("../docs/v2-history.js");
require("../docs/v2-models.js");
const core=global.CRLCore;
assert.deepEqual(core.models,["gbm","markov","ewma","adaptive_gbm","garch"]);
assert.equal(core.origin,93576);
assert(Math.abs(core.adaptiveWarmStart()-0.02323151385685791)<1e-13);
assert(Math.abs(core.CAL.garch.nextVar-5.547208876802669)<1e-12);
assert(core.CAL.garch.alpha+core.CAL.garch.beta<1);
const scenario={investment:1000,horizon:90,paths:30000,threshold:.1,volatility:1,
  regime:0,seed:42,lambda:.90};
function run(s,batch){
 const runner=core.createRunner(s);
 while(!runner.state.complete)runner.step(batch);
 const result=runner.finish();
 assert.equal(core.verifyResult(result).ok,true);
 for(const m of core.models){
  const item=result.models[m];
  assert.equal(item.n,s.paths);
  assert.equal(item.bands.length,s.horizon+1);
  assert.equal(item.paths.length,28);
  assert(Number.isFinite(item.var95)&&item.es95>=item.var95);
  for(const t of ["0.100","0.200","0.350"]){
   assert(item.prob[t].p>=0&&item.prob[t].p<=1);
  }
  assert(item.prob["0.100"].p>=item.prob["0.200"].p);
  assert(item.prob["0.200"].p>=item.prob["0.350"].p);
 }
 return result;
}
const start=Date.now();
const heavy=run(scenario,500);
console.log("PASS: Five models × 30,000 seeded paths × 90 days in",Date.now()-start,"ms");
const small={...scenario,horizon:30,paths:1000};
const first=run(small,200),second=run(small,37);
for(const m of core.models){
 assert.deepEqual(first.models[m].prob,second.models[m].prob,
  "Changing chunk size changed seeded scientific outcomes for "+m);
 assert.deepEqual(first.models[m].bands,second.models[m].bands,
  "Changing chunk size changed model percentile forecast for "+m);
}
console.log("PASS: All five models reproducible with identical settings and different compute batch sizes");
console.log("PASS: Non-negative tail probabilities and VaR/ES order across the supported maximum scenario");
