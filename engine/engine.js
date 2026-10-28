/* ---------- value engine: pure functions, no I/O (books: Greenwald §3, Graham §3, Shenanigans §4, Lynch §3.3, NMW §11) ---------- */
const N = v => { const n = typeof v==="number"?v:parseFloat(v); return Number.isFinite(n) ? n : null; };
const fmt = (n, d=2) => (n=N(n))==null ? "—" : n.toLocaleString("en-US",{minimumFractionDigits:d,maximumFractionDigits:d});
const fmtBig = n => { n=N(n); if(n==null) return "—"; const a=Math.abs(n); return a>=1e12?(n/1e12).toFixed(2)+"T":a>=1e9?(n/1e9).toFixed(2)+"B":a>=1e6?(n/1e6).toFixed(2)+"M":fmt(n,0); };
const pct = (n,d=1) => (n=N(n))==null ? "—" : (n>0?"+":"")+(n*100).toFixed(d)+"%";
const pc=(n,d=0)=>(n*100).toFixed(d)+"%";
const sum = a => a.reduce((x,y)=>x+y,0);
const mean = a => a.length?sum(a)/a.length:null;
const clamp=(v,lo=0,hi=100)=>Math.max(lo,Math.min(hi,v));
const smaAt=(c,i,n)=>i+1>=n?sum(c.slice(i+1-n,i+1))/n:null;
function rsiW(c){ if(c.length<16) return null; let g=0,l=0; for(let i=1;i<=14;i++){ const d=c[i]-c[i-1]; d>0?g+=d:l-=d; } g/=14; l/=14; for(let i=15;i<c.length;i++){ const d=c[i]-c[i-1]; g=(g*13+Math.max(d,0))/14; l=(l*13+Math.max(-d,0))/14; } return l===0?100:100-100/(1+g/l); }
function emaArr(c,n){ const k=2/(n+1); const o=[c[0]]; for(let i=1;i<c.length;i++) o.push(c[i]*k+o[i-1]*(1-k)); return o; }
function atrW(b){ if(b.length<16) return null; const tr=b.slice(1).map((x,i)=>Math.max(x.h-x.l,Math.abs(x.h-b[i].c),Math.abs(x.l-b[i].c))); let a=sum(tr.slice(0,14))/14; for(let i=14;i<tr.length;i++) a=(a*13+tr[i])/14; return a; }
function asJson(p){ if(typeof p==="string"){ try{ return JSON.parse(p); }catch{ return null; } } return p; }
function findArr(o,test,depth=0){
  o=asJson(o); if(o==null||depth>5) return null;
  if(Array.isArray(o)){ if(o.length&&test(o[0])) return o; for(const x of o){ const r=findArr(x,test,depth+1); if(r) return r; } return null; }
  if(typeof o==="object"){ if(test(o)) return [o]; for(const k of Object.keys(o)){ const r=findArr(o[k],test,depth+1); if(r) return r; } }
  return null;
}
const newestFirst=a=>(a||[]).slice().sort((x,y)=>x.end_date<y.end_date?1:-1);

const REQ_MOS=0.33, TAX=0.25, RISK_PER_TRADE=0.015;
/* equal weights (Chan, Kahneman): finely tuned weights mostly fit past noise */
const W={mos:.2,forensic:.2,strength:.2,price:.2,owners:.2};
const CYCLICAL=/oil|gas|energy|drill|petrol|steel|metal|mining|gold|copper|alumin|chemical|auto|semiconductor|airline|homebuild|construction|shipping|marine|paper|forest|commodit|machinery|trucking|coal|fertili/i;
const FINANCIAL=/bank|insur|financ|credit|capital markets|asset management|reit|real estate investment|mortgage|thrift|brokerage/i;
const CAT_NOTES={
  "Asset play":"Valued on what it owns, not what it earns. Check the assets are real and someone can unlock them (Lynch, Graham net-nets).",
  "Turnaround":"Bought for recovery. The balance sheet must survive until it happens; check debt, cash burn and what is being fixed (Lynch).",
  "Cyclical":"Low P/E at peak earnings is a trap and a high P/E at the bottom can be the buy. Value is on mid-cycle margins (Lynch, Greenwald).",
  "Fast grower":"Growth is only worth paying for inside a franchise. Check the moat and that growth is not bought with debt (Lynch, Greenwald §3.5).",
  "Stalwart":"Big, steady grower. Buy on dips below value, take 30–50% gains, and don't overpay (Lynch).",
  "Slow grower":"Owned mainly for dividends and steadiness. Pay no more than value with zero growth (Lynch, Greenwald)."
};

/* D = {sym,cat,s (snapshot),bars,prof,incQ,incA,cfQ,cfA,bsQ,bsA,rate,tgt,alert,ins,inst,tsy,missing:[]} (raw tool payloads) */
function engine(D){
  const s=D.s, sym=D.sym, missing=D.missing||[];
  /* ---- price history and technicals ---- */
  const raw=findArr(D.bars,x=>x&&x.close!=null&&x.time!=null)||[];
  const bars=raw.map(b=>({d:String(b.time).slice(0,10),h:N(b.high),l:N(b.low),c:N(b.close),v:N(b.volume)||0})).filter(b=>b.c).sort((a,b)=>a.d<b.d?-1:1);
  if(bars.length<60) throw {plain:"Webull returned too little price history to analyze this ticker."};
  const c=bars.map(b=>b.c), L=c.length-1, price=N(s.price)??c[L];
  const s20=smaAt(c,L,20), s50=smaAt(c,L,50), s200=smaAt(c,L,200), rsi=rsiW(c), rsi10ago=rsiW(c.slice(0,L-9)), atr=atrW(bars);
  const e26=emaArr(c,26), macd=emaArr(c,12).map((v,i)=>v-e26[i]); const sig=emaArr(macd,9); const macdHist=macd[L]-sig[L];
  const lr=[]; for(let i=Math.max(1,L-59);i<=L;i++) lr.push(Math.log(c[i]/c[i-1])); const m=mean(lr); const vol60=Math.sqrt(sum(lr.map(x=>(x-m)**2))/(lr.length-1)*252);
  const ret=n=>L>=n?c[L]/c[L-n]-1:null;
  const last60=bars.slice(-60), lo60=Math.min(...last60.map(b=>b.l)), hi60=Math.max(...last60.map(b=>b.h));
  let lastCross="—"; for(let i=L;i>200;i--){ const a=smaAt(c,i,50)-smaAt(c,i,200), b=smaAt(c,i-1,50)-smaAt(c,i-1,200); if(a>0&&b<=0){ lastCross="Golden cross on "+bars[i].d; break; } if(a<0&&b>=0){ lastCross="Death cross on "+bars[i].d; break; } }
  const v20=mean(bars.slice(-20).map(b=>b.v)), v50=mean(bars.slice(-50).map(b=>b.v));
  const chart=bars.slice(-252).map((b,k,arr)=>{ const i=L-(arr.length-1-k); const r2=x=>x==null?null:Math.round(x*100)/100; return {d:b.d,c:r2(b.c),s50:r2(smaAt(c,i,50)),s200:r2(smaAt(c,i,200))}; });
  /* "has the selling stopped?" (NMW §11.B price behaviour) — a stock far below its 200-day is not penalised */
  const yr=bars.slice(-252), lo52=Math.min(...yr.map(b=>b.l));
  const recentLow=Math.min(...bars.slice(-10).map(b=>b.l)), priorLow=Math.min(...bars.slice(-60,-10).map(b=>b.l));
  const newLow20=bars.slice(-20).some(b=>b.l<=lo52*1.0001);
  const pb=[
    {ok:recentLow>priorLow, label:"Higher low: the last 10 sessions held above the prior 50-session low"},
    {ok:!newLow20, label:"No new 52-week low in the last 20 sessions"},
    {ok:s20!=null&&price>=s20, label:"Price at or above its 20-day average"},
    {ok:rsi!=null&&rsi>=40&&rsi<=70&&(rsi10ago==null||rsi>=rsi10ago), label:"RSI 40–70 and not falling"}];
  const priceScore=25*pb.filter(x=>x.ok).length;
  const priceState=priceScore>=75?"Selling has stopped":priceScore<=25?"Still falling":"Stabilising";
  /* bad-news drop (Chan, post-earnings drift): a big one-day fall in the last 10 sessions tends to keep drifting the same
     way, so a value buy waits 2-4 weeks and re-checks the value. "Big" = 7%, or 3 normal days' moves for a jumpy stock. */
  const dropLim=Math.max(0.07,3*vol60/Math.sqrt(252));
  let newsDrop=null; for(let i=Math.max(1,L-9);i<=L;i++){ const r=c[i]/c[i-1]-1; if(r<=-dropLim&&(!newsDrop||r<newsDrop.pct)) newsDrop={date:bars[i].d,pct:r,sessionsAgo:L-i}; }
  /* worst fall from a high over the price history (~19 months): a disaster stop must sit beyond it (Chan) */
  let peakC=c[0], worstDD=0; for(const x of c){ peakC=Math.max(peakC,x); worstDD=Math.max(worstDD,1-x/peakC); }
  const ddMonths=Math.round(bars.length/21);

  /* ---- statements ---- */
  const isInc=x=>x&&x.total_revenue!=null, isCf=x=>x&&x.cfo!=null, isBs=x=>x&&x.total_assets!=null;
  const iQ=newestFirst(findArr(D.incQ,isInc)), iA=newestFirst(findArr(D.incA,isInc)).filter(x=>N(x.total_revenue)>0);
  const cQ=newestFirst(findArr(D.cfQ,isCf)), cA=newestFirst(findArr(D.cfA,isCf));
  const bQ=newestFirst(findArr(D.bsQ,isBs)), bA=newestFirst(findArr(D.bsA,isBs));
  /* foreign reporters: Webull gives statements in the company's own currency (e.g. BRL) while the price is in US dollars */
  const cur=(iA[0]||iQ[0]||bQ[0]||bA[0]||{}).currency||"USD", fx=cur==="USD"?1:N(D.fx);
  if(!fx) throw {plain:`${sym} reports its financials in ${cur}, and the ${cur}-to-dollar exchange rate couldn't be loaded, so no value can be estimated. Try again in a minute.`};
  if(fx!==1){ const conv=r=>{ const o={...r}; for(const k in o) if(!/shares|fiscal|date|currency/.test(k)&&N(o[k])!=null) o[k]=N(o[k])*fx; return o; };
    for(const a of [iQ,iA,cQ,cA,bQ,bA]) a.forEach((r,i)=>{ a[i]=conv(r); }); }
  const prof=(findArr(D.prof,x=>x&&x.company_name)||[])[0]||null;
  const rt=(findArr(D.rate,x=>x&&x.number!=null)||[])[0]||null, tg=(findArr(D.tgt,x=>x&&x.mean!=null)||[])[0]||null;
  const al=(findArr(D.alert,x=>x&&(x.start_date||x.eps_est))||[])[0]||null;
  const name=prof?.company_name||s.symbol||sym;
  const industry=(prof?.industries||[]).join(" · ");
  const isFin=FINANCIAL.test(industry), mcap=N(s.market_value);
  const ttm=(arr,k,off=0)=>arr.length>=off+4&&arr.slice(off,off+4).every(q=>N(q[k])!=null)?sum(arr.slice(off,off+4).map(q=>N(q[k]))):null;
  const at=(arr,end)=>arr.find(x=>x.end_date===end)||null;
  const F={}, flags=[], strengths=[], weaknesses=[], notes=[], metrics=[];
  const flag=(issue,severity,detail)=>flags.push({issue,severity,detail});
  const metric=(name,value,status,detail)=>metrics.push({name,value,status,detail});
  F.rev=ttm(iQ,"total_revenue")??N(iA[0]?.total_revenue);
  const revPrev=ttm(iQ,"total_revenue",4)??N(iA[1]?.total_revenue);
  F.revG=F.rev&&revPrev?F.rev/revPrev-1:null;
  F.ebit=ttm(iQ,"op_income")??N(iA[0]?.op_income);
  F.ni=ttm(iQ,"net_income")??N(iA[0]?.net_income);
  F.cfo=ttm(cQ,"cfo")??N(cA[0]?.cfo);
  F.capex=ttm(cQ,"capex")??N(cA[0]?.capex);
  F.da=ttm(cQ,"dna")??N(cA[0]?.dna);
  F.fcf=F.cfo!=null&&F.capex!=null?F.cfo+F.capex:null;
  const b0=bQ[0]||bA[0]||null;
  let shares=N(b0?.common_shares_out)||N(iQ[0]?.diluted_avg_shares)||N(iA[0]?.diluted_avg_shares)||(mcap&&price?mcap/price:null);
  /* share classes and ADRs: Webull's eps_ttm is per traded share, so profit ÷ eps_ttm is the share count the price applies to */
  let shareNote=null, adrK=1;
  const epsT=N(s.eps_ttm)!=null?N(s.eps_ttm):null, implied=F.ni>0&&epsT>=0.05?F.ni/epsT:null;
  if(implied&&shares&&Math.abs(shares/implied-1)>0.25){
    const alt=[N(iQ[0]?.diluted_avg_shares),N(iA[0]?.diluted_avg_shares)].find(x=>x&&Math.abs(x/implied-1)<=0.15);
    shareNote=`Share count changed from ${fmtBig(shares)} to ${fmtBig(alt||implied)}: the balance-sheet figure didn't match the per-share earnings Webull quotes for the traded share (${alt?"a second share class was left out":"likely an ADR that represents several shares"}).`;
    if(!alt) adrK=(N(iA[0]?.diluted_avg_shares)||implied)/implied;
    shares=alt||implied;
  }
  const cash=N(b0?.cash_st_invest)||0, debt=N(b0?.total_debt)||0, minority=N(b0?.minority_interest)||0;
  const equity=N(b0?.total_sh_equity)??N(b0?.total_equity);
  const goodwill=N(b0?.goodwill_net)||0, intang=N(b0?.intangibles_net)||0;
  const ca=N(b0?.total_cur_assets), cl=N(b0?.total_cur_liab), tl=N(b0?.total_liab), ta=N(b0?.total_assets);
  F.curRatio=ca&&cl?ca/cl:null; F.netCash=cash-debt;
  F.om=F.rev&&F.ebit!=null?F.ebit/F.rev:null;
  if(iQ.length>=5){ const gm=q=>N(q.gross_profit)/N(q.total_revenue); F.gm=gm(iQ[0]); F.gmY=gm(iQ[4]); }
  const dil=(a,b)=>N(a?.diluted_avg_shares)&&N(b?.diluted_avg_shares)?N(a.diluted_avg_shares)/N(b.diluted_avg_shares)-1:null;
  F.sharesG=iQ.length>=5?dil(iQ[0],iQ[4]):dil(iA[0],iA[1]);

  /* ---- Lynch category (§3.3) ---- */
  /* one-off charges (Webull's "unusual" line) are smoothed: every period carries the median charge, so one big write-down
     doesn't drag the average while charges that recur every year still count (Greenwald §3.3) */
  const unus=y=>N(y.unusual_expense_income)||0;
  const uR=iA.map(y=>unus(y)/N(y.total_revenue)).filter(Number.isFinite).sort((a,b)=>a-b);
  const medU=uR.length?(uR[Math.floor((uR.length-1)/2)]+uR[Math.ceil((uR.length-1)/2)])/2:0;
  const rawM=iA.map(y=>N(y.op_income)/N(y.total_revenue)).filter(Number.isFinite);
  const margins=iA.map(y=>(N(y.op_income)+unus(y))/N(y.total_revenue)-medU).filter(Number.isFinite);
  if(F.om!=null&&iQ.length>=4){ rawM.unshift(F.om); margins.unshift((F.ebit+sum(iQ.slice(0,4).map(unus)))/F.rev-medU); }
  const avgM=mean(margins), minM=margins.length?Math.min(...margins):null, maxM=margins.length?Math.max(...margins):null;
  /* swings are judged before one-off charges, so big write-downs don't make a steady business look cyclical */
  const adjM=iA.map(y=>((N(y.op_income)||0)+Math.max(0,N(y.unusual_expense_income)||0))/N(y.total_revenue)).filter(Number.isFinite);
  const avgAdj=mean(adjM), sdM=adjM.length>1?Math.sqrt(mean(adjM.map(x=>(x-avgAdj)**2))):0;
  const cagr=iA.length>=3?Math.pow(N(iA[0].total_revenue)/N(iA[iA.length-1].total_revenue),1/(iA.length-1))-1:F.revG;
  const cyclical=CYCLICAL.test(industry)||(avgAdj?sdM/Math.abs(avgAdj)>0.5:false);

  /* ---- intrinsic value (Greenwald EPV, Graham number, asset values) ---- */
  const tsyRow=(findArr(D.tsy,x=>x&&x.date&&x.value!=null)||[])[0];
  const tsy=N(tsyRow?.value)!=null?N(tsyRow.value)/100:null;
  const rf=tsy??0.045;
  let prem=0.03; if(cyclical||vol60>0.45) prem+=0.02; if(mcap&&mcap<2e9) prem+=0.01;
  const R=Math.max(0.08,rf+prem);
  const revBase=F.rev;
  /* maintenance capex (Greenwald §3.3 step 6): growth capex = avg(net PP&E / sales) × change in sales */
  let daAdj=0, maint=null;
  const ppeRatio=mean(iA.map(y=>{ const b=at(bA,y.end_date); return b&&N(b.ppe_net)!=null?N(b.ppe_net)/N(y.total_revenue):null; }).filter(Number.isFinite));
  if(F.da!=null&&F.capex!=null&&ppeRatio!=null&&revBase&&revPrev){
    const growthCapex=Math.max(0,ppeRatio*(revBase-revPrev)); const cap=Math.abs(F.capex);
    maint=clamp(cap-growthCapex,0.5*cap,cap); daAdj=F.da-maint;
    if(avgM!=null&&daAdj>0) daAdj=Math.min(daAdj,0.3*Math.abs(avgM*revBase));
  }
  const V={R,rf,rfDate:tsyRow?.date||null,premium:prem,taxRate:TAX,normMargin:avgM,minMargin:minM,maxMargin:maxM,years:iA.length,maintCapex:maint,method:null,notes:[]};
  if(fx!==1) V.notes.push(`Financials are reported in ${cur} and were converted to US dollars at today's rate (${fx.toPrecision(4)} USD per ${cur}); older years at today's rate, so a currency swing changes the value.`);
  if(shareNote) V.notes.push(shareNote);
  const rawAvg=mean(rawM); if(rawAvg!=null&&avgM!=null&&Math.abs(avgM-rawAvg)>0.02) V.notes.push(`One-off charges smoothed: average operating margin is taken as ${pc(avgM,1)} instead of the reported ${pc(rawAvg,1)}, because a single large write-down or gain is replaced by the company's typical yearly charge.`);
  const perShare=x=>x!=null&&shares?x/shares:null;
  const excess=Math.max(0,cash-0.01*(revBase||0));
  const epvAt=(margin,r)=>{ if(margin==null||!revBase) return null; const e=(margin*revBase+daAdj)*(1-TAX); return e/r+excess-debt-minority; };
  if(isFin){
    const nis=iA.map(y=>N(y.net_income)).filter(Number.isFinite);
    const nAvg=mean(nis); V.method="Earnings power (financial company: average net income ÷ cost of equity)";
    V.epvEquity=nAvg!=null?nAvg/R:null; V.trough=nis.length?Math.min(...nis)/(R+0.02):null; V.peak=nis.length?Math.max(...nis)/R:null;
    V.earnings=nAvg;
  }else{
    V.method="Earnings power value: mid-cycle operating margin × current sales, taxed at 25%, ÷ cost of capital, plus excess cash, minus debt";
    V.earnings=avgM!=null&&revBase?(avgM*revBase+daAdj)*(1-TAX):null;
    V.epvEquity=epvAt(avgM,R); V.trough=epvAt(minM,R+0.02); V.peak=epvAt(maxM,R);
  }
  V.epv=perShare(V.epvEquity);
  V.bvps=perShare(equity); V.tbvps=equity!=null?perShare(equity-goodwill-intang):null;
  V.ncav=ca!=null&&tl!=null?perShare(ca-tl-minority):null;
  const eps3=iA.length>=3?mean(iA.slice(0,3).map(y=>N(y.diluted_eps_excl_extra)??N(y.diluted_eps_incl_extra)))*adrK:null;
  V.eps3=eps3; V.graham=eps3>0&&V.bvps>0?Math.sqrt(22.5*eps3*V.bvps):null;
  /* return on capital is judged on TANGIBLE capital (Greenwald §3.5): goodwill and intangibles from past acquisitions
     are the price once paid for a business, not capital it needs to run, so a big stock-paid deal (e.g. AMD-Xilinx)
     doesn't hide how much the operating business earns. The all-in figure is kept for reference. */
  const invested=(equity||0)+debt-cash;
  const tangInvested=(equity!=null?equity-goodwill-intang:0)+debt-cash;
  V.roicTotal=V.earnings!=null&&invested>0?V.earnings/invested:null;
  V.assetLight=V.earnings!=null&&V.earnings>0&&tangInvested<=0;
  V.roic=V.earnings==null?null:V.assetLight?1:tangInvested>0?V.earnings/tangInvested:null;
  V.franchise=V.epv!=null&&V.epv>0&&V.roic!=null&&V.roic>R+0.04&&(V.tbvps==null||V.tbvps<=0||V.epv>1.5*V.tbvps);
  /* growth value (Greenwald §3.5, two stages): growth only counts inside a franchise, and each year part of profit is
     reinvested to fund it (reinvestment = growth ÷ return on capital). Years 1-5 grow at g1, years 6-10 fade to a 3%
     long-run rate, then a perpetuity. g1 is the LOWER of the multi-year sales growth and the last year's, capped at 25%.
     The starting margin is halfway between the last 12 months and the mid-cycle average, so a cyclical peak isn't
     taken at face value but a business whose margins have moved up isn't judged only on its old years. */
  const gT=Math.min(0.03,rf), revGs=[cagr,F.revG].filter(Number.isFinite);
  const g1=revGs.length?Math.max(0,Math.min(...revGs,0.25)):0;
  const ttmAdjM=F.om!=null&&iQ.length>=4?(F.ebit+sum(iQ.slice(0,4).map(unus)))/F.rev-medU:null;
  const runM=avgM!=null&&ttmAdjM!=null?(avgM+ttmAdjM)/2:avgM;
  const growthEq=(gStart,margin)=>{
    if(margin==null||!revBase||V.roic==null) return null;
    let e=(margin*revBase+daAdj)*(1-TAX); if(!(e>0)) return null;
    let pv=0, d=1, g=gStart;
    for(let t=1;t<=10;t++){ g=t<=5?gStart:gStart+(gT-gStart)*(t-5)/5; e*=1+g; d/=1+R; pv+=e*Math.max(0,1-g/V.roic)*d; }
    const tv=e*(1+gT)*Math.max(0,1-gT/V.roic)/(R-gT);
    return pv+tv*d+excess-debt-minority; };
  V.g1=g1; V.gT=gT; V.runMargin=runM; V.growth=g1;
  V.growthValue=V.franchise&&g1>0?perShare(growthEq(g1,runM)):null;
  const gBull=revGs.length?Math.max(0,Math.min(Math.max(...revGs),0.35)):0;
  V.growthBull=V.franchise&&gBull>0?perShare(growthEq(gBull,ttmAdjM!=null?Math.max(ttmAdjM,runM):runM)):null;
  V.multiplier=V.growthValue!=null&&V.epv>0?V.growthValue/V.epv:1;
  /* what the price assumes: the 5-year growth rate (then the same fade) that makes the growth value equal today's price */
  V.impliedG=null; V.impliedNote=null;
  if(price>0&&V.roic!=null&&V.roic>R&&runM!=null&&shares){
    const at=g=>perShare(growthEq(g,runM));
    if(at(0)!=null&&at(0)>=price) V.impliedG=0;
    else if(at(1)!=null&&at(1)<price) V.impliedNote="more than 100% a year";
    else if(at(0)!=null){ let lo=0,hi=1; for(let k=0;k<60;k++){ const mid=(lo+hi)/2; (at(mid)>=price?hi=mid:lo=mid); } V.impliedG=(lo+hi)/2; }
  }else if(V.roic!=null&&V.roic<=R) V.impliedNote="no growth rate: at this return on capital growth doesn't add value";
  /* choose intrinsic value */
  if(V.growthValue!=null&&V.epv>0&&V.growthValue>V.epv){ V.iv=V.growthValue; V.ivMethod="Growth value (earnings power plus growth inside a franchise)"; V.method="Growth value: earnings power at a margin halfway between the last 12 months and the mid-cycle average, growing "+pc(g1,1)+" a year for 5 years then fading to "+pc(gT,0)+", with each year's growth paid for out of profit (growth ÷ return on tangible capital), discounted at the cost of capital, plus excess cash, minus debt"; }
  else if(V.epv!=null&&V.epv>0){ V.iv=V.epv; V.ivMethod="Earnings power value"; }
  else if(V.graham!=null){ V.iv=V.graham; V.ivMethod="Graham number"; }
  else if(V.ncav!=null&&V.ncav>0){ V.iv=V.ncav; V.ivMethod="Net current asset value"; }
  else { V.iv=null; V.ivMethod="None: earnings and assets don't support a value"; }
  if(V.iv!=null&&V.ncav>0&&V.ncav>V.iv){ V.iv=V.ncav; V.ivMethod="Net current asset value (above earnings power)"; }
  V.mos=V.iv?1-price/V.iv:null;
  V.buyBelow=V.iv?V.iv*(1-REQ_MOS):null;
  V.reqMos=REQ_MOS;
  const troughPs=perShare(V.trough);
  V.bear=Math.max(troughPs??-Infinity,V.ncav??-Infinity,0); if(V.iv!=null) V.bear=Math.min(V.bear,V.iv);
  V.bearBasis=V.bear===0?"No asset floor: a bad outcome could mean most of the price is lost":V.bear===V.ncav?"Net current assets":"Earnings power at the worst operating margin of recent years";
  V.bull=V.iv==null?null:Math.max(V.iv,V.growthBull??-Infinity,V.franchise?-Infinity:(perShare(V.peak)??V.iv));
  /* SANITY GUARD: a value under a quarter of the price (or over four times it) means the methods can't explain this
     stock (a fast grower the market prices on growth it can't yet see, or bad data). Show the estimate, but give no
     buy-below price, no margin-of-safety score and no paper-bot trigger, and say why. */
  V.ratio=V.iv&&price?V.iv/price:null;
  V.fit=!(V.ratio!=null&&(V.ratio<0.25||V.ratio>4));
  if(!V.fit){
    V.estimate=V.iv;
    V.fitNote=V.ratio<0.25
      ?`The value methods can't explain this price: it is ${fmt(1/V.ratio,1)}× the $${fmt(V.iv)} estimate. `+(V.impliedG!=null?`To be worth $${fmt(price)}, profit would have to grow about ${pc(V.impliedG)} a year for 5 years (then fade), against ${pc(g1)} assumed here.`:V.impliedNote?`The price would need growth of ${V.impliedNote}.`:"")+" No buy-below price is set, because one this far below the market isn't a usable level."
      :`The estimate ($${fmt(V.iv)}) is over 4× the price. That usually means a data error or a one-off figure, not a bargain. Check the statements before trusting it; no buy-below price is set.`;
    V.notes.unshift(V.fitNote);
    V.buyBelow=null; V.mos=null;
  }
  V.netNet=V.ncav>0&&price<V.ncav*2/3;
  if(V.netNet) V.notes.push(`Graham net-net: price is below two-thirds of net current assets ($${fmt(V.ncav)} a share). Graham bought these only as a diversified group of 30 or more.`);
  if(V.epv!=null&&V.tbvps>0&&V.epv<V.tbvps) V.notes.push("Earnings power is below tangible asset value: the assets earn less than they cost. Look for a catalyst (activist, sale, capacity leaving the industry); growth spending here destroys value (Greenwald §3.4).");
  if(V.franchise) V.notes.push(`Possible franchise: return on tangible capital ${V.assetLight?"is very high (it needs almost no tangible capital)":pc(V.roic)} vs a ${pc(R,1)} cost of capital${V.roicTotal!=null&&Math.abs(V.roicTotal-V.roic)>0.05?` (${pc(V.roicTotal)} if past acquisitions' goodwill is counted)`:""}. Name the moat (captive customers, scale, cost edge, licence) before paying for growth.`+(V.growthValue!=null?` With ${pc(g1,1)} growth for 5 years it is worth about ${fmt(V.multiplier,2)}× earnings power.`:""));
  else if(V.roic!=null&&V.roic<R) V.notes.push(`Return on tangible capital ${pc(V.roic)} is below the ${pc(R,1)} cost of capital: growth would destroy value, so it gets no credit.`);
  else if(V.roic!=null&&g1>0.06) V.notes.push(`Return on tangible capital ${pc(V.roic)} is only a little above the ${pc(R,1)} cost of capital, so its ${pc(g1)} growth gets no credit (Greenwald: growth only adds value inside a franchise).`);
  if(V.fit&&V.impliedG!=null&&V.iv&&price>V.iv*1.1) V.notes.push(`At $${fmt(price)} the market is assuming profit growth of about ${pc(V.impliedG)} a year for 5 years (then fading), vs ${pc(g1)} assumed here.`);
  if(V.graham&&V.epv>0){ const gap=V.graham/V.epv-1; if(Math.abs(gap)>0.5) V.notes.push(`The Graham number ($${fmt(V.graham)}) and earnings power ($${fmt(V.epv)}) disagree by ${pc(Math.abs(gap))}. Treat the value as uncertain.`); }
  if(isFin) V.notes.push("Financial company: Altman Z and working-capital checks don't apply; the balance sheet needs a lender-style review.");
  const agree=[V.epv,V.graham,V.tbvps].filter(x=>x!=null&&x>0);
  V.methodsAbovePrice=agree.filter(x=>x>price).length; V.methodsCount=agree.length;

  /* ---- Lynch category ---- */
  let category;
  const lastNi=N(iA[0]?.net_income), hadProfit=iA.slice(1).some(y=>N(y.net_income)>0);
  if((V.ncav>0&&price<V.ncav)||(V.tbvps>0&&price<0.8*V.tbvps)) category="Asset play";
  else if(lastNi!=null&&lastNi<0&&hadProfit) category="Turnaround";
  else if(cyclical) category="Cyclical";
  else if(cagr!=null&&cagr>0.15) category="Fast grower";
  else if(cagr!=null&&cagr>=0.06) category="Stalwart";
  else category="Slow grower";
  if(cyclical&&F.om!=null&&avgM>0&&F.om>avgM*1.3) flag("Earnings near a cyclical peak","medium",`Operating margin ${pc(F.om,1)} is well above the ${margins.length}-period average of ${pc(avgM,1)}. A low P/E on peak earnings is a trap (Lynch); the value uses the average.`);

  /* ---- forensic checks (Financial Shenanigans §4.2) ---- */
  const days=(a,b)=>a!=null&&b?a/b*91.25:null;
  const q=(i,k)=>{ const inc=iQ[i]; if(!inc) return null; const b=at(bQ,inc.end_date); return b?{rev:N(inc.total_revenue),cogs:N(inc.cost_of_revenue),ar:N(b.total_recv_net),inv:N(b.total_inv),ap:N(b.ap),soft:(N(b.other_cur_assets)||0)+(N(b.other_lt_assets)||0),ta:N(b.total_assets)}:null; };
  const q0=q(0), q4=q(4);
  if(q0&&q4){
    const d0=days(q0.ar,q0.rev), d4=days(q4.ar,q4.rev);
    if(d0!=null&&d4){ const ch=d0/d4-1; const st=ch>0.4?"bad":ch>0.2?"warn":"ok"; metric("Days sales outstanding",`${fmt(d0,0)} days (was ${fmt(d4,0)})`,st,"Ending receivables ÷ quarterly sales. Rising means sales may be pulled forward or hard to collect (EM1/EM2).");
      if(st!=="ok") flag("Customers are taking longer to pay",st==="bad"?"high":"medium",`Days sales outstanding rose from ${fmt(d4,0)} to ${fmt(d0,0)} in a year.`); }
    const i0=days(q0.inv,q0.cogs), i4=days(q4.inv,q4.cogs);
    if(i0!=null&&i4&&q0.inv>0.03*q0.ta){ const ch=i0/i4-1; const st=ch>0.2?"warn":"ok"; metric("Days inventory",`${fmt(i0,0)} days (was ${fmt(i4,0)})`,st,"Inventory ÷ quarterly cost of sales. Rising points to slow sales or obsolete stock (EM4).");
      if(st!=="ok") flag("Inventory building up","medium",`Days of inventory rose from ${fmt(i4,0)} to ${fmt(i0,0)} in a year.`); }
    const p0=days(q0.ap,q0.cogs), p4=days(q4.ap,q4.cogs);
    const cfoPrev=ttm(cQ,"cfo",4), niPrev=ttm(iQ,"net_income",4);
    if(p0!=null&&p4){ const ch=p0/p4-1; const cfoG=F.cfo!=null&&cfoPrev>0?F.cfo/cfoPrev-1:null, niG=F.ni!=null&&niPrev>0?F.ni/niPrev-1:null;
      const swing=ch>0.25&&cfoG!=null&&(niG==null||cfoG>niG+0.1); metric("Days payable",`${fmt(p0,0)} days (was ${fmt(p4,0)})`,swing?"warn":"ok","Payables ÷ quarterly cost of sales. A jump that drives cash-flow growth won't repeat (CF3 swing test).");
      if(swing) flag("Cash flow boosted by paying suppliers later","medium",`Days payable rose from ${fmt(p4,0)} to ${fmt(p0,0)} while operating cash flow grew ${pc(cfoG)} vs profit ${niG!=null?pc(niG):"n/a"}. Treat that part of cash flow as one-off.`); }
    if(q0.ta&&q4.ta){ const s0=q0.soft/q0.ta, s4=q4.soft/q4.ta; const st=s0-s4>0.05?"warn":"ok"; metric("Soft assets",`${pc(s0,1)} of assets (was ${pc(s4,1)})`,st,"Other current and long-term assets. Fast growth can hide capitalised costs (EM4).");
      if(st!=="ok") flag("Soft assets growing","medium",`'Other' assets rose from ${pc(s4,1)} to ${pc(s0,1)} of total assets in a year. Read the footnote for capitalised costs.`); }
  }
  if(cA.length>=3){
    const ni3=sum(cA.slice(0,3).map(y=>N(y.net_income)||0)), cfo3=sum(cA.slice(0,3).map(y=>N(y.cfo)||0));
    if(ni3>0){ const r=cfo3/ni3; const st=r<0.5?"bad":r<0.8?"warn":"ok"; metric("Cash flow ÷ profit (3 years)",pc(r),st,"Operating cash flow over reported profit, summed over three years. Below 100% means profits aren't turning into cash.");
      if(st!=="ok") flag("Profits not turning into cash",st==="bad"?"high":"medium",`Over three years operating cash flow was ${pc(r)} of reported profit (healthy is 100% or more).`);
      else if(r>=1.1) strengths.push("Cash flow exceeds reported profit over three years"); }
    const fcfY=cA.slice(0,3).map(y=>N(y.cfo)+(N(y.capex)||0)); const neg=fcfY.filter(x=>x<0).length;
    metric("Free cash flow (3 years)",fcfY.map(x=>fmtBig(x)).join(" · "),neg>=2?"warn":"ok","Operating cash flow minus capex, newest first.");
    if(neg>=2&&ni3>0) flag("Free cash flow negative while profitable","medium",`Free cash flow was negative in ${neg} of the last 3 years despite reported profits (capitalised costs or heavy reinvestment).`);
  }
  if(iA.length>=2&&cA.length>=2){
    const d0=N(cA[0].dna), d1=N(cA[1].dna), g0=N(at(bA,cA[0].end_date)?.ppe_gross), g1=N(at(bA,cA[1].end_date)?.ppe_gross);
    if(d0&&d1&&g0&&g1){ const r0=d0/g0, r1=d1/g1, ch=r0/r1-1; const st=ch<-0.15?"warn":"ok"; metric("Depreciation rate",`${pc(r0,1)} of gross PP&E (was ${pc(r1,1)})`,st,"A falling rate means asset lives were stretched, which flatters profit (EM4).");
      if(st!=="ok") flag("Depreciating assets more slowly","low",`Depreciation fell from ${pc(r1,1)} to ${pc(r0,1)} of gross property and equipment.`); }
  }
  if(F.gm!=null&&F.gmY!=null){ const d=F.gm-F.gmY; const st=d<-0.05?"bad":d<-0.02?"warn":"ok"; metric("Gross margin",`${pc(F.gm,1)} (was ${pc(F.gmY,1)})`,st,"Shrinking margins often come before bigger problems.");
    if(st!=="ok"){ flag("Gross margin shrinking",st==="bad"?"high":"medium",`Gross margin fell from ${pc(F.gmY,1)} to ${pc(F.gm,1)} in a year.`); weaknesses.push("Gross margin shrinking"); } else if(d>0.02) strengths.push("Gross margin improving"); }
  const ebitPrev=ttm(iQ,"op_income",4);
  if(F.ebit!=null&&ebitPrev>0&&F.revG!=null){ const opG=F.ebit/ebitPrev-1; if(opG-F.revG>0.25&&F.revG<0.05) flag("Profit growing far faster than sales","low",`Operating profit up ${pc(opG)} on sales ${pct(F.revG)}. Check for one-time gains or released reserves (EM3, EM5).`); }
  if(F.sharesG!=null){ const st=F.sharesG>0.08?"bad":F.sharesG>0.03?"warn":"ok"; metric("Share count change (1 year)",pct(F.sharesG),st,"Dilution shrinks each share's slice.");
    if(st!=="ok") flag("Share dilution",st==="bad"?"high":"medium",`Share count up ${pc(F.sharesG,1)} in a year.`); else if(F.sharesG<-0.01) strengths.push(`Buying back shares (count down ${pc(-F.sharesG,1)} in a year)`); }
  /* accruals (Sloan), Piotroski F, Altman Z, Beneish M — standard academic screens [outside the books] */
  const A0=iA[0], A1=iA[1], C0=cA[0], C1=cA[1], B0=A0&&at(bA,A0.end_date), B1=A1&&at(bA,A1.end_date);
  const X={};
  if(A0&&C0&&B0&&B1){
    const avgTA=(N(B0.total_assets)+N(B1.total_assets))/2;
    X.accruals=(N(A0.net_income)-N(C0.cfo))/avgTA;
    const st=X.accruals>0.1?"warn":"ok"; metric("Accruals ratio",pc(X.accruals,1),st,"(Profit − operating cash flow) ÷ average assets. High accruals predict weaker future returns [outside the books: Sloan].");
    if(st!=="ok") flag("High accruals","medium",`Profit exceeded operating cash flow by ${pc(X.accruals,1)} of assets last year.`);
  }
  if(A0&&A1&&C0&&B0&&B1){
    const roa=(i,b)=>N(i.net_income)/N(b.total_assets);
    const lev=b=>(N(b.total_lt_debt)||0)/N(b.total_assets), cr=b=>N(b.total_cur_assets)/N(b.total_cur_liab);
    const gmA=i=>N(i.gross_profit)/N(i.total_revenue), turn=(i,b)=>N(i.total_revenue)/N(b.total_assets);
    const t=[roa(A0,B0)>0,N(C0.cfo)>0,roa(A0,B0)>roa(A1,B1),N(C0.cfo)>N(A0.net_income),lev(B0)<=lev(B1),cr(B0)>cr(B1),!(N(A0.diluted_avg_shares)>N(A1.diluted_avg_shares)*1.005),gmA(A0)>gmA(A1),turn(A0,B0)>turn(A1,B1)];
    X.piotroski=t.filter(Boolean).length;
    metric("Piotroski F-score",`${X.piotroski}/9`,X.piotroski>=7?"ok":X.piotroski<=3?"bad":"warn","Nine yes/no tests of profit, cash, leverage and efficiency. 7+ strong, 3 or less weak [outside the books].");
    if(X.piotroski<=2) flag("Weak Piotroski score","medium",`Only ${X.piotroski} of 9 financial-health tests passed.`);
    if(!isFin){
      const S0=N(A0.total_revenue),S1=N(A1.total_revenue),AR0=N(B0.total_recv_net)||0,AR1=N(B1.total_recv_net)||0,TA0=N(B0.total_assets),TA1=N(B1.total_assets);
      const PPE0=N(B0.ppe_net)||0,PPE1=N(B1.ppe_net)||0,CA0=N(B0.total_cur_assets),CA1=N(B1.total_cur_assets),Dp0=N(C0.dna),Dp1=N(C1?.dna);
      const SG0=N(A0.sga_exp),SG1=N(A1.sga_exp),CL0=N(B0.total_cur_liab),CL1=N(B1.total_cur_liab),LD0=N(B0.total_lt_debt)||0,LD1=N(B1.total_lt_debt)||0;
      if(S0&&S1&&TA0&&TA1&&CA0&&CA1&&AR1>0){
        const DSRI=(AR0/S0)/(AR1/S1), GMI=gmA(A1)/gmA(A0), AQI=(1-(CA0+PPE0)/TA0)/(1-(CA1+PPE1)/TA1), SGI=S0/S1;
        const DEPI=Dp0&&Dp1?(Dp1/(Dp1+PPE1))/(Dp0/(Dp0+PPE0)):1, SGAI=SG0&&SG1?(SG0/S0)/(SG1/S1):1, LVGI=((CL0+LD0)/TA0)/((CL1+LD1)/TA1), TATA=(N(A0.net_income)-N(C0.cfo))/TA0;
        X.beneish=-4.84+0.92*DSRI+0.528*GMI+0.404*AQI+0.892*SGI+0.115*DEPI-0.172*SGAI+4.679*TATA-0.327*LVGI;
        if(Number.isFinite(X.beneish)){ const st=X.beneish>-1.78?"warn":"ok"; metric("Beneish M-score",fmt(X.beneish,2),st,"Eight-ratio earnings-manipulation screen; above −1.78 resembles past manipulators [outside the books].");
          if(st!=="ok") flag("Beneish M-score in the manipulator zone","medium",`M-score ${fmt(X.beneish,2)} is above −1.78. Read the revenue and receivables footnotes before trusting the earnings.`); } else delete X.beneish;
      }
    }
  }
  if(!isFin&&b0&&ta&&tl&&mcap&&F.rev){
    const re=N(b0.retained_earnings)||0;
    X.altmanZ=1.2*((ca-cl)/ta)+1.4*(re/ta)+3.3*((F.ebit||0)/ta)+0.6*(mcap/tl)+1.0*(F.rev/ta);
    const st=X.altmanZ<1.8?"bad":X.altmanZ<3?"warn":"ok"; metric("Altman Z-score",fmt(X.altmanZ,2),st,"Bankruptcy-risk score: under 1.8 distress, 1.8–3 grey zone, over 3 safe [outside the books].");
    if(st==="bad") flag("Altman Z in the distress zone",F.fcf!=null&&F.fcf<0?"high":"medium",`Z-score ${fmt(X.altmanZ,2)} is below 1.8.`);
  }
  if(F.curRatio!=null&&F.curRatio<0.8&&!isFin) flag("Tight short-term liquidity","medium",`Current assets cover ${fmt(F.curRatio,2)}× the bills due within a year.`);
  /* coverage on the last four quarters, with one-off charges added back (impairments aren't paid in cash) */
  const q4i=iQ.slice(0,4), useQ=q4i.length===4;
  const src=useQ?q4i:(A0?[A0]:[]);
  /* interest actually paid (cash flow statement); the net non-operating line nets in investment gains */
  const cq4=cQ.slice(0,4), paid=(cq4.length===4&&useQ?cq4:(cA[0]?[cA[0]]:[])).map(x=>N(x.interest_paid));
  const intExp=paid.length&&paid.every(v=>v!=null)?sum(paid):-sum(src.map(x=>N(x.inter_inc_expse_net_non_oper)||0));
  const ebitAdj=src.length?sum(src.map(x=>(N(x.op_income)||0)+Math.max(0,N(x.unusual_expense_income)||0))):null;
  X.coverage=intExp>0&&ebitAdj!=null?ebitAdj/intExp:null;
  if(X.coverage!=null&&!isFin){ const st=X.coverage<1?"bad":X.coverage<2?"warn":"ok"; metric("Interest coverage",fmt(X.coverage,1)+"×",st,"Last four quarters of operating profit (before one-off charges) ÷ interest paid. Under 2× is fragile.");
    if(st!=="ok") flag("Thin interest coverage",st==="bad"?"high":"medium",`Operating profit covers net interest only ${fmt(X.coverage,1)}×.`); }
  X.grahamStrength=!isFin&&F.curRatio!=null&&ca!=null?(F.curRatio>=1.5&&(N(b0?.total_lt_debt)||0)<=1.1*(ca-cl)):null;
  if(X.grahamStrength===true) strengths.push("Passes Graham's financial-strength test (current ratio ≥ 1.5, long-term debt ≤ 110% of working capital)");
  else if(X.grahamStrength===false) weaknesses.push("Fails Graham's financial-strength test (current ratio ≥ 1.5 and long-term debt ≤ 110% of working capital)");
  if(F.revG!=null){ if(F.revG>0.1) strengths.push(`Revenue up ${pc(F.revG)} from a year ago`); else if(F.revG<0) weaknesses.push(`Revenue down ${pc(-F.revG)} from a year ago`); }
  if(F.om!=null){ if(F.om>0.2) strengths.push(`Strong operating margin (${pc(F.om)})`); else if(F.om<0) weaknesses.push(`Losing money on operations (margin ${pc(F.om)})`); }
  if(F.fcf!=null&&F.fcf<0) weaknesses.push(`Burned ${fmtBig(-F.fcf)} of free cash over the last year`);
  if(mcap&&F.netCash<-0.3*mcap) weaknesses.push("Debt is large relative to the company's value");

  /* ---- owners and neglect (Greenblatt §3.4, Skin in the Game §9) ---- */
  /* an empty list means no insider trades in the year asked for, not missing data */
  const insRaw=asJson(D.ins), insRows=findArr(insRaw,x=>x&&x.transaction_date&&x.acquisition_or_disposal)||(Array.isArray(insRaw?.data)?[]:null);
  const O={source:insRows?"Alpha Vantage (SEC Form 4)":null};
  if(insRows){ const cut=new Date(Date.now()-365*864e5).toISOString().slice(0,10); const yrRows=insRows.filter(r=>r.transaction_date>=cut);
    const buys=yrRows.filter(r=>r.acquisition_or_disposal==="P"), sells=yrRows.filter(r=>r.acquisition_or_disposal==="S");
    const val=r=>(N(r.shares)||0)*(N(r.share_price)||0);
    O.buyers=[...new Set(buys.map(r=>r.executive))]; O.buyValue=sum(buys.map(val)); O.sellers=[...new Set(sells.map(r=>r.executive))]; O.sellValue=sum(sells.map(val));
    O.lastBuy=buys.map(r=>r.transaction_date).sort().pop()||null; }
  const instTxt=D.inst?JSON.stringify(D.inst):""; const im=instTxt.match(/total_institutional_ownership_percentage\\?":\s*\\?"([\d.]+)%/);
  O.instPct=im?N(im[1])/100:null;
  O.analysts=rt?N(rt.number):null;
  O.neglected=(O.analysts!=null&&O.analysts<5)||(O.instPct!=null&&O.instPct<0.4);
  let ownersScore=null;
  if(O.buyers||O.instPct!=null||O.analysts!=null){
    ownersScore=O.buyers?(O.buyers.length>=2?90:O.buyers.length===1?70:O.sellers.length?45:50):50;
    if(O.neglected) ownersScore+=10; ownersScore=clamp(ownersScore); }
  if(O.buyers?.length>=2) strengths.push(`${O.buyers.length} insiders bought shares on the open market in the last year`);

  /* ---- scores and verdict ---- */
  const high=flags.filter(f=>f.severity==="high").length, med=flags.filter(f=>f.severity==="medium").length, low=flags.filter(f=>f.severity==="low").length;
  const mosScore=V.mos==null||!V.fit?null:Math.round(clamp(40+V.mos*120));
  let forensicScore=100-25*high-12*med-4*low; if(X.piotroski!=null) forensicScore+=(X.piotroski-5)*4; forensicScore=Math.round(clamp(forensicScore));
  const st=[];
  if(X.altmanZ!=null) st.push(X.altmanZ>=3?85:X.altmanZ>=1.8?55:15);
  if(F.curRatio!=null&&!isFin) st.push(F.curRatio>=1.5?80:F.curRatio>=1?55:25);
  if(X.grahamStrength!=null) st.push(X.grahamStrength?80:40);
  if(X.coverage!=null) st.push(X.coverage>=5?85:X.coverage>=2?55:20);
  if(cA.length>=3) st.push(cA.slice(0,3).filter(y=>N(y.cfo)+(N(y.capex)||0)>0).length/3*100);
  if(mcap) st.push(F.netCash>0?80:F.netCash>-0.2*mcap?55:25);
  const strengthScore=st.length?Math.round(mean(st)):null;
  const vs={mos:mosScore,forensic:forensicScore,strength:strengthScore,price:priceScore,owners:ownersScore};
  const Wk=Object.entries(W).filter(([k])=>vs[k]!=null);
  const total=sum(Wk.map(([k,w])=>vs[k]*w))/sum(Wk.map(([,w])=>w));
  let verdict, why;
  if(high>=2){ verdict="AVOID"; why=`${high} serious red flags`; }
  else if(V.iv==null){ verdict="AVOID"; why="Earnings and assets don't support a value"; }
  else if(!V.fit){ verdict="WATCH"; why=V.ratio<0.25?"Value methods can't explain this price":"Estimate looks too good: check the data"; }
  else if(X.altmanZ!=null&&X.altmanZ<1.8&&F.fcf!=null&&F.fcf<0){ verdict="AVOID"; why="Distress-zone balance sheet and burning cash"; }
  else if(total<35){ verdict="AVOID"; why="Weak on value, quality and strength together"; }
  else if(V.mos>=REQ_MOS&&high===0&&total>=55){ verdict="BUY"; why=`Price is ${pc(V.mos)} below estimated value`; }
  else { verdict="WATCH"; why=V.mos<REQ_MOS?`Needs a ${pc(REQ_MOS)} margin of safety; buy below $${fmt(V.buyBelow)}`:high?"A serious red flag needs checking first":"Mixed quality"; }
  const dropTxt=newsDrop?`Fell ${pc(-newsDrop.pct)} in one day on ${newsDrop.date}`:null;
  if(verdict==="BUY"&&newsDrop){ verdict="WATCH"; why=`${dropTxt}: wait 2–4 weeks for the drift to settle, then re-check the value`; }
  const legacy={BUY:"BUY",WATCH:"HOLD",AVOID:"SELL"}[verdict];
  let confidence=45+(V.methodsCount>=2&&(V.methodsAbovePrice===0||V.methodsAbovePrice===V.methodsCount)?10:0)+(iA.length>=5?10:0)+(bQ.length>=9?5:0)-missing.length*5;
  if(X.piotroski!=null&&(X.piotroski>=7||X.piotroski<=2)) confidence+=5;
  if(!V.fit) confidence=Math.min(confidence,35);
  confidence=Math.round(clamp(confidence,30,85));
  /* exits (Skin in the Game §9 working rule, NMW §3.3) */
  /* REALISTIC ENTRY. The value buy-below (value × 0.67) is a bargain test and for most stocks sits far below any price
     the stock will reach. So the plan's entry is the value line only when it is within reach (at or above 80% of the
     price); otherwise it is the nearest chart support at least one normal day's move (1 ATR) under the price and no more
     than 20% under it: the 20-, 50- or 200-day average or the 60-day low, set 0.5% above the level so a touch fills.
     With no such level, 1.5 ATR under the price. Chart entries get a chart stop (2 ATR, kept 6-15% under the entry) and
     a target at estimated value when that is 15%+ above, else 2× the risk; time stop 6 months. */
  const atrV=atr||price*0.02, floorE=price*0.80;
  let entry, entryType, entryBasis;
  if(V.buyBelow!=null&&V.buyBelow>=price){ entry=price; entryType="value"; entryBasis="Price is already below the value buy-below line"; }
  else{
    const cands=[["20-day average",s20],["50-day average",s50],["200-day average",s200],["60-day low (support)",lo60]]
      .filter(([,v])=>v!=null&&v<=price-atrV&&v>=floorE).sort((a,b)=>b[1]-a[1]);
    if(cands.length){ entry=cands[0][1]*1.005; entryBasis="Pullback to the "+cands[0][0]+" ($"+fmt(cands[0][1])+")"; }
    else{ entry=Math.max(price-1.5*atrV,floorE); entryBasis="Pullback of 1.5× a normal day's move (no chart support within 20%)"; }
    entryType="chart";
    if(V.buyBelow!=null&&V.buyBelow>=floorE&&V.buyBelow>entry){ entry=V.buyBelow; entryType="value"; entryBasis="Value buy-below line (within reach of the price)"; }
  }
  entry=Math.round(entry*100)/100;
  let stop, stopBasis, target, targetBasis, timeStop;
  if(entryType==="value"){
    /* disaster insurance only (Chan): wider than the stock's worst past fall, never closer than 25% */
    const stopPct=Math.max(0.25,worstDD+0.05);
    stop=Math.max(entry*(1-stopPct),0.01); stopBasis=`Disaster stop ${pc(stopPct)} below entry: wider than the stock's worst fall in the last ${ddMonths} months (${pc(worstDD)}), so normal swings don't shake you out`;
    target=V.iv; targetBasis="Sell or trim when price reaches estimated value"; timeStop=18;
  }else{
    stop=Math.min(Math.max(entry-2*atrV,entry*0.85),entry*0.94); stopBasis="Chart stop: 2× a normal day's move under the entry (kept 6–15% under it)";
    if(V.fit&&V.iv!=null&&V.iv>=entry*1.15){ target=V.iv; targetBasis="Sell or trim at estimated value"; }
    else{ target=entry+2*(entry-stop); targetBasis="Twice the risk taken (no value target above the entry)"; }
    timeStop=6;
  }
  stop=Math.round(stop*100)/100; target=target!=null?Math.round(target*100)/100:null;
  const exitPlan={entry, entryType, entryBasis, entryDist:entry/price-1, target, targetBasis, stop, stopBasis, timeStopMonths:timeStop,
    thesisBreak:["A new serious forensic flag, restatement, auditor change or late filing","Operating margin falls below the worst of the last five years ("+(minM!=null?pc(minM,1):"n/a")+")",entryType==="value"?"Value re-check shows the margin of safety gone without the price rising":"Price closes below the stop: the pullback turned into a breakdown"]};
  if(verdict==="WATCH"&&V.mos!=null&&V.mos<REQ_MOS) why=entryType==="value"?`Needs a ${pc(REQ_MOS)} margin of safety; buy below $${fmt(V.buyBelow)} (${pct(entry/price-1)} from here)`:`Not a bargain; realistic entry $${fmt(entry)} (value line $${fmt(V.buyBelow)})`;
  else if(verdict==="WATCH"&&!V.fit) why=`Value methods can't explain this price; chart entry $${fmt(entry)}`;
  /* legacy scores kept for the Options Desk worker */
  /* old v1 formulas, unchanged in meaning (the Options Desk worker reads them) */
  let fundLegacy=null; if(F.revG!=null&&iQ.length>=5){ const sc=[]; const add=(v,w=1)=>sc.push([clamp(v),w]);
    add(50+F.revG*250,1.5); add((F.om||0)*250,1); if(F.gm!=null&&F.gmY!=null) add(50+(F.gm-F.gmY)*1000,.7);
    if(F.cfo!=null&&F.ni){ const r=F.cfo/F.ni; add(r>=1?85:r>=.8?60:25,1); } if(F.fcf!=null) add(F.fcf>0?80:20,1);
    if(F.sharesG!=null) add(F.sharesG<=0?80:F.sharesG<.02?55:20,.6); if(mcap) add(F.netCash>0?80:F.netCash>-.2*mcap?55:25,.8);
    fundLegacy=Math.round(sum(sc.map(([v,w])=>v*w))/sum(sc.map(([,w])=>w))); }
  let valuLegacy=null; { const sc=[]; const pe=N(s.pe_ratio);
    if(pe!=null&&pe>0) sc.push(clamp(100-pe/(Math.max(F.revG??.05,.02)*100)*25)); if(F.fcf!=null&&mcap) sc.push(clamp(F.fcf/mcap*1500));
    if(tg&&N(tg.median)) sc.push(clamp(50+(N(tg.median)/price-1)*250)); if(sc.length) valuLegacy=Math.round(mean(sc)); }
  const r6=ret(126);
  const techLegacy=Math.round(mean([s50&&price>s50?75:30,...(s200?[price>s200?75:25]:[]),...(s50&&s200?[s50>s200?70:30]:[]),...(r6!=null?[clamp(50+r6*150)]:[]),...(rsi!=null?[rsi>75?35:rsi<30?40:rsi>=50?70:45]:[]),macdHist>0?65:40]));
  let senti=null, analystView="";
  if(rt&&N(rt.number)){ const n=N(rt.number), b=(N(rt.strong_buy)||0)+(N(rt.buy)||0), sl=(N(rt.sell)||0)+(N(rt.under_perform)||0); senti=clamp(Math.round(30+70*(b/n)-40*(sl/n)));
    analystView=`${n} analysts: ${b} buy, ${N(rt.hold)||0} hold, ${sl} sell.`+(tg&&N(tg.median)?` Median target $${fmt(tg.median)} (${pct(N(tg.median)/price-1)} from here). Shown for context only; it doesn't affect the score.`:" Shown for context only."); }
  const trend=s50&&s200?(price>s50&&s50>s200?"Uptrend":price<s50&&s50<s200?"Downtrend":"Mixed / sideways"):"Not enough history";
  if(rsi>70) notes.push(`RSI ${fmt(rsi,0)}: stretched after a strong run.`); else if(rsi<30) notes.push(`RSI ${fmt(rsi,0)}: oversold; wait for the selling to stop.`);
  const nextE=al?.start_date||null;
  const advDollar=v20*price;
  /* pre-buy checklist (NMW §11.B, Greenwald §3.6) */
  const daysToE=nextE?Math.round((new Date(nextE)-Date.now())/864e5):null;
  const checklist=[
    {item:"Edge: why is the market wrong, in one sentence?",status:"you",note:O.neglected?"Neglected: few analysts or low institutional ownership.":ret(126)!=null&&ret(126)<-0.25?`Sold off ${pc(-ret(126))} in six months.`:"Write it down before buying."},
    {item:"Thesis-break condition written down",status:"auto",note:exitPlan.thesisBreak[1]},
    {item:"Downside sized: loss to bear value within 1–2% of the account",status:"auto",note:`Bear value $${fmt(V.bear)} (${V.bearBasis.toLowerCase()}). See sizing below.`},
    {item:"Binary event ahead",status:daysToE!=null&&daysToE>=0&&daysToE<=30?"warn":"ok",note:nextE?`Earnings ${nextE}${daysToE!=null&&daysToE>=0?` (in ${daysToE} days)`:""}.`:"No earnings date found."},
    {item:"Liquidity: could you exit in a few days?",status:advDollar<1e6?"warn":"ok",note:`About $${fmtBig(advDollar)} trades a day.`},
    {item:"Catalyst: what makes the market see the value?",status:"you",note:"Full analysis looks for one in filings and news."},
    {item:"Price behaviour: has the selling stopped?",status:priceScore>=75?"ok":"warn",note:priceState+"."},
    {item:"No big bad-news drop in the last two weeks",status:newsDrop?"warn":"ok",note:newsDrop?`${dropTxt}. Drops on real news tend to keep drifting; wait 2–4 weeks, then re-check the value (Chan).`:`No one-day fall of ${pc(dropLim)} or more in the last 10 sessions.`},
    {item:"Why is this available to me? Forced seller or broken business?",status:"you",note:(new Date().getMonth()>=9&&ret(251)!=null&&ret(251)<-0.3?`Tax-loss season and down ${pc(-ret(251))} over the year: some selling may be for tax reasons, not the business. `:"")+"Selling by someone who needs cash (fund redemptions, index removal, spinoff, tax-loss season) tends to reverse; a change in the business doesn't. Compare with value traps: cheap after a restatement, on 'adjusted' numbers, or at a cyclical peak."},
    {item:"No leverage, and you'd stay calm if it halved",status:"you",note:"Sleep test."}];
  const thesis=verdict==="BUY"?`Trades at $${fmt(price)} against an estimated value of $${fmt(V.iv)} (${V.ivMethod.toLowerCase()}), a ${pc(V.mos)} margin of safety. ${flags.length?`${flags.length} item${flags.length>1?"s":""} to check in the forensic section.`:"No forensic red flags found."}`
    :!V.fit?`${V.ratio<0.25?`Priced at $${fmt(price)}, about ${fmt(1/V.ratio,1)}× the $${fmt(V.iv)} value estimate, so a value buy price isn't meaningful here. A realistic entry from the chart is $${fmt(entry)} (${exitPlan.entryBasis.toLowerCase()}).`:`The $${fmt(V.iv)} estimate is over 4× the $${fmt(price)} price, which points to a data problem rather than a bargain.`} ${V.impliedG!=null?`The price assumes about ${pc(V.impliedG)} a year profit growth for 5 years.`:""}`
    :verdict==="WATCH"?`Estimated value $${fmt(V.iv)} vs price $${fmt(price)} (margin of safety ${V.mos!=null?pc(V.mos):"n/a"}). ${entryType==="value"?`Buy below $${fmt(V.buyBelow)} (${pct(exitPlan.entryDist)} from here), which is within reach`:`A realistic entry is $${fmt(entry)} (${pct(exitPlan.entryDist)} from here, ${exitPlan.entryBasis.toLowerCase()}); the full value bargain is below $${fmt(V.buyBelow)}`}${high?". Clear the serious red flag first":""}.${newsDrop?` ${dropTxt}: wait 2–4 weeks before buying, then re-check the value.`:""}`
    :`Avoid for now: ${why.toLowerCase()}.`;
  const summary=[`${name} is ${/^[aeiou]/i.test(category)?"an":"a"} ${category.toLowerCase()} trading at $${fmt(price)}${ret(252)!=null?`, ${pct(ret(252))} over the past year`:""}.`,
    F.rev?`Sales over the last year were $${fmtBig(F.rev)}${F.revG!=null?` (${pct(F.revG)})`:""} with a ${F.om!=null?pc(F.om,1):"n/a"} operating margin against a ${avgM!=null?pc(avgM,1):"n/a"} average over ${margins.length} periods.`:"Company financials weren't available (common for ETFs), so no value can be estimated.",
    V.iv?`Earnings power is about $${fmt(V.epv)} a share at a ${pc(R,1)} cost of capital${V.growthValue!=null?`, $${fmt(V.growthValue)} with growth`:""}; tangible book is $${fmt(V.tbvps)} and the Graham number $${fmt(V.graham)}.`:"",
    `Price behaviour: ${priceState.toLowerCase()}.`,
    "This quick check reads Webull numbers only; run the full analysis for SEC filings, walk-away checks and news before acting."].filter(Boolean).join(" ");
  const quote={companyName:name,price,change:N(s.change),changeRatio:N(s.change_ratio),marketCap:mcap,pe:N(s.pe_ratio),ps:N(s.ps_ratio),pb:N(s.pb_ratio),epsTtm:N(s.eps_ttm),divYield:N(s.yield),high52:N(s.fifty_two_wk_high),low52:N(s.fifty_two_wk_low),asOf:new Date(N(s.quote_time)||Date.now()).toISOString()};
  const tech={rsi14:rsi,macdHist,atr14:atr,sma20:s20,sma50:s50,sma200:s200,annVol60d:vol60,ret1m:ret(21),ret3m:ret(63),ret6m:ret(126),ret1y:ret(251),volRatio20v50:v50?v20/v50:null,low60:lo60,high60:hi60,lastCross,advDollar};
  return {quote,tech,chart,missing,fin:{currency:cur,rev:F.rev,ebit:F.ebit,ni:F.ni,annual:iA.slice(0,5).map(y=>({end:y.end_date,rev:N(y.total_revenue),op:N(y.op_income),ni:N(y.net_income)}))},
    analysis:{companyName:name,verdict,verdictWhy:why,rating:legacy,confidence,horizon:entryType==="value"?"Until value is reached (time stop 18 months)":"Swing from a pullback (time stop 6 months)",thesis,summary,
      valueScores:vs,valueTotal:Math.round(total),
      scores:{fundamental:fundLegacy,valuation:valuLegacy,technical:techLegacy,sentiment:senti},
      priceTargets:tg&&N(tg.median)?{bull:N(tg.high),base:N(tg.median),bear:N(tg.low)}:{bull:price*(1+vol60),base:price,bear:price*(1-vol60)},
      valueTargets:V.fit?{bull:V.bull,base:V.iv,bear:V.bear}:null, intrinsicValue:V.fit?V.iv:null, buyBelow:V.buyBelow, entryPrice:verdict==="AVOID"?null:entry, entryType, entryBasis, marginOfSafety:V.mos, valueFit:V.fit,
      value:V, newsDrop, worstDrop:worstDD, category:{name:category,note:CAT_NOTES[category],cyclical,cagr,special:null},
      forensic:{metrics,...X}, owners:O, priceBehaviour:{state:priceState,signals:pb}, exitPlan, checklist,
      fundamentals:{overview:industry?`${name} · ${industry}`:"",strengths,weaknesses,valuation:N(s.pe_ratio)?`P/E ${fmt(s.pe_ratio,1)}, P/S ${fmt(s.ps_ratio,1)}${F.fcf!=null&&mcap?`, free-cash-flow yield ${pc(F.fcf/mcap,1)}`:""}.`:""},
      technicals:{trend,momentum:`MACD ${macdHist>0?"positive":"negative"}, RSI ${fmt(rsi,0)}, 6-month return ${pct(ret(126))}.`,support:[`$${fmt(lo60)} (60-day low)`].concat(s200&&s200<price?[`$${fmt(s200)} (200-day)`]:[]),resistance:[`$${fmt(hi60)} (60-day high)`].concat(N(s.fifty_two_wk_high)?[`$${fmt(s.fifty_two_wk_high)} (52-week high)`]:[]),notes},
      redFlags:flags,walkAway:[],news:[],recentEvents:nextE?[{date:nextE,event:"Next earnings report",impact:al?.eps_est?`EPS estimate ${fmt(al.eps_est)} vs ${fmt(al.eps_ly)} a year ago`:""}]:[],
      analystView,catalysts:nextE?[`Earnings on ${nextE}`]:[],risks:flags.map(f=>f.issue),
      whatChangesTheCall:[newsDrop&&verdict!=="AVOID"?`2–4 weeks passing after the ${newsDrop.date} drop with the value intact`:"",verdict!=="AVOID"&&entry<price?`Price pulling back to $${fmt(entry)} (the realistic entry)`:"",V.buyBelow&&V.buyBelow<entry?`Price falling below $${fmt(V.buyBelow)} (the value buy-below)`:"",...exitPlan.thesisBreak.slice(0,2),"Filings and news the quick check can't see: run the full analysis"].filter(Boolean)}};
}
if(typeof module!=="undefined") module.exports={engine,findArr,N};
